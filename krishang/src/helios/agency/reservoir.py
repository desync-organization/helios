import json
import re
from pathlib import Path
from typing import Any

import yaml

from helios.contracts import CanonicalEvent
from helios.contracts.adapter import AdapterManifest
from helios.contracts.plan import SpawnRequest
from helios.experts.base import ExpertHandler, deterministic_expert
from helios.experts.model import model_expert
from helios.models import ModelManager

from .registry import AgentDefinition


class AgentReservoir:
    """Single source of truth for discoverable and executable Helios agents."""

    def __init__(self, definitions: list[AgentDefinition], model_manager: ModelManager,
                 *, model_backed: bool, snapshot_path: Path | None = None,
                 catalog_root: Path | None = None) -> None:
        self.model_manager = model_manager
        self.model_backed = model_backed
        self.snapshot_path = snapshot_path
        self.catalog_root = (catalog_root or Path.cwd()).resolve()
        self._active: dict[str, AgentDefinition] = {}
        self._templates: dict[str, AgentDefinition] = {}
        self._handlers: dict[str, ExpertHandler] = {}
        self.revision = 1
        for definition in definitions:
            self._validate_model_binding(definition)
            self._add_definition(definition)
        self._load_snapshot()

    @classmethod
    def from_yaml(cls, path: Path, model_manager: ModelManager, *, model_backed: bool,
                  snapshot_path: Path | None = None) -> "AgentReservoir":
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != "1.0" or not isinstance(payload.get("agents"), list):
            raise ValueError("agent reservoir catalog must use schemaVersion 1.0")
        definitions = [AgentDefinition.model_validate(item) for item in payload["agents"]]
        names = [item.name for item in definitions]
        if len(names) != len(set(names)):
            raise ValueError("agent reservoir contains duplicate names")
        return cls(definitions, model_manager, model_backed=model_backed, snapshot_path=snapshot_path,
                   catalog_root=path.resolve().parent)

    def _add_definition(self, definition: AgentDefinition) -> None:
        target = self._templates if definition.status == "template" else self._active
        if definition.name in self._active or definition.name in self._templates:
            raise ValueError(f"duplicate agent definition: {definition.name}")
        target[definition.name] = definition
        if definition.status == "active" and definition.handler_key:
            self._handlers[definition.name] = self._make_handler(definition)

    def _validate_model_binding(self, definition: AgentDefinition) -> None:
        if definition.model_id == "deterministic":
            return
        configured = self.model_manager.registry.get(definition.model_role)
        if not configured:
            raise ValueError(f"agent {definition.name} references unknown model role {definition.model_role}")
        if configured.model_id != definition.model_id:
            raise ValueError(
                f"agent {definition.name} model mismatch: catalog={definition.model_id}, runtime={configured.model_id}"
            )

    def _make_handler(self, definition: AgentDefinition) -> ExpertHandler:
        if self.model_backed and definition.handler_key not in {"intent", "integration"}:
            adapter = None
            if definition.adapter_id:
                adapter = {"id": definition.adapter_id, "version": definition.adapter_version, "scale": 1.0}
            return model_expert(self.model_manager, definition.name, role_override=definition.model_role,
                                adapter=adapter)
        return deterministic_expert

    def _verify_adapter_binding(self, definition: AgentDefinition) -> None:
        if not self.model_backed or not definition.adapter_id:
            return
        if not definition.adapter_manifest:
            raise ValueError(f"agent {definition.name} has no promoted adapter manifest")
        manifest_path = (self.catalog_root / definition.adapter_manifest).resolve()
        if not manifest_path.is_file():
            raise ValueError(f"promoted adapter manifest is missing for {definition.name}: {manifest_path}")
        manifest = AdapterManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        configured = self.model_manager.registry[definition.model_role]
        if (manifest.adapter_id != definition.adapter_id
                or manifest.adapter_version != definition.adapter_version
                or manifest.base_model_id != definition.model_id
                or definition.name not in manifest.target_roles):
            raise ValueError(f"promoted adapter manifest does not match agent {definition.name}")
        if not configured.model_path:
            raise ValueError(f"base model path is not configured for {definition.name}")
        manifest.verify(configured.model_path)

    def _load_snapshot(self) -> None:
        if not self.snapshot_path or not self.snapshot_path.is_file():
            return
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        for item in payload.get("spawned", []):
            definition = AgentDefinition.model_validate(item)
            self._validate_model_binding(definition)
            self._verify_adapter_binding(definition)
            if definition.name in self._templates:
                self._templates.pop(definition.name)
            if definition.name not in self._active:
                self._add_definition(definition)

    def _persist(self) -> None:
        if not self.snapshot_path:
            return
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        spawned = [item.model_dump(mode="json") for item in self._active.values() if item.origin == "spawned"]
        temporary = self.snapshot_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"schemaVersion": "1.0", "spawned": spawned}, indent=2), encoding="utf-8")
        temporary.replace(self.snapshot_path)

    def handlers(self) -> dict[str, ExpertHandler]:
        return dict(self._handlers)

    def handler(self, name: str) -> ExpertHandler | None:
        return self._handlers.get(name)

    def executable_names(self) -> set[str]:
        return set(self._handlers)

    def planner_catalog(self) -> list[dict[str, Any]]:
        definitions = [*self._active.values(), *self._templates.values()]
        return [
            {
                "name": item.name,
                "version": item.version,
                "capability": item.capability,
                "description": item.description,
                "modelId": item.model_id,
                "tools": item.tools,
                "modes": item.modes,
                "produces": item.produces,
                "maxTokens": item.max_tokens,
                "maxSeconds": item.max_seconds,
                "origin": item.origin,
                "status": item.status,
                "spawnable": item.status == "template",
                "adapterId": item.adapter_id,
                "reservoirRevision": self.revision,
            }
            for item in sorted(definitions, key=lambda value: value.name)
        ]

    def list(self) -> list[AgentDefinition]:
        return sorted([*self._active.values(), *self._templates.values()], key=lambda item: item.name)

    def get(self, name: str) -> AgentDefinition:
        return self._active.get(name) or self._templates[name]

    def resolve(self, capability: str, *, mode: str, required_tools: set[str] | None = None) -> AgentDefinition | None:
        words = set(capability.lower().replace("-", " ").split())
        required_tools = required_tools or set()
        candidates: list[tuple[int, AgentDefinition]] = []
        for definition in self.list():
            if mode not in definition.modes or not required_tools <= set(definition.tools):
                continue
            haystack = set(f"{definition.name} {definition.capability} {definition.description}".lower().replace("-", " ").split())
            score = len(words & haystack)
            if score:
                candidates.append((score, definition))
        return max(candidates, default=(0, None), key=lambda item: item[0])[1]

    def spawn(self, request: SpawnRequest, *, run_id: str, budget_tokens: int,
              budget_seconds: float, allowed_tools: set[str]) -> tuple[AgentDefinition, CanonicalEvent]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-_]*", request.name):
            raise ValueError("spawned agent name is invalid")
        if request.name in self._active:
            raise ValueError(f"agent is already active or paused: {request.name}")
        template = self._templates.get(request.name)
        requested_tools = set(request.tools)
        if requested_tools - allowed_tools:
            raise PermissionError("spawn requested tools outside node policy")
        if template:
            if request.base_model_id != template.model_id:
                raise ValueError("spawn base model does not match the reviewed template")
            self._verify_adapter_binding(template)
            if requested_tools - set(template.tools):
                raise PermissionError("spawn requested tools outside template grants")
            definition = template.model_copy(update={
                "status": "active", "origin": "spawned", "spawned_by": run_id,
                "tools": sorted(requested_tools),
                "max_tokens": min(template.max_tokens, budget_tokens),
                "max_seconds": min(template.max_seconds, budget_seconds),
            })
            self._templates.pop(request.name)
        else:
            matching_role = next((role for role, model in self.model_manager.registry.items()
                                  if model.model_id == request.base_model_id), None)
            if not matching_role:
                raise ValueError("spawn requested a base model outside the runtime registry")
            definition = AgentDefinition(
                name=request.name, capability=request.capability,
                description=f"Dynamically spawned specialist for {request.capability}",
                model_id=request.base_model_id, model_role=matching_role, persona=f"Specialize in {request.capability}.",
                handler_key=request.name, tools=sorted(requested_tools), max_tokens=min(8000, budget_tokens),
                max_seconds=min(120, budget_seconds), origin="spawned", spawned_by=run_id,
            )
        self._active[definition.name] = definition
        self._handlers[definition.name] = self._make_handler(definition)
        self.revision += 1
        self._persist()
        event = CanonicalEvent(type="agent_spawned", run_id=run_id, payload={
            "name": definition.name, "version": definition.version, "origin": "spawned",
            "capability": definition.capability, "modelId": definition.model_id,
            "adapterId": definition.adapter_id, "tools": definition.tools,
        })
        return definition, event

    def set_status(self, name: str, status: str) -> AgentDefinition:
        if status not in {"active", "paused"}:
            raise ValueError("runtime status must be active or paused")
        current = self._active[name]
        updated = current.model_copy(update={"status": status})
        self._active[name] = updated
        if status == "paused":
            self._handlers.pop(name, None)
        elif updated.handler_key:
            self._handlers[name] = self._make_handler(updated)
        self._persist()
        self.revision += 1
        return updated

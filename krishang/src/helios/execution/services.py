import asyncio
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

from helios.contracts import Artifact, ArtifactType, NormalizedTask, PlanNode, RuntimeMode
from helios.contracts.security import Finding
from helios.security.findings import make_finding
from helios.security.inventory import inventory_repository
from helios.security.normalize import normalize_findings
from helios.security.remediation import remediation_plan
from helios.security.redaction import contains_suspected_secret, redact, redact_text
from helios.workspace.commands import CommandResult, SafeCommandRunner
from helios.workspace.repositories import safe_join


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$", re.I)
SCANNER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
DEFAULT_PROTECTED_PATHS = (
    ".git",
    ".git/**",
    ".github/workflows",
    ".github/workflows/**",
    ".github/actions",
    ".github/actions/**",
    "CODEOWNERS",
    ".gitmodules",
)
TEXT_SUFFIXES = {
    ".css", ".go", ".html", ".java", ".js", ".json", ".md", ".py", ".rs",
    ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
}


class ExecutionPolicyError(PermissionError):
    """A requested repository/tool operation exceeded task consent or policy."""


class PathScope:
    def __init__(self, allowed: list[str], excluded: list[str], protected: list[str]) -> None:
        self.allowed = tuple(self._pattern(item) for item in (allowed or ["."]))
        self.excluded = tuple(self._pattern(item) for item in excluded)
        self.protected = tuple(self._pattern(item) for item in protected)

    @staticmethod
    def normalize(value: str) -> str:
        normalized = value.replace("\\", "/").strip()
        if normalized in {"", "."}:
            return "."
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", normalized):
            raise ExecutionPolicyError(f"repository path escapes consent scope: {value}")
        normalized = path.as_posix()
        return normalized[2:] if normalized.startswith("./") else normalized

    @classmethod
    def _pattern(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip()
        if (any(part == ".." for part in PurePosixPath(normalized).parts)
                or normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized)):
            raise ExecutionPolicyError(f"invalid consent path pattern: {value}")
        if normalized in {"", ".", "./"}:
            return "."
        return normalized[2:] if normalized.startswith("./") else normalized

    @staticmethod
    def _matches(path: str, pattern: str) -> bool:
        if pattern == ".":
            return True
        base = pattern.removesuffix("/**").rstrip("/")
        return path == base or path.startswith(f"{base}/") or fnmatch.fnmatchcase(path, pattern)

    def permits(self, value: str, *, write: bool = False) -> str:
        path = self.normalize(value)
        if not any(self._matches(path, item) for item in self.allowed):
            raise ExecutionPolicyError(f"path is outside allowedPaths: {path}")
        if any(self._matches(path, item) for item in self.excluded):
            raise ExecutionPolicyError(f"path is excluded by consent: {path}")
        if write and any(self._matches(path, item) for item in self.protected):
            raise ExecutionPolicyError(f"write targets a protected path: {path}")
        return path


class ExecutionServices:
    """Task-scoped, mode-neutral boundary for repository and local-tool execution."""

    def __init__(self, task: NormalizedTask, workspace_root: Path, *,
                 source_repository: Path | None = None, output_cap: int = 32_000) -> None:
        task.assert_authorized()
        self.task = task
        self.root = workspace_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.repository = safe_join(self.root, "repo")
        self.checkout = safe_join(self.root, "checkout")
        self.staging = safe_join(self.root, "staging")
        self.source_repository = source_repository.resolve() if source_repository else None
        protected = [*DEFAULT_PROTECTED_PATHS, *self._policy_list("protectedPaths")]
        excluded = [".git", ".git/**", *task.consent.excluded_paths]
        self.scope = PathScope(task.consent.allowed_paths, excluded, protected)
        self.output_cap = min(max(output_cap, 1_024), 64_000)
        self._materialize_lock = asyncio.Lock()
        self._tool_lock = asyncio.Lock()
        self._materialized_sha: str | None = None

    def _policy_list(self, key: str) -> list[str]:
        value = self.task.policy_pack.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ExecutionPolicyError(f"policy {key} must be a string list")
        return value

    def for_node(self, node: PlanNode) -> "NodeExecutionContext":
        return NodeExecutionContext(self, node)

    async def _git(self, argv: list[str], *, timeout: float = 60,
                   network_permitted: bool | None = None) -> CommandResult:
        runner = SafeCommandRunner(
            self.root,
            {"git"},
            self.output_cap,
            network_permitted=(self.task.consent.network_permitted
                               if network_permitted is None else network_permitted),
        )
        return await runner.run(["git", *argv], timeout=min(timeout, self.task.consent.max_runtime_s))

    async def materialize_repository(self) -> dict[str, Any]:
        async with self._materialize_lock:
            if not SHA_PATTERN.fullmatch(self.task.base_sha):
                raise ExecutionPolicyError("repository execution requires an authorized 40-character base SHA")
            has_pinned_sha = set(self.task.base_sha) != {"0"}
            if self._materialized_sha:
                return self._materialization_evidence(self._materialized_sha, "existing")
            if (self.checkout / ".git").exists():
                revision = await self._git(["-C", "checkout", "rev-parse", "HEAD"], timeout=15)
                if revision.exit_code:
                    raise RuntimeError("existing task checkout is not a valid Git worktree")
                sha = revision.stdout.strip()
                self._verify_revision(sha)
                reset = await self._git(["-C", "checkout", "reset", "--hard", sha], timeout=30)
                clean = await self._git(["-C", "checkout", "clean", "-ffd"], timeout=30)
                if reset.exit_code or clean.exit_code:
                    raise RuntimeError("existing task checkout could not be restored to a clean base")
                self._materialized_sha = sha
                return self._materialization_evidence(sha, "existing")

            if not REPOSITORY_PATTERN.fullmatch(self.task.repository):
                raise ExecutionPolicyError("repository identifier is invalid")
            owner, name = self.task.repository.split("/", 1)
            if owner in {".", ".."} or name in {".", ".."}:
                raise ExecutionPolicyError("repository identifier contains a relative component")
            if self.repository.exists() and any(self.repository.iterdir()):
                shutil.rmtree(self.repository)
            self.repository.mkdir(parents=True, exist_ok=True)

            if self.source_repository:
                if not (self.source_repository / ".git").exists():
                    raise ValueError("trusted local source is not a Git repository")
                source = str(self.source_repository)
                clone_args = ["clone", "--no-checkout", "--no-hardlinks", source, "repo"]
                source_kind = "trusted-local"
            else:
                if self.task.source != "github" or self.task.visibility != "public":
                    raise ExecutionPolicyError(
                        "non-public repositories require a brokered snapshot or trusted local source"
                    )
                source = f"https://github.com/{self.task.repository}.git"
                # This is the one narrow network exception: an unauthenticated
                # clone of the exact allowlisted public GitHub repository. Avoid
                # partial clone so later checkout commands never fetch implicitly.
                clone_args = ["clone", "--no-checkout", source, "repo"]
                source_kind = "allowlisted-public-github"

            clone = await self._git(
                clone_args,
                timeout=120,
                network_permitted=source_kind == "allowlisted-public-github",
            )
            if clone.exit_code:
                raise RuntimeError(f"repository clone failed: {(clone.stderr or clone.stdout)[-1_000:]}")
            revision = self.task.base_sha if has_pinned_sha else "HEAD"
            worktree = await self._git(
                ["-C", "repo", "worktree", "add", "--detach", "../checkout", revision],
                timeout=60,
            )
            if worktree.exit_code:
                raise RuntimeError(f"isolated worktree creation failed: {(worktree.stderr or worktree.stdout)[-1_000:]}")
            resolved = await self._git(["-C", "checkout", "rev-parse", "HEAD"], timeout=15)
            if resolved.exit_code:
                raise RuntimeError("could not resolve isolated checkout revision")
            sha = resolved.stdout.strip()
            self._verify_revision(sha)
            self.task.base_sha = sha
            self._materialized_sha = sha
            return self._materialization_evidence(sha, source_kind)

    def _verify_revision(self, actual: str) -> None:
        if not SHA_PATTERN.fullmatch(actual):
            raise RuntimeError("repository returned an invalid commit revision")
        if (
            SHA_PATTERN.fullmatch(self.task.base_sha)
            and set(self.task.base_sha) != {"0"}
            and actual.lower() != self.task.base_sha.lower()
        ):
            raise ExecutionPolicyError("isolated checkout does not match the authorized base SHA")

    def _materialization_evidence(self, sha: str, source_kind: str) -> dict[str, Any]:
        return {
            "authoritative": True,
            "isolated": True,
            "repository": self.task.repository,
            "commitSha": sha,
            "sourceKind": source_kind,
            "networkPermitted": self.task.consent.network_permitted,
            "networkUsed": source_kind == "allowlisted-public-github",
        }

    def _git_file_names(self) -> list[str]:
        git = shutil.which("git")
        if not git:
            raise FileNotFoundError("git is required to inspect a Git checkout")
        environment = os.environ.copy()
        environment.update({
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        })
        try:
            result = subprocess.run(
                [
                    git,
                    "ls-files",
                    "-z",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "--deduplicate",
                ],
                cwd=self.checkout,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=max(1.0, min(60.0, self.task.consent.max_runtime_s)),
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Git file enumeration timed out") from exc
        if result.returncode:
            raise RuntimeError("Git could not enumerate repository files")
        return [
            os.fsdecode(value)
            for value in result.stdout.split(b"\0")
            if value
        ]

    def _iter_files(self) -> list[Path]:
        if (self.checkout / ".git").exists():
            paths: list[Path] = []
            for relative in self._git_file_names():
                try:
                    normalized = self.scope.permits(relative)
                except ExecutionPolicyError:
                    continue
                path = self.checkout.joinpath(*PurePosixPath(normalized).parts)
                if path.is_file() and not path.is_symlink():
                    paths.append(path)
        else:
            paths = []
            for path in self.checkout.rglob("*"):
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(self.checkout).as_posix()
                try:
                    self.scope.permits(relative)
                except ExecutionPolicyError:
                    continue
                paths.append(path)
        return sorted(paths, key=lambda item: item.relative_to(self.checkout).as_posix())

    @staticmethod
    def _file_digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(128 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _collect_repository_evidence(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]], bool]:
        files: list[dict[str, Any]] = []
        excerpts: list[dict[str, str]] = []
        excerpt_budget = 48_000
        preferred = {"README.md", "package.json", "pyproject.toml", "Cargo.toml", "go.mod"}
        all_files = self._iter_files()
        for path in all_files[:1_000]:
            relative = path.relative_to(self.checkout).as_posix()
            size = path.stat().st_size
            digest = self._file_digest(path)
            files.append({"path": relative, "bytes": size, "sha256": digest})
        for path in sorted(all_files, key=lambda item: (item.name not in preferred, item.stat().st_size)):
            if excerpt_budget <= 0 or path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 24_000:
                continue
            relative = path.relative_to(self.checkout).as_posix()
            content = redact_text(path.read_text(encoding="utf-8", errors="replace"))[:excerpt_budget]
            excerpts.append({"path": relative, "content": content})
            excerpt_budget -= len(content)
            if len(excerpts) >= 12:
                break
        return files, excerpts, len(all_files) > len(files)

    async def repository_evidence(self) -> dict[str, Any]:
        materialization = await self.materialize_repository()
        files, excerpts, truncated = await asyncio.to_thread(
            self._collect_repository_evidence
        )
        return {
            **materialization,
            "allowedPaths": list(self.scope.allowed),
            "excludedPaths": list(self.scope.excluded),
            "files": files,
            "excerpts": excerpts,
            "truncated": truncated,
        }

    def validate_files(self, files: Any) -> list[dict[str, Any]]:
        if not isinstance(files, list) or not files:
            raise ValueError("implementation output must contain at least one complete file")
        if len(files) > 200:
            raise ExecutionPolicyError("implementation exceeds the 200-file task limit")
        validated: list[dict[str, Any]] = []
        total = 0
        seen: set[str] = set()
        for record in files:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise ValueError("implementation contains an invalid file record")
            if not isinstance(record.get("content"), str) or record.get("encoding", "utf-8") != "utf-8":
                raise ValueError("implementation files must contain UTF-8 text")
            if contains_suspected_secret(record["content"]):
                raise ExecutionPolicyError("implementation output contains suspected credential material")
            relative = self.scope.permits(record["path"], write=True)
            if relative == "." or relative in seen:
                raise ValueError(f"implementation contains an invalid or duplicate path: {relative}")
            self._reject_symlink_target(relative)
            seen.add(relative)
            encoded = record["content"].encode("utf-8")
            total += len(encoded)
            if len(encoded) > 1_000_000 or total > 2_000_000:
                raise ExecutionPolicyError("implementation exceeds bounded file output limits")
            validated.append({
                "path": relative,
                "content": record["content"],
                "encoding": "utf-8",
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "bytes": len(encoded),
            })
        return validated

    def _reject_symlink_target(self, relative: str) -> None:
        cursor = self.checkout
        for part in PurePosixPath(relative).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ExecutionPolicyError(f"write may not follow a repository symlink: {relative}")

    def _write_files(self, root: Path, files: list[dict[str, Any]]) -> None:
        root.mkdir(parents=True, exist_ok=True)
        for record in files:
            target = safe_join(root, record["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(record["content"], encoding="utf-8")

    async def stage_or_apply(self, node: PlanNode, content: dict[str, Any]) -> dict[str, Any] | None:
        output = ArtifactType(node.output_artifact)
        if output not in {ArtifactType.PATCH, ArtifactType.PACKAGE_RESULT}:
            return None
        await self.materialize_repository()
        if content.get("noChangesRequired") is True:
            allowed_noops = self._policy_list("allowNoopAgents")
            if node.expert not in allowed_noops or content.get("files") not in ([], None):
                raise ExecutionPolicyError("no-op implementation was not authorized by task policy")
            return {
                "authoritative": True,
                "scopeValidated": True,
                "protectedPathsTouched": False,
                "staged": False,
                "appliedToWorktree": False,
                "files": [],
            }
        files = self.validate_files(content.get("files"))
        # The artifact must describe the exact canonical paths and bytes written;
        # downstream write-back may not reinterpret the agent's original strings.
        content["files"] = files
        staged_root = safe_join(self.staging, node.node_id)
        if staged_root.exists():
            shutil.rmtree(staged_root)
        self._write_files(staged_root, files)
        apply_now = output == ArtifactType.PACKAGE_RESULT or self.task.mode != RuntimeMode.BUILD
        if apply_now:
            self._write_files(self.checkout, files)
        return {
            "authoritative": True,
            "scopeValidated": True,
            "protectedPathsTouched": False,
            "staged": True,
            "appliedToWorktree": apply_now,
            "files": [{key: item[key] for key in ("path", "sha256", "bytes")} for item in files],
        }

    def _configured_test_commands(self) -> list[list[str]]:
        configured = self.task.policy_pack.get("testCommands", [])
        if configured:
            if not isinstance(configured, list) or not all(
                isinstance(item, list) and all(isinstance(token, str) for token in item) for item in configured
            ):
                raise ExecutionPolicyError("policy testCommands must contain argv arrays")
            commands = [list(item) for item in configured]
            for command in commands:
                self._validate_test_command(command)
            return commands

        commands: list[list[str]] = []
        package_json = self.checkout / "package.json"
        if package_json.is_file():
            payload = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = payload.get("scripts", {}) if isinstance(payload, dict) else {}
            executable = "bun" if (self.checkout / "bun.lock").is_file() else "npm"
            for script in ("test", "lint", "typecheck", "check", "build"):
                if script in scripts:
                    commands.append([executable, "run", script])
        if (self.checkout / "Cargo.toml").is_file():
            commands.append(["cargo", "test", "--locked"])
        if (self.checkout / "go.mod").is_file():
            commands.append(["go", "test", "./..."])
        if (self.checkout / "pyproject.toml").is_file() and (
            (self.checkout / "tests").is_dir()
            or "pytest" in (self.checkout / "pyproject.toml").read_text(encoding="utf-8", errors="replace")
        ):
            commands.append([sys.executable, "-m", "pytest", "-q"])
        return commands

    @staticmethod
    def _validate_test_command(argv: list[str]) -> None:
        if not argv or len(argv) > 12 or any(len(token) > 256 or "\0" in token for token in argv):
            raise ExecutionPolicyError("test command is malformed")
        executable = Path(argv[0]).name.lower()
        valid = False
        if executable in {"bun", "npm"}:
            valid = len(argv) == 3 and argv[1] == "run" and argv[2] in {"test", "lint", "typecheck", "check", "build"}
        elif executable == "cargo":
            valid = argv[1:] in (["test"], ["test", "--locked"])
        elif executable == "go":
            valid = argv[1:] == ["test", "./..."]
        elif executable.startswith("python") or argv[0] == sys.executable:
            valid = argv[1:3] == ["-m", "pytest"] and set(argv[3:]) <= {"-q", "--disable-warnings"}
        if not valid:
            raise ExecutionPolicyError(f"policy test command is outside the curated command grammar: {argv}")

    async def run_tests(self, timeout: float) -> dict[str, Any]:
        await self.materialize_repository()
        trusted_local = self.source_repository is not None or self.task.policy_pack.get("trustedLocalExecution") is True
        dependencies_prepared = self.source_repository is not None or self.task.policy_pack.get("dependenciesPrepared") is True
        if not trusted_local or not dependencies_prepared:
            return {
                "authoritative": True,
                "fabricated": False,
                "executed": False,
                "coverageComplete": False,
                "success": False,
                "commands": [],
                "results": [],
                "status": "not_configured",
                "limitations": [
                    "Repository-owned commands require explicit trusted-local execution and a prepared isolated dependency environment"
                ],
            }
        if "." not in self.scope.allowed:
            raise ExecutionPolicyError(
                "repository commands require full-checkout allowedPaths because subprocess file access cannot be path-confined"
            )
        commands = self._configured_test_commands()
        before_workspace = await self.workspace_evidence()
        results: list[dict[str, Any]] = []
        for argv in commands:
            self._validate_test_command(argv)
            runner = SafeCommandRunner(
                self.checkout,
                {argv[0]},
                self.output_cap,
                network_permitted=self.task.consent.network_permitted,
                state_root=self.root,
            )
            try:
                result = await runner.run(argv, timeout=min(timeout, self.task.consent.max_runtime_s))
                results.append(self._command_evidence(result))
            except FileNotFoundError as error:
                results.append({
                    "argv": argv,
                    "commandHash": hashlib.sha256("\0".join(argv).encode()).hexdigest(),
                    "exitCode": None,
                    "timedOut": False,
                    "status": "unavailable",
                    "error": str(error),
                })
        after_workspace = await self.workspace_evidence()
        if after_workspace["diffHash"] != before_workspace["diffHash"]:
            raise ExecutionPolicyError("repository-owned test commands modified the task worktree")
        executed = [item for item in results if item.get("exitCode") is not None]
        success = bool(commands) and len(executed) == len(commands) and all(item["exitCode"] == 0 for item in executed)
        return {
            "authoritative": True,
            "fabricated": False,
            "executed": bool(executed),
            "coverageComplete": bool(commands) and len(executed) == len(commands),
            "success": success,
            "commands": [item["argv"] for item in results],
            "results": results,
            "status": "passed" if success else ("failed" if executed else "not_configured"),
        }

    @staticmethod
    def _command_evidence(result: CommandResult) -> dict[str, Any]:
        return {
            "argv": result.argv,
            "commandHash": result.command_hash,
            "exitCode": result.exit_code,
            "timedOut": result.timed_out,
            "status": "passed" if result.exit_code == 0 else "failed",
            "stdout": result.stdout[-4_000:],
            "stderr": result.stderr[-4_000:],
        }

    async def repository_inventory(self) -> dict[str, Any]:
        materialization = await self.materialize_repository()

        def permitted(relative: str) -> bool:
            try:
                self.scope.permits(relative)
            except ExecutionPolicyError:
                return False
            return True

        inventory = inventory_repository(
            self.checkout,
            self.task.repository,
            materialization["commitSha"],
            excluded=[],
            path_filter=permitted,
        )
        return {
            **materialization,
            **inventory.model_dump(mode="json", by_alias=True),
        }

    async def dependency_inventory(self) -> dict[str, Any]:
        inventory = await self.repository_inventory()
        dependencies: list[dict[str, str]] = []
        for relative in inventory["manifests"]:
            path = safe_join(self.checkout, self.scope.permits(relative))
            try:
                if path.name == "package.json":
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    for group in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                        values = payload.get(group, {})
                        if isinstance(values, dict):
                            dependencies.extend({"name": str(name), "constraint": str(version),
                                                 "scope": group, "manifest": relative}
                                                for name, version in values.items())
                elif path.name == "pyproject.toml":
                    payload = tomllib.loads(path.read_text(encoding="utf-8"))
                    for value in payload.get("project", {}).get("dependencies", []):
                        dependencies.append({"name": str(value), "constraint": "declared", "scope": "runtime", "manifest": relative})
                elif path.name == "Cargo.toml":
                    payload = tomllib.loads(path.read_text(encoding="utf-8"))
                    for group in ("dependencies", "dev-dependencies", "build-dependencies"):
                        for name, value in payload.get(group, {}).items():
                            dependencies.append({"name": str(name), "constraint": str(value), "scope": group, "manifest": relative})
            except (json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
                dependencies.append({"name": "[manifest-parse-error]", "constraint": str(error),
                                     "scope": "error", "manifest": relative})
        return {
            "authoritative": True,
            "repository": self.task.repository,
            "commitSha": inventory["commitSha"],
            "dependencies": dependencies,
            "manifestsRead": inventory["manifests"],
            "lockfiles": inventory["lockfiles"],
            "lockfileAuthoritative": bool(inventory["lockfiles"]),
        }

    def _scanner_spec(self, scanner: str) -> list[str]:
        targets = self._scanner_targets()
        exclusions = [item for item in self.scope.excluded if item != "."]
        if scanner == "bandit":
            argv = ["bandit", "-r", *targets, "-f", "json"]
            if exclusions:
                argv.extend(["-x", ",".join(exclusions)])
            return argv
        if scanner == "gitleaks":
            if "." not in self.scope.allowed:
                raise ExecutionPolicyError("gitleaks requires full-checkout allowedPaths")
            return ["gitleaks", "detect", "--source", ".", "--no-git", "--report-format", "json", "--report-path", "-"]
        if scanner == "semgrep":
            configs = self.task.policy_pack.get("scannerConfigs", {})
            config = configs.get("semgrep") if isinstance(configs, dict) else None
            if not isinstance(config, str):
                raise ExecutionPolicyError("semgrep requires a policy-owned local scannerConfigs.semgrep path")
            config = self.scope.permits(config)
            return ["semgrep", "--json", "--config", config, *targets]
        if scanner == "trivy":
            if "." not in self.scope.allowed:
                raise ExecutionPolicyError("trivy requires full-checkout allowedPaths")
            argv = ["trivy", "fs", "--format", "json"]
            if not self.task.consent.network_permitted:
                argv.append("--offline-scan")
            for path in exclusions:
                argv.extend(["--skip-dirs", path])
            return [*argv, "."]
        if scanner == "npm":
            if "." not in self.scope.allowed:
                raise ExecutionPolicyError("npm audit requires full-checkout allowedPaths")
            if not self.task.consent.network_permitted:
                raise ExecutionPolicyError("npm advisory scanning requires network consent")
            return ["npm", "audit", "--json"]
        if scanner == "pip-audit":
            if "." not in self.scope.allowed:
                raise ExecutionPolicyError("pip-audit requires full-checkout allowedPaths")
            if not self.task.consent.network_permitted:
                raise ExecutionPolicyError("pip-audit advisory scanning requires network consent")
            return ["pip-audit", "--format=json"]
        raise ExecutionPolicyError(f"scanner is not in the local scanner catalog: {scanner}")

    def _scanner_targets(self) -> list[str]:
        if "." in self.scope.allowed:
            return ["."]
        targets: set[str] = set()
        for pattern in self.scope.allowed:
            candidate = pattern.removesuffix("/**").rstrip("/")
            if not any(character in candidate for character in "*?[") and safe_join(self.checkout, candidate).exists():
                targets.add(candidate)
        if not targets:
            targets.update(path.relative_to(self.checkout).as_posix() for path in self._iter_files()[:1_000])
        if not targets:
            raise ExecutionPolicyError("allowedPaths contains no scanner-readable files")
        return sorted(targets)

    async def run_scanners(self, timeout: float) -> dict[str, Any]:
        await self.materialize_repository()
        before_workspace = await self.workspace_evidence()
        configured = list(dict.fromkeys(item.lower() for item in self.task.consent.allowed_scanners))
        results: list[dict[str, Any]] = []
        findings: list[Finding] = []
        for scanner in configured:
            if not SCANNER_PATTERN.fullmatch(scanner):
                raise ExecutionPolicyError(f"invalid scanner identifier: {scanner}")
            try:
                argv = self._scanner_spec(scanner)
                runner = SafeCommandRunner(
                    self.checkout,
                    {argv[0]},
                    self.output_cap,
                    network_permitted=self.task.consent.network_permitted,
                    state_root=self.root,
                )
                version = await runner.run([argv[0], "--version"], timeout=min(15, timeout))
                result = await runner.run(argv, timeout=min(timeout, self.task.consent.max_runtime_s))
                scanner_findings = self._parse_scanner(scanner, result.stdout)
                scanner_findings = [
                    finding for finding in scanner_findings
                    if self._finding_is_in_scope(finding)
                ]
                findings.extend(scanner_findings)
                finding_exit = scanner in {"bandit", "gitleaks"} and result.exit_code == 1 and bool(scanner_findings)
                completed = not result.timed_out and (result.exit_code == 0 or finding_exit)
                results.append({
                    "scanner": scanner,
                    "scannerVersion": redact_text((version.stdout or version.stderr).strip())[:200] or "unknown",
                    "commandHash": result.command_hash,
                    "exitCode": result.exit_code,
                    "timedOut": result.timed_out,
                    "outputRef": hashlib.sha256(f"{result.stdout}\n{result.stderr}".encode()).hexdigest(),
                    "findingCount": len(scanner_findings),
                    "status": "completed" if completed else ("timed_out" if result.timed_out else "failed"),
                    "exclusions": list(self.scope.excluded),
                })
            except (ExecutionPolicyError, FileNotFoundError, TypeError, ValueError) as error:
                results.append({"scanner": scanner, "status": "unavailable", "error": redact_text(str(error))})
        after_workspace = await self.workspace_evidence()
        if after_workspace["diffHash"] != before_workspace["diffHash"]:
            raise ExecutionPolicyError("scanner execution modified the task worktree")
        normalized = normalize_findings(findings)
        coverage = bool(configured) and len(results) == len(configured) and all(item["status"] == "completed" for item in results)
        return {
            "authoritative": True,
            "fabricated": False,
            "version": "2.1.0",
            "configuredScanners": configured,
            "scannerResults": results,
            "coverageComplete": coverage,
            "runs": [{"tool": {"driver": {"name": item["scanner"]}}, "properties": item} for item in results],
            "findings": [item.model_dump(mode="json", by_alias=True) for item in normalized],
            "secretsRedacted": True,
        }

    @staticmethod
    def _parse_scanner(scanner: str, output: str) -> list[Finding]:
        try:
            payload = json.loads(output or "{}")
        except json.JSONDecodeError as error:
            raise ValueError("scanner returned invalid JSON") from error
        if scanner in {"semgrep", "bandit", "trivy", "npm"} and not isinstance(payload, dict):
            raise ValueError(f"{scanner} returned an unexpected JSON shape")
        if scanner == "gitleaks" and not isinstance(payload, list):
            raise ValueError("gitleaks returned an unexpected JSON shape")
        findings: list[Finding] = []
        if scanner == "semgrep":
            for item in payload.get("results", []):
                extra = item.get("extra", {})
                findings.append(make_finding(
                    kind="sast", rule_id=str(item.get("check_id", "semgrep.unknown")),
                    title=str(extra.get("message", "Semgrep finding")),
                    severity=str(extra.get("severity", "warning")).lower(), confidence="medium",
                    path=str(item.get("path", "unknown")), line=item.get("start", {}).get("line"),
                    evidence="Semgrep rule match (source text withheld)",
                ))
        elif scanner == "bandit":
            for item in payload.get("results", []):
                findings.append(make_finding(
                    kind="sast", rule_id=str(item.get("test_id", "bandit.unknown")),
                    title=str(item.get("issue_text", "Bandit finding")),
                    severity=str(item.get("issue_severity", "medium")).lower(),
                    confidence=str(item.get("issue_confidence", "medium")).lower(),
                    path=str(item.get("filename", "unknown")), line=item.get("line_number"),
                    evidence="Bandit rule match (source text withheld)",
                ))
        elif scanner == "gitleaks" and isinstance(payload, list):
            for item in payload:
                findings.append(make_finding(
                    kind="secret", rule_id=str(item.get("RuleID", "gitleaks.unknown")),
                    title=str(item.get("Description", "Potential secret")), severity="high", confidence="high",
                    path=str(item.get("File", "unknown")), line=item.get("StartLine"),
                    evidence="Potential secret value redacted",
                ))
        elif scanner == "trivy":
            for result in payload.get("Results", []):
                target = str(result.get("Target", "unknown"))
                for item in result.get("Vulnerabilities", []):
                    findings.append(make_finding(
                        kind="dependency", rule_id=str(item.get("VulnerabilityID", "trivy.unknown")),
                        title=str(item.get("Title", "Dependency vulnerability")),
                        severity=str(item.get("Severity", "unknown")).lower(), confidence="high",
                        path=target, evidence=f"Installed package: {item.get('PkgName', 'unknown')}",
                        remediation=str(item.get("FixedVersion", "")),
                    ))
                for item in result.get("Misconfigurations", []):
                    findings.append(make_finding(
                        kind="configuration", rule_id=str(item.get("ID", "trivy.misconfiguration")),
                        title=str(item.get("Title", "Configuration finding")),
                        severity=str(item.get("Severity", "unknown")).lower(), confidence="high",
                        path=target, evidence="Trivy configuration rule match (source text withheld)",
                        remediation=str(item.get("Resolution", "")),
                    ))
                for item in result.get("Secrets", []):
                    findings.append(make_finding(
                        kind="secret", rule_id=str(item.get("RuleID", "trivy.secret")),
                        title=str(item.get("Title", "Potential secret")), severity="high", confidence="high",
                        path=target, line=item.get("StartLine"), evidence="Potential secret value redacted",
                    ))
        elif scanner == "npm":
            for name, item in payload.get("vulnerabilities", {}).items():
                via = item.get("via", []) if isinstance(item, dict) else []
                advisory = next((value for value in via if isinstance(value, dict)), {})
                findings.append(make_finding(
                    kind="dependency", rule_id=str(advisory.get("source", f"npm:{name}")),
                    title=str(advisory.get("title", f"Vulnerable dependency: {name}")),
                    severity=str(item.get("severity", advisory.get("severity", "unknown"))).lower(),
                    confidence="high", path="package.json", evidence=f"Affected package: {name}",
                    remediation=str(item.get("fixAvailable", "")),
                    advisory_urls=[str(advisory["url"])] if advisory.get("url") else [],
                ))
        elif scanner == "pip-audit":
            dependencies = payload.get("dependencies", []) if isinstance(payload, dict) else payload
            for dependency in dependencies if isinstance(dependencies, list) else []:
                if not isinstance(dependency, dict):
                    continue
                for vulnerability in dependency.get("vulns", []):
                    if not isinstance(vulnerability, dict):
                        continue
                    fixes = vulnerability.get("fix_versions", [])
                    findings.append(make_finding(
                        kind="dependency", rule_id=str(vulnerability.get("id", "pip-audit.unknown")),
                        title=str(vulnerability.get("description", "Python dependency vulnerability"))[:500],
                        severity="unknown", confidence="high", path="pyproject.toml",
                        evidence=f"Affected package: {dependency.get('name', 'unknown')}",
                        remediation=f"Upgrade to {', '.join(map(str, fixes))}" if fixes else "",
                    ))
        else:
            raise ValueError(f"no structured scanner parser is registered for {scanner}")
        return findings

    def _finding_is_in_scope(self, finding: Finding) -> bool:
        try:
            normalized = self.scope.permits(finding.path)
        except ExecutionPolicyError:
            return False
        finding.path = normalized
        return True

    async def security_report(self, upstream: list[Artifact], timeout: float) -> dict[str, Any]:
        scan = next((item.content for item in upstream if item.artifact_type == ArtifactType.SARIF_REPORT), None)
        if scan is None:
            scan = await self.run_scanners(timeout)
        findings = [Finding.model_validate(item) for item in scan.get("findings", [])]
        normalized = normalize_findings(findings)
        coverage = scan.get("coverageComplete") is True
        safe = coverage and not normalized
        return {
            "authoritative": True,
            "fabricated": False,
            "safe": safe,
            "coverageComplete": coverage,
            "findings": [item.model_dump(mode="json", by_alias=True) for item in normalized],
            "scannerResults": scan.get("scannerResults", []),
            "secretsRedacted": True,
            "limitations": [] if coverage else ["One or more consented scanners did not execute successfully"],
        }

    async def remediation_evidence(self, upstream: list[Artifact]) -> dict[str, Any]:
        findings: list[Finding] = []
        for artifact in upstream:
            for item in artifact.content.get("findings", []):
                findings.append(Finding.model_validate(item))
        return {
            **remediation_plan(normalize_findings(findings), self.task.consent.remediation_permitted),
            "authoritative": True,
            "sourceFindingFingerprints": sorted({item.fingerprint for item in findings}),
        }

    async def workspace_evidence(self) -> dict[str, Any]:
        await self.materialize_repository()
        diff = await self._git(["-C", "checkout", "diff", "--no-ext-diff", "--binary"], timeout=30)
        paths = await self._changed_paths()
        digest = hashlib.sha256(diff.stdout.encode())
        for relative in paths:
            target = safe_join(self.checkout, relative)
            digest.update(relative.encode())
            if target.is_file():
                digest.update(bytes.fromhex(self._file_digest(target)))
        return {
            "authoritative": True,
            "baseSha": self.task.base_sha,
            "changedPaths": paths,
            "diffHash": digest.hexdigest(),
            "diffCheckExitCode": (await self._git(["-C", "checkout", "diff", "--check"], timeout=15)).exit_code,
        }

    async def _changed_paths(self) -> list[str]:
        status = await self._git(["-C", "checkout", "status", "--short", "--untracked-files=all"], timeout=15)
        if status.exit_code:
            raise RuntimeError("could not inspect isolated worktree changes")
        paths: list[str] = []
        for line in status.stdout.splitlines():
            value = line[3:].strip() if len(line) >= 4 else ""
            if " -> " in value:
                value = value.split(" -> ", 1)[1]
            value = value.strip('"')
            if value:
                paths.append(self.scope.permits(value, write=True))
        return sorted(set(paths))

    async def _assert_no_protected_command_writes(self) -> None:
        # Scope validation here catches protected and out-of-scope paths created
        # as side effects by repository-owned test/scanner processes.
        await self._changed_paths()


class NodeExecutionContext:
    def __init__(self, services: ExecutionServices, node: PlanNode) -> None:
        self.services = services
        self.node = node
        self.grants = frozenset(node.tool_grants)

    def require(self, grant: str) -> None:
        if grant not in self.grants:
            raise ExecutionPolicyError(f"node {self.node.node_id} has no {grant} grant")

    async def repository_evidence(self) -> dict[str, Any]:
        self.require("repo:read")
        return await self.services.repository_evidence()

    async def test_evidence(self) -> dict[str, Any]:
        self.require("command:test")
        async with self.services._tool_lock:
            return await self.services.run_tests(self.node.budget.max_seconds)

    async def scanner_evidence(self) -> dict[str, Any]:
        self.require("scanner:local")
        async with self.services._tool_lock:
            return await self.services.run_scanners(self.node.budget.max_seconds)

    async def inventory_evidence(self) -> dict[str, Any]:
        self.require("repo:read")
        return await self.services.repository_inventory()

    async def dependency_evidence(self) -> dict[str, Any]:
        self.require("scanner:local")
        return await self.services.dependency_inventory()

    async def security_evidence(self, upstream: list[Artifact]) -> dict[str, Any]:
        if not any(item.artifact_type == ArtifactType.SARIF_REPORT for item in upstream):
            self.require("scanner:local")
            async with self.services._tool_lock:
                return await self.services.security_report(upstream, self.node.budget.max_seconds)
        return await self.services.security_report(upstream, self.node.budget.max_seconds)

    async def remediation_evidence(self, upstream: list[Artifact]) -> dict[str, Any]:
        if not self.services.task.consent.remediation_permitted:
            raise ExecutionPolicyError("remediation requires separate consent")
        return await self.services.remediation_evidence(upstream)

    async def commit_validated_output(self, content: dict[str, Any]) -> dict[str, Any] | None:
        if ArtifactType(self.node.output_artifact) in {ArtifactType.PATCH, ArtifactType.PACKAGE_RESULT}:
            self.require("workspace:write")
        return await self.services.stage_or_apply(self.node, content)

    async def workspace_evidence(self) -> dict[str, Any]:
        return await self.services.workspace_evidence()

    def validate_output_scope(self, content: dict[str, Any]) -> list[str]:
        if ArtifactType(self.node.output_artifact) not in {ArtifactType.PATCH, ArtifactType.PACKAGE_RESULT}:
            return []
        self.require("workspace:write")
        if content.get("noChangesRequired") is True:
            allowed_noops = self.services._policy_list("allowNoopAgents")
            if self.node.expert not in allowed_noops or content.get("files") not in ([], None):
                raise ExecutionPolicyError("no-op implementation was not authorized by task policy")
            return ["policy-authorized-no-op"]
        self.services.validate_files(content.get("files"))
        return ["allowed-path-scope", "protected-path-policy", "bounded-file-output"]


def redact_execution_payload(value: Any) -> Any:
    """Explicit public helper for structured execution evidence."""
    return redact(value)

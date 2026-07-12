from typing import Any

from pydantic import Field
from .common import WireModel


class RequirementsSpec(WireModel):
    goals: list[str]
    non_goals: list[str]
    user_stories: list[str]
    constraints: list[str]
    acceptance_criteria: list[str]
    unanswered_decisions: list[str] = Field(default_factory=list)
    repository_citations: list[str] = Field(default_factory=list)


class ArchitectureDecision(WireModel):
    alternatives: list[str]
    chosen_approach: str
    affected_modules: list[str]
    data_flow: str
    migration_impact: str
    test_plan: list[str]
    security_considerations: list[str]
    rollback: str


class BuildManifest(WireModel):
    base_sha: str
    files: list[dict[str, Any]]
    commands: list[dict[str, Any]]
    test_results: list[dict[str, Any]]
    security_results: list[dict[str, Any]]
    known_limitations: list[str]
    result_hashes: dict[str, str]

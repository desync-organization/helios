from helios.contracts import Artifact, ArtifactType


def make_escalation(*, task_id: str, run_id: str, producer: str, what_i_tried: str,
                    exact_failure: str, smallest_failing_case: str,
                    artifact_chain: list[str], decision_needed: str) -> Artifact:
    return Artifact.create(task_id=task_id, run_id=run_id, artifact_type=ArtifactType.ESCALATION,
                           producer=producer, upstream_artifact_ids=artifact_chain,
                           policy_ids=["runtime.context-complete-escalation"],
                           content={"whatITried": what_i_tried, "exactFailure": exact_failure,
                                    "smallestFailingCase": smallest_failing_case,
                                    "artifactChain": artifact_chain, "decisionNeeded": decision_needed})


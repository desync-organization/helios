from helios.control_plane.local_cache import LocalRunCache


def completed_nodes(cache: LocalRunCache | None, run_id: str) -> set[str]:
    state = cache.load(run_id) if cache else None
    return set(state.get("completedNodes", [])) if state else set()


def save_progress(
    cache: LocalRunCache | None,
    run_id: str,
    completed: set[str],
    artifacts: dict[str, str],
    plan_identity: dict[str, str],
) -> None:
    if cache:
        cache.save(
            run_id,
            {
                "completedNodes": sorted(completed),
                "artifacts": artifacts,
                "planIdentity": plan_identity,
            },
        )

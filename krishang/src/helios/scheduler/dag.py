from helios.contracts import Plan


def execution_layers(plan: Plan) -> list[list[str]]:
    pending = {node.node_id: set(node.dependencies) for node in plan.nodes}
    completed: set[str] = set()
    layers: list[list[str]] = []
    while pending:
        ready = sorted(node_id for node_id, dependencies in pending.items() if dependencies <= completed)
        if not ready:
            raise ValueError("DAG cannot make progress")
        layers.append(ready)
        completed.update(ready)
        for node_id in ready:
            pending.pop(node_id)
    return layers


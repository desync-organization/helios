from helios.contracts import CanonicalEvent


def model_event(event_type: str, definition, *, run_id: str | None = None, **details) -> CanonicalEvent:
    return CanonicalEvent(type=event_type, run_id=run_id,
                          payload={"modelId": definition.model_id, "role": definition.role,
                                   "quantization": definition.quantization, "tier": definition.tier, **details})


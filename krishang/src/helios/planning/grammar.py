from helios.contracts import Plan


_PLAN_JSON_SCHEMA = Plan.model_json_schema()


def plan_json_schema() -> dict:
    """Schema passed to llama.cpp grammar-constrained JSON decoding."""
    return _PLAN_JSON_SCHEMA

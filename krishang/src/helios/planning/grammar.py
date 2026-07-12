from helios.contracts import Plan


def plan_json_schema() -> dict:
    """Schema passed to llama.cpp grammar-constrained JSON decoding."""
    return Plan.model_json_schema()


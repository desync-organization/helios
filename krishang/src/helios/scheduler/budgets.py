class BudgetExceeded(RuntimeError):
    pass


def enforce_usage(*, tokens: int, cost_usd: float, max_tokens: int, max_cost_usd: float) -> None:
    if tokens > max_tokens:
        raise BudgetExceeded("token budget exceeded")
    if cost_usd > max_cost_usd:
        raise BudgetExceeded("cost budget exceeded")


from helios.demo.seed_runtime import seed


async def test_all_three_modes_run_on_one_kernel():
    result = await seed()
    assert result["runs"] == 3
    assert len(result["intents"]) == 3
    assert {item["action"] for item in result["intents"]} == {"issue_update", "branch_pr", "private_security_report"}
    assert result["events"] > 20


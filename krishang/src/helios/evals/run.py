import importlib


def main() -> None:
    evaluator = importlib.import_module("helios_member3_evals")
    evaluator.main()


if __name__ == "__main__":
    main()


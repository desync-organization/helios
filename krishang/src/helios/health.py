import json

from helios.models.bootstrap import preflight


def main() -> None:
    result = preflight()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready"] else 1)


if __name__ == "__main__":
    main()


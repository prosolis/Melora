"""CLI entry point for Melora.

Usage:
    python -m app --check    Verify configuration and connectivity
    python -m app            Start the server
"""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="melora",
        description="Melora — *arr media arrival webhook bridge for Matrix",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify configuration and connectivity, then exit",
    )
    args = parser.parse_args()

    if args.check:
        from app.check import run_checks

        raise SystemExit(run_checks())

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

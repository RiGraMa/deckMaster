"""
Backwards-compatible entrypoint for the CLI tool.

Actual implementation lives in `cli/deckmaster.py`.
"""

from cli.deckmaster import main


if __name__ == "__main__":
    main()


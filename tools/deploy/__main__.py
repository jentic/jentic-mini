"""Entrypoint for `uv run python -m tools.deploy`."""

from .cli import cli

if __name__ == "__main__":
    cli()

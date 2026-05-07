"""Command-line utilities for Jentic Mini."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from collections.abc import Sequence

import aiosqlite
import bcrypt

from src.auth import MIN_PASSWORD_LENGTH
from src.db import get_db


class CliError(Exception):
    """Expected CLI failure with a user-facing message."""


class CliArgumentParser(argparse.ArgumentParser):
    """Argument parser that exits with code 1 for command errors."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def prompt_new_password() -> str:
    """Prompt for and validate a confirmed new password."""
    password = getpass.getpass("New password: ")
    confirmation = getpass.getpass("Confirm new password: ")

    if password != confirmation:
        raise CliError("Passwords do not match.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise CliError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    return password


async def reset_password(new_password: str) -> str:
    """Reset the single root account password and return its username."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise CliError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username FROM users ORDER BY created_at ASC LIMIT 2"
        ) as cur:
            users = await cur.fetchall()

        if not users:
            raise CliError("No user account exists.")
        if len(users) > 1:
            raise CliError("Expected a single root account, but found multiple users.")

        user = users[0]
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user["id"]),
        )
        await db.commit()

    return user["username"]


async def reset_password_command(_args: argparse.Namespace) -> int:
    """Run the reset-password subcommand."""
    new_password = prompt_new_password()
    username = await reset_password(new_password)
    print(f"Password updated for user '{username}'.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = CliArgumentParser(prog="python3 -m src")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reset_parser = subparsers.add_parser(
        "reset-password",
        help="Reset the single root account password.",
    )
    reset_parser.set_defaults(func=reset_password_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return asyncio.run(args.func(args))
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

import asyncio

import aiosqlite
import bcrypt
import src.__main__ as cli
import src.config as config
import src.db as db_module
from fastapi import FastAPI
from src.routers.user import router as user_router
from starlette.testclient import TestClient


async def _password_hash(db_path: str) -> str:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT password_hash FROM users LIMIT 1") as cur:
            row = await cur.fetchone()
    assert row is not None
    return row[0]


async def _insert_user(db_path: str, username: str, password_hash: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (username, username, password_hash),
        )
        await db.commit()


def _setup_test_db(tmp_path, monkeypatch) -> str:
    db_path = str(tmp_path / "jentic-mini.db")
    monkeypatch.setenv("DB_PATH", db_path)

    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.run_migrations()

    return db_path


def _create_user(username: str = "testadmin", password: str = "oldpassword") -> None:
    app = FastAPI()
    app.include_router(user_router)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/user/create",
            json={"username": username, "password": password},
        )

    assert response.status_code == 201, response.text


def test_reset_password_cli_updates_single_root_account(tmp_path, monkeypatch, capsys):
    db_path = _setup_test_db(tmp_path, monkeypatch)
    _create_user()

    passwords = iter(["newpassword", "newpassword"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))

    assert cli.main(["reset-password"]) == 0

    captured = capsys.readouterr()
    assert "Password updated for user 'testadmin'." in captured.out

    new_hash = asyncio.run(_password_hash(db_path))
    assert bcrypt.checkpw("newpassword".encode(), new_hash.encode())
    assert not bcrypt.checkpw("oldpassword".encode(), new_hash.encode())


def test_reset_password_cli_errors_when_no_user_account_exists(
    tmp_path, monkeypatch, capsys
):
    _setup_test_db(tmp_path, monkeypatch)
    passwords = iter(["newpassword", "newpassword"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))

    assert cli.main(["reset-password"]) == 1

    captured = capsys.readouterr()
    assert "No user account exists." in captured.err


def test_reset_password_cli_errors_when_multiple_users_exist(
    tmp_path, monkeypatch, capsys
):
    db_path = _setup_test_db(tmp_path, monkeypatch)
    _create_user()
    password_hash = bcrypt.hashpw(b"placeholder", bcrypt.gensalt()).decode()
    asyncio.run(_insert_user(db_path, "second-user", password_hash))
    passwords = iter(["newpassword", "newpassword"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))

    assert cli.main(["reset-password"]) == 1

    captured = capsys.readouterr()
    assert "Expected a single root account, but found multiple users." in captured.err


def test_reset_password_cli_errors_when_password_confirmation_mismatches(
    tmp_path, monkeypatch, capsys
):
    db_path = _setup_test_db(tmp_path, monkeypatch)
    _create_user()
    original_hash = asyncio.run(_password_hash(db_path))
    passwords = iter(["newpassword", "newpassxxxx"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))

    assert cli.main(["reset-password"]) == 1

    captured = capsys.readouterr()
    current_hash = asyncio.run(_password_hash(db_path))
    assert "Passwords do not match." in captured.err
    assert current_hash == original_hash
    assert bcrypt.checkpw("oldpassword".encode(), current_hash.encode())


def test_reset_password_cli_errors_when_password_is_too_short(
    tmp_path, monkeypatch, capsys
):
    db_path = _setup_test_db(tmp_path, monkeypatch)
    _create_user()
    original_hash = asyncio.run(_password_hash(db_path))
    passwords = iter(["short", "short"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))

    assert cli.main(["reset-password"]) == 1

    captured = capsys.readouterr()
    current_hash = asyncio.run(_password_hash(db_path))
    assert "Password must be at least 8 characters." in captured.err
    assert current_hash == original_hash
    assert bcrypt.checkpw("oldpassword".encode(), current_hash.encode())

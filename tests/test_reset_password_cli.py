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


def test_reset_password_cli_updates_single_root_account(tmp_path, monkeypatch, capsys):
    db_path = str(tmp_path / "jentic-mini.db")
    monkeypatch.setenv("DB_PATH", db_path)

    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.run_migrations()

    app = FastAPI()
    app.include_router(user_router)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/user/create",
            json={"username": "testadmin", "password": "oldpassword"},
        )

    assert response.status_code == 201, response.text

    passwords = iter(["newpassword", "newpassword"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))

    assert cli.main(["reset-password"]) == 0

    captured = capsys.readouterr()
    assert "Password updated for user 'testadmin'." in captured.out

    new_hash = asyncio.run(_password_hash(db_path))
    assert bcrypt.checkpw("newpassword".encode(), new_hash.encode())
    assert not bcrypt.checkpw("oldpassword".encode(), new_hash.encode())

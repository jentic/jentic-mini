"""Fernet-encrypted credential vault."""
import json
import os
import re
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from src.db import get_db

_KEY_FILE = Path(os.getenv("DB_PATH", "/app/data/jentic-mini.db")).parent / "vault.key"


def _slugify(label: str) -> str:
    """Generate a URL-safe slug from a label.

    Examples:
      "Work Gmail"       → "work-gmail"
      "GitHub PAT"       → "github-pat"
      "My Calendar (v2)" → "my-calendar-v2"
    """
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "credential"


def _fernet() -> Fernet:
    key = os.getenv("JENTIC_VAULT_KEY", "")
    if key:
        try:
            return Fernet(key.encode())
        except Exception:
            pass  # fall through to auto-generate
    # Auto-generate and persist a key on first use
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_text().strip()
    else:
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key().decode()
        _KEY_FILE.write_text(key)
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt credential") from e


async def create_credential(
    label: str,
    env_var: str,
    value: str,
    routes: list[str] | None = None,
    auth_type: str | None = None,
    identity: str | None = None,
    credential_id: str | None = None,
) -> dict:
    """Create a new credential in the vault.

    If credential_id is provided, use it as-is. Otherwise auto-generate from label.
    """
    base_slug = credential_id or _slugify(label)
    enc = encrypt(value)
    routes_json = json.dumps(routes or [])

    async with get_db() as db:
        # Collision-safe ID
        cid = base_slug
        suffix_n = 2
        while True:
            async with db.execute("SELECT id FROM credentials WHERE id=?", (cid,)) as cur:
                if not await cur.fetchone():
                    break
            cid = f"{base_slug}-{suffix_n}"
            suffix_n += 1

        await db.execute(
            "INSERT INTO credentials (id, label, env_var, encrypted_value, routes, auth_type, identity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, label, env_var, enc, routes_json, auth_type, identity),
        )
        await db.commit()
        async with db.execute("SELECT * FROM credentials WHERE id=?", (cid,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row)


async def patch_credential(cid: str, label: str | None, value: str | None,
                           routes: list[str] | None = None,
                           auth_type: str | None = None,
                           identity: str | None = None) -> dict | None:
    async with get_db() as db:
        if label:
            await db.execute("UPDATE credentials SET label=?, updated_at=unixepoch() WHERE id=?", (label, cid))
        if value:
            enc = encrypt(value)
            await db.execute("UPDATE credentials SET encrypted_value=?, updated_at=unixepoch() WHERE id=?", (enc, cid))
        if routes is not None:
            await db.execute("UPDATE credentials SET routes=?, updated_at=unixepoch() WHERE id=?", (json.dumps(routes), cid))
        if auth_type is not None:
            await db.execute("UPDATE credentials SET auth_type=?, updated_at=unixepoch() WHERE id=?", (auth_type, cid))
        if identity is not None:
            await db.execute("UPDATE credentials SET identity=?, updated_at=unixepoch() WHERE id=?", (identity, cid))
        await db.commit()
        async with db.execute("SELECT * FROM credentials WHERE id=?", (cid,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None


async def delete_credential(cid: str) -> bool:
    async with get_db() as db:
        cur = await db.execute("DELETE FROM credentials WHERE id=?", (cid,))
        await db.commit()
    return cur.rowcount > 0


async def get_credential_value(db, vault_id: str) -> str | None:
    """Return the decrypted value for a credential by ID."""
    async with db.execute(
        "SELECT encrypted_value FROM credentials WHERE id=?", (vault_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return decrypt(row[0])


async def get_credential_ids_for_route(toolkit_id: str, host: str, path: str) -> list[str]:
    """Return credential IDs (no decryption) matching a route. Used for policy checks.

    Matches credentials whose routes JSON array contains a prefix of host/path.
    Ordered by longest matching prefix (most specific first).
    """
    from src.db import DEFAULT_TOOLKIT_ID
    full_path = f"{host}/{path}".rstrip("/")
    async with get_db() as db:
        if toolkit_id == DEFAULT_TOOLKIT_ID:
            async with db.execute(
                """SELECT c.id FROM credentials c
                   WHERE EXISTS (
                       SELECT 1 FROM json_each(c.routes)
                       WHERE ? LIKE (value || '%')
                   )
                   ORDER BY (
                       SELECT MAX(length(value)) FROM json_each(c.routes)
                       WHERE ? LIKE (value || '%')
                   ) DESC""",
                (full_path, full_path),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                """SELECT c.id FROM credentials c
                   JOIN toolkit_credentials cc ON c.id = cc.credential_id
                   WHERE cc.toolkit_id = ?
                   AND EXISTS (
                       SELECT 1 FROM json_each(c.routes)
                       WHERE ? LIKE (value || '%')
                   )
                   ORDER BY (
                       SELECT MAX(length(value)) FROM json_each(c.routes)
                       WHERE ? LIKE (value || '%')
                   ) DESC""",
                (toolkit_id, full_path, full_path),
            ) as cur:
                rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_credentials_for_route(toolkit_id: str, host: str, path: str) -> list[dict]:
    """Return decrypted credentials matching a route, ordered by longest prefix match.

    The default toolkit implicitly contains ALL credentials — no join needed.
    Named toolkits are scoped via toolkit_credentials.
    """
    from src.db import DEFAULT_TOOLKIT_ID
    full_path = f"{host}/{path}".rstrip("/")
    async with get_db() as db:
        if toolkit_id == DEFAULT_TOOLKIT_ID:
            async with db.execute(
                """SELECT id, env_var, encrypted_value, auth_type, identity, routes
                   FROM credentials
                   WHERE EXISTS (
                       SELECT 1 FROM json_each(routes)
                       WHERE ? LIKE (value || '%')
                   )
                   ORDER BY (
                       SELECT MAX(length(value)) FROM json_each(routes)
                       WHERE ? LIKE (value || '%')
                   ) DESC""",
                (full_path, full_path),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                """SELECT c.id, c.env_var, c.encrypted_value, c.auth_type, c.identity, c.routes
                   FROM credentials c
                   JOIN toolkit_credentials cc ON c.id = cc.credential_id
                   WHERE cc.toolkit_id = ?
                   AND EXISTS (
                       SELECT 1 FROM json_each(c.routes)
                       WHERE ? LIKE (value || '%')
                   )
                   ORDER BY (
                       SELECT MAX(length(value)) FROM json_each(c.routes)
                       WHERE ? LIKE (value || '%')
                   ) DESC""",
                (toolkit_id, full_path, full_path),
            ) as cur:
                rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "value": decrypt(r[2]),
            "auth_type": r[3],
            "identity": r[4] if len(r) > 4 else None,
        }
        for r in rows
    ]


def _row_to_dict(row) -> dict:
    """Convert a credentials row to a dict for API responses.

    Column order (after migration 0004):
    0: id, 1: label, 2: env_var, 3: encrypted_value,
    4: created_at, 5: updated_at, 6: routes, 7: auth_type, 8: identity
    """
    routes_raw = row[6] if len(row) > 6 else "[]"
    try:
        routes = json.loads(routes_raw) if routes_raw else []
    except (json.JSONDecodeError, TypeError):
        routes = []
    return {
        "id": row[0],
        "label": row[1],
        # encrypted_value (row[3]) intentionally omitted
        "created_at": row[4],
        "updated_at": row[5],
        "routes": routes,
        "auth_type": row[7] if len(row) > 7 else None,
        "identity": row[8] if len(row) > 8 else None,
    }

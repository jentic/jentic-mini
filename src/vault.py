"""Fernet-encrypted credential vault."""
import os
import re
import uuid
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from src.db import get_db

_KEY_FILE = Path(os.getenv("DB_PATH", "/app/data/jentic-mini.db")).parent / "vault.key"

_COMMON_WORDS = {
    "api", "key", "token", "secret", "auth", "oauth",
    "credential", "credentials", "access", "the", "a", "an",
}


def _credential_slug(api_id: str | None, label: str) -> str:
    """Generate a semantic, URL-safe credential ID from api_id + label.

    Strategy:
      - Start with api_id (e.g. "api.elevenlabs.io")
      - Tokenize label; strip tokens appearing in api_id or that are common words
      - Slugify the remainder and append with '-' separator
      - If nothing remains, use api_id alone
      - If no api_id, slugify the label directly

    Examples:
      api.elevenlabs.io + "ElevenLabs API Key"  → "api.elevenlabs.io"
      api.github.com    + "GitHub PAT"          → "api.github.com-pat"
      api.openai.com    + "OpenAI Org Key"      → "api.openai.com-org"
      api.stripe.com    + "Stripe Live Secret"  → "api.stripe.com-live"
    """
    if not api_id:
        slug = re.sub(r"[^a-z0-9.-]+", "-", label.lower()).strip("-")
        return slug or "credential"

    api_tokens = set(re.split(r"[./\-_]", api_id.lower())) | _COMMON_WORDS
    label_parts = re.split(r"[\s\-_./]+", label.lower())
    remainder = [p for p in label_parts if p and p not in api_tokens]

    if remainder:
        suffix = re.sub(r"[^a-z0-9]+", "-", "-".join(remainder)).strip("-")
        return f"{api_id}-{suffix}" if suffix else api_id
    return api_id


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
    api_id: str | None = None,
    scheme_name: str | None = None,
) -> dict:
    base_slug = _credential_slug(api_id, label)
    enc = encrypt(value)

    async with get_db() as db:
        # Collision-safe semantic ID
        cid = base_slug
        suffix_n = 2
        while True:
            async with db.execute("SELECT id FROM credentials WHERE id=?", (cid,)) as cur:
                if not await cur.fetchone():
                    break
            cid = f"{base_slug}-{suffix_n}"
            suffix_n += 1

        await db.execute(
            "INSERT INTO credentials (id, label, env_var, encrypted_value, api_id, scheme_name) VALUES (?,?,?,?,?,?)",
            (cid, label, env_var, enc, api_id, scheme_name),
        )
        await db.commit()
        async with db.execute("SELECT * FROM credentials WHERE id=?", (cid,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row)


async def patch_credential(cid: str, label: str | None, value: str | None,
                           api_id: str | None = None, scheme_name: str | None = None) -> dict | None:
    async with get_db() as db:
        if label:
            await db.execute("UPDATE credentials SET label=?, updated_at=unixepoch() WHERE id=?", (label, cid))
        if value:
            enc = encrypt(value)
            await db.execute("UPDATE credentials SET encrypted_value=?, updated_at=unixepoch() WHERE id=?", (enc, cid))
        if api_id is not None:
            await db.execute("UPDATE credentials SET api_id=?, updated_at=unixepoch() WHERE id=?", (api_id, cid))
        if scheme_name is not None:
            await db.execute("UPDATE credentials SET scheme_name=?, updated_at=unixepoch() WHERE id=?", (scheme_name, cid))
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
    """
    Return the decrypted value for a credential by UUID.
    Used by auth_override to resolve vault_id references.
    """
    async with db.execute(
        "SELECT encrypted_value FROM credentials WHERE id=?", (vault_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return decrypt(row[0])


async def get_credential_ids_for_api(toolkit_id: str, api_id: str) -> list[str]:
    """Return credential IDs (no decryption) bound to a toolkit+api. Used for policy checks."""
    from src.db import DEFAULT_TOOLKIT_ID
    async with get_db() as db:
        if toolkit_id == DEFAULT_TOOLKIT_ID:
            async with db.execute(
                "SELECT id FROM credentials WHERE api_id = ?", (api_id,)
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                """SELECT c.id FROM credentials c
                   JOIN toolkit_credentials cc ON c.id = cc.credential_id
                   WHERE cc.toolkit_id = ? AND c.api_id = ?""",
                (toolkit_id, api_id),
            ) as cur:
                rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_credentials_for_api(toolkit_id: str, api_id: str) -> list[dict]:
    """
    Return credentials bound to a specific api_id.
    The default toolkit implicitly contains ALL credentials — no join needed.
    Named toolkits are scoped via toolkit_credentials.
    """
    from src.db import DEFAULT_TOOLKIT_ID
    async with get_db() as db:
        if toolkit_id == DEFAULT_TOOLKIT_ID:
            async with db.execute(
                "SELECT id, env_var, encrypted_value, scheme_name FROM credentials WHERE api_id = ?",
                (api_id,),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                """SELECT c.id, c.env_var, c.encrypted_value, c.scheme_name
                   FROM credentials c
                   JOIN toolkit_credentials cc ON c.id = cc.credential_id
                   WHERE cc.toolkit_id = ? AND c.api_id = ?""",
                (toolkit_id, api_id),
            ) as cur:
                rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "env_var": r[1],
            "value": decrypt(r[2]),
            "scheme_name": r[3],
        }
        for r in rows
    ]


def _row_to_dict(row) -> dict:
    # columns: id, label, env_var, encrypted_value, created_at, updated_at, api_id, scheme_name
    # env_var is an internal derived key — not exposed in API responses
    return {
        "id": row[0],
        "label": row[1],
        # encrypted_value (row[3]) intentionally omitted
        "created_at": row[4],
        "updated_at": row[5],
        "api_id": row[6] if len(row) > 6 else None,
        "scheme_name": row[7] if len(row) > 7 else None,
    }

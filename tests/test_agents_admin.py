"""Human admin agent lifecycle: decline (JWKS wiped), deregister (soft archive)."""


def _sample_jwks() -> dict:
    # RFC 8037 / OKP test vector (32-byte public coordinate, base64url)
    return {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": "11qYAAY5xuyJPig0M6_HbmJEsUKUn_3w1CzCJxZpkn4",
                "kid": "k1",
            }
        ]
    }


def test_deregister_agent_delete_returns_404_when_missing(admin_client):
    r = admin_client.delete("/agents/agnt_does_not_exist_zzzz")
    assert r.status_code == 404


def test_deregister_agent_soft_deletes_strips_jwks_and_grants(client, admin_client):
    reg = client.post(
        "/register",
        json={"client_name": "dereg-test", "jwks": _sample_jwks()},
    )
    assert reg.status_code == 201, reg.text
    cid = reg.json()["client_id"]

    d = admin_client.delete(f"/agents/{cid}")
    assert d.status_code == 204, d.text

    g = admin_client.get(f"/agents/{cid}")
    assert g.status_code == 200
    body = g.json()
    assert body["deleted_at"] is not None
    assert body["jwks"].get("keys") == []

    grants = admin_client.get(f"/agents/{cid}/grants").json()["grants"]
    assert grants == []

    active = admin_client.get("/agents?view=active").json()["agents"]
    assert all(a["client_id"] != cid for a in active)
    removed = admin_client.get("/agents?view=removed").json()["agents"]
    assert any(a["client_id"] == cid for a in removed)


def test_decline_pending_agent_clears_jwks_and_soft_delete_archive(client, admin_client):
    reg = client.post(
        "/register",
        json={"client_name": "decline-test", "jwks": _sample_jwks()},
    )
    assert reg.status_code == 201
    cid = reg.json()["client_id"]

    deny = admin_client.post(f"/agents/{cid}/deny")
    assert deny.status_code == 200
    assert deny.json()["status"] == "denied"

    detail = admin_client.get(f"/agents/{cid}")
    assert detail.status_code == 200
    dj = detail.json()
    assert dj["status"] == "denied"
    assert dj["jwks"].get("keys") == []

    assert admin_client.get(f"/agents/{cid}/grants").json()["grants"] == []

    assert admin_client.delete(f"/agents/{cid}").status_code == 204
    denied_removed = admin_client.get(f"/agents/{cid}").json()
    assert denied_removed["status"] == "denied"
    assert denied_removed["deleted_at"] is not None
    assert denied_removed["jwks"].get("keys") == []

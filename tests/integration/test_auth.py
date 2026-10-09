import pytest
from fastapi import Depends, FastAPI
import httpx
from sqlalchemy import update

from app.core.dependencies import get_current_admin
from app.database.session import get_db
from app.middleware.error_middleware import register_exception_handlers
from app.models.user import User, UserRole, UserStatus

BASE = "/api/v1/auth"
USER = {"name": "Asha", "email": "Asha@Example.com", "password": "Passw0rd!x"}


async def register(client, **overrides):
    return await client.post(f"{BASE}/register", json={**USER, **overrides})


async def login_token(client, email="asha@example.com", password=USER["password"]):
    r = await client.post(f"{BASE}/login", json={"email": email, "password": password})
    return r.json()["data"]["access_token"]


async def test_register_success_hides_password_and_lowercases_email(client):
    r = await register(client)
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["email"] == "asha@example.com"
    assert data["role"] == "USER" and data["status"] == "ACTIVE"
    assert "password" not in data and "password_hash" not in data


async def test_register_cannot_choose_admin_role(client):
    r = await register(client, role="ADMIN")
    assert r.json()["data"]["role"] == "USER"


async def test_register_duplicate_email_conflict(client):
    await register(client)
    r = await register(client, email="asha@example.com")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.parametrize("bad", [
    {"password": "short"},
    {"password": "x" * 73},
    {"email": "not-an-email"},
    {"name": "   "},
])
async def test_register_validation(client, bad):
    r = await register(client, **bad)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_login_and_me(client):
    await register(client)
    token = await login_token(client)
    r = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "asha@example.com"


async def test_login_wrong_password_and_unknown_email_same_error(client):
    await register(client)
    a = await client.post(f"{BASE}/login", json={"email": "asha@example.com", "password": "nope-nope"})
    b = await client.post(f"{BASE}/login", json={"email": "ghost@example.com", "password": "nope-nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


async def test_me_requires_valid_token(client):
    assert (await client.get(f"{BASE}/me")).status_code == 401
    r = await client.get(f"{BASE}/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


async def test_blocked_user_cannot_login_or_use_existing_token(client, session_factory):
    await register(client)
    token = await login_token(client)
    async with session_factory() as s:
        await s.execute(update(User).values(status=UserStatus.BLOCKED))
        await s.commit()
    r = await client.post(f"{BASE}/login", json={"email": "asha@example.com", "password": USER["password"]})
    assert r.status_code == 403 and r.json()["error"]["code"] == "USER_BLOCKED"
    r = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


async def test_admin_dependency_enforces_role(client, session_factory):
    # Throwaway route; real admin routes arrive in Phase 8.
    mini = FastAPI()
    register_exception_handlers(mini)

    async def override_db():
        async with session_factory() as s:
            yield s

    mini.dependency_overrides[get_db] = override_db

    @mini.get("/admin-only")
    async def admin_only(admin: User = Depends(get_current_admin)):
        return {"ok": True}

    await register(client)
    token = await login_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mini), base_url="http://t") as c:
        r = await c.get("/admin-only", headers=headers)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"

        async with session_factory() as s:
            await s.execute(update(User).values(role=UserRole.ADMIN))
            await s.commit()
        assert (await c.get("/admin-only", headers=headers)).status_code == 200

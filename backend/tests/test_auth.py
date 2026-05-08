from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.app import app
from app.auth import create_access_token, hash_password
from app.db import get_session
from app.models import User

# ── shared in-memory engine ───────────────────────────────────────────────────

_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(_engine)
    with Session(_engine) as session:
        yield session
    SQLModel.metadata.drop_all(_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── helpers ───────────────────────────────────────────────────────────────────


def _add_user(session: Session, username: str, role: str) -> User:
    user = User(username=username, hashed_password=hash_password("secret"), role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _token(username: str, role: str, **kw) -> str:
    return create_access_token({"sub": username, "role": role}, **kw)


CREATURE = {
    "name": "Sphinx",
    "mythology": "Egyptian",
    "creature_type": "Beast",
    "danger_level": 7,
}


# ── auth endpoint tests ───────────────────────────────────────────────────────


def test_login_returns_token(session, client):
    _add_user(session, "alice", "admin")
    r = client.post("/auth/token", data={"username": "alice", "password": "secret"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(session, client):
    _add_user(session, "bob", "viewer")
    r = client.post("/auth/token", data={"username": "bob", "password": "wrong"})
    assert r.status_code == 401


def test_register_creates_user(session, client):
    r = client.post(
        "/auth/register",
        json={"username": "carol", "password": "pass", "role": "viewer"},
    )
    assert r.status_code == 201
    assert r.json()["username"] == "carol"


def test_register_duplicate_username(session, client):
    _add_user(session, "dave", "viewer")
    r = client.post(
        "/auth/register",
        json={"username": "dave", "password": "pass", "role": "viewer"},
    )
    assert r.status_code == 400


# ── token validation tests ────────────────────────────────────────────────────


def test_missing_token_returns_401(client):
    r = client.post("/creatures/", json=CREATURE)
    assert r.status_code == 401


def test_expired_token_returns_401(session, client):
    _add_user(session, "exp_admin", "admin")
    token = _token("exp_admin", "admin", expires_delta=timedelta(seconds=-1))
    r = client.post(
        "/creatures/",
        json=CREATURE,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


def test_malformed_token_returns_401(client):
    r = client.post(
        "/creatures/",
        json=CREATURE,
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert r.status_code == 401


# ── role / scope tests ────────────────────────────────────────────────────────


def test_viewer_cannot_create_creature(session, client):
    _add_user(session, "viewer1", "viewer")
    token = _token("viewer1", "viewer")
    r = client.post(
        "/creatures/",
        json=CREATURE,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_viewer_cannot_delete_creature(session, client):
    # Create creature as admin first
    _add_user(session, "adm", "admin")
    adm_tok = _token("adm", "admin")
    creature_id = client.post(
        "/creatures/",
        json=CREATURE,
        headers={"Authorization": f"Bearer {adm_tok}"},
    ).json()["id"]

    _add_user(session, "viewer2", "viewer")
    tok = _token("viewer2", "viewer")
    r = client.delete(
        f"/creatures/{creature_id}",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 403


def test_admin_can_create_and_delete(session, client):
    _add_user(session, "superuser", "admin")
    tok = _token("superuser", "admin")
    headers = {"Authorization": f"Bearer {tok}"}

    r = client.post("/creatures/", json=CREATURE, headers=headers)
    assert r.status_code == 200
    creature_id = r.json()["id"]

    r = client.delete(f"/creatures/{creature_id}", headers=headers)
    assert r.status_code == 200


def test_get_creatures_is_public(client):
    r = client.get("/creatures/")
    assert r.status_code == 200

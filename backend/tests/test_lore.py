from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.app import app
from app.auth import create_access_token, hash_password
from app.db import get_session
from app.models import Creature, User

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


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session) -> User:
    user = User(username="lore_admin", hashed_password=hash_password("x"), role="admin")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_headers")
def admin_headers_fixture(admin_user: User) -> dict:
    token = create_access_token({"sub": admin_user.username, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def _seed_creature(session: Session, owner_id: int) -> int:
    c = Creature(
        name="Sphinx",
        mythology="Egyptian",
        creature_type="Guardian",
        danger_level=8,
        image_url="",
        owner_id=owner_id,
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c.id


# ── happy path ────────────────────────────────────────────────────────────────


def test_lore_returns_generated_text(session, client, admin_user, admin_headers):
    creature_id = _seed_creature(session, admin_user.id)
    expected = "The Sphinx stands eternal at the desert's edge, posing riddles to all who dare pass."

    with patch("app.services.lore.generate_lore", return_value=expected) as mock_fn:
        r = client.post(f"/creatures/{creature_id}/lore", headers=admin_headers)

    assert r.status_code == 200
    assert r.json() == {"lore": expected}
    mock_fn.assert_called_once_with("Sphinx", "Egyptian", "Guardian")


def test_lore_passes_correct_fields_to_gemini(
    session, client, admin_user, admin_headers
):
    """Verify that the endpoint forwards name, mythology, and creature_type — not other fields."""
    c = Creature(
        name="Kirin",
        mythology="Chinese",
        creature_type="Celestial",
        danger_level=2,
        image_url="",
        owner_id=admin_user.id,
    )
    session.add(c)
    session.commit()
    session.refresh(c)

    with patch(
        "app.services.lore.generate_lore", return_value="A lucky omen."
    ) as mock_fn:
        r = client.post(f"/creatures/{c.id}/lore", headers=admin_headers)

    assert r.status_code == 200
    mock_fn.assert_called_once_with("Kirin", "Chinese", "Celestial")


# ── 404 when creature doesn't exist ───────────────────────────────────────────


def test_lore_404_for_missing_creature(client, admin_headers):
    with patch("app.services.lore.generate_lore", return_value="irrelevant"):
        r = client.post("/creatures/99999/lore", headers=admin_headers)
    assert r.status_code == 404


# ── 503 when API key is absent ────────────────────────────────────────────────


def test_lore_503_when_api_key_missing(
    session, client, admin_user, admin_headers, monkeypatch
):
    creature_id = _seed_creature(session, admin_user.id)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Call through the real service (no mock) — should get 503
    r = client.post(f"/creatures/{creature_id}/lore", headers=admin_headers)
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.json()["detail"]


# ── Gemini SDK is invoked correctly ──────────────────────────────────────────


def test_lore_calls_gemini_sdk(session, client, admin_user, admin_headers, monkeypatch):
    """Integration-level check: real service code hits the Client stub."""
    creature_id = _seed_creature(session, admin_user.id)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.text = "Born of sand and starlight, the Sphinx endures."

    with patch("google.genai.Client") as mock_cls:
        mock_cls.return_value.models.generate_content.return_value = mock_response
        r = client.post(f"/creatures/{creature_id}/lore", headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["lore"] == "Born of sand and starlight, the Sphinx endures."
    mock_cls.assert_called_once_with(api_key="test-key")
    mock_cls.return_value.models.generate_content.assert_called_once_with(
        model="gemini-2.5-flash",
        contents=mock_cls.return_value.models.generate_content.call_args.kwargs[
            "contents"
        ],
    )

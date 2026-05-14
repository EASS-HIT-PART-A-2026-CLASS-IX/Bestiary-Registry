import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.app import app
from app.auth import create_access_token, hash_password
from app.db import get_session
from app.models import Creature, User
from app.services.creatures import _CSV_FIELDS

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
    user = User(username="csv_admin", hashed_password=hash_password("x"), role="admin")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_headers")
def admin_headers_fixture(admin_user: User) -> dict:
    token = create_access_token({"sub": admin_user.username, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def _seed(
    session: Session,
    name: str,
    mythology: str,
    creature_type: str,
    danger_level: int,
    owner_id: int = None,
) -> Creature:
    c = Creature(
        name=name,
        mythology=mythology,
        creature_type=creature_type,
        danger_level=danger_level,
        owner_id=owner_id,
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


# ── response shape ────────────────────────────────────────────────────────────


def test_export_returns_200(client, admin_headers):
    r = client.get("/creatures/export/csv", headers=admin_headers)
    assert r.status_code == 200


def test_export_content_type_is_csv(client, admin_headers):
    r = client.get("/creatures/export/csv", headers=admin_headers)
    assert "text/csv" in r.headers["content-type"]


def test_export_content_disposition(client, admin_headers):
    r = client.get("/creatures/export/csv", headers=admin_headers)
    cd = r.headers["content-disposition"]
    assert "attachment" in cd
    assert "creatures.csv" in cd


# ── CSV structure ─────────────────────────────────────────────────────────────


def test_export_has_correct_column_headers(client, admin_headers):
    r = client.get("/creatures/export/csv", headers=admin_headers)
    reader = csv.DictReader(io.StringIO(r.text))
    assert reader.fieldnames == _CSV_FIELDS


def test_export_empty_db_yields_header_only(client, admin_headers):
    r = client.get("/creatures/export/csv", headers=admin_headers)
    reader = csv.DictReader(io.StringIO(r.text))
    assert list(reader) == []


# ── data correctness ──────────────────────────────────────────────────────────


def test_export_contains_seeded_creatures(session, client, admin_user, admin_headers):
    _seed(session, "Dragon", "Norse", "Reptile", 9, owner_id=admin_user.id)
    _seed(session, "Unicorn", "Greek", "Equine", 2, owner_id=admin_user.id)

    r = client.get("/creatures/export/csv", headers=admin_headers)
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)

    assert len(rows) == 2
    names = {row["name"] for row in rows}
    assert names == {"Dragon", "Unicorn"}


def test_export_row_values_match_creature_fields(
    session, client, admin_user, admin_headers
):
    c = _seed(session, "Sphinx", "Egyptian", "Guardian", 7, owner_id=admin_user.id)

    r = client.get("/creatures/export/csv", headers=admin_headers)
    reader = csv.DictReader(io.StringIO(r.text))
    row = list(reader)[0]

    assert row["name"] == "Sphinx"
    assert row["mythology"] == "Egyptian"
    assert row["creature_type"] == "Guardian"
    assert int(row["danger_level"]) == 7
    assert row["id"] == str(c.id)

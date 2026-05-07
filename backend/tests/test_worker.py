import pytest
from unittest.mock import AsyncMock
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.worker as worker_module
from app.models import Creature


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(name="worker_engine")
def worker_engine_fixture(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr(worker_module, "engine", test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


def _seed(engine) -> int:
    with Session(engine) as session:
        c = Creature(
            name="Dragon",
            mythology="Norse",
            creature_type="Beast",
            danger_level=5,
        )
        session.add(c)
        session.commit()
        session.refresh(c)
        return c.id


@pytest.mark.anyio
async def test_refresh_skips_creature_with_existing_key(worker_engine):
    """A creature whose idempotency key is already set in Redis must be skipped."""
    creature_id = _seed(worker_engine)

    mock_redis = AsyncMock()
    mock_redis.exists.return_value = 1  # key already present

    result = await worker_module.refresh_creatures({"redis": mock_redis})

    mock_redis.exists.assert_called_once_with(f"refresh:creature:{creature_id}")
    mock_redis.set.assert_not_called()
    assert result["refreshed"] == 1


@pytest.mark.anyio
async def test_refresh_processes_creature_without_key(worker_engine):
    """A creature without an idempotency key must be processed and the key set."""
    creature_id = _seed(worker_engine)

    mock_redis = AsyncMock()
    mock_redis.exists.return_value = 0  # key absent

    result = await worker_module.refresh_creatures({"redis": mock_redis})

    mock_redis.exists.assert_called_once_with(f"refresh:creature:{creature_id}")
    mock_redis.set.assert_called_once_with(
        f"refresh:creature:{creature_id}", "1", ex=worker_module.IDEMPOTENCY_TTL
    )
    assert result["refreshed"] == 1


@pytest.mark.anyio
async def test_refresh_empty_db_returns_zero(worker_engine):
    """refresh_creatures on an empty database should succeed and report 0."""
    mock_redis = AsyncMock()

    result = await worker_module.refresh_creatures({"redis": mock_redis})

    mock_redis.exists.assert_not_called()
    assert result["refreshed"] == 0


@pytest.mark.anyio
async def test_refresh_retries_on_failure(worker_engine, monkeypatch):
    """_process_one failures trigger up to 3 attempts before re-raising."""
    _seed(worker_engine)

    call_count = 0

    async def _always_fail(creature: Creature) -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(worker_module, "_process_one", _always_fail)
    monkeypatch.setattr(worker_module, "asyncio", __import__("asyncio"))

    mock_redis = AsyncMock()
    mock_redis.exists.return_value = 0

    # Patch sleep so tests don't actually wait
    async def _no_sleep(_delay):
        pass

    monkeypatch.setattr("app.worker.asyncio.sleep", _no_sleep)

    with pytest.raises(RuntimeError, match="simulated failure"):
        await worker_module.refresh_creatures({"redis": mock_redis})

    assert call_count == 3
    mock_redis.set.assert_not_called()

"""
Standalone creature refresh script.

Fetches all creatures from the DB and re-processes each one with:
  - Bounded concurrency (Semaphore)
  - Exponential-backoff retries (up to 3 attempts)
  - Redis-backed idempotency (24-hour TTL per creature)

Usage (from the backend/ directory):
    uv run python ../scripts/refresh.py

Environment variables:
    REDIS_URL   Redis DSN (default: redis://localhost:6379)
    DB_PATH     SQLite file path (default: creatures.db)
"""

import asyncio
import os
import sys

# Allow `from app.*` imports when run from the backend/ directory or project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from arq.connections import RedisSettings, create_pool
from sqlmodel import Session, select

from app.db import engine
from app.models import Creature

IDEMPOTENCY_TTL = 86_400  # 24 hours
CONCURRENCY = 5
MAX_RETRIES = 3


async def _process_one(creature: Creature) -> None:
    """Per-creature work. Extend here for real refresh logic (e.g. re-fetch avatar URL)."""
    await asyncio.sleep(0)


async def _refresh_one(redis, sem: asyncio.Semaphore, creature: Creature) -> None:
    key = f"refresh:creature:{creature.id}"
    async with sem:
        if await redis.exists(key):
            print(f"  skip  [{creature.id}] {creature.name} (idempotency key present)")
            return

        last_exc: Exception = RuntimeError("no attempts made")
        for attempt in range(MAX_RETRIES):
            try:
                await _process_one(creature)
                break
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    delay = 2**attempt
                    print(
                        f"  retry [{creature.id}] attempt {attempt + 1} — sleeping {delay}s"
                    )
                    await asyncio.sleep(delay)
        else:
            print(f"  error [{creature.id}] {creature.name}: {last_exc}")
            raise last_exc

        await redis.set(key, "1", ex=IDEMPOTENCY_TTL)
        print(f"  done  [{creature.id}] {creature.name}")


async def refresh_all(redis) -> dict:
    def _fetch_all() -> list[Creature]:
        with Session(engine) as session:
            return list(session.exec(select(Creature)).all())

    creatures = await asyncio.to_thread(_fetch_all)
    print(
        f"Found {len(creatures)} creatures — refreshing (concurrency={CONCURRENCY}) ..."
    )

    sem = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(
        *[_refresh_one(redis, sem, c) for c in creatures],
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, Exception)]
    return {"total": len(creatures), "errors": len(errors)}


async def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    print(f"Connecting to Redis at {redis_url} ...")
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    try:
        summary = await refresh_all(redis)
        print(
            f"\nRefresh complete — {summary['total']} creatures, "
            f"{summary['errors']} error(s)."
        )
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())

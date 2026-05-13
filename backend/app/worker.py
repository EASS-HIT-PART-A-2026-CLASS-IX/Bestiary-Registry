import asyncio
import os

from sqlmodel import Session, select
from arq.connections import RedisSettings

from app.db import engine
from app.models import Creature

IDEMPOTENCY_TTL = 86_400  # 24 hours


async def _process_one(creature: Creature) -> None:
    """Placeholder for per-creature refresh work (e.g. re-fetch avatar URL)."""
    await asyncio.sleep(0)


async def _refresh_one(redis, sem: asyncio.Semaphore, creature: Creature) -> None:
    key = f"refresh:creature:{creature.id}"
    async with sem:
        if await redis.exists(key):
            return

        last_exc: Exception = RuntimeError("no attempts made")
        for attempt in range(3):
            try:
                await _process_one(creature)
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
        else:
            raise last_exc

        await redis.set(key, "1", ex=IDEMPOTENCY_TTL)


async def generate_creature_lore_task(ctx: dict, creature_id: int) -> None:
    """Fetch creature from DB, generate lore via Gemini, save result back."""
    from app.services.lore import generate_lore

    def _run() -> None:
        with Session(engine) as session:
            creature = session.get(Creature, creature_id)
            if not creature:
                return
            try:
                lore = generate_lore(
                    creature.name, creature.mythology, creature.creature_type
                )
                creature.lore = lore
                session.add(creature)
                session.commit()
            except Exception:
                pass

    await asyncio.to_thread(_run)


async def refresh_creatures(ctx: dict) -> dict:
    redis = ctx["redis"]
    sem = asyncio.Semaphore(5)

    def _fetch_all() -> list[Creature]:
        with Session(engine) as session:
            return list(session.exec(select(Creature)).all())

    creatures = await asyncio.to_thread(_fetch_all)
    await asyncio.gather(*[_refresh_one(redis, sem, c) for c in creatures])
    return {"refreshed": len(creatures)}


async def startup(ctx: dict) -> None:
    pass


async def shutdown(ctx: dict) -> None:
    pass


class WorkerSettings:
    functions = [refresh_creatures, generate_creature_lore_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    health_check_interval = 10

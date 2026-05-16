import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from arq.connections import create_pool, RedisSettings
from app.db import create_db_and_tables, run_migrations, seed_default_admin
from app.limiter import limiter
from app.routers import auth, creatures, classes


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    run_migrations()
    seed_default_admin()
    try:
        app.state.arq = await create_pool(
            RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
        )
    except Exception:
        app.state.arq = None
    yield
    if getattr(app.state, "arq", None):
        await app.state.arq.aclose()


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(creatures.router)
app.include_router(classes.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "creatures-backend"}

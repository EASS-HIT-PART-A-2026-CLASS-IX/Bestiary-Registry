from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import create_db_and_tables, run_migrations, seed_default_admin
from app.routers import auth, creatures, classes


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    run_migrations()
    seed_default_admin()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(creatures.router)
app.include_router(classes.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "creatures-backend"}

# Backend Documentation Index

Parent: [Root](../README.md)

## Files Covered
- `backend/` directory
- `backend/main.py`
- `backend/app/app.py`
- `backend/app/db.py`

FastAPI backend for Bestiary Registry. Manages creatures and creature classes via a REST API backed by SQLite.

## Running

```bash
cd backend && uv run python main.py   # http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

## Module Docs

### [app/models.md](app/models.md)

Creature and CreatureClass SQLModel schemas.
**Read when:** Adding/modifying fields, understanding data structure.

### [app/routers/routers.md](app/routers/routers.md)

API endpoints — routes, request/response shapes, status codes.
**Read when:** Adding endpoints, changing API contracts, debugging HTTP errors.

### [app/services/services.md](app/services/services.md)

Business logic — cascade rename, auto-avatar, auto-timestamps, auto-class registration.
**Read when:** Changing business rules, adding side effects to CRUD operations.

## App Entry Points

### `main.py`
Starts uvicorn on port 8000 with hot reload. Run directly for local development.

### `app/app.py`
Creates the FastAPI instance, registers routers (`/creatures`, `/classes`), and defines the lifespan context (creates all DB tables on startup).

### `app/db.py`
- Creates SQLite engine (`creatures.db`)
- `get_session()` — FastAPI dependency for DB sessions (used via `Depends`)

## Testing

```bash
cd backend && uv run pytest tests/
```

Tests use FastAPI `TestClient` with an in-memory SQLite DB — never touches `creatures.db`.

| File | Coverage |
|------|----------|
| `tests/test_creatures.py` | 13 tests: CRUD, 404, validation, persistence |
| `tests/test_creature_classes.py` | 8 tests: CRUD, unique constraint, cascade rename |
| `tests/test_health.py` | Health endpoint check |

# EX3 Orchestration Notes

## Architecture Overview

The Bestiary Registry is a four-service system coordinated by Docker Compose.

```
┌─────────────────┐        HTTP         ┌──────────────────────┐
│  Streamlit      │ ──────────────────► │  FastAPI Backend     │
│  Frontend       │                     │  (port 8000)         │
│  (port 8501)    │                     │                      │
└─────────────────┘                     │  • CRUD /creatures   │
                                        │  • CRUD /classes     │
                                        │  • JWT /auth         │
                                        │  • CSV export        │
                                        └──────────┬───────────┘
                                                   │ SQLite
                                                   ▼
                                        ┌──────────────────────┐
                                        │  SQLite + SQLModel   │
                                        │  (creatures.db)      │
                                        └──────────────────────┘
                                                   │
                                        ┌──────────┴───────────┐
                                        │  Redis 7             │
                                        │  (port 6379)         │
                                        │  • Job queue (ARQ)   │
                                        │  • Idempotency keys  │
                                        └──────────┬───────────┘
                                                   │ ARQ
                                                   ▼
                                        ┌──────────────────────┐
                                        │  ARQ Worker          │
                                        │                      │
                                        │  • generate_lore     │
                                        │  • refresh_creatures │
                                        └──────────┬───────────┘
                                                   │ google-genai
                                                   ▼
                                        ┌──────────────────────┐
                                        │  Gemini LLM          │
                                        │  (gemini-2.5-flash)  │
                                        └──────────────────────┘
```

### Services

**FastAPI Backend** (`backend/`) — the central API layer. Handles all CRUD
operations for creatures and classes, JWT authentication, CSV export, and
avatar persistence. On startup it creates the SQLite schema, runs additive
column migrations, seeds the default admin user, and opens an ARQ connection
pool to Redis. When a creature is created, the endpoint enqueues a
`generate_creature_lore_task` job and returns immediately — lore is written
asynchronously.

**SQLite + SQLModel** — the persistence layer. A single `creatures.db` file
holds two tables: `creature` and `app_user`. `run_migrations()` in `db.py`
uses `PRAGMA table_info` to add missing columns idempotently, meaning the
schema can evolve without destructive migrations or committed `.db` artifacts.

**Streamlit Frontend** (`frontend/`) — a multi-page dashboard that talks
exclusively to the FastAPI backend over HTTP. Renders the creature registry
table with live search, multi-faceted filters, metrics cards, and dialogs for
creating, editing, and deleting entries. JWT token is persisted in
`st.query_params` so sessions survive page refreshes.

**Redis 7** — serves two roles: ARQ job queue (the backend pushes jobs, the
worker pops them) and idempotency store (the worker writes a 24-hour key per
creature so repeat runs are skipped).

**ARQ Worker** (`backend/app/worker.py`) — an async worker process that
consumes jobs from Redis. Implements bounded concurrency (`asyncio.Semaphore(5)`),
exponential-backoff retries (up to 3 attempts), and Redis-backed idempotency.
Registers two task functions: `generate_creature_lore_task` (calls Gemini and
saves the result to the DB) and `refresh_creatures` (periodic per-creature
maintenance with idempotency).

**Gemini LLM** (`backend/app/services/lore.py`) — the fourth microservice.
Called by the worker task with the creature's name, mythology, and type.
Returns a 2–3 sentence atmospheric lore description via the `google-genai`
SDK (`gemini-2.5-flash` model). Requires `GEMINI_API_KEY` in the environment;
raises HTTP 503 if the key is absent.

---

## Redis Trace Excerpt

Worker startup log captured from `docker compose logs worker`:

```
16:05:56: Starting worker for 1 functions: refresh_creatures
16:05:56: redis_version=7.4.7 mem_usage=1.01M clients_connected=1 db_keys=0
```

The first line confirms ARQ connected to Redis and registered its task
functions. The second line shows the Redis server version, current memory
usage, connected client count, and number of keys in the DB (0 on a fresh
start before any jobs are enqueued).

---

## JWT Security

### Authentication model

Passwords are hashed with **bcrypt** via `passlib` — no plaintext credentials
are stored anywhere. On login (`POST /auth/token`), the backend verifies the
password hash and issues a signed **HS256 JWT** containing the `sub` (username)
and `role` claims, with a 30-minute expiry.

```python
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-do-not-use-in-production")
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

The `dev-secret-do-not-use-in-production` default is intentionally visible so
developers notice it must be overridden; the backend will work locally without
setting `SECRET_KEY` but production deployments must set it to a random value.

### Protected routes and role checks

All mutating creature endpoints require an authenticated user with the `admin`
role. The dependency chain is:

```
request → oauth2_scheme (Bearer token) → get_current_user (validates JWT, loads User)
        → require_role("admin") (raises 403 if role != "admin")
```

| Method | Path | Protection |
|--------|------|-----------|
| `POST` | `/creatures/` | admin only |
| `PUT` | `/creatures/{id}` | admin only |
| `DELETE` | `/creatures/{id}` | admin only |
| `GET` | `/creatures/` | public |
| `GET` | `/creatures/{id}` | public |
| `GET` | `/auth/me` | authenticated (any role) |
| `PUT` | `/auth/me/password` | authenticated (any role) |
| `PUT` | `/auth/me/avatar` | authenticated (any role) |

Read endpoints are intentionally public so the Streamlit frontend can display
the registry without requiring a token.

### Token expiry and scope failures

Tests in `backend/tests/test_auth.py` and `backend/tests/test_lore.py` verify
that:

- Requests with a missing or malformed token receive **401 Unauthorized**.
- Requests with a valid token but insufficient role receive **403 Forbidden**.
- Requests with an expired token (clock-advanced in tests) receive **401**.

### JWT key rotation

To rotate the signing key in production:

1. Generate a new secret: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Set the new value as `SECRET_KEY` in the environment (Docker Compose env,
   Render dashboard, or `.env` file).
3. Restart the backend container: `docker compose up -d backend`

All existing tokens are immediately invalid because they were signed with the
old key. Users will need to log in again to obtain a new token. There is no
grace period — this is intentional for a security rotation event.

---

## Running the Stack

Full launch instructions, health check verification, and troubleshooting are
documented in [`docs/runbooks/compose.md`](../runbooks/compose.md).

Quick start:

```bash
# Set required secrets
export GEMINI_API_KEY=your-key-here
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Build and start all services
docker compose up --build -d

# Verify all services are healthy
docker compose ps
```

---

## Running Tests

```bash
cd backend

# Full test suite (backend + frontend tests)
uv run python -m pytest ../frontend/tests/ -v

# Backend only
uv run python -m pytest tests/ -v

# Specific test file
uv run python -m pytest tests/test_worker.py -v

# Async worker tests (uses pytest-anyio)
uv run python -m pytest tests/test_worker.py -v

# Linting and format check
uv run ruff check .
uv run ruff format --check .
```

The CI pipeline (`.github/workflows/ci.yml`) runs ruff and the full pytest
suite on every push and pull request to `main`.

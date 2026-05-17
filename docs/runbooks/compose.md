# Compose Runbook

## Files Covered
- `compose.yaml`
- `.github/workflows/ci.yml`

Three-service stack: **backend** (FastAPI on port 8000), **redis** (Redis 7), **worker** (ARQ async worker).
Redis must be healthy before either the backend or worker starts (`depends_on: condition: service_healthy`).

---

## Starting the Stack

```bash
# Build images and start all services in the background
docker compose up --build -d

# Follow logs for all services
docker compose logs -f

# Follow logs for a single service
docker compose logs -f backend
docker compose logs -f worker
```

To stop and remove containers:

```bash
docker compose down
```

To also remove volumes:

```bash
docker compose down -v
```

---

## Verifying Service Health

Docker tracks the health of each service. Check the current status of all containers:

```bash
docker compose ps
```

The `STATUS` column shows `healthy`, `unhealthy`, or `starting`.

To watch health transitions in real time:

```bash
watch -n 5 docker compose ps
```

### Per-service health checks

| Service | Health check | Expected result |
|---------|-------------|-----------------|
| `redis` | `redis-cli ping` | `PONG` |
| `backend` | `GET http://localhost:8000/` | HTTP 200 |
| `worker` | `arq app.worker.WorkerSettings --check` | exit 0 |

Run a health check manually against a running container:

```bash
# Redis
docker compose exec redis redis-cli ping

# Backend (returns JSON)
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/').read())"

# Worker — queries Redis for a live worker heartbeat
docker compose exec worker uv run arq app.worker.WorkerSettings --check
```

---

## Verifying Health Headers

The backend root endpoint returns a JSON body. To inspect the full response headers:

```bash
curl -si http://localhost:8000/ | head -30
```

Expected response headers include:

```
HTTP/1.1 200 OK
content-type: application/json
```

To check a specific header value:

```bash
curl -si http://localhost:8000/ | grep -i content-type
```

---

## Rate-Limit Headers

The backend uses `slowapi` to enforce a limit of **100 requests per minute per IP**.
Every response includes three headers:

| Header | Meaning |
| :--- | :--- |
| `X-RateLimit-Limit` | Maximum requests allowed in the window (100) |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

### Verify headers on a normal request

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=admin123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -D - http://localhost:8000/creatures/ \
  -H "Authorization: Bearer $TOKEN" \
  -o /dev/null | grep -i x-ratelimit
```

Expected output:

```
x-ratelimit-limit: 100
x-ratelimit-remaining: 99
x-ratelimit-reset: 1234567890
```

### Trigger a 429 Too Many Requests

Send 101 requests in rapid succession to exhaust the window:

```bash
for i in $(seq 1 101); do curl -si http://localhost:8000/ | grep -E "HTTP/|x-ratelimit"; done
```

The 101st response should return:

```
HTTP/1.1 429 Too Many Requests
```

---

## Running Tests in CI

### Current CI (pytest + ruff)

The CI pipeline defined in `.github/workflows/ci.yml` runs on every push and pull
request to `main`. It installs dependencies with `uv`, checks formatting with
`ruff`, and runs the full test suite with `pytest`:

```yaml
- name: Run ruff (format check + lint)
  run: |
    uv run ruff format --check .
    uv run ruff check .

- name: Run tests
  run: |
    uv run python -m pytest
```

Run the same checks locally:

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest
```

### Adding Schemathesis (OpenAPI contract testing)

[Schemathesis](https://schemathesis.readthedocs.io/) fuzzes every endpoint
defined in the OpenAPI schema and checks that responses match their declared
shapes. To add it:

**1. Install Schemathesis:**

```bash
cd backend
uv add --dev schemathesis
```

**2. Run against the live stack:**

```bash
# Start the stack first
docker compose up -d

# Run Schemathesis against the OpenAPI schema
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=admin123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
uv run schemathesis run http://localhost:8000/openapi.json \
  --checks not_a_server_error \
  --max-examples 10 \
  --rate-limit 60/m \
  --phases coverage,fuzzing \
  --exclude-path "/creatures/{creature_id}/lore" \
  -H "Authorization: Bearer $TOKEN"
```

**3. Add a pytest-based Schemathesis test** (runs without a live server, using
the FastAPI `TestClient`):

```python
# backend/tests/test_schemathesis.py
import schemathesis
from app.app import app

schema = schemathesis.from_asgi("/openapi.json", app)

@schema.parametrize()
def test_api_schema(case):
    response = case.call_asgi()
    case.validate_response(response)
```

**4. Add to CI** — append a step to `.github/workflows/ci.yml`:

```yaml
- name: Run Schemathesis contract tests
  run: |
    source .venv/bin/activate
    uv run python -m pytest tests/test_schemathesis.py -v
```

---

## Rebuilding After Code Changes

```bash
# Rebuild only the changed service (e.g. backend)
docker compose up --build -d backend

# Rebuild everything
docker compose up --build -d
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `worker` stays `unhealthy` | `docker compose logs worker` — confirm Redis URL is reachable and `REDIS_URL` env var is set |
| `backend` stays `starting` for > 30s | `docker compose logs backend` — look for import errors or port conflicts |
| Redis health never becomes `healthy` | `docker compose logs redis` — check for port 6379 conflicts on the host |

# Compose Runbook

## Files Covered
- `compose.yaml`

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

## Checking Rate-Limit Headers

If rate limiting is enabled on the backend, each response will include headers such as:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1700000060
```

To inspect them:

```bash
curl -si http://localhost:8000/creatures | grep -i x-ratelimit
```

To trigger a rate-limit response (HTTP 429) and confirm the headers are present:

```bash
for i in $(seq 1 110); do curl -si http://localhost:8000/creatures | grep -i "x-ratelimit\|HTTP/"; done
```

---

## Rebuilding After Code Changes

```bash
# Rebuild only the changed service (e.g. backend)
docker compose up --build -d backend

# Rebuild everything
docker compose up --build -d
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `worker` stays `unhealthy` | `docker compose logs worker` — confirm Redis URL is reachable and `REDIS_URL` env var is set |
| `backend` stays `starting` for > 30s | `docker compose logs backend` — look for import errors or port conflicts |
| Redis health never becomes `healthy` | `docker compose logs redis` — check for port 6379 conflicts on the host |

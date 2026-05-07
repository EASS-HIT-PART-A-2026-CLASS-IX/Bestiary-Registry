# Project Instructions

## General Rules

- Do NOT scan the whole project files by default.
- Only read documentation files and code files that are directly relevant to the current task.
- If you are unsure about the relevant documentation files, **ask before reading**.
- If a task touches multiple modules, confirm which ones need to be read before proceeding.
- Prefer reading individual files over directory-wide scans.
- **Always ask before changing the `CLAUDE.md` file.**

## Documentation Management

- When creating new modules or logic components, create corresponding documentation files.
- When updating code in existing modules, update the corresponding documentation files.
- Documentation files should be located near the code they document.
- Keep documentation concise - focus on what the module does, its main components, and when it should be modified.
- **Keep the "Documentation Files" section current** - add new entries when creating docs, remove entries for deleted modules. Each entry must explain what it documents and **when it's relevant to read.**
- Each documentation file must include a `## Files Covered` section at the top.

### Tiered Documentation Structure

- `CLAUDE.md` → folder index → specific module docs → code files.
- For module folders, create an index doc (e.g., `backend/backend.md`) as a navigation hub.

## Architecture

```
CLAUDE.md                    - This file
backend/                     - FastAPI backend
    main.py                  - Entry point (uvicorn runner)
    app/
        app.py               - FastAPI app instance + lifespan (DB table creation)
        db.py                - SQLite engine, session dependency
        models.py            - SQLModel schemas: Creature, CreatureClass
        routers/
            creatures.py     - GET/POST/PUT/DELETE /creatures endpoints
            classes.py       - GET/POST/PUT/DELETE /classes endpoints
        services/
            creatures.py     - Business logic: CRUD, auto-avatar, timestamps
            classes.py       - Business logic: CRUD, cascade rename
    tests/
        test_creatures.py    - 13 tests (CRUD, 404, validation)
        test_creature_classes.py - 8 tests (CRUD, unique, cascade)
        test_health.py       - Health check test
    seed_classes.py          - Seeds 8 default creature classes (idempotent)
    Dockerfile               - Docker build
    pyproject.toml           - Dependencies (uv)
frontend/                    - Streamlit frontend
    dashboard.py             - Main app: registry table, filters, CRUD dialogs
    sidebar.py               - Navigation (Registry, Realm Map, Settings)
    settings.py              - Admin panel: class management
    realm_map.py             - Static map image display
    api_client.py            - HTTP client wrapper around requests
    api_utils.py             - Streamlit cache layer (2s TTL) + clear_cache()
    style.css                - Custom dark theme CSS
```

## Running the Project

```bash
# Backend (http://localhost:8000)
cd backend && uv run python main.py

# Frontend (http://localhost:8501) — in a separate terminal
cd backend && uv run python -m streamlit run ../frontend/dashboard.py

# Tests
cd backend && uv run pytest tests/

# Seed default classes (first time)
cd backend && uv run python seed_classes.py
```

## Documentation Files

### [backend/backend.md](backend/backend.md)

Index for the backend folder — lists all backend docs and when to read each one.
**Read when:** Starting any backend task.

### [backend/app/models.md](backend/app/models.md)

Creature and CreatureClass SQLModel schemas — fields, relationships, auto-behaviors.
**Read when:** Adding/modifying model fields, understanding data structure, adding new models.

### [backend/app/routers/routers.md](backend/app/routers/routers.md)

API endpoints for creatures and classes — routes, request/response shapes.
**Read when:** Adding new endpoints, changing API contracts, debugging HTTP errors.

### [backend/app/services/services.md](backend/app/services/services.md)

Business logic — cascade rename, auto-avatar, auto-timestamps, auto-class registration.
**Read when:** Changing business rules, adding side effects to CRUD operations.

### [frontend/frontend.md](frontend/frontend.md)

Streamlit frontend — pages, components, API client, caching layer.
**Read when:** Any frontend change — new pages, UI components, or API calls.

## Known Tasks

Each task lists the relevant documentation files to read first.

### Adding a New Field to Creature

Relevant docs: `backend/app/models.md`, `backend/app/services/services.md`.

1. Add field to `Creature` model in `backend/app/models.py`
2. If the field has auto-behavior (default, computed), add it in `backend/app/services/creatures.py`
3. Update relevant routers if request/response shape changes
4. Add/update field in frontend forms in `frontend/dashboard.py`
5. Update `backend/app/models.md`

### Adding a New API Endpoint

Relevant docs: `backend/app/routers/routers.md`, `backend/app/services/services.md`.

1. Add service function in the relevant `backend/app/services/*.py`
2. Add route in the relevant `backend/app/routers/*.py`
3. Add method to `frontend/api_client.py` if frontend needs it
4. Add cached wrapper in `frontend/api_utils.py` if needed
5. Update `backend/app/routers/routers.md`

### Adding a New Frontend Page

Relevant docs: `frontend/frontend.md`.

1. Create new file in `frontend/` (e.g., `frontend/my_page.py`)
2. Add navigation button in `frontend/sidebar.py`
3. Handle the new page in `frontend/dashboard.py` (check session state for current page)
4. Update `frontend/frontend.md`

### Running Tests

```bash
cd backend && uv run pytest tests/
cd backend && uv run pytest tests/test_creatures.py -v   # specific file
```

Tests use FastAPI `TestClient` with an in-memory SQLite DB (not the real `creatures.db`).

### Seeding / Resetting Classes

```bash
cd backend && uv run python seed_classes.py    # Add default 8 classes (idempotent)
cd backend && uv run python update_classes.py  # Randomize all creature_type values (demo/testing)
```

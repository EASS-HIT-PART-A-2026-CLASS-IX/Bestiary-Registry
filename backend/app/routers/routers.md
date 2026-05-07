# Routers Documentation

Parent: [Backend](../../backend.md)

## Files Covered
- `backend/app/routers/creatures.py`
- `backend/app/routers/classes.py`

API endpoint definitions. Routes delegate directly to services — no business logic here.

## Creatures Router (`/creatures`)

| Method | Path | Description | Success | Error |
|--------|------|-------------|---------|-------|
| `POST` | `/creatures/` | Create creature | 200 | 422 validation |
| `GET` | `/creatures/` | List all creatures | 200 | — |
| `GET` | `/creatures/{id}` | Get single creature | 200 | 404 |
| `PUT` | `/creatures/{id}` | Update creature | 200 | 404, 422 |
| `DELETE` | `/creatures/{id}` | Delete creature | 200 | 404 |

## Classes Router (`/classes`)

| Method | Path | Description | Success | Error |
|--------|------|-------------|---------|-------|
| `POST` | `/classes/` | Create class | 200 | 400 duplicate name |
| `GET` | `/classes/` | List all classes | 200 | — |
| `PUT` | `/classes/{id}` | Update class (cascade rename) | 200 | 404, 400 |
| `DELETE` | `/classes/{id}` | Delete class | 200 | 404 |

## Notes

- All routes use `Depends(get_session)` for DB session injection
- Business logic (auto-avatar, cascade rename, etc.) lives in `services/` — see [services.md](../services/services.md)
- Swagger UI available at `http://localhost:8000/docs`

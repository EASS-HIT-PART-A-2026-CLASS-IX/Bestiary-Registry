# Services Documentation

Parent: [Backend](../../backend.md)

## Files Covered
- `backend/app/services/creatures.py`
- `backend/app/services/classes.py`

Business logic layer. Routers delegate here — this is where side effects and rules live.

## Creatures Service (`services/creatures.py`)

### CRUD Operations
- `get_creatures(session)` — Returns all creatures
- `get_creature(id, session)` — Returns one creature or raises 404
- `create_creature(creature, session)` — Creates creature with auto-behaviors
- `update_creature(id, data, session)` — Updates creature with auto-behaviors
- `delete_creature(id, session)` — Deletes creature or raises 404

### Auto-Behaviors on Create/Update

| Behavior | Trigger | Logic |
|----------|---------|-------|
| Auto-avatar | `image_url` not provided | Sets URL to `https://api.dicebear.com/9.x/identicon/svg?seed={name}` |
| Auto-timestamp | Every create/update | Sets `last_modify` to current UTC ISO string |
| Auto-class | `creature_type` not in DB | Creates a new CreatureClass with default neutral colors |

## Classes Service (`services/classes.py`)

### CRUD Operations
- `get_classes(session)` — Returns all classes
- `get_class(id, session)` — Returns one class or raises 404
- `create_class(cls, session)` — Creates class, raises 400 if name already exists
- `update_class(id, data, session)` — Updates class with cascade rename
- `delete_class(id, session)` — Deletes class or raises 404

### Cascade Rename

When a class is renamed, all creatures with `creature_type == old_name` are updated to the new name. This happens automatically in `update_class` — no extra steps needed.

```
update_class(id, {name: "New Name"})
  → finds old name
  → updates CreatureClass.name
  → updates all Creature.creature_type where == old name
```

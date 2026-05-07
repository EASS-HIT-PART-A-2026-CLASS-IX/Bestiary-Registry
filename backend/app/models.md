# Models Documentation

Parent: [Backend](../backend.md)

## Files Covered
- `backend/app/models.py`

SQLModel schemas for Bestiary Registry. Defines the two core data models and their relationships.

## CreatureClass

Represents a category/type for creatures (e.g., Draconic, Fae, Abyssal).

| Field | Type | Notes |
|-------|------|-------|
| `id` | int (PK) | Auto-generated |
| `name` | str (unique) | Class display name |
| `color` | str | RGBA/hex — background color for badge |
| `border_color` | str | RGBA/hex — border color for badge |
| `text_color` | str | RGBA/hex — text color for badge |

- Name is unique — duplicate names raise a 400 error
- Badge colors are used directly in frontend CSS styling
- 8 default classes seeded via `seed_classes.py` (Draconic, Chimeric, Fae, Titanic, Abyssal, Ethereal, Mythic Beasts, Other)

## Creature

Represents a single mythological creature entry.

| Field | Type | Notes |
|-------|------|-------|
| `id` | int (PK) | Auto-generated |
| `name` | str (indexed) | Creature name |
| `mythology` | str | Origin mythology (e.g., Greek, Norse) |
| `creature_type` | str | References a CreatureClass by name |
| `danger_level` | int | 1–10 scale |
| `habitat` | str | Where the creature lives |
| `last_modify` | str | ISO format UTC timestamp, auto-set on create/update |
| `image_url` | str | DiceBear Identicon URL, auto-generated from name |

### Auto-Behaviors (handled in services, not models)

- **`image_url`**: If not provided, auto-generated from `https://api.dicebear.com/9.x/identicon/svg?seed={name}`
- **`last_modify`**: Auto-set to current UTC time on every create and update
- **`creature_type`**: If the type doesn't exist as a CreatureClass, it's auto-created with default colors

## Relationship

`CreatureClass (1) ──── (N) Creature` via `creature_type` field (name reference, not FK).

Cascade behavior: renaming a CreatureClass updates all creatures using that name (handled in `services/classes.py`).

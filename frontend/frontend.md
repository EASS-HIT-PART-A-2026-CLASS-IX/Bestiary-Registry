# Frontend Documentation

Parent: [Root](../README.md)

## Files Covered
- `frontend/dashboard.py`
- `frontend/sidebar.py`
- `frontend/settings.py`
- `frontend/realm_map.py`
- `frontend/api_client.py`
- `frontend/api_utils.py`
- `frontend/style.css`

Streamlit frontend for Bestiary Registry. Three pages: Registry, Realm Map, Settings.

## Running

```bash
# From backend/ directory (so uv environment is used):
cd backend && uv run python -m streamlit run ../frontend/dashboard.py
# http://localhost:8501
```

## Pages

### Registry (`dashboard.py`)

Main creature management dashboard.

- **Metrics bar**: Total creatures, critical danger count, monthly additions
- **Search**: Case-insensitive real-time filter by name
- **Filters**: Multi-select by Class, Mythology, and Danger Level range
- **Table**: Sortable creature list with Edit and Delete buttons per row
- **Create**: "Add Creature" button opens a dialog form
- **Dialogs**: All mutations (create, edit, delete) happen in modal dialogs

### Realm Map (`realm_map.py`)

Displays a static `creatureMap.jpg` image. No interactivity.

### Settings (`settings.py`)

Admin panel with two tabs:
- **Class Management**: Add, edit (rename + recolor), delete classes. Live badge preview. "Other" class is protected from deletion.
- **General**: Placeholder, not yet implemented.

## Navigation (`sidebar.py`)

- User profile card ("Merlin's Admin")
- Buttons: Registry, Realm Map, Settings — stored in `st.session_state["page"]`
- Log Out button: shows confirmation modal, clears session state on confirm

## API Layer

### `api_client.py`

HTTP wrapper around `requests`. All methods call the backend and raise on error.

```python
# Base URL from env var API_URL (default: http://localhost:8000)
client = APIClient()

# Creatures
client.get_creatures()
client.get_creature(id)
client.create_creature(data: dict)
client.update_creature(id, data: dict)
client.delete_creature(id)

# Classes
client.get_classes()
client.create_class(data: dict)
client.update_class(id, data: dict)
client.delete_class(id)
```

### `api_utils.py`

Streamlit caching layer on top of `api_client`.

- `get_creatures()` / `get_classes()` — cached with 2-second TTL
- `clear_cache()` — call after any mutation to force fresh data on next render

**Important:** Always call `clear_cache()` after create/update/delete, then `st.rerun()`.

## Styling (`style.css`)

Custom dark theme loaded in `dashboard.py` via `st.markdown`. Key elements:
- Dark background with purple accents
- Fonts: Space Grotesk (headings), Noto Sans (body)
- Material Design icons
- Badge styling for creature class display
- Animated transitions

To change the theme, edit `style.css` directly — no need to touch Python files.

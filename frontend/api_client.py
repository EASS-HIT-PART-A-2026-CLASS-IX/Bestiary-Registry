import requests
import os

# Centralize API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(username: str, password: str) -> dict:
    response = requests.post(
        f"{API_URL}/auth/token",
        data={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()


def register(username: str, password: str, role: str = "viewer") -> dict:
    response = requests.post(
        f"{API_URL}/auth/register",
        json={"username": username, "password": password, "role": role},
    )
    response.raise_for_status()
    return response.json()


def change_password(old_password: str, new_password: str, token: str) -> dict:
    response = requests.put(
        f"{API_URL}/auth/me/password",
        json={"old_password": old_password, "new_password": new_password},
        headers=_auth_headers(token),
    )
    response.raise_for_status()
    return response.json()


def get_me(token: str) -> dict:
    response = requests.get(f"{API_URL}/auth/me", headers=_auth_headers(token))
    response.raise_for_status()
    return response.json()


def update_avatar(avatar_b64: str, token: str) -> dict:
    response = requests.put(
        f"{API_URL}/auth/me/avatar",
        json={"avatar": avatar_b64},
        headers=_auth_headers(token),
    )
    response.raise_for_status()
    return response.json()


def get_creatures(token: str = None):
    try:
        headers = _auth_headers(token) if token else {}
        response = requests.get(f"{API_URL}/creatures/", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def get_creature(creature_id: int) -> dict:
    response = requests.get(f"{API_URL}/creatures/{creature_id}")
    response.raise_for_status()
    return response.json()


def get_classes():
    try:
        response = requests.get(f"{API_URL}/classes/")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def generate_lore(creature_id: int) -> str:
    response = requests.post(f"{API_URL}/creatures/{creature_id}/lore")
    response.raise_for_status()
    return response.json()["lore"]


def export_creatures_csv() -> bytes:
    response = requests.get(f"{API_URL}/creatures/export/csv")
    response.raise_for_status()
    return response.content


def create_creature(payload, token: str = None):
    headers = _auth_headers(token) if token else {}
    response = requests.post(f"{API_URL}/creatures/", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_creature(creature_id, payload, token: str = None):
    headers = _auth_headers(token) if token else {}
    response = requests.put(
        f"{API_URL}/creatures/{creature_id}", json=payload, headers=headers
    )
    response.raise_for_status()
    return response.json()


def delete_creature(creature_id, token: str = None):
    headers = _auth_headers(token) if token else {}
    response = requests.delete(f"{API_URL}/creatures/{creature_id}", headers=headers)
    response.raise_for_status()
    return True


def create_class(payload):
    response = requests.post(f"{API_URL}/classes/", json=payload)
    response.raise_for_status()
    return response.json()


def update_class(class_id, payload):
    response = requests.put(f"{API_URL}/classes/{class_id}", json=payload)
    response.raise_for_status()
    return response.json()


def delete_class(class_id):
    response = requests.delete(f"{API_URL}/classes/{class_id}")
    response.raise_for_status()
    return True

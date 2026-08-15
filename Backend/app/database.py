"""
database.py — User store (CSV-backed) and per-user folders.

The store keeps a **bcrypt hash** in the ``password_hash`` column — plaintext
passwords are never written to disk. The CSV backend is intentionally simple
and dependency-free; swapping it for SQLite/Postgres later only requires
re-implementing the functions in this module.

CSV columns:
    name, email, password_hash, username, registered_at, whl_path
"""

import csv
import threading
from datetime import datetime, timezone

from .config import DATA_DIR
from .security import hash_password, verify_password

LOGIN_CSV = DATA_DIR / "login.csv"
COLUMNS = ["name", "email", "password_hash", "username", "registered_at", "whl_path"]

# CSV read-modify-write is not atomic; guard it with a process-level lock.
_lock = threading.Lock()


def _ensure_csv() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOGIN_CSV.exists():
        with open(LOGIN_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()


def _read_all() -> list[dict]:
    _ensure_csv()
    with open(LOGIN_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_all(rows: list[dict]) -> None:
    _ensure_csv()
    with open(LOGIN_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# ── Public API ────────────────────────────────────────────────────────────────


def user_exists(email: str) -> bool:
    return any(r["email"].lower() == email.lower() for r in _read_all())


def create_user(name: str, email: str, password: str, username: str) -> dict:
    """Create a user (password stored as a bcrypt hash) and their data folder."""
    with _lock:
        user_folder = DATA_DIR / username
        (user_folder / "voices").mkdir(parents=True, exist_ok=True)

        new_user = {
            "name": name,
            "email": email,
            "password_hash": hash_password(password),
            "username": username,
            "registered_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "whl_path": "",
        }
        rows = _read_all()
        rows.append(new_user)
        _write_all(rows)
    return new_user


def get_user_by_email(email: str) -> dict | None:
    for r in _read_all():
        if r["email"].lower() == email.lower():
            return r
    return None


def get_user_by_username(username: str) -> dict | None:
    for r in _read_all():
        if r["username"].lower() == username.lower():
            return r
    return None


def authenticate_user(email: str, password: str) -> dict | None:
    """Return the user row if the password matches its stored hash, else None."""
    user = get_user_by_email(email)
    if not user or not verify_password(password, user.get("password_hash", "")):
        return None
    return user


def save_whl_path(email: str, whl_path: str) -> None:
    with _lock:
        rows = _read_all()
        for r in rows:
            if r["email"].lower() == email.lower():
                r["whl_path"] = str(whl_path)
                break
        _write_all(rows)


def get_whl_path(email: str) -> str | None:
    user = get_user_by_email(email)
    return user["whl_path"] if user and user.get("whl_path") else None


def delete_user(email: str) -> bool:
    with _lock:
        rows = _read_all()
        kept = [r for r in rows if r["email"].lower() != email.lower()]
        if len(kept) == len(rows):
            return False
        _write_all(kept)
    return True

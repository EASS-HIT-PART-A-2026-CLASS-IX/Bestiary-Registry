import os
from typing import Annotated
from fastapi import Depends
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

# --- Database Setup ---
sqlite_file_name = os.getenv("DB_PATH", "creatures.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Maps table name -> list of (column_name, sqlite_type) to ensure exist.
_MIGRATIONS = {
    "creature": [
        ("lore", "TEXT"),
    ],
    "app_user": [
        ("avatar", "TEXT"),
    ],
}


def run_migrations():
    """Add any missing columns to existing tables (safe, idempotent)."""
    with engine.connect() as conn:
        for table, columns in _MIGRATIONS.items():
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            existing = {row[1] for row in rows}
            for col_name, col_type in columns:
                if col_name not in existing:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    )
            conn.commit()


def seed_default_admin():
    """Create the default admin user if it doesn't exist."""
    from app.models import User
    from app.auth import hash_password

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == "admin")).first()
        if not existing:
            session.add(
                User(
                    username="admin",
                    hashed_password=hash_password("admin123"),
                    role="admin",
                )
            )
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

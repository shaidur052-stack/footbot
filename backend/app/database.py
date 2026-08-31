"""Database engine and session management.

SQLite locally, Postgres in production. Only DATABASE_URL changes —
SQLAlchemy handles the rest, which is why the swap is one env var.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# check_same_thread is a SQLite-only quirk: FastAPI serves requests on
# multiple threads and SQLite objects to that by default.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.engine import engine


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def session_scope() -> Generator[Session, Any, None]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

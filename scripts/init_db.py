from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.db.engine import engine
from app.db.models import Base  # o app.db.base import Base


def _run_sql_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")

    sql = path.read_text(encoding="utf-8").strip()
    if not sql:
        print(f"SKIP: {path.name} vacío")
        return

    with engine.begin() as conn:
        conn.execute(text(sql))

    print(f"OK: ejecutado {path.name}")


def main():
    print("DB:", engine.url)

    # 1) Tablas
    Base.metadata.create_all(bind=engine)
    print(f"OK: create_all() ejecutado. Tablas registradas: {len(Base.metadata.tables)}")

    # 2) Vistas (desde .sql)
    scripts_dir = Path(__file__).resolve().parent
    _run_sql_file(scripts_dir / "vista_auditoria.sql")
    _run_sql_file(scripts_dir / "vista_debitos.sql")

    print("OK: DB inicializada (tablas + vistas).")


if __name__ == "__main__":
    main()

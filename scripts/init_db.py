from __future__ import annotations

from pathlib import Path
from sqlalchemy import text
from app.db.engine import engine
from app.db.models import Base


def _run_sql_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")

    sql = path.read_text(encoding="utf-8").strip()
    if not sql:
        print(f"SKIP: {path.name} vacío")
        return

    # Intento simple de idempotencia para VIEWS / FUNCTIONS si tus .sql no traen OR REPLACE
    normalized = sql.lstrip().upper()
    if normalized.startswith("CREATE VIEW "):
        sql = sql.replace("CREATE VIEW", "CREATE OR REPLACE VIEW", 1)
    elif normalized.startswith("CREATE FUNCTION "):
        sql = sql.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)

    with engine.begin() as conn:
        conn.execute(text(sql))

    print(f"OK: ejecutado {path.name}")


def main() -> None:
    print("DB:", engine.url)

    # OJO: create_all NO actualiza, solo crea lo que falta
    Base.metadata.create_all(bind=engine)
    print(f"OK: create_all() ejecutado. Tablas registradas: {len(Base.metadata.tables)}")

    scripts_dir = Path(__file__).resolve().parent
    for name in [
        "vista_auditoria.sql",
        "vista_debitos.sql",
        "vista_exluida.sql",
        "vista_resumen.sql",
        "funcion_arrastre.sql",
    ]:
        _run_sql_file(scripts_dir / name)

    print("OK: DB inicializada (tablas + vistas/funciones).")


if __name__ == "__main__":
    main()

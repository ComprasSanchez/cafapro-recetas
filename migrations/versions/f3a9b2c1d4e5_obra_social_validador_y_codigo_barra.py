"""obra social validador y codigo barra en archivo detalle

Revision ID: f3a9b2c1d4e5
Revises: c750c673a271
Create Date: 2026-03-19 00:00:00.000000

"""

from typing import Sequence, Union
from pathlib import Path

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a9b2c1d4e5"
down_revision: Union[str, Sequence[str], None] = "c750c673a271"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_script(name: str) -> None:
    root = Path(__file__).resolve().parents[2]
    sql_path = root / "scripts" / name
    sql_text = sql_path.read_text(encoding="utf-8")
    op.execute(sa.text(sql_text))


def upgrade() -> None:
    op.add_column(
        "obra_social",
        sa.Column("validador", sa.String(length=20), nullable=False, server_default=sa.text("'imed'")),
    )
    op.add_column(
        "obra_social",
        sa.Column("dias_vencimiento", sa.Integer(), nullable=True),
    )
    op.add_column(
        "obra_social",
        sa.Column("codigo_financiador", sa.Integer(), nullable=True),
    )

    op.create_check_constraint(
        "ck_obra_social_obra_social_validador",
        "obra_social",
        "validador IN ('imed','preserfar','facaf')",
    )

    op.execute("UPDATE obra_social SET validador = 'imed' WHERE validador IS NULL")
    op.execute("UPDATE obra_social SET dias_vencimiento = 60 WHERE codigo IN ('12', '80')")
    op.execute("UPDATE obra_social SET codigo_financiador = 41 WHERE codigo = '12'")
    op.execute("UPDATE obra_social SET codigo_financiador = 4007 WHERE codigo = '80'")

    op.add_column(
        "archivo_detalle",
        sa.Column("codigo_barra", sa.String(), nullable=True),
    )

    op.add_column(
        "archivo",
        sa.Column("importe_bruto", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "archivo",
        sa.Column("importe_cobertura", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "archivo",
        sa.Column("importe_afiliado", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )

    op.add_column(
        "archivo_detalle",
        sa.Column("importe_bruto", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "archivo_detalle",
        sa.Column("importe_cobertura", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )

    op.execute("UPDATE archivo SET importe_afiliado = COALESCE(importe_neto, 0)")
    op.execute("UPDATE archivo SET importe_bruto = COALESCE(importe_obs, 0)")
    op.execute("UPDATE archivo SET importe_cobertura = COALESCE(a_cargo_entidad, 0)")

    op.execute("UPDATE archivo_detalle SET importe_bruto = COALESCE(importe_neto, 0)")
    op.execute("UPDATE archivo_detalle SET importe_cobertura = COALESCE(importe_obs, 0)")

    _run_sql_script("vista_auditoria.sql")
    _run_sql_script("vista_debitos.sql")
    _run_sql_script("vista_exluida.sql")
    _run_sql_script("vista_resumen.sql")

    op.drop_column("archivo_detalle", "importe_obs")
    op.drop_column("archivo_detalle", "importe_neto")
    op.drop_column("archivo", "a_cargo_entidad")
    op.drop_column("archivo", "importe_obs")
    op.drop_column("archivo", "importe_neto")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_archivo_resumen_auditoria")
    op.execute("DROP VIEW IF EXISTS vw_archivo_receta_debitos")
    op.execute("DROP VIEW IF EXISTS vw_archivos_excluidos")
    op.execute("DROP VIEW IF EXISTS vw_resumen_recepcion")

    op.execute("ALTER TABLE archivo ADD COLUMN IF NOT EXISTS importe_neto NUMERIC(12,2) NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE archivo ADD COLUMN IF NOT EXISTS importe_obs NUMERIC(12,2) NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE archivo ADD COLUMN IF NOT EXISTS a_cargo_entidad NUMERIC(12,2) NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE archivo_detalle ADD COLUMN IF NOT EXISTS importe_neto NUMERIC(12,2) NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE archivo_detalle ADD COLUMN IF NOT EXISTS importe_obs NUMERIC(12,2) NOT NULL DEFAULT 0")

    op.execute("UPDATE archivo SET importe_neto = COALESCE(importe_afiliado, 0)")
    op.execute("UPDATE archivo SET importe_obs = COALESCE(importe_bruto, 0)")
    op.execute("UPDATE archivo SET a_cargo_entidad = COALESCE(importe_cobertura, 0)")
    op.execute("UPDATE archivo_detalle SET importe_neto = COALESCE(importe_bruto, 0)")
    op.execute("UPDATE archivo_detalle SET importe_obs = COALESCE(importe_cobertura, 0)")

    op.drop_column("archivo_detalle", "importe_cobertura")
    op.drop_column("archivo_detalle", "importe_bruto")
    op.drop_column("archivo", "importe_afiliado")
    op.drop_column("archivo", "importe_cobertura")
    op.drop_column("archivo", "importe_bruto")

    op.drop_column("archivo_detalle", "codigo_barra")

    op.drop_constraint(
        "ck_obra_social_obra_social_validador",
        "obra_social",
        type_="check",
    )
    op.drop_column("obra_social", "codigo_financiador")
    op.drop_column("obra_social", "dias_vencimiento")
    op.drop_column("obra_social", "validador")

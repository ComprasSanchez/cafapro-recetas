from __future__ import annotations

from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class VwArchivoResumenAuditoria(Base):
    __tablename__ = "vw_archivo_resumen_auditoria"
    __table_args__ = {"info": {"is_view": True}}

    # ✅ PK compuesta (segura si hay más de una fila por archivo)
    archivo_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    asociacion_id: Mapped[int | None] = mapped_column(sa.Integer, primary_key=True, nullable=True)

    recepcion_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    numero_receta: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    numero_referencia: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    nro_lote: Mapped[int] = mapped_column(sa.Integer, nullable=True)

    existe_archivo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    existe_receta: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

    # ✅ Numeric -> Decimal
    importe_reconocido: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False)
    importe_oficial: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False)

    estado_receta_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    # ✅ nuevo: texto del estado (estado_seguimiento.descripcion)
    estado_receta: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    frente_jpg: Mapped[str | None] = mapped_column(sa.String, nullable=False)

class VwArchivoRecetaDebitos(Base):
    __tablename__ = "vw_archivo_receta_debitos"

    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "receta_id",
            "orden_lote",
            "descripcion_debito",
            "detalle",
            name="pk_vw_archivo_receta_debitos",
        ),
    )

    receta_id: Mapped[int] = mapped_column(sa.Integer)
    recepcion_id: Mapped[int] = mapped_column(sa.Integer)

    estado_seguimiento_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    estado_seguimiento: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    fecha: Mapped[sa.Date] = mapped_column(sa.Date)
    hora: Mapped[sa.Time] = mapped_column(sa.Time)

    orden_lote: Mapped[int] = mapped_column(sa.Integer)
    nro_receta: Mapped[str] = mapped_column(sa.String)

    importe_obs: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2))
    a_cargo_entidad: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2))

    descripcion_debito: Mapped[str] = mapped_column(sa.String)
    detalle: Mapped[str | None] = mapped_column(sa.String, nullable=True)



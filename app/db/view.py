from __future__ import annotations

from datetime import date, time
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
    flag_debitos: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

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


    recepcion_numero: Mapped[int] = mapped_column(sa.Integer, nullable=True)
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
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False)

class VwArchivosExcluidos(Base):
    __tablename__ = "vw_archivos_excluidos"

    recepcion_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    nro_referencia: Mapped[str | None] = mapped_column(sa.String, primary_key=True)
    nro_receta: Mapped[str | None] = mapped_column(sa.String, primary_key=True)
    fecha: Mapped[date | None] = mapped_column(sa.Date, primary_key=True)
    hora: Mapped[time | None] = mapped_column(sa.Time, primary_key=True)

    importe_obs: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2))
    a_cargo_entidad: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2))


class VwResumenRecepcionPrestador(Base):
    __tablename__ = "vw_resumen_recepcion_prestador"

    # PK lógica (vista)
    recepcion_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    prestador_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    periodo_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)

    recepcion_numero: Mapped[int | None] = mapped_column(sa.Integer)
    fecha_presentacion: Mapped[date | None] = mapped_column(sa.Date)
    estado_recepcion_id: Mapped[int | None] = mapped_column(sa.Integer)

    cantidad_recetas: Mapped[int] = mapped_column(sa.Integer)

    total_general: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2))
    total_importe_obs: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2))
    total_a_cargo_entidad: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2))





from __future__ import annotations

from enum import Enum as PyEnum
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date


# Nombres consistentes (Alembic)
NAMING_CONVENTION = dict(
    ix="ix_%(table_name)s_%(column_0_N_name)s",
    uq="uq_%(table_name)s_%(column_0_N_name)s",
    ck="ck_%(table_name)s_%(constraint_name)s",
    fk="fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    pk="pk_%(table_name)s",
)


class Base(DeclarativeBase):
    metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)


recepcion_numero_seq = sa.Sequence("recepcion_numero_seq", metadata=Base.metadata)

# =========================
# ENUMS (DBML)
# =========================
class LadoEnum(str, PyEnum):
    F = "F"
    D = "D"


class SiNoEnum(str, PyEnum):
    S = "S"
    N = "N"


lado_enum = sa.Enum(LadoEnum, name="lado_enum", native_enum=True)
si_no_enum = sa.Enum(SiNoEnum, name="si_no_enum", native_enum=True)


# =========================
# CATALOGOS
# =========================
class ObraSocial(Base):
    __tablename__ = "obra_social"

    obra_social_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    codigo: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(sa.String, nullable=False)
    activo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Periodo(Base):
    __tablename__ = "periodo"
    __table_args__ = (sa.UniqueConstraint("anio", "mes", "quincena", name="uq_periodo_anio"),)

    periodo_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    anio: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    mes: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    quincena: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    creado_en: Mapped[date] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Prestador(Base):
    __tablename__ = "prestador"

    prestador_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    codigo: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True)
    nombre: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    imed: Mapped[str] = mapped_column(sa.String, nullable=True)
    activo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


class EstadoSeguimiento(Base):
    __tablename__ = "estado_seguimiento"

    estado_seguimiento_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    descripcion: Mapped[str] = mapped_column(sa.String, nullable=False)


# =========================
# PLAN (obra_social + periodo)
# =========================
class Plan(Base):
    __tablename__ = "plan"
    __table_args__ = (sa.UniqueConstraint("obra_social_id", "nombre", "codigo", name="uq_plan_obra"),)

    plan_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    obra_social_id: Mapped[int] = mapped_column(sa.ForeignKey("obra_social.obra_social_id"), nullable=False)

    codigo: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    nombre: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    activo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


# =========================
# USUARIOS
# =========================
class Roles(Base):
    __tablename__ = "roles"

    rol_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    descripcion: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True)


class Usuarios(Base):
    __tablename__ = "usuarios"

    usuario_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True)
    hash_contrasena: Mapped[str] = mapped_column(sa.String, nullable=False)
    rol_id: Mapped[int] = mapped_column(sa.ForeignKey("roles.rol_id"), nullable=False)
    activo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())
    ultimo_login_en: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime, nullable=True)


# =========================
# RECEPCION (absorbe lo de LoteTemporal)
# =========================
class Recepcion(Base):
    __tablename__ = "recepcion"
    __table_args__ = (
        sa.Index("ix_recepcion_prestador_obra_periodo", "prestador_id", "obra_social_id", "periodo_id"),
        sa.Index("ix_recepcion_estado_recepcion", "estado_recepcion"),
        sa.UniqueConstraint("numero", name="uq_recepcion_numero"),
    )

    recepcion_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)

    numero: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        server_default=recepcion_numero_seq.next_value(),
    )

    obra_social_id: Mapped[int] = mapped_column(sa.ForeignKey("obra_social.obra_social_id"), nullable=False)
    periodo_id: Mapped[int] = mapped_column(sa.ForeignKey("periodo.periodo_id"), nullable=False)
    prestador_id: Mapped[int] = mapped_column(sa.ForeignKey("prestador.prestador_id"), nullable=False)

    # antes estaba en lote_temporal
    cantidad_imagenes: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))

    estado_recepcion: Mapped[str] = mapped_column(sa.String, nullable=False)
    fecha_recepcion: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    creado_por_usuario_id: Mapped[int | None] = mapped_column(sa.ForeignKey("usuarios.usuario_id"), nullable=True)
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


# =========================
# ARCHIVO + DETALLE ARCHIVO
# =========================
class Archivo(Base):
    __tablename__ = "archivo"
    __table_args__ = (
        sa.Index("ix_archivo_recepcion_id", "recepcion_id"),
        sa.Index("ix_archivo_nro_referencia", "nro_referencia"),
    )

    archivo_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    recepcion_id: Mapped[int] = mapped_column(sa.ForeignKey("recepcion.recepcion_id"), nullable=False)

    afiliado: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    fecha: Mapped[sa.Date | None] = mapped_column(sa.Date, nullable=True)
    hora: Mapped[sa.Time | None] = mapped_column(sa.Time, nullable=True)

    nro_referencia: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    importe_neto: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2), nullable=False, server_default=sa.text("0"))
    a_cargo_entidad: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2), nullable=False, server_default=sa.text("0"))

    nro_recetas: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    orden_lote: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ArchivoDetalle(Base):
    __tablename__ = "archivo_detalle"
    __table_args__ = (
        sa.Index("ix_archivo_detalle_archivo_id", "archivo_id"),
        sa.Index("ix_archivo_detalle_codigo_barra", "codigo_barra"),
    )

    archivo_detalle_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    archivo_id: Mapped[int] = mapped_column(sa.ForeignKey("archivo.archivo_id"), nullable=False)

    descripcion: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    codigo_respuesta: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    estado: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    nro_autorizacion: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    cantidad: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    importe_neto: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2), nullable=False, server_default=sa.text("0"))
    cobertura: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2), nullable=False, server_default=sa.text("0"))

    codigo_barra: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


# =========================
# RECETAS + TROQUELES
# =========================
class Recetas(Base):
    __tablename__ = "recetas"
    __table_args__ = (
        sa.Index("ix_recetas_recepcion_id", "recepcion_id"),
        sa.Index("ix_recetas_nro_receta", "nro_receta"),
    )

    receta_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    recepcion_id: Mapped[int] = mapped_column(sa.ForeignKey("recepcion.recepcion_id"), nullable=False)

    nro_receta: Mapped[str] = mapped_column(sa.String, nullable=False)
    ubicacion_frente: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    ubicacion_dorso: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    fecha_prescripcion: Mapped[sa.Date | None] = mapped_column(sa.Date, nullable=True)
    estado_seguimiento_id: Mapped[int] = mapped_column(
        sa.ForeignKey("estado_seguimiento.estado_seguimiento_id"),
        nullable=False,
    )
    observacion: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    usuario_id: Mapped[int] = mapped_column(sa.ForeignKey("usuarios.usuario_id"), nullable=False)
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


class RecetasHistorial(Base):
    __tablename__ = "recetas_historial"
    __table_args__ = (
        sa.Index("ix_recetas_historial_recepcion_id", "recepcion_id"),
        sa.Index("ix_recetas_historial_nro_receta", "nro_receta"),
    )

    receta_historial_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    receta_id: Mapped[int] = mapped_column(sa.ForeignKey("recetas.receta_id"), nullable=False)
    recepcion_id: Mapped[int] = mapped_column(sa.ForeignKey("recepcion.recepcion_id"), nullable=False)

    nro_receta: Mapped[str] = mapped_column(sa.String, nullable=False)
    ubicacion_frente: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    ubicacion_dorso: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    fecha_prescripcion: Mapped[sa.Date | None] = mapped_column(sa.Date, nullable=True)
    estado_seguimiento_id: Mapped[int] = mapped_column(
        sa.ForeignKey("estado_seguimiento.estado_seguimiento_id"),
        nullable=False,
    )

    usuario_id: Mapped[int] = mapped_column(sa.ForeignKey("usuarios.usuario_id"), nullable=False)
    fecha_historial: Mapped[sa.Date | None] = mapped_column(sa.Date, nullable=True)
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Troqueles(Base):
    __tablename__ = "troqueles"
    __table_args__ = (
        sa.Index("ix_troqueles_receta_id", "receta_id"),
        sa.Index("ix_troqueles_codigo_barra", "codigo_barra"),
    )

    troquel_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    receta_id: Mapped[int] = mapped_column(sa.ForeignKey("recetas.receta_id"), nullable=False)

    codigo_barra: Mapped[str] = mapped_column(sa.String, nullable=False)
    monto: Mapped[sa.Numeric] = mapped_column(sa.Numeric(12, 2), nullable=False, server_default=sa.text("0"))
    cantidad: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))
    estado: Mapped[str] = mapped_column(sa.String, nullable=False)

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())


# =========================
# DEBITOS + MOTIVOS
# =========================
class MotivoDebito(Base):
    __tablename__ = "motivo_debito"

    motivo_debito_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    descripcion: Mapped[str] = mapped_column(sa.String, nullable=False)
    lado: Mapped[LadoEnum] = mapped_column(lado_enum, nullable=False)
    excluyente: Mapped[SiNoEnum] = mapped_column(si_no_enum, nullable=False)
    codigo: Mapped[str] = mapped_column(sa.String, nullable=False)


class Debitos(Base):
    __tablename__ = "debitos"

    debito_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    receta_id: Mapped[int] = mapped_column(sa.ForeignKey("recetas.receta_id"), nullable=False)
    motivo_debito_id: Mapped[int] = mapped_column(sa.ForeignKey("motivo_debito.motivo_debito_id"), nullable=False)
    detalle: Mapped[str | None] = mapped_column(sa.String, nullable=True)


# =========================
# ASOCIACION (TABLA INTERMEDIA)
# =========================
class Asociacion(Base):
    __tablename__ = "asociacion"
    __table_args__ = (
        sa.UniqueConstraint("receta_id", "archivo_id", name="uq_asociacion_receta_archivo"),
        sa.Index("ix_asociacion_receta_id", "receta_id"),
        sa.Index("ix_asociacion_archivo_id", "archivo_id"),
    )

    asociacion_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    receta_id: Mapped[int] = mapped_column(sa.ForeignKey("recetas.receta_id"), nullable=False)
    archivo_id: Mapped[int] = mapped_column(sa.ForeignKey("archivo.archivo_id"), nullable=False)

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())

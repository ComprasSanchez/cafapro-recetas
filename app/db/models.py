from __future__ import annotations

from decimal import Decimal
from enum import Enum as PyEnum
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import date, datetime

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

class EstadoTroquelEnum(str, PyEnum):
    V = "V" #Verde, escaneado y encontrado
    A = "A" #Amarillo, escaneado y no encontrado
    R = "R" #Roja, escanead y pero no machea

lado_enum = sa.Enum(LadoEnum, name="lado_enum", native_enum=True)
si_no_enum = sa.Enum(SiNoEnum, name="si_no_enum", native_enum=True)
estado_troquel_enum = sa.Enum(EstadoTroquelEnum, name="estado_troquel_enum", native_enum=True)


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
    activo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
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


class EstadoReceta(Base):
    __tablename__ = "estado_receta"

    estado_receta_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    descripcion: Mapped[str] = mapped_column(sa.String, nullable=False)

class EstadoRecepcion(Base):
    __tablename__ = "estado_recepcion"

    estado_recepcion_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    descripcion: Mapped[str] = mapped_column(sa.String, nullable=False)

class Plan(Base):
    __tablename__ = "plan"
    __table_args__ = (sa.UniqueConstraint("obra_social_id", "nombre", "codigo", name="uq_plan_obra"),)

    plan_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    obra_social_id: Mapped[int] = mapped_column(sa.ForeignKey("obra_social.obra_social_id"), nullable=False)

    codigo: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    nombre: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    activo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())



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
        sa.Index("ix_recepcion_estado_recepcion_id", "estado_recepcion_id"),
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

    fecha_presentacion: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    pendientes: Mapped[int] = mapped_column(sa.Integer, nullable=True, server_default=sa.text("0"))
    estado_recepcion_id: Mapped[int] = mapped_column(sa.ForeignKey("estado_recepcion.estado_recepcion_id"), nullable=False)

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

        sa.Index("ix_archivo_recepcion_nro_referencia", "recepcion_id", "nro_referencia"),
        sa.Index("ix_archivo_recepcion_nro_receta", "recepcion_id", "nro_receta"),
    )

    archivo_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)

    # ✅ ahora puede ser NULL
    recepcion_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("recepcion.recepcion_id"),
        nullable=True,
    )

    # --- Campos “IMED receta” lo más parecidos posible ---
    beneficiario: Mapped[str | None] = mapped_column(sa.String, nullable=False)

    fecha: Mapped[sa.Date] = mapped_column(sa.Date, nullable=False)
    hora: Mapped[sa.Time] = mapped_column(sa.Time, nullable=False)

    nro_referencia: Mapped[str | None] = mapped_column(sa.String, nullable=False)
    nro_receta: Mapped[str | None] = mapped_column(sa.String, nullable=False)

    orden_lote: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    # Importe Gral (antes importe_neto) -> lo dejo como importe_neto para tu app,
    # pero conceptualmente es el “gral”.
    importe_neto: Mapped[sa.Numeric] = mapped_column(
        sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")
    )

    # ✅ “Importe Pami” -> importe_obs
    importe_obs: Mapped[sa.Numeric] = mapped_column(
        sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")
    )

    # A cargo entidad
    a_cargo_entidad: Mapped[sa.Numeric] = mapped_column(
        sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")
    )

    creado_en: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    vencido: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.false())

    asociaciones: Mapped[list["Asociacion"]] = relationship(
        "Asociacion",
        back_populates="archivo",
    )

    archivo_detalles: Mapped[list["ArchivoDetalle"]] = relationship(
        "ArchivoDetalle",
        back_populates="archivo",
        lazy="selectin",
    )


class ArchivoDetalle(Base):
    __tablename__ = "archivo_detalle"
    __table_args__ = (
        sa.Index("ix_archivo_detalle_archivo_id", "archivo_id"),
    )

    archivo_detalle_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    archivo_id: Mapped[int] = mapped_column(sa.ForeignKey("archivo.archivo_id"), nullable=False)

    # --- Similar a la grilla IMED ---
    cod_medic: Mapped[str | None] = mapped_column(sa.String, nullable=False)
    nombre: Mapped[str | None] = mapped_column(sa.String, nullable=False)            # name
    presentacion: Mapped[str | None] = mapped_column(sa.String, nullable=False)      # description / present.
    estado: Mapped[str | None] = mapped_column(sa.String, nullable=False)            # estado

    nro_autorizacion: Mapped[str | None] = mapped_column(sa.String, nullable=False) # nro aut.

    cantidad: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))

    # Importes
    importe_neto: Mapped[sa.Numeric] = mapped_column(
        sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")
    )

    # ✅ “Importe Pami” -> importe_obs
    importe_obs: Mapped[sa.Numeric] = mapped_column(
        sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")
    )

    # “Desc.” (en tu CSV viene tipo "40%")
    descuento: Mapped[str | None] = mapped_column(sa.String, nullable=False)

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())

    archivo: Mapped["Archivo"] = relationship(
        "Archivo",
        back_populates="archivo_detalles",
    )

class Recetas(Base):
    __tablename__ = "recetas"
    __table_args__ = (
        sa.Index("ix_recetas_recepcion_id", "recepcion_id"),
        sa.Index("ix_recetas_nro_receta", "nro_receta"),
        sa.Index(
            "uq_recetas_recepcion_nro_receta_vigente",
            "recepcion_id",
            "nro_receta",
            unique=True,
            postgresql_where=sa.text("vigente IS TRUE"),
        ),
    )

    receta_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    recepcion_id: Mapped[int] = mapped_column(sa.ForeignKey("recepcion.recepcion_id"), nullable=False)

    nro_receta: Mapped[str] = mapped_column(sa.String, nullable=False)
    ubicacion_frente: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    ubicacion_dorso: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    fecha_prescripcion: Mapped[date  | None] = mapped_column(sa.Date, nullable=True)
    fecha_emision: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    fecha_venta: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    estado_receta_id: Mapped[int] = mapped_column(sa.ForeignKey("estado_receta.estado_receta_id"), nullable=True)
    estado_seguimiento_id: Mapped[int] = mapped_column(
        sa.ForeignKey("estado_seguimiento.estado_seguimiento_id"),
        nullable=True,
    )
    observacion: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    usuario_id: Mapped[int] = mapped_column(sa.ForeignKey("usuarios.usuario_id"), nullable=False)
    vendedor_id: Mapped[int] = mapped_column(sa.ForeignKey("vendedores.vendedor_id"), nullable=True)

    # ✅ NUEVO: receta vigente / histórica
    vigente: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=True)

    asociaciones: Mapped[list["Asociacion"]] = relationship(
        "Asociacion",
        back_populates="receta",
    )

    troqueles: Mapped[list["Troqueles"]] = relationship(
        "Troqueles",
        back_populates="receta",
        lazy="selectin",
    )

    debitos: Mapped[list["Debitos"]] = relationship(
        "Debitos",
        back_populates="receta",
        lazy="selectin",
    )



class Troqueles(Base):
    __tablename__ = "troqueles"
    __table_args__ = (
        sa.Index("ix_troqueles_receta_id", "receta_id"),
        sa.Index("ix_troqueles_codigo_barra", "codigo_barra"),
    )

    troquel_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    receta_id: Mapped[int] = mapped_column(sa.ForeignKey("recetas.receta_id"), nullable=False)

    codigo_barra: Mapped[str] = mapped_column(sa.String, nullable=False)
    droga: Mapped[str] = mapped_column(sa.String, nullable=True)
    presentacion: Mapped[str] = mapped_column(sa.String, nullable=True)
    code_alfabeta: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    monto: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False, server_default=sa.text("0"))
    cantidad: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))
    estado: Mapped[EstadoTroquelEnum] = mapped_column(estado_troquel_enum, nullable=False)

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())

    receta: Mapped["Recetas"] = relationship(
        "Recetas",
        back_populates="troqueles",
    )


class MotivoDebito(Base):
    __tablename__ = "motivo_debito"

    motivo_debito_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    descripcion: Mapped[str] = mapped_column(sa.String, nullable=False)
    lado: Mapped[LadoEnum] = mapped_column(lado_enum, nullable=False)
    excluyente: Mapped[SiNoEnum] = mapped_column(si_no_enum, nullable=False)
    codigo: Mapped[str] = mapped_column(sa.String, nullable=False)
    activo: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.true(),
    )


class Debitos(Base):
    __tablename__ = "debitos"

    debito_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    receta_id: Mapped[int] = mapped_column(sa.ForeignKey("recetas.receta_id"), nullable=False)
    motivo_debito_id: Mapped[int] = mapped_column(sa.ForeignKey("motivo_debito.motivo_debito_id"), nullable=False)
    detalle: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    receta: Mapped["Recetas"] = relationship(
        "Recetas",
        back_populates="debitos",
    )

    motivo_debito: Mapped["MotivoDebito"] = relationship("MotivoDebito")

class Asociacion(Base):
    __tablename__ = "asociacion"
    __table_args__ = (
        sa.UniqueConstraint("receta_id", "archivo_id", name="uq_asociacion_receta_archivo"),
        sa.Index("ix_asociacion_receta_id", "receta_id"),
        sa.Index("ix_asociacion_archivo_id", "archivo_id"),

        # ✅ NUEVOS: para buscar “asociación vigente” rápido
        sa.Index("ix_asociacion_archivo_vigente", "archivo_id", "vigente"),
        sa.Index("ix_asociacion_receta_vigente", "receta_id", "vigente"),
    )

    asociacion_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    receta_id: Mapped[int] = mapped_column(sa.ForeignKey("recetas.receta_id"), nullable=False)
    archivo_id: Mapped[int] = mapped_column(sa.ForeignKey("archivo.archivo_id"), nullable=False)

    vigente: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())

    creado_en: Mapped[sa.DateTime] = mapped_column(sa.DateTime, nullable=False, server_default=sa.func.now())

    receta: Mapped["Recetas"] = relationship("Recetas", back_populates="asociaciones")
    archivo: Mapped["Archivo"] = relationship("Archivo", back_populates="asociaciones")


class Vendedores(Base):
    __tablename__ = "vendedores"
    __table_args__ = (
        sa.Index("ix_vendedores_codigo", "codigo"),
        sa.UniqueConstraint("codigo", "descripcion", name="uq_vendedores_codigo_descripcion"),
    )

    vendedor_id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)
    codigo: Mapped[str] = mapped_column(sa.String, nullable=False)
    descripcion: Mapped[str] = mapped_column(sa.String, nullable=False)
    activo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())


class AppVersion(Base):
    __tablename__ = "app_versions"

    __table_args__ = (
        sa.Index("ix_app_versions_version", "version"),
        sa.Index("ix_app_versions_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, sa.Identity(), primary_key=True)

    version: Mapped[str] = mapped_column(sa.String(50), nullable=False)

    min_required_version: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    mandatory: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.false(),
    )

    download_url: Mapped[str] = mapped_column(sa.Text, nullable=False)

    file_hash: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    release_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.true(),
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
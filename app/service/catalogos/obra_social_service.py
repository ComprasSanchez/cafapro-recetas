from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ObraSocial


# =========================
# DTOs
# =========================
@dataclass(frozen=True)
class ObraSocialItem:
    obra_social_id: int
    codigo: str
    nombre: str
    validador: str
    dias_vencimiento: int | None
    codigo_financiador: int | None
    activo: bool


# =========================
# SERVICE
# =========================
class ObraSocialService:
    VALIDADORES = {"imed", "preserfar", "facaf"}

    @staticmethod
    def _normalize_validador(validador: str | None) -> str:
        v = (validador or "").strip().lower()
        if v not in ObraSocialService.VALIDADORES:
            allowed = ", ".join(sorted(ObraSocialService.VALIDADORES))
            raise ValueError(f"Validador invalido. Valores permitidos: {allowed}.")
        return v

    @staticmethod
    def _normalize_dias_vencimiento(dias_vencimiento: int | str | None) -> int | None:
        if dias_vencimiento in (None, ""):
            return None
        try:
            value = int(dias_vencimiento)
        except Exception as e:
            raise ValueError("Dias de vencimiento debe ser un entero o vacio.") from e
        if value < 0:
            raise ValueError("Dias de vencimiento no puede ser negativo.")
        return value

    @staticmethod
    def _normalize_codigo_financiador(codigo_financiador: int | str | None) -> int | None:
        if codigo_financiador in (None, ""):
            return None
        try:
            value = int(codigo_financiador)
        except Exception as e:
            raise ValueError("Codigo financiador debe ser numerico o vacio.") from e
        if value <= 0:
            raise ValueError("Codigo financiador debe ser mayor a 0.")
        return value

    # ---------------------
    # LISTADOS
    # ---------------------
    @staticmethod
    def list(s: Session, *, solo_activas: bool = True) -> list[ObraSocialItem]:
        stmt = select(
            ObraSocial.obra_social_id,
            ObraSocial.codigo,
            ObraSocial.nombre,
            ObraSocial.validador,
            ObraSocial.dias_vencimiento,
            ObraSocial.codigo_financiador,
            ObraSocial.activo,
        )

        if solo_activas:
            stmt = stmt.where(ObraSocial.activo.is_(True))

        stmt = stmt.order_by(ObraSocial.nombre)

        rows = s.execute(stmt).all()

        return [
            ObraSocialItem(
                obra_social_id=r[0],
                codigo=r[1],
                nombre=r[2],
                validador=r[3] or "imed",
                dias_vencimiento=r[4],
                codigo_financiador=r[5],
                activo=r[6],
            )
            for r in rows
        ]

    # ---------------------
    # GET
    # ---------------------
    @staticmethod
    def get(s: Session, obra_social_id: int) -> ObraSocial | None:
        return s.get(ObraSocial, obra_social_id)

    # ---------------------
    # CREATE
    # ---------------------
    @staticmethod
    def create(
        s: Session,
        *,
        codigo: str,
        nombre: str,
        validador: str = "imed",
        dias_vencimiento: int | str | None = 60,
        codigo_financiador: int | str | None = None,
    ) -> ObraSocial:
        codigo = codigo.strip()
        nombre = nombre.strip()
        validador_norm = ObraSocialService._normalize_validador(validador)
        dias_norm = ObraSocialService._normalize_dias_vencimiento(dias_vencimiento)
        codigo_fin_norm = ObraSocialService._normalize_codigo_financiador(codigo_financiador)

        if not codigo or not nombre:
            raise ValueError("Código y nombre son obligatorios")

        existe = s.execute(
            select(ObraSocial).where(ObraSocial.codigo == codigo)
        ).scalar_one_or_none()

        if existe:
            raise ValueError(f"Ya existe una obra social con código '{codigo}'")

        os = ObraSocial(
            codigo=codigo,
            nombre=nombre,
            validador=validador_norm,
            dias_vencimiento=dias_norm,
            codigo_financiador=codigo_fin_norm,
            activo=True,
        )

        s.add(os)
        s.flush()      # para obtener obra_social_id
        s.refresh(os)

        return os

    # ---------------------
    # UPDATE
    # ---------------------
    @staticmethod
    def update(
        s: Session,
        *,
        obra_social_id: int,
        codigo: str,
        nombre: str,
        validador: str,
        dias_vencimiento: int | str | None,
        codigo_financiador: int | str | None,
    ) -> None:
        os = s.get(ObraSocial, obra_social_id)
        if not os:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")

        codigo = codigo.strip()
        nombre = nombre.strip()
        validador_norm = ObraSocialService._normalize_validador(validador)
        dias_norm = ObraSocialService._normalize_dias_vencimiento(dias_vencimiento)
        codigo_fin_norm = ObraSocialService._normalize_codigo_financiador(codigo_financiador)

        if not codigo or not nombre:
            raise ValueError("Código y nombre son obligatorios")

        # validar código único (excluyendo la actual)
        existe = s.execute(
            select(ObraSocial)
            .where(
                ObraSocial.codigo == codigo,
                ObraSocial.obra_social_id != obra_social_id,
            )
        ).scalar_one_or_none()

        if existe:
            raise ValueError(f"Ya existe otra obra social con código '{codigo}'")

        os.codigo = codigo
        os.nombre = nombre
        os.validador = validador_norm
        os.dias_vencimiento = dias_norm
        os.codigo_financiador = codigo_fin_norm

    # ---------------------
    # BAJA LÓGICA
    # ---------------------
    @staticmethod
    def delete_logico(s: Session, obra_social_id: int) -> None:
        os = s.get(ObraSocial, obra_social_id)
        if not os:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")

        os.activo = False

    # ---------------------
    # RESTAURAR
    # ---------------------
    @staticmethod
    def restore(s: Session, obra_social_id: int) -> None:
        os = s.get(ObraSocial, obra_social_id)
        if not os:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")

        os.activo = True

from __future__ import annotations

from decimal import Decimal
from datetime import date as dt_date, time as dt_time, date, datetime
from typing import Any

from sqlalchemy import select, func, exists, distinct, cast, Date
from sqlalchemy.orm import Session

from app.db.models import Archivo, ArchivoDetalle, Recepcion


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    s = str(v).strip()
    if not s:
        return Decimal("0")
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")


def _pct(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")

    s = str(v).strip()
    if not s:
        return Decimal("0")

    if s.endswith("%"):
        s = s[:-1].strip()

    if "," in s:
        s = s.replace(".", "").replace(",", ".")

    try:
        out = Decimal(s)
    except Exception:
        return Decimal("0")

    if out < 0:
        return Decimal("0")
    if out > 100:
        return Decimal("100")
    return out

def parse_date_any(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    try:
        return date.fromisoformat(s[:10])  # "2026-01-01" o "2026-01-01 00:00:00"
    except Exception:
        return None


def _parse_date(v: Any) -> dt_date | None:
    if not v:
        return None
    s = str(v).strip()
    if s.isdigit() and len(s) == 8:
        yyyy = int(s[0:4]); mm = int(s[4:6]); dd = int(s[6:8])
        return dt_date(yyyy, mm, dd)
    if "/" in s:
        dd, mm, yyyy = s.split("/")
        return dt_date(int(yyyy), int(mm), int(dd))
    return None


def _parse_time(v: Any) -> dt_time | None:
    if not v:
        return None
    s = str(v).strip()
    parts = s.split(":")
    if len(parts) == 2:
        hh, mm = map(int, parts)
        return dt_time(hh, mm, 0)
    if len(parts) == 3:
        hh, mm, ss = map(int, parts)
        return dt_time(hh, mm, ss)
    return None


class ArchivoService:
    @staticmethod
    def exists_by_ref(session: Session, *, nro_referencia: str) -> bool:
        stmt = select(Archivo.archivo_id).where(Archivo.nro_referencia == nro_referencia)
        return session.execute(stmt).first() is not None

    @staticmethod
    def exists_by_recepcion_and_ref(session: Session, *, recepcion_id: int, nro_referencia: str) -> bool:
        stmt = select(Archivo.archivo_id).where(
            Archivo.recepcion_id == recepcion_id,
            Archivo.nro_referencia == nro_referencia,
        )
        return session.execute(stmt).first() is not None

    @staticmethod
    def list_existing_refs(session: Session, refs: list[str]) -> set[str]:
        if not refs:
            return set()

        rows = session.execute(
            select(Archivo.nro_referencia).where(Archivo.nro_referencia.in_(refs))
        ).scalars().all()

        return {
            str(x).strip()
            for x in rows
            if x not in (None, "")
        }

    @staticmethod
    def create_from_imed(
            session,
            receta: dict,
            detalles: list[dict],
            recepcion_id: int | None,
            nro_referencia: str | None = None,
            orden_lote: int | None = None,
            skip_if_exists: bool = True,
            check_scope: str = "ref",
            existing_refs: set[str] | None = None,  # ✅ NUEVO (opcional): cache de refs ya existentes
    ) -> bool:
        # --------- nro_referencia ---------
        if not nro_referencia:
            nro_referencia = (
                    receta.get("Nro_Referencia")
                    or receta.get("Nro Referencia")
                    or receta.get("nro_referencia")
            )
        nro_referencia = str(nro_referencia).strip() if nro_referencia else ""
        if not nro_referencia:
            raise ValueError("La receta no trae Nro Referencia (no se puede insertar).")

        # --------- control duplicados (NO explota si skip_if_exists) ---------
        if skip_if_exists:
            # ✅ si me pasás cache, no consulto DB
            if existing_refs is not None:
                if nro_referencia in existing_refs:
                    return False
            else:
                exists = False
                if check_scope == "recepcion+ref":
                    if recepcion_id is None:
                        raise ValueError("check_scope='recepcion+ref' requiere recepcion_id.")
                    exists = ArchivoService.exists_by_recepcion_and_ref(
                        session, recepcion_id=recepcion_id, nro_referencia=nro_referencia
                    )
                else:
                    exists = ArchivoService.exists_by_ref(session, nro_referencia=nro_referencia)

                if exists:
                    return False  # 👈 clave: no insertó

        # --------- mapeo receta IMED ---------
        beneficiario = receta.get("Beneficiario") or receta.get("beneficiario")
        fecha_raw = receta.get("Fecha") or receta.get("fecha")
        hora_raw = receta.get("Hora") or receta.get("hora")

        nro_receta = (
                receta.get("Nro_Receta")
                or receta.get("Nro Receta")
                or receta.get("nro_receta")
        )

        if orden_lote is None:
            orden_lote = 0

        importe_bruto_raw = (
            receta.get("importe_bruto")
            or receta.get("Importe_Bruto")
            or receta.get("Importe Bruto")
            or receta.get("Importe_Pami")
            or receta.get("Importe Pami")
        )
        importe_cobertura_raw = (
            receta.get("importe_cobertura")
            or receta.get("Importe_Cobertura")
            or receta.get("Importe Cobertura")
            or receta.get("A_Cargo_Entidad")
            or receta.get("A Cargo Entidad")
        )
        importe_afiliado_input = (
            receta.get("importe_afiliado")
            or receta.get("Importe_Afiliado")
            or receta.get("Importe Afiliado")
        )

        importe_bruto_dec = _dec(importe_bruto_raw)
        importe_cobertura_dec = _dec(importe_cobertura_raw)
        if importe_afiliado_input in (None, ""):
            importe_afiliado_dec = importe_bruto_dec - importe_cobertura_dec
        else:
            importe_afiliado_dec = _dec(importe_afiliado_input)

        archivo = Archivo(
            recepcion_id=recepcion_id,  # puede ser None
            beneficiario=str(beneficiario).strip() if beneficiario else None,
            fecha=_parse_date(fecha_raw),
            hora=_parse_time(hora_raw),
            nro_referencia=nro_referencia,
            nro_receta=str(nro_receta).strip() if nro_receta else None,
            orden_lote=int(orden_lote),
            importe_bruto=importe_bruto_dec,
            importe_cobertura=importe_cobertura_dec,
            importe_afiliado=importe_afiliado_dec,
        )
        session.add(archivo)
        session.flush()  # ✅ necesario si cargás detalles por archivo_id

        # --------- detalles ---------
        rows: list[ArchivoDetalle] = []
        for d in detalles:
            cod_medic_raw = d.get("cod_medic")
            cod_medic = str(cod_medic_raw).strip() if cod_medic_raw not in (None, "") else None
            codigo_barra_raw = d.get("codigo_barra")
            codigo_barra = str(codigo_barra_raw).strip() if codigo_barra_raw not in (None, "") else None

            nombre = (d.get("nombre") or "").strip() or None
            present = (d.get("presentacion") or "").strip() or None

            estado = (d.get("estado") or "").strip() or None
            nro_aut = (d.get("nro_aut") or "").strip() or None
            cant_raw = d.get("cantidad")

            imp_gral_raw_d = d.get("importe_gral")
            imp_obs_raw_d = d.get("importe_pami")
            imp_bruto_raw_d = d.get("importe_bruto")
            imp_cobertura_raw_d = d.get("importe_cobertura")
            desc = (d.get("desc") or "").strip() or None

            # si "importe_pami" viene tipo "40%" y desc está vacío
            if isinstance(imp_obs_raw_d, str) and "%" in imp_obs_raw_d and not desc:
                desc = imp_obs_raw_d.strip()
                imp_obs_raw_d = "0"

            if imp_bruto_raw_d in (None, "") and imp_cobertura_raw_d in (None, ""):
                # IMED CSV: bruto = importe_pami; cobertura = descuento aplicado sobre importe_pami
                imp_pami_dec = _dec(imp_obs_raw_d)
                pct_desc = _pct(desc)
                imp_bruto_dec = imp_pami_dec
                imp_cobertura_dec = imp_pami_dec * (pct_desc / Decimal("100"))
            else:
                imp_bruto_dec = _dec(imp_bruto_raw_d if imp_bruto_raw_d not in (None, "") else imp_gral_raw_d)
                imp_cobertura_dec = _dec(imp_cobertura_raw_d if imp_cobertura_raw_d not in (None, "") else imp_obs_raw_d)

            # cantidad robusta
            try:
                cantidad = int(str(cant_raw).strip())
            except Exception:
                cantidad = 0

            rows.append(
                ArchivoDetalle(
                    archivo_id=int(archivo.archivo_id),
                    cod_medic=cod_medic,
                    codigo_barra=codigo_barra,
                    nombre=nombre,
                    presentacion=present,
                    estado=estado,
                    nro_autorizacion=nro_aut,
                    cantidad=cantidad,
                    importe_bruto=imp_bruto_dec,
                    importe_cobertura=imp_cobertura_dec,
                    descuento=desc,
                )
            )

        if rows:
            session.add_all(rows)

        # ✅ si tenías cache, actualizala para evitar duplicados dentro de la misma corrida
        if existing_refs is not None:
            existing_refs.add(nro_referencia)

        return True

    @staticmethod
    def get_start_orden_lote(session: Session, recepcion_id: int) -> int:
        # A) si ya hay archivos en esta recepción -> MAX+1
        max_orden = session.execute(
            select(func.max(Archivo.orden_lote))
            .where(Archivo.recepcion_id == recepcion_id)
        ).scalar_one()

        if max_orden is not None:
            return int(max_orden) + 1

        # B) si está vacía -> usar pendientes de la recepción anterior
        cur = session.get(Recepcion, recepcion_id)
        if not cur:
            return 1

        prev = session.execute(
            select(Recepcion)
            .where(
                Recepcion.prestador_id == cur.prestador_id,
                Recepcion.obra_social_id == cur.obra_social_id,
                Recepcion.fecha_presentacion < cur.fecha_presentacion,
            )
            .order_by(Recepcion.fecha_presentacion.desc())
            .limit(1)
        ).scalars().first()

        offset = int(prev.pendientes or 0) if prev else 0
        return offset + 1

    @staticmethod
    def list_fechas(recepcion_id: int) -> list[date]:
        import httpx
        from app.config.settings import settings

        url = f"{settings.API_CAFAPRO.rstrip('/')}/recepciones/{int(recepcion_id)}/fechas"
        resp = httpx.get(url, timeout=15)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        out: list[date] = []
        for v in resp.json():
            d = parse_date_any(v)
            if d:
                out.append(d)
        return out


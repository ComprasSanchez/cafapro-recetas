from __future__ import annotations

from datetime import date as dt_date, time as dt_time, date, datetime
from decimal import Decimal
from typing import Any

from core.api_client import get_client, TIMEOUT_HEAVY

from app.config.settings import settings


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/archivos{path}"


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
        return date.fromisoformat(s[:10])
    except Exception:
        return None


def _parse_date(v: Any) -> dt_date | None:
    if not v:
        return None
    s = str(v).strip()
    if s.isdigit() and len(s) == 8:
        return dt_date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
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
        return dt_time(int(parts[0]), int(parts[1]), 0)
    if len(parts) == 3:
        return dt_time(int(parts[0]), int(parts[1]), int(parts[2]))
    return None


def _normalize_item(receta: dict, detalles: list[dict], nro_referencia: str | None) -> dict:
    if not nro_referencia:
        nro_referencia = (
            receta.get("Nro_Referencia")
            or receta.get("Nro Referencia")
            or receta.get("nro_referencia")
        )
    nro_referencia = str(nro_referencia).strip() if nro_referencia else ""
    if not nro_referencia:
        raise ValueError("La receta no trae Nro Referencia (no se puede insertar).")

    beneficiario = receta.get("Beneficiario") or receta.get("beneficiario")
    fecha_raw = receta.get("Fecha") or receta.get("fecha")
    hora_raw = receta.get("Hora") or receta.get("hora")
    nro_receta = (
        receta.get("Nro_Receta")
        or receta.get("Nro Receta")
        or receta.get("nro_receta")
    )

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
    importe_afiliado_dec = (
        importe_bruto_dec - importe_cobertura_dec
        if importe_afiliado_input in (None, "")
        else _dec(importe_afiliado_input)
    )

    fecha_parsed = _parse_date(fecha_raw)
    hora_parsed = _parse_time(hora_raw)

    normalized_detalles = []
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

        if isinstance(imp_obs_raw_d, str) and "%" in imp_obs_raw_d and not desc:
            desc = imp_obs_raw_d.strip()
            imp_obs_raw_d = "0"

        if imp_bruto_raw_d in (None, "") and imp_cobertura_raw_d in (None, ""):
            imp_pami_dec = _dec(imp_obs_raw_d)
            pct_desc = _pct(desc)
            det_bruto = imp_pami_dec
            det_cobertura = imp_pami_dec * (pct_desc / Decimal("100"))
        else:
            det_bruto = _dec(imp_bruto_raw_d if imp_bruto_raw_d not in (None, "") else imp_gral_raw_d)
            det_cobertura = _dec(imp_cobertura_raw_d if imp_cobertura_raw_d not in (None, "") else imp_obs_raw_d)

        try:
            cantidad = int(str(cant_raw).strip())
        except Exception:
            cantidad = 0

        normalized_detalles.append({
            "codMedic": cod_medic,
            "codigoBarra": codigo_barra,
            "nombre": nombre,
            "presentacion": present,
            "estado": estado,
            "nroAutorizacion": nro_aut,
            "cantidad": cantidad,
            "importeBruto": str(det_bruto),
            "importeCobertura": str(det_cobertura),
            "descuento": desc,
        })

    return {
        "nroReferencia": nro_referencia,
        "nroReceta": str(nro_receta).strip() if nro_receta else None,
        "beneficiario": str(beneficiario).strip() if beneficiario else None,
        "fecha": fecha_parsed.isoformat() if fecha_parsed else None,
        "hora": hora_parsed.strftime("%H:%M:%S") if hora_parsed else None,
        "importeBruto": str(importe_bruto_dec),
        "importeCobertura": str(importe_cobertura_dec),
        "importeAfiliado": str(importe_afiliado_dec),
        "detalles": normalized_detalles,
    }


_BATCH_SIZE = 100


class ArchivoService:
    @staticmethod
    def bulk_from_imed(
        items: list[tuple[dict, list[dict], str]],
        recepcion_id: int | None,
        check_scope: str = "ref",
        actualizar_historial: bool = False,
    ) -> tuple[int, int]:
        """Recibe lista de (receta, detalles, nro_referencia), envía en lotes de 100.
        Retorna (insertados, omitidos) acumulados."""
        normalized = [_normalize_item(r, d, ref) for r, d, ref in items]
        total_insertados = 0
        total_omitidos = 0
        for i in range(0, len(normalized), _BATCH_SIZE):
            batch = normalized[i: i + _BATCH_SIZE]
            payload = {
                "recepcionId": int(recepcion_id) if recepcion_id is not None else None,
                "checkScope": check_scope,
                "actualizarHistorial": actualizar_historial,
                "recetas": batch,
            }
            resp = get_client().post(_url("/bulk"), json=payload, timeout=TIMEOUT_HEAVY)
            resp.raise_for_status()
            data = resp.json()
            total_insertados += int(data["insertados"])
            total_omitidos += int(data["omitidos"])
        return total_insertados, total_omitidos

    @staticmethod
    def list_fechas(recepcion_id: int) -> list[date]:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recepciones/{int(recepcion_id)}/fechas"
        resp = get_client().get(url)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        out: list[date] = []
        for v in resp.json():
            d = parse_date_any(v)
            if d:
                out.append(d)
        return out

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.db.session import session_scope
from app.service.integraciones.validators_client import ValidatorsClient
from app.service.recepcion.arrastre_exclusivos_service import ArrastreExcluidosService
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recetas.archivo_service import ArchivoService


def parse_aut_ts(receta: dict) -> datetime:
    f = (receta.get("Fecha") or "").strip()
    h = (receta.get("Hora") or "").strip()

    if not h:
        h = "00:00:00"
    elif len(h) == 5:
        h += ":00"

    return datetime.strptime(f"{f} {h}", "%d/%m/%Y %H:%M:%S")


def _fmt_num(v: Any) -> str:
    if v is None:
        return "0"
    return str(v)


def _to_ddmmyyyy(v: str | None) -> str:
    if not v:
        return datetime.now().strftime("%d/%m/%Y")

    s = str(v).strip()
    if not s:
        return datetime.now().strftime("%d/%m/%Y")

    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        pass

    if "T" in s:
        s = s.split("T", 1)[0]
    elif " " in s:
        s = s.split(" ", 1)[0]

    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        yyyy, mm, dd = s.split("-")
        return f"{dd}/{mm}/{yyyy}"

    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        return s

    return datetime.now().strftime("%d/%m/%Y")


def _to_hhmmss(v: str | None) -> str:
    if not v:
        return "00:00:00"

    s = str(v).strip()
    if not s:
        return "00:00:00"

    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        pass

    if "T" in s:
        s = s.split("T", 1)[1]
    elif " " in s:
        s = s.split(" ", 1)[1]

    s = s.strip().rstrip("Z")
    if len(s) >= 8 and s[2] == ":" and s[5] == ":":
        return s[:8]
    if len(s) >= 5 and s[2] == ":":
        return f"{s[:5]}:00"

    return "00:00:00"


def _to_iso_yyyy_mm_dd(v: str | None) -> str:
    s = str(v or "").strip()
    if not s:
        raise ValueError("La fecha es obligatoria para consultar validador IMED.")

    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        try:
            return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
        except ValueError as e:
            raise ValueError("Fecha inválida. Use formato dd/MM/yyyy.") from e

    if "T" in s:
        s = s.split("T", 1)[0]
    elif " " in s:
        s = s.split(" ", 1)[0]

    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError as e:
            raise ValueError("Fecha inválida para fechaHasta.") from e

    raise ValueError("Fecha inválida. Use formato dd/MM/yyyy.")


@dataclass(frozen=True)
class RecepcionOut:
    recepcion_id: int
    numero: str
    prestador: str
    obra_social: str
    imed: str
    obs: str
    validador: str
    dias_vencimiento: int | None
    codigo_financiador: int | None


@dataclass(frozen=True)
class CsvOut:
    recetas_por_ref: dict[str, dict]
    detalles_por_ref: dict[str, list[dict]]


@dataclass(frozen=True)
class SubirOut:
    inserted: int
    skipped: int
    failed: int
    errores: list[str]
    moved_prev_excluidos: int


class ArchivoCvsApplication:
    def __init__(self) -> None:
        self._validators = ValidatorsClient()

    @staticmethod
    def load_recepcion(*, recepcion_id: int, ctx=None) -> RecepcionOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo recepcion...")

        rec = RecepcionService.get(recepcion_id)
        if not rec:
            raise ValueError("No se encontro la recepcion seleccionada.")

        return RecepcionOut(
            recepcion_id=rec.recepcion_id,
            numero=str(getattr(rec, "numero", "") or ""),
            prestador=str(getattr(rec, "prestador", "") or ""),
            obra_social=str(getattr(rec, "obra_social", "") or ""),
            imed=str(getattr(rec, "imed", "") or ""),
            obs=str(getattr(rec, "obra_social", "") or ""),
            validador=str(getattr(rec, "validador", "imed") or "imed").lower(),
            dias_vencimiento=getattr(rec, "dias_vencimiento", None),
            codigo_financiador=getattr(rec, "codigo_financiador", None),
        )

    def load_csv(
        self,
        *,
        imed: str,
        fecha_str: str,
        obs: str,
        validador: str,
        nro_prestador: str,
        codigo_financiador: int | None,
        ctx=None,
    ) -> CsvOut:
        validador_norm = (validador or "imed").strip().lower()

        if not nro_prestador:
            raise ValueError("La recepcion no tiene prestador.imed para consultar API.")
        if codigo_financiador is None:
            raise ValueError("La obra social no tiene codigo financiador configurado.")

        try:
            nro_prestador_int = int(str(nro_prestador).strip())
        except Exception as e:
            raise ValueError("Prestador.imed debe ser numerico para consultar API.") from e

        fecha_hasta = date.today().isoformat()
        if validador_norm == "imed":
            fecha_hasta = _to_iso_yyyy_mm_dd(fecha_str)

        if ctx:
            ctx.emit_progress(10, "Consultando API de validadores (puede demorar varios minutos)...")

        raw = self._validators.get_pendientes(
            validador=validador_norm,
            nro_prestador=nro_prestador_int,
            cod_financiador=int(codigo_financiador),
            fecha_hasta=fecha_hasta,
        )

        recetas, detalles = self._api_to_internal(raw)

        if ctx:
            ctx.emit_progress(90, f"API lista: {len(recetas)} recetas")

        return CsvOut(recetas_por_ref=recetas, detalles_por_ref=detalles)

    @staticmethod
    def _api_to_internal(rows: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, list[dict]]]:
        recetas_por_ref: dict[str, dict] = {}
        detalles_por_ref: dict[str, list[dict]] = {}

        if not isinstance(rows, list):
            return recetas_por_ref, detalles_por_ref

        for raw in rows:
            if not isinstance(raw, dict):
                continue

            ref = str(raw.get("referencia") or "").strip()
            if not ref:
                continue

            fecha_txt = _to_ddmmyyyy(raw.get("fecha"))
            hora_txt = _to_hhmmss(raw.get("hora") or raw.get("fecha"))
            totales_raw = raw.get("totales")
            importe_bruto = _fmt_num(totales_raw.get("importeBruto", 0) if isinstance(totales_raw, dict) else 0)
            importe_cobertura = _fmt_num(totales_raw.get("importeCobertura", 0) if isinstance(totales_raw, dict) else 0)
            importe_afiliado = _fmt_num(totales_raw.get("importeAfiliado", 0) if isinstance(totales_raw, dict) else 0)

            receta = {
                "Beneficiario": str(raw.get("beneficiarioId") or "").strip(),
                "Orden_Del_Lote": str(raw.get("ordenLote") or 0),
                "Fecha": fecha_txt,
                "Hora": hora_txt,
                "Nro_Referencia": ref,
                "Nro_Receta": str(raw.get("numeroReceta") or "").strip(),
                "importe_bruto": importe_bruto,
                "importe_cobertura": importe_cobertura,
                "importe_afiliado": importe_afiliado,
            }
            recetas_por_ref[ref] = receta

            out_items: list[dict] = []
            items_raw = raw.get("items")
            items: list[Any] = []
            if isinstance(items_raw, list):
                items = items_raw
            for idx, it in enumerate(items, start=1):
                if not isinstance(it, dict):
                    continue
                codigo_medic = it.get("codigoMedicamento")
                codigo_barra = it.get("codigoBarra")
                descuento = it.get("descuentoPorcentaje")

                out_items.append(
                    {
                        "cod_medic": str(codigo_medic).strip() if codigo_medic is not None else None,
                        "codigo_barra": str(codigo_barra).strip() if codigo_barra not in (None, "") else None,
                        "nombre": str(it.get("nombre") or "").strip(),
                        "presentacion": str(it.get("presentacion") or "").strip(),
                        "estado": str(it.get("estado") or "").strip(),
                        "nro_aut": str(idx),
                        "cantidad": str(it.get("cantidad") or 0),
                        "importe_bruto": _fmt_num(it.get("importeBruto", 0)),
                        "importe_cobertura": _fmt_num(it.get("importeCobertura", 0)),
                        "desc": f"{descuento}%" if descuento not in (None, "") else None,
                    }
                )

            detalles_por_ref[ref] = out_items

        return recetas_por_ref, detalles_por_ref

    @staticmethod
    def load_csv_from_file(*, imed: str, fecha_str: str, obs: str, ctx=None) -> "CsvOut":
        from core.imed_cvs_handler import ImedCvsHandler

        if ctx:
            ctx.emit_progress(10, "Leyendo CSV IMED…")

        handler = ImedCvsHandler()
        recetas, detalles = handler.read_cvs_by_imed_and_date(imed=imed, date=fecha_str, obs=obs)
        recetas = recetas or {}
        detalles = detalles or {}

        if ctx:
            ctx.emit_progress(90, f"CSV listo: {len(recetas)} recetas")

        return CsvOut(recetas_por_ref=recetas, detalles_por_ref=detalles)

    @staticmethod
    def list_fechas_descargadas(*, recepcion_id: int):
        return ArchivoService.list_fechas(recepcion_id)

    @staticmethod
    def subir(
        *,
        recepcion_id: int,
        recetas_por_ref: dict[str, dict],
        detalles_por_ref: dict[str, list[dict]],
        ctx=None,
    ) -> SubirOut:
        total = len(recetas_por_ref)
        if total == 0:
            return SubirOut(inserted=0, skipped=0, failed=0, errores=[], moved_prev_excluidos=0)

        inserted = 0
        skipped = 0
        failed = 0
        errores: list[str] = []

        if ctx:
            ctx.emit_progress(2, "Preparando...")

        if ctx:
            ctx.emit_progress(4, "Chequeando pendientes anteriores...")

        moved_prev = ArrastreExcluidosService.run(recepcion_id=recepcion_id)

        if ctx and moved_prev > 0:
            ctx.emit_progress(6, f"Pendientes arrastrados: {moved_prev}")

        with session_scope() as s:

            current_orden = ArchivoService.get_start_orden_lote(s, recepcion_id)

            items: list[tuple] = []
            for nro_ref, receta in recetas_por_ref.items():
                ts = parse_aut_ts(receta)
                items.append((ts, str(nro_ref), receta))
            items.sort(key=lambda x: (x[0], x[1]))

            refs = [ref for _, ref, _ in items]
            existing_refs = ArchivoService.list_existing_refs(s, refs)

            chunk = 500
            progress_every = 50

            for i, (_ts, nro_ref, receta) in enumerate(items, start=1):
                if ctx and (i % progress_every == 0 or i == total):
                    pct = int((i / total) * 100)
                    ctx.emit_progress(pct, f"Subiendo {i}/{total}...")

                if nro_ref in existing_refs:
                    skipped += 1
                    continue

                detalles = detalles_por_ref.get(nro_ref, [])

                try:
                    creado = ArchivoService.create_from_imed(
                        s,
                        receta=receta,
                        detalles=detalles,
                        recepcion_id=recepcion_id,
                        nro_referencia=nro_ref,
                        orden_lote=current_orden,
                        skip_if_exists=True,
                        check_scope="ref",
                        existing_refs=existing_refs,
                    )

                    if creado:
                        inserted += 1
                        current_orden += 1
                    else:
                        skipped += 1

                except ValueError as e:
                    msg = str(e)
                    if "ya existe" in msg.lower() or "existe" in msg.lower():
                        skipped += 1
                    else:
                        failed += 1
                        errores.append(f"{nro_ref}: {msg}")

                except Exception as e:
                    failed += 1
                    errores.append(f"{nro_ref}: {e}")

                if i % chunk == 0:
                    s.flush()
                    s.commit()

            s.flush()
            s.commit()

        if ctx:
            ctx.emit_progress(100, "Subida finalizada")

        return SubirOut(
            inserted=inserted,
            skipped=skipped,
            failed=failed,
            errores=errores,
            moved_prev_excluidos=moved_prev,
        )

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
import unicodedata

from core.api_client import get_client, TIMEOUT_HEAVY
import xlsxwriter

from app.config.settings import settings


@dataclass
class DebitoViewRow:
    receta_id: int
    recepcion_id: int
    recepcion_numero: int | None
    motivo_debito_id: int
    estado_seguimiento_id: int | None
    estado_seguimiento: str | None
    orden_lote: int | None
    nro_receta: str | None
    nro_referencia: str | None
    importe_bruto: str | None
    importe_cobertura: str | None
    importe_afiliado: str | None
    descripcion_debito: str | None
    detalle: str | None
    creado_en: datetime | str | None
    prestador_nombre: str | None
    obs: str | None
    vendedor_nombre: str | None
    auditor_nombre: str | None
    fecha: str | None
    hora: str | None


def _url_debitos(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/debitos{path}"


def _url_recepciones(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones{path}"


def _url_recetas(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recetas{path}"


def _parse_datetime(value: str | None) -> datetime | str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return value


def _to_row(d: dict) -> DebitoViewRow:
    return DebitoViewRow(
        receta_id=int(d["recetaId"]),
        recepcion_id=int(d["recepcionId"]),
        recepcion_numero=d.get("recepcionNumero"),
        motivo_debito_id=int(d["motivoDebitoId"]),
        estado_seguimiento_id=d.get("estadoSeguimientoId"),
        estado_seguimiento=d.get("estadoSeguimiento"),
        orden_lote=d.get("ordenLote"),
        nro_receta=d.get("nroReceta"),
        nro_referencia=d.get("nroReferencia"),
        importe_bruto=d.get("importeBruto"),
        importe_cobertura=d.get("importeCobertura"),
        importe_afiliado=d.get("importeAfiliado"),
        descripcion_debito=d.get("descripcionDebito"),
        detalle=d.get("detalle"),
        creado_en=_parse_datetime(d.get("creadoEn")),
        prestador_nombre=d.get("prestadorNombre"),
        obs=d.get("obs"),
        vendedor_nombre=d.get("vendedorNombre"),
        auditor_nombre=d.get("auditorNombre"),
        fecha=d.get("fecha"),
        hora=d.get("hora"),
    )


class ViewDebitos:
    _MESES_ES = {
        1: "ENERO",
        2: "FEBRERO",
        3: "MARZO",
        4: "ABRIL",
        5: "MAYO",
        6: "JUNIO",
        7: "JULIO",
        8: "AGOSTO",
        9: "SEPTIEMBRE",
        10: "OCTUBRE",
        11: "NOVIEMBRE",
        12: "DICIEMBRE",
    }

    @staticmethod
    def list_recepciones() -> list[tuple[int, int]]:
        resp = get_client().get(_url_debitos("/recepciones"))
        resp.raise_for_status()
        out: list[tuple[int, int]] = []
        for r in resp.json():
            rid = r.get("recepcionId")
            if rid is None:
                continue
            rnum = r.get("recepcionNumero")
            out.append((int(rid), int(rnum) if rnum is not None else 0))
        return out

    @staticmethod
    def list_debitos(
        recepcion_id: int | None = None,
        fecha_auditoria: date | None = None,
    ) -> list[DebitoViewRow]:
        params: dict = {}
        if recepcion_id is not None:
            params["recepcionId"] = int(recepcion_id)
        if fecha_auditoria is not None:
            params["fechaAuditoria"] = (
                fecha_auditoria.isoformat()
                if isinstance(fecha_auditoria, date)
                else str(fecha_auditoria)
            )
        resp = get_client().get(_url_debitos(), params=params)
        resp.raise_for_status()
        return [_to_row(r) for r in resp.json()]

    @staticmethod
    def has_debitos_sin_estado_by_recepcion(*, recepcion_id: int) -> bool:
        resp = get_client().get(
            _url_debitos(f"/recepcion/{int(recepcion_id)}/sin-estado"),
        )
        resp.raise_for_status()
        return bool(resp.json().get("sinEstado", False))

    @staticmethod
    def get_periodo_label(recepcion_id: int) -> str:
        if not recepcion_id:
            return "sin-periodo"
        try:
            resp = get_client().get(
                _url_recepciones(f"/{int(recepcion_id)}/periodo-parts"),
            )
            if resp.status_code == 404:
                return "sin-periodo"
            resp.raise_for_status()
            data = resp.json()
            anio = int(data["anio"])
            mes = int(data["mes"])
            quincena = int(data["quincena"])
            return f"{anio:04d}-{mes:02d}-q{quincena}"
        except Exception:
            return "sin-periodo"

    @staticmethod
    def list_wrong_debitos_month(
        *,
        obra_social_id: int,
        anio: int,
        mes: int,
    ) -> list[DebitoViewRow]:
        resp = get_client().get(
            _url_debitos("/mal-entrego"),
            params={"obraSocialId": int(obra_social_id), "anio": int(anio), "mes": int(mes)},
        )
        resp.raise_for_status()
        return [_to_row(r) for r in resp.json()]

    @staticmethod
    def export_wrong_debitos_excel(
        *,
        rows: list[DebitoViewRow],
        folder: str,
        obra_social_nombre: str,
        anio: int,
        mes: int,
    ) -> str:
        if not rows:
            raise ValueError("No hay débitos mal entregados para exportar.")

        file_name = ViewDebitos.build_wrong_excel_filename(
            obra_social_nombre=obra_social_nombre,
            anio=int(anio),
            mes=int(mes),
        )
        output_path = Path(folder) / file_name

        workbook = xlsxwriter.Workbook(str(output_path))
        try:
            ws = workbook.add_worksheet("Mal Entrego")

            fmt_header = workbook.add_format({
                "bold": True,
                "bg_color": "#E6E6E6",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            })
            fmt_cell = workbook.add_format({"border": 1, "valign": "vcenter"})
            fmt_money = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
            fmt_date = workbook.add_format({"border": 1, "num_format": "dd/mm/yyyy"})

            headers = [
                "Farmacia",
                "Obra social",
                "N° Recepción",
                "Orden lote",
                "N° receta",
                "N° referencia",
                "Fecha auditoría",
                "Total",
                "A cargo OBS",
                "Débito",
                "Estado seguimiento",
                "Detalle",
                "Vendedor",
            ]

            obra_social_txt = str(obra_social_nombre or "").strip()

            for col, title in enumerate(headers):
                ws.write(0, col, title, fmt_header)

            ws.set_column(0, 0, 30)
            ws.set_column(1, 1, 28)
            ws.set_column(2, 2, 14)
            ws.set_column(3, 3, 10)
            ws.set_column(4, 4, 14)
            ws.set_column(5, 5, 16)
            ws.set_column(6, 6, 15)
            ws.set_column(7, 8, 12)
            ws.set_column(9, 9, 34)
            ws.set_column(10, 10, 24)
            ws.set_column(11, 11, 44)
            ws.set_column(12, 12, 24)
            ws.freeze_panes(1, 0)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, str(getattr(r, "prestador_nombre", "") or ""), fmt_cell)
                ws.write(i, 1, obra_social_txt, fmt_cell)
                ws.write(i, 2, getattr(r, "recepcion_numero", "") or "", fmt_cell)
                ws.write(i, 3, getattr(r, "orden_lote", "") or "", fmt_cell)
                ws.write(i, 4, str(getattr(r, "nro_receta", "") or ""), fmt_cell)
                ws.write(i, 5, str(getattr(r, "nro_referencia", "") or ""), fmt_cell)

                creado_en = getattr(r, "creado_en", None)
                if creado_en is not None:
                    try:
                        ws.write_datetime(i, 6, creado_en, fmt_date)
                    except Exception:
                        ws.write(i, 6, str(creado_en), fmt_cell)
                else:
                    ws.write(i, 6, "", fmt_cell)

                try:
                    ws.write_number(i, 7, float(getattr(r, "importe_bruto", 0) or 0), fmt_money)
                except Exception:
                    ws.write(i, 7, str(getattr(r, "importe_bruto", "") or ""), fmt_cell)

                try:
                    ws.write_number(i, 8, float(getattr(r, "importe_cobertura", 0) or 0), fmt_money)
                except Exception:
                    ws.write(i, 8, str(getattr(r, "importe_cobertura", "") or ""), fmt_cell)

                ws.write(i, 9, str(getattr(r, "descripcion_debito", "") or ""), fmt_cell)
                estado_seguimiento = getattr(r, "estado_seguimiento", None)
                estado_text = str(estado_seguimiento or "").strip() or "Sin estado"
                ws.write(i, 10, estado_text, fmt_cell)
                ws.write(i, 11, str(getattr(r, "detalle", "") or ""), fmt_cell)
                ws.write(i, 12, str(getattr(r, "vendedor_nombre", "") or ""), fmt_cell)
        finally:
            workbook.close()

        return str(output_path)

    @staticmethod
    def build_wrong_excel_filename(*, obra_social_nombre: str, anio: int, mes: int) -> str:
        os_slug = ViewDebitos._sanitize_filename_part(obra_social_nombre, fallback="OBRA_SOCIAL")
        mes_txt = ViewDebitos._MESES_ES.get(int(mes), f"MES_{int(mes):02d}")
        return f"MAL_ENTREGO_{os_slug}_{mes_txt}_{int(anio):04d}.xlsx"

    @staticmethod
    def _to_download_url(raw: str) -> str:
        v = (raw or "").strip()
        if not v:
            return ""
        if v.startswith("http://") or v.startswith("https://"):
            return v
        # Normaliza el base igual que _to_cloudfront_url en auditoria_application
        base = (settings.CLOUDFRONT_BASE_URL or "").strip()
        base = base.replace("https://", "").replace("http://", "").strip().rstrip("/")
        if not base:
            return ""
        return f"https://{base}/{v.lstrip('/')}"

    @staticmethod
    def download_wrong_debitos(rows, folder):
        receta_ids = {int(r.receta_id) for r in rows}
        rows_by_receta = {r.receta_id: r for r in rows}

        if not receta_ids:
            return 0

        resp = get_client().post(
            _url_recetas("/paths"),
            json={"recetaIds": list(receta_ids)},
        )
        resp.raise_for_status()
        recetas = resp.json()

        tasks = []
        for r in recetas:
            receta_id = r["recetaId"]
            row = rows_by_receta.get(receta_id)
            if row is None:
                continue

            obs = getattr(row, "obs", "")
            prestador = getattr(row, "prestador_nombre", "")
            nro_receta = getattr(row, "nro_receta", "")
            nro_referencia = getattr(row, "nro_referencia", "")

            if r.get("ubicacionFrente"):
                url = ViewDebitos._to_download_url(r["ubicacionFrente"])
                dest = os.path.join(
                    folder,
                    f"{obs}_{prestador}_{nro_receta}_{nro_referencia}_frente.jpg",
                )
                if url:
                    tasks.append((url, dest))

            if r.get("ubicacionDorso"):
                url = ViewDebitos._to_download_url(r["ubicacionDorso"])
                dest = os.path.join(
                    folder,
                    f"{obs}_{prestador}_{nro_receta}_{nro_referencia}_dorso.jpg",
                )
                if url:
                    tasks.append((url, dest))

        total = 0
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [
                executor.submit(ViewDebitos._download_one, url, dest)
                for url, dest in tasks
            ]
            for f in as_completed(futures):
                if f.result():
                    total += 1

        return total

    @staticmethod
    def _download_one(url, dest):
        if os.path.exists(dest):
            return False
        try:
            resp = get_client().get(url, timeout=TIMEOUT_HEAVY, follow_redirects=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            print("ERROR DOWNLOAD:", e)
            return False

    @staticmethod
    def _sanitize(text: str | None) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = text.encode("ascii", "ignore").decode("utf-8")
        text = text.replace(" ", "_")
        return re.sub(r"[^a-z0-9_]", "", text)

    @staticmethod
    def _sanitize_filename_part(text: str | None, *, fallback: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return fallback
        raw = unicodedata.normalize("NFD", raw)
        raw = raw.encode("ascii", "ignore").decode("utf-8")
        raw = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")
        up = raw.upper()
        return up or fallback

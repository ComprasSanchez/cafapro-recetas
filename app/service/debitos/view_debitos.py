import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
import re

import unicodedata
import xlsxwriter

from app.adapters.sqlalchemy.debitos_view_repository import DebitosViewRepository
from app.db.session import session_scope
from app.db.view import VwArchivoRecetaDebitos


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

        with session_scope() as s:
            rows = DebitosViewRepository.list_recepciones(s)

        out: list[tuple[int, int]] = []

        for rid, rnum in rows:

            if rid is None:
                continue

            out.append((int(rid), int(rnum) if rnum is not None else 0))

        return out

    @staticmethod
    def list_debitos(
        recepcion_id: int | None = None,
        fecha_auditoria: date | None = None,
    ) -> list[VwArchivoRecetaDebitos]:

        with session_scope() as s:
            return DebitosViewRepository.list_debitos(
                s,
                recepcion_id=recepcion_id,
                fecha_auditoria=fecha_auditoria,
            )

    @staticmethod
    def has_debitos_sin_estado_by_recepcion(*, recepcion_id: int) -> bool:
        with session_scope() as s:
            return DebitosViewRepository.has_debitos_sin_estado_by_recepcion(
                s,
                recepcion_id=int(recepcion_id),
            )

    @staticmethod
    def get_periodo_label(recepcion_id: int) -> str:
        if not recepcion_id:
            return "sin-periodo"

        try:
            with session_scope() as s:
                periodo_parts = DebitosViewRepository.get_periodo_parts(
                    s,
                    recepcion_id=int(recepcion_id),
                )

            if not periodo_parts:
                return "sin-periodo"

            anio, mes, quincena = periodo_parts
            return f"{int(anio):04d}-{int(mes):02d}-q{int(quincena)}"
        except Exception:
            return "sin-periodo"

    @staticmethod
    def list_wrong_debitos_month(
        *,
        obra_social_id: int,
        anio: int,
        mes: int,
    ) -> list[VwArchivoRecetaDebitos]:
        with session_scope() as s:
            return DebitosViewRepository.list_wrong_debitos_month(
                s,
                obra_social_id=int(obra_social_id),
                anio=int(anio),
                mes=int(mes),
            )

    @staticmethod
    def export_wrong_debitos_excel(
        *,
        rows: list[VwArchivoRecetaDebitos],
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
    def download_wrong_debitos(rows, folder, s3):

        receta_ids = {
            int(r.receta_id)
            for r in rows
        }
        rows_by_receta = {r.receta_id: r for r in rows}

        if not receta_ids:
            return 0

        with session_scope() as s:
            recetas = DebitosViewRepository.get_recetas_paths(
                s,
                receta_ids=receta_ids,
            )

        tasks = []

        for r in recetas:

            receta_id = r.receta_id

            row = rows_by_receta.get(receta_id)
            if row is None:
                continue

            obs = getattr(row, "obs", "")
            prestador = getattr(row, "prestador_nombre", "")
            nro_receta = getattr(row, "nro_receta", "")
            nro_referencia = getattr(row, "nro_referencia", "")

            if r.ubicacion_frente:
                dest = os.path.join(
                    folder,
                    f"{obs}_{prestador}_{nro_receta}_{nro_referencia}_frente.jpg"
                )

                tasks.append((r.ubicacion_frente, dest))

            if r.ubicacion_dorso:
                dest = os.path.join(
                    folder,
                    f"{obs}_{prestador}_{nro_receta}_{nro_referencia}_dorso.jpg"
                )

                tasks.append((r.ubicacion_dorso, dest))

        total = 0

        with ThreadPoolExecutor(max_workers=16) as executor:

            futures = [
                executor.submit(ViewDebitos._download_one, s3, key, dest)
                for key, dest in tasks
            ]

            for f in as_completed(futures):

                if f.result():
                    total += 1

        return total

    @staticmethod
    def _download_one(s3, key, dest):

        if os.path.exists(dest):
            return False

        try:

            s3.download_file(key, dest)

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

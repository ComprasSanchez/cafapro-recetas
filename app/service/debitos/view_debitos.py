import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import re

import unicodedata

from app.adapters.sqlalchemy.debitos_view_repository import DebitosViewRepository
from app.db.session import session_scope
from app.db.view import VwArchivoRecetaDebitos


class ViewDebitos:

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

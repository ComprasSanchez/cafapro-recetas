from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.db.models import Archivo
from app.db.session import session_scope
from app.service.recetas.archivo_service import ArchivoService
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recepcion.arrastre_exclusivos_service import ArrastreExcluidosService
from core.imed_cvs_handler import ImedCvsHandler


def parse_aut_ts(receta: dict) -> datetime:
    f = (receta.get("Fecha") or "").strip()
    h = (receta.get("Hora") or "").strip()

    if not h:
        h = "00:00:00"
    elif len(h) == 5:
        h += ":00"

    return datetime.strptime(f"{f} {h}", "%d/%m/%Y %H:%M:%S")


@dataclass(frozen=True)
class RecepcionOut:
    recepcion_id: int
    numero: str
    prestador: str
    obra_social: str
    imed: str
    obs: str


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


class ArchivoCvsUseCase:
    def __init__(self) -> None:
        self._cvs = ImedCvsHandler()

    @staticmethod
    def load_recepcion(*, recepcion_id: int, ctx=None) -> RecepcionOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo recepción…")

        with session_scope() as s:
            rows = RecepcionService.list(s)

        rec = next((x for x in rows if x.recepcion_id == recepcion_id), None)
        if not rec:
            raise ValueError("No se encontró la recepción seleccionada.")

        return RecepcionOut(
            recepcion_id=rec.recepcion_id,
            numero=str(getattr(rec, "numero", "") or ""),
            prestador=str(getattr(rec, "prestador", "") or ""),
            obra_social=str(getattr(rec, "obra_social", "") or ""),
            imed=str(getattr(rec, "imed", "") or ""),
            obs=str(getattr(rec, "obra_social", "") or ""),
        )

    def load_csv(self, *, imed: str, fecha_str: str, ctx=None) -> CsvOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo CSV IMED…")

        recetas, detalles = self._cvs.read_cvs_by_imed_and_date(imed=imed, date=fecha_str)
        recetas = recetas or {}
        detalles = detalles or {}

        if ctx:
            ctx.emit_progress(90, f"CSV listo: {len(recetas)} recetas")

        return CsvOut(recetas_por_ref=recetas, detalles_por_ref=detalles)

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
            ctx.emit_progress(2, "Preparando…")

        moved_prev = 0

        with session_scope() as s:
            if ctx:
                ctx.emit_progress(4, "Chequeando pendientes anteriores…")

            moved_prev = ArrastreExcluidosService.run(s, recepcion_id=recepcion_id)

            if ctx and moved_prev > 0:
                ctx.emit_progress(6, f"Pendientes arrastrados: {moved_prev}")


            current_orden = ArchivoService.get_start_orden_lote(s, recepcion_id)

            items: list[tuple] = []
            for nro_ref, receta in recetas_por_ref.items():
                ts = parse_aut_ts(receta)
                items.append((ts, str(nro_ref), receta))
            items.sort(key=lambda x: (x[0], x[1]))

            # ---------------------------------------------------------
            # 3) Prefetch existentes (1 query)
            #    (scope global por nro_referencia como venías haciendo)
            # ---------------------------------------------------------
            refs = [ref for _, ref, _ in items]
            existing_refs = set(
                s.execute(
                    select(Archivo.nro_referencia)
                    .where(Archivo.nro_referencia.in_(refs))
                ).scalars().all()
            )

            CHUNK = 500
            PROGRESS_EVERY = 50

            for i, (ts, nro_ref, receta) in enumerate(items, start=1):
                if ctx and (i % PROGRESS_EVERY == 0 or i == total):
                    pct = int((i / total) * 100)
                    ctx.emit_progress(pct, f"Subiendo {i}/{total}…")

                # saltar duplicados sin consultar DB por item
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

                if i % CHUNK == 0:
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


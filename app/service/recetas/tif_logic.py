from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import os

from core.process_tif import TroquelEstado

from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.tif_repository import TifRepository
from app.db.models import Archivo, ArchivoDetalle, EstadoTroquelEnum
from app.dto.medicamentos_dto import MedicamentoDTO
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.service.recetas.tif_types import _DetalleContext, _MatchResult, _TroquelEval


def norm_str(x) -> str:
    return str(x).strip() if x is not None else ""


def ref_candidates(token: str) -> list[str]:
    raw = norm_str(token)
    if not raw:
        return []
    return [raw]


def archivo_ts(a: Archivo) -> datetime:
    return datetime.fromisoformat(f"{a.fecha} {a.hora}")


def esta_vencido(archivo_ts_value: datetime, fecha_presentacion: datetime, dias_vencimiento: int | None) -> bool:
    if dias_vencimiento is None:
        return False
    cutoff = fecha_presentacion - timedelta(days=int(dias_vencimiento))
    return archivo_ts_value < cutoff


def base_from_tif_path(full_path: str) -> str:
    return Path(full_path).stem


def match_all_refs(
    session: Session,
    *,
    recepcion_id: int,
    refs: list[str],
    only_referencia: bool,
) -> _MatchResult:
    refs_set = {norm_str(r) for r in refs if norm_str(r)}
    if not refs_set:
        return _MatchResult(ref_to_archivo={}, duplicated_refs=set(), missing_refs=set())

    by_candidate: dict[str, set[str]] = {}
    for ref in refs_set:
        for cand in ref_candidates(ref):
            by_candidate.setdefault(cand, set()).add(ref)

    candidate_values = list(by_candidate.keys())
    if not candidate_values:
        return _MatchResult(ref_to_archivo={}, duplicated_refs=set(), missing_refs=refs_set)

    rows = TifRepository.list_archivos_for_match(
        session,
        recepcion_id=int(recepcion_id),
        candidate_values=candidate_values,
        only_referencia=only_referencia,
    )

    by_token: dict[str, dict[int, Archivo]] = {}
    for a in rows:
        tokens_to_check = [getattr(a, "nro_referencia", None)]
        if not only_referencia:
            tokens_to_check.append(getattr(a, "nro_receta", None))

        for db_token in tokens_to_check:
            db_candidates = ref_candidates(norm_str(db_token))
            for cand in db_candidates:
                matched_refs = by_candidate.get(cand, set())
                if not matched_refs:
                    continue
                for ref in matched_refs:
                    bucket = by_token.setdefault(ref, {})
                    bucket[int(a.archivo_id)] = a

    duplicated = {tok for tok, arr in by_token.items() if len(arr) > 1}
    missing = {tok for tok in refs_set if tok not in by_token}

    ref_to_archivo: dict[str, Archivo | None] = {}
    for tok in refs_set:
        if tok in duplicated:
            ref_to_archivo[tok] = None
        else:
            arr = by_token.get(tok)
            ref_to_archivo[tok] = next(iter(arr.values())) if arr else None

    return _MatchResult(ref_to_archivo=ref_to_archivo, duplicated_refs=duplicated, missing_refs=missing)


def year_month_from_basename_or_fallback(base_name: str, archivo: Archivo, tif_path: str) -> tuple[str, str]:
    part = base_name.split("_", 1)[1] if "_" in base_name else base_name
    if len(part) >= 6 and part[:6].isdigit():
        yyyy = part[:4]
        mm = part[4:6]
        if len(yyyy) == 4 and 1 <= int(mm) <= 12:
            return yyyy, mm
    try:
        fecha_txt = str(archivo.fecha)
        yyyy, mm, _dd = fecha_txt.split("-", 2)
        return yyyy, mm
    except Exception:
        ts = datetime.fromtimestamp(os.path.getmtime(tif_path))
        return f"{ts.year:04d}", f"{ts.month:02d}"


def build_s3_keys(*, prestador_imed: str, yyyy: str, mm: str, base_name: str) -> tuple[str, str]:
    base = f"{prestador_imed}/{yyyy}/{mm}"
    return f"{base}/{base_name}_f.jpg", f"{base}/{base_name}_d.jpg"


def codebar_candidates(codebar: str) -> list[str]:
    raw = norm_str(codebar)
    if not raw:
        return []
    return [raw]


def warm_medicamento_cache(
    client: MedicamentoClient,
    med_cache: dict[str, MedicamentoDTO | None],
    codebars: set[str],
) -> None:
    missing = [cb for cb in codebars if cb and cb not in med_cache]
    if not missing:
        return

    variants_by_codebar: dict[str, list[str]] = {
        cb: codebar_candidates(cb)
        for cb in missing
    }

    to_fetch: set[str] = set()
    for variants in variants_by_codebar.values():
        for v in variants:
            if v not in med_cache:
                to_fetch.add(v)

    if to_fetch:
        batch_result = client.get_many_by_codebars(list(to_fetch))
        for cb, dto in batch_result.items():
            med_cache[cb] = dto

    for original, variants in variants_by_codebar.items():
        chosen: MedicamentoDTO | None = None
        for v in variants:
            dto = med_cache.get(v)
            if dto is not None:
                chosen = dto
                break
        med_cache[original] = chosen


def build_detalle_context(dets: list[ArchivoDetalle]) -> _DetalleContext:
    cods_detalle: set[str] = set()
    cant_por_cod: dict[str, int] = {}
    importe_por_cod: dict[str, Decimal] = {}

    for d in dets:
        ca = norm_str(getattr(d, "cod_medic", None))
        if not ca:
            continue

        cods_detalle.add(ca)

        cant_por_cod[ca] = cant_por_cod.get(ca, 0) + int(getattr(d, "cantidad", 0) or 0)

        imp_cob = getattr(d, "importe_bruto", 0)
        imp_dec = Decimal(str(imp_cob or 0))
        importe_por_cod[ca] = importe_por_cod.get(ca, Decimal("0")) + imp_dec

    return _DetalleContext(
        cods_detalle=cods_detalle,
        cant_por_cod=cant_por_cod,
        importe_por_cod=importe_por_cod,
    )


def evaluate_troqueles(
    *,
    scan_troqueles: list[str],
    detalle: _DetalleContext,
    med_cache: dict[str, MedicamentoDTO | None],
) -> list[_TroquelEval]:
    counts: dict[str, int] = dict(
        Counter(
            norm_str(c)
            for c in (scan_troqueles or [])
            if norm_str(c)
        )
    )

    evals: list[_TroquelEval] = []

    for codebar, qty_scan in counts.items():
        dto = med_cache.get(codebar)

        if dto is None:
            evals.append(
                _TroquelEval(
                    codebar=codebar,
                    cantidad_scan=int(qty_scan),
                    estado=EstadoTroquelEnum.A,
                    code_alfabeta=0,
                    droga_concat=None,
                    presentacion=None,
                    monto=Decimal("0"),
                )
            )
            continue

        code_alfabeta = int(dto.code_alfabeta or 0)
        ca = norm_str(dto.code_alfabeta)
        match_detalle = bool(ca) and (ca in detalle.cods_detalle)

        if not match_detalle:
            estado = EstadoTroquelEnum.R
            monto = Decimal("0")
        else:
            qty_det = int(detalle.cant_por_cod.get(ca, 0))
            estado = EstadoTroquelEnum.V if qty_det == int(qty_scan) else EstadoTroquelEnum.R
            monto = detalle.importe_por_cod.get(ca, Decimal("0"))

        evals.append(
            _TroquelEval(
                codebar=codebar,
                cantidad_scan=int(qty_scan),
                estado=estado,
                code_alfabeta=code_alfabeta,
                droga_concat=dto.drogas_concat,
                presentacion=dto.presentacion,
                monto=monto,
            )
        )

    return evals


def evaluate_revision_troqueles(
    *,
    scan_troqueles: list[str],
    med_cache: dict[str, MedicamentoDTO | None],
) -> list[_TroquelEval]:
    counts: dict[str, int] = dict(
        Counter(
            norm_str(c)
            for c in (scan_troqueles or [])
            if norm_str(c)
        )
    )

    evals: list[_TroquelEval] = []
    for codebar, qty_scan in counts.items():
        dto = med_cache.get(codebar)

        if dto is None:
            evals.append(
                _TroquelEval(
                    codebar=codebar,
                    cantidad_scan=int(qty_scan),
                    estado=EstadoTroquelEnum.A,
                    code_alfabeta=0,
                    droga_concat=None,
                    presentacion=None,
                    monto=Decimal("0"),
                )
            )
            continue

        evals.append(
            _TroquelEval(
                codebar=codebar,
                cantidad_scan=int(qty_scan),
                estado=EstadoTroquelEnum.A,
                code_alfabeta=int(dto.code_alfabeta or 0),
                droga_concat=dto.drogas_concat,
                presentacion=dto.presentacion,
                monto=Decimal("0"),
            )
        )

    return evals


def to_render_states(evals: list[_TroquelEval]) -> dict[str, TroquelEstado]:
    out: dict[str, TroquelEstado] = {}

    for e in evals:
        if e.estado == EstadoTroquelEnum.V:
            out[e.codebar] = "V"
        elif e.estado == EstadoTroquelEnum.A:
            out[e.codebar] = "A"
        else:
            out[e.codebar] = "R"

    return out


def is_valesalud(obra_social_nombre: str | None) -> bool:
    return "valesalud" in (obra_social_nombre or "").strip().lower()

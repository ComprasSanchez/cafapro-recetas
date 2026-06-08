from __future__ import annotations

import httpx

from app.config.settings import settings
from app.service.recetas.tif_logic import norm_str
from app.service.recetas.tif_types import ProcesarResumen, _TroquelEval, _UploadResult


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones{path}"


def filter_valid_uploaded(uploaded: list[_UploadResult], resumen: ProcesarResumen) -> list[_UploadResult]:
    valid_uploaded: list[_UploadResult] = []
    for u in uploaded:
        if not u.front_key and not u.back_key:
            resumen.errores.append(f"{u.work.it.file_name}: no se subio frente ni dorso")
            continue
        valid_uploaded.append(u)
    return valid_uploaded


def persist_uploaded_chunk(
    *,
    recepcion_id: int,
    usuario_id: int,
    valid_uploaded: list[_UploadResult],
    archivo_by_id: dict,
    troquel_evals_by_work_id: dict[int, list[_TroquelEval]],
    troquel_evals_by_archivo_id: dict[int, list[_TroquelEval]],
    revision_reason_by_work_id: dict[int, str],
    dias_vencimiento: int | None,
    motivo_debito_receta_vencida_id: int,
    revision_counter: int,
) -> int:
    recetas_payload = []

    for u in valid_uploaded:
        w = u.work
        es_revision = w.archivo_id == 0

        if es_revision:
            reason = str(revision_reason_by_work_id.get(id(w), "Revision") or "Revision")
            nro_receta = "-"
            observacion = reason
            estado_receta_id = 3
            archivo_id = 0
            vencida = False
            replace_receta_id = None
        else:
            archivo = archivo_by_id[w.archivo_id]
            nro_receta = norm_str(getattr(archivo, "nro_receta", None)) or f"REV-{revision_counter}"
            observacion = None
            estado_receta_id = 2
            archivo_id = int(w.archivo_id)
            vencida = bool(getattr(archivo, "vencido", False))
            replace_raw = int(getattr(w, "replace_receta_id", 0) or 0)
            replace_receta_id = replace_raw if replace_raw > 0 else None

        evals: list[_TroquelEval] = troquel_evals_by_work_id.get(
            id(w),
            troquel_evals_by_archivo_id.get(w.archivo_id, []) if not es_revision else [],
        )

        troqueles = []
        for e in evals:
            estado_val = e.estado.value if hasattr(e.estado, "value") else str(e.estado)
            if es_revision:
                estado_val = "A"
            troqueles.append({
                "codigoBarra": e.codebar,
                "droga": e.droga_concat,
                "presentacion": e.presentacion,
                "codeAlfabeta": int(e.code_alfabeta),
                "monto": str(e.monto),
                "cantidad": int(e.cantidad_scan),
                "estado": estado_val,
            })

        recetas_payload.append({
            "archivoId": archivo_id,
            "nroReceta": nro_receta,
            "ubicacionFrente": u.front_key,
            "ubicacionDorso": u.back_key,
            "estadoRecetaId": estado_receta_id,
            "observacion": observacion,
            "esRevision": es_revision,
            "replaceRecetaId": replace_receta_id,
            "vencida": vencida,
            "troqueles": troqueles,
        })

    if not recetas_payload:
        return 0

    resp = httpx.post(
        _url(f"/{recepcion_id}/tif-chunk"),
        json={
            "usuarioId": int(usuario_id),
            "recetas": recetas_payload,
            "motivoDebitoVencidaId": int(motivo_debito_receta_vencida_id),
        },
        timeout=600,
    )
    resp.raise_for_status()
    return int(resp.json().get("persistidos", 0))

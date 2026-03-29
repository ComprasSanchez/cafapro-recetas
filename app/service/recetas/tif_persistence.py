from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.tif_repository import TifRepository
from app.db.models import Archivo, Asociacion, Debitos, EstadoTroquelEnum, Recetas, Troqueles
from app.service.recetas.tif_logic import norm_str
from app.service.recetas.tif_types import ProcesarResumen, _TroquelEval, _UploadResult


def filter_valid_uploaded(uploaded: list[_UploadResult], resumen: ProcesarResumen) -> list[_UploadResult]:
    valid_uploaded: list[_UploadResult] = []
    for u in uploaded:
        if not u.front_key and not u.back_key:
            resumen.errores.append(f"{u.work.it.file_name}: no se subio frente ni dorso")
            continue
        valid_uploaded.append(u)
    return valid_uploaded


def persist_uploaded_chunk(
    session: Session,
    *,
    recepcion_id: int,
    usuario_id: int,
    valid_uploaded: list[_UploadResult],
    archivo_by_id: dict[int, Archivo],
    troquel_evals_by_work_id: dict[int, list[_TroquelEval]],
    troquel_evals_by_archivo_id: dict[int, list[_TroquelEval]],
    dias_vencimiento: int | None,
    motivo_debito_receta_vencida_id: int,
    revision_counter: int,
) -> int:
    recetas_to_add: list[Recetas] = []
    asoc_to_add: list[Asociacion] = []
    troqueles_to_add: list[Troqueles] = []

    receta_by_archivo_id: dict[int, Recetas] = {}
    receta_by_work_id: dict[int, Recetas] = {}

    for u in valid_uploaded:
        if u.work.archivo_id == 0:
            receta = Recetas(
                recepcion_id=int(recepcion_id),
                nro_receta="-",
                ubicacion_frente=u.front_key,
                ubicacion_dorso=u.back_key,
                fecha_prescripcion=None,
                observacion=None,
                usuario_id=usuario_id,
                estado_receta_id=3,
                creado_en=datetime.now(),
                vigente=True,
            )

            recetas_to_add.append(receta)
            receta_by_work_id[id(u.work)] = receta
            continue

        archivo = archivo_by_id[u.work.archivo_id]
        nro_receta = norm_str(getattr(archivo, "nro_receta", None)) or f"REV-{revision_counter}"

        receta = Recetas(
            recepcion_id=int(recepcion_id),
            nro_receta=nro_receta,
            ubicacion_frente=u.front_key,
            ubicacion_dorso=u.back_key,
            fecha_prescripcion=None,
            observacion=None,
            usuario_id=usuario_id,
            estado_receta_id=2,
            creado_en=datetime.now(),
            vigente=True,
        )
        recetas_to_add.append(receta)
        receta_by_archivo_id[u.work.archivo_id] = receta
        receta_by_work_id[id(u.work)] = receta

    session.add_all(recetas_to_add)
    session.flush()

    recetas_vencidas_ids: list[int] = []

    for u in valid_uploaded:
        w = u.work

        if w.archivo_id == 0:
            receta = receta_by_work_id.get(id(w))
            if receta is None:
                continue

            evals = troquel_evals_by_work_id.get(id(w), [])
            for e in evals:
                troqueles_to_add.append(
                    Troqueles(
                        receta_id=receta.receta_id,
                        codigo_barra=e.codebar,
                        droga=e.droga_concat,
                        presentacion=e.presentacion,
                        code_alfabeta=e.code_alfabeta,
                        monto=e.monto,
                        cantidad=e.cantidad_scan,
                        estado=EstadoTroquelEnum.A,
                    )
                )
            continue

        archivo = archivo_by_id[w.archivo_id]
        receta = receta_by_archivo_id[w.archivo_id]

        asoc_to_add.append(Asociacion(receta_id=receta.receta_id, archivo_id=w.archivo_id, vigente=True))

        esta_vencido = bool(getattr(archivo, "vencido", False))
        if esta_vencido:
            recetas_vencidas_ids.append(int(receta.receta_id))

        evals = troquel_evals_by_work_id.get(id(w), troquel_evals_by_archivo_id.get(w.archivo_id, []))
        for e in evals:
            troqueles_to_add.append(
                Troqueles(
                    receta_id=receta.receta_id,
                    codigo_barra=e.codebar,
                    droga=e.droga_concat,
                    presentacion=e.presentacion,
                    code_alfabeta=e.code_alfabeta,
                    monto=e.monto,
                    cantidad=e.cantidad_scan,
                    estado=e.estado,
                )
            )

    if asoc_to_add:
        session.add_all(asoc_to_add)
    if troqueles_to_add:
        session.add_all(troqueles_to_add)

    if recetas_vencidas_ids:
        ya_tienen = TifRepository.get_recetas_with_motivo(
            session,
            receta_ids=recetas_vencidas_ids,
            motivo_id=motivo_debito_receta_vencida_id,
        )

        for rid in recetas_vencidas_ids:
            if rid in ya_tienen:
                continue
            session.add(
                Debitos(
                    receta_id=rid,
                    motivo_debito_id=motivo_debito_receta_vencida_id,
                    detalle=(
                        f"Vencido por {dias_vencimiento} dias (auto)"
                        if dias_vencimiento is not None
                        else "Vencido (auto)"
                    ),
                )
            )

    return len(valid_uploaded)

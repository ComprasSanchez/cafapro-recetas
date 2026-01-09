from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.service.archivo_match_service import ArchivoMatchServiceFast
from app.service.tiff_processing_service import TiffProcessingService, TiffResult
from app.db.models import Recetas, Asociacion, Troqueles, Archivo


@dataclass(frozen=True)
class ProcesarItemIn:
    file_name: str
    full_path: str


@dataclass
class ProcesarResumen:
    ok: int = 0
    sin_match: int = 0
    duplicados: int = 0
    ya_asociado: int = 0
    errores: List[str] = None

    def __post_init__(self):
        if self.errores is None:
            self.errores = []


class ProcesarRecepcionServiceFast:
    def __init__(
        self,
        tiff_svc: Optional[TiffProcessingService] = None,
        match_svc: Optional[ArchivoMatchServiceFast] = None,
    ):
        self._tiff = tiff_svc or TiffProcessingService()
        self._match = match_svc or ArchivoMatchServiceFast()

    def procesar(
        self,
        s: Session,
        recepcion_id: int,
        usuario_id: int | None,
        items: List[ProcesarItemIn],
        output_dir: str | None = None,
    ) -> ProcesarResumen:
        resumen = ProcesarResumen()
        parsed_per_item: list[tuple[ProcesarItemIn, TiffResult]] = []
        all_refs: list[str] = []

        for it in items:
            try:
                tiff_res = self._tiff.process(it.full_path, output_dir=output_dir)
                parsed_per_item.append((it, tiff_res))
                all_refs.extend(tiff_res.referencias)
            except Exception as e:
                resumen.errores.append(f"{it.file_name}: {e}")

        # 2) Match masivo de Archivo por referencias
        match = self._match.match_all_refs(s, all_refs)

        # 3) Para cada item elegimos EL primer ref que tenga match único
        #    - si alguno de sus refs es duplicado => marcamos duplicado y no insertamos
        #    - si ninguno matchea => sin_match
        #    - si matchea => seguimos
        work: list[tuple[int, TiffResult]] = []   # (archivo_id, tiff_res)
        archivos_to_update = []                   # Archivo objects

        for it, tiff_res in parsed_per_item:
            refs = [str(x).strip() for x in tiff_res.referencias if x]

            if not refs:
                resumen.sin_match += 1
                continue

            # si tiene al menos un ref duplicado, abortamos este tif
            if any(ref in match.duplicated_refs for ref in refs):
                resumen.duplicados += 1
                continue

            archivo = None
            for ref in refs:
                archivo = match.ref_to_archivo.get(ref)
                if archivo is not None:
                    break

            if archivo is None:
                resumen.sin_match += 1
                continue

            # update recepcion_id en memoria (1 commit al final)
            if archivo.recepcion_id != recepcion_id:
                archivo.recepcion_id = recepcion_id
                archivos_to_update.append(archivo)

            work.append((archivo.archivo_id, tiff_res))

        if not work:
            return resumen

        archivo_ids = [aid for aid, _ in work]
        archivos = archivos = s.execute(
            select(Archivo).where(Archivo.archivo_id.in_(archivo_ids))
        ).scalars().all()
        archivo_by_id = {a.archivo_id: a for a in archivos}

        # 5) Preparar recetas (key: recepcion_id + nro_receta)
        receta_keys = []
        receta_data = []
        for archivo_id, tiff_res in work:
            a = archivo_by_id[archivo_id]
            nro_receta = str(a.nro_receta) if a.nro_receta else "-"
            receta_keys.append((recepcion_id, nro_receta))
            receta_data.append((archivo_id, nro_receta, tiff_res))

        # traer recetas existentes en 1 query
        existentes = s.execute(
            select(Recetas).where(tuple_(Recetas.recepcion_id, Recetas.nro_receta).in_(receta_keys))
        ).scalars().all()
        receta_by_key = {(r.recepcion_id, r.nro_receta): r for r in existentes}

        nuevas_recetas = []
        # actualizar ubicaciones/estado en existentes y preparar nuevas
        for archivo_id, nro_receta, tiff_res in receta_data:
            key = (recepcion_id, nro_receta)
            r = receta_by_key.get(key)
            if r:
                r.estado_seguimiento_id = 6
                r.ubicacion_frente = tiff_res.frente_jpg
                r.ubicacion_dorso = tiff_res.dorso_jpg
            else:
                nuevas_recetas.append(
                    Recetas(
                        recepcion_id=recepcion_id,
                        nro_receta=nro_receta,
                        ubicacion_frente=tiff_res.frente_jpg,
                        ubicacion_dorso=tiff_res.dorso_jpg,
                        fecha_prescripcion=None,
                        estado_seguimiento_id=6,
                        observacion=None,
                        usuario_id=usuario_id,  # puede ser None si tu DB lo permite
                    )
                )

        if nuevas_recetas:
            s.add_all(nuevas_recetas)
            s.flush()  # asigna receta_id

            # refrescar mapping con nuevas
            for r in nuevas_recetas:
                receta_by_key[(r.recepcion_id, r.nro_receta)] = r

        # 6) Asociaciones: evitar 1 query por fila
        # armar pares (receta_id, archivo_id)
        pairs = []
        pair_to_payload = []  # (receta_id, archivo_id, tiff_res)
        for archivo_id, nro_receta, tiff_res in receta_data:
            receta = receta_by_key[(recepcion_id, nro_receta)]
            pairs.append((receta.receta_id, archivo_id))
            pair_to_payload.append((receta.receta_id, archivo_id, tiff_res))

        # traer existentes en 1 query
        existentes_asoc = s.execute(
            select(Asociacion.receta_id, Asociacion.archivo_id)
            .where(tuple_(Asociacion.receta_id, Asociacion.archivo_id).in_(pairs))
        ).all()
        exists_set = set(existentes_asoc)

        nuevas_asoc = []
        troqueles_bulk: dict[tuple[int, str], Troqueles] = {}


        for receta_id, archivo_id, tiff_res in pair_to_payload:
            if (receta_id, archivo_id) in exists_set:
                resumen.ya_asociado += 1
                continue

            nuevas_asoc.append(Asociacion(receta_id=receta_id, archivo_id=archivo_id))

            # troqueles bulk (si querés idempotencia, lo vemos después)
            for cod in tiff_res.troqueles:
                cod = str(cod).strip()
                if not cod:
                    continue
                key = (receta_id, cod)

                if key in troqueles_bulk:
                    troqueles_bulk[key].cantidad += 1
                else:
                    troqueles_bulk[key] = Troqueles(
                        receta_id=receta_id,
                        codigo_barra=cod,
                        cantidad=1,
                        monto=0,
                        estado="OK",
                    )

            resumen.ok += 1

        if nuevas_asoc:
            s.add_all(nuevas_asoc)
        if troqueles_bulk:
            s.add_all(troqueles_bulk.values())

        return resumen

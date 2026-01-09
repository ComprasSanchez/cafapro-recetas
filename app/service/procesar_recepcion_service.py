from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.service.recetas_service import RecetaService
from app.service.tiff_processing_service import TiffProcessingService
from app.service.archivo_match_service import ArchivoMatchService


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


class ProcesarRecepcionService:
    def __init__(
        self,
        tiff_svc: Optional[TiffProcessingService] = None,
        match_svc: Optional[ArchivoMatchService] = None,
        receta_svc: Optional[RecetaService] = None,
    ):
        self._tiff = tiff_svc or TiffProcessingService()
        self._match = match_svc or ArchivoMatchService()
        self._receta = receta_svc or RecetaService()

    def procesar(
        self,
        s: Session,
        recepcion_id: int,
        usuario_id: int | None,
        items: List[ProcesarItemIn],
        output_dir: str | None = None,
    ) -> ProcesarResumen:
        resumen = ProcesarResumen()

        for it in items:
            try:
                tiff_res = self._tiff.process(it.full_path, output_dir=output_dir)

                match = self._match.match_by_referencias(s, tiff_res.referencias)

                if match.motivo == "duplicado":
                    resumen.duplicados += 1
                    continue

                if match.motivo == "sin_match" or match.archivo is None:
                    resumen.sin_match += 1
                    continue

                archivo = match.archivo

                # Actualizar archivo->recepcion
                self._receta.attach_archivo_to_recepcion(archivo, recepcion_id)

                # nro_receta sale del Archivo (porque el TiffProcessor no devuelve nro_receta)
                nro_receta = str(archivo.nro_receta) if archivo.nro_receta else "-"
                receta = self._receta.get_or_create_receta(
                    s=s,
                    recepcion_id=recepcion_id,
                    nro_receta=nro_receta,
                    usuario_id=usuario_id,
                    ubicacion_frente=tiff_res.frente_jpg,
                    ubicacion_dorso=tiff_res.dorso_jpg,
                )

                # Asociacion
                created = self._receta.ensure_asociacion(s, receta.receta_id, archivo.archivo_id)
                if not created:
                    resumen.ya_asociado += 1
                    continue

                # Troqueles
                self._receta.add_troqueles(s, receta.receta_id, tiff_res.troqueles)

                resumen.ok += 1

            except Exception as e:
                resumen.errores.append(f"{it.file_name}: {e}")

        return resumen

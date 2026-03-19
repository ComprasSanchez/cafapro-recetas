from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Literal, Iterable
from collections import Counter
import os

from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import select, update, or_, and_, tuple_
from sqlalchemy.orm import Session

from core.process_tif import TiffProcessor, ScanOut
from app.db.models import (
    Archivo,
    ArchivoDetalle,
    Recetas,
    Asociacion,
    Troqueles,
    EstadoTroquelEnum,
    Recepcion,
    Debitos,
    Prestador,
    ObraSocial,
)
from app.infra.s3_storage import S3Storage
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.dto.medicamentos_dto import MedicamentoDTO


# -------------------------
# Helpers
# -------------------------
def _chunks(lst: List, size: int) -> Iterable[List]:
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


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

    def __post_init__(self) -> None:
        if self.errores is None:
            self.errores = []

    def merge(self, other: "ProcesarResumen") -> None:
        self.ok += other.ok
        self.sin_match += other.sin_match
        self.duplicados += other.duplicados
        self.ya_asociado += other.ya_asociado
        self.errores.extend(other.errores)


@dataclass(frozen=True)
class _MatchResult:
    ref_to_archivo: Dict[str, Optional[Archivo]]
    duplicated_refs: Set[str]
    missing_refs: Set[str]


@dataclass(frozen=True)
class _ScannedItem:
    it: ProcesarItemIn
    scan: ScanOut


@dataclass(frozen=True)
class _WorkItem:
    it: ProcesarItemIn
    scan: ScanOut
    archivo_id: int


@dataclass(frozen=True)
class _UploadResult:
    work: _WorkItem
    front_key: Optional[str]
    back_key: Optional[str]


class TiffService:
    def __init__(
        self,
        *,
        storage: S3Storage,
        tif: Optional[TiffProcessor] = None,
        client: Optional[MedicamentoClient] = None,
        chunk_size: int = 75,
        scan_workers: Optional[int] = None,
        upload_workers: int = 32,
    ) -> None:
        self._storage = storage
        self._tif = tif or TiffProcessor()
        self._client = client or MedicamentoClient()

        cpu = os.cpu_count() or 4
        self._chunk_size = int(chunk_size)
        self._scan_workers = int(scan_workers or min(cpu, 6))
        self._upload_workers = int(upload_workers)

    # -------------------------
    # Helpers (idénticos a los tuyos)
    # -------------------------
    @staticmethod
    def _norm_str(x) -> str:
        return str(x).strip() if x is not None else ""

    @staticmethod
    def _exists_processed_base_in_recepcion(s: Session, recepcion_id: int, base_name: str) -> bool:
        like_pat = f"%/{base_name}_%"
        rid = (
            s.execute(
                select(Recetas.receta_id)
                .where(
                    and_(
                        Recetas.recepcion_id == int(recepcion_id),
                        or_(
                            Recetas.ubicacion_frente.ilike(like_pat),
                            Recetas.ubicacion_dorso.ilike(like_pat),
                        ),
                    )
                )
                .limit(1)
            )
            .scalar_one_or_none()
        )
        return rid is not None

    @staticmethod
    def _archivo_ts(a: Archivo) -> datetime:
        return datetime.fromisoformat(f"{a.fecha} {a.hora}")

    @staticmethod
    def _esta_vencido(archivo_ts: datetime, fecha_presentacion: datetime, dias_vencimiento: int | None) -> bool:
        if dias_vencimiento is None:
            return False
        cutoff = fecha_presentacion - timedelta(days=int(dias_vencimiento))
        return archivo_ts < cutoff

    @staticmethod
    def _base_from_tif_path(full_path: str) -> str:
        return Path(full_path).stem

    @staticmethod
    def _match_all_refs(
        s: Session,
        recepcion_id: int,
        refs: List[str],
        *,
        only_referencia: bool = False,
    ) -> _MatchResult:
        refs_set: Set[str] = {str(r).strip() for r in refs if r and str(r).strip()}
        if not refs_set:
            return _MatchResult(ref_to_archivo={}, duplicated_refs=set(), missing_refs=set())

        where_match = Archivo.nro_referencia.in_(list(refs_set))
        if not only_referencia:
            where_match = or_(
                where_match,
                Archivo.nro_receta.in_(list(refs_set)),
            )

        rows = (
            s.execute(
                select(Archivo).where(
                    and_(
                        Archivo.recepcion_id == int(recepcion_id),
                        where_match,
                    )
                )
            )
            .scalars()
            .all()
        )

        by_token: Dict[str, List[Archivo]] = {}
        for a in rows:
            nro_ref = (getattr(a, "nro_referencia", "") or "").strip()
            nro_rec = (getattr(a, "nro_receta", "") or "").strip()

            if nro_ref and nro_ref in refs_set:
                by_token.setdefault(nro_ref, []).append(a)
            if not only_referencia and nro_rec and nro_rec in refs_set:
                by_token.setdefault(nro_rec, []).append(a)

        duplicated = {tok for tok, arr in by_token.items() if len(arr) > 1}
        missing = {tok for tok in refs_set if tok not in by_token}

        ref_to_archivo: Dict[str, Optional[Archivo]] = {}
        for tok in refs_set:
            if tok in duplicated:
                ref_to_archivo[tok] = None
            else:
                arr = by_token.get(tok)
                ref_to_archivo[tok] = arr[0] if arr else None

        return _MatchResult(ref_to_archivo=ref_to_archivo, duplicated_refs=duplicated, missing_refs=missing)

    @staticmethod
    def _year_month_from_basename_or_fallback(base_name: str, archivo: Archivo, tif_path: str) -> tuple[str, str]:
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

    @staticmethod
    def _build_s3_keys(*, prestador_imed: str, yyyy: str, mm: str, base_name: str) -> tuple[str, str]:
        base = f"{prestador_imed}/{yyyy}/{mm}"
        return (f"{base}/{base_name}_f.jpg", f"{base}/{base_name}_d.jpg")

    # -------------------------
    # Paralelos
    # -------------------------
    def _parallel_scan(self, items: List[ProcesarItemIn], resumen: ProcesarResumen) -> List[_ScannedItem]:
        out: List[_ScannedItem] = []

        def job(it: ProcesarItemIn) -> Tuple[ProcesarItemIn, ScanOut]:
            scan = self._tif.scan(it.full_path)  # carga pages internamente
            return it, scan

        with ThreadPoolExecutor(max_workers=self._scan_workers) as ex:
            futs = [ex.submit(job, it) for it in items]
            for fut in as_completed(futs):
                try:
                    it, scan = fut.result()
                    out.append(_ScannedItem(it=it, scan=scan))
                except Exception as e:
                    # no tenemos it acá si explotó antes; lo dejamos genérico
                    resumen.errores.append(f"scan error: {e}")

        return out

    def _parallel_render_upload(
            self,
            work_items: List[_WorkItem],
            *,
            archivo_by_id: Dict[int, Archivo],
            prestador_imed: str,
            estado_render_by_work: Dict[int, Dict[str, Literal["V", "A", "R"]]],
            resumen: ProcesarResumen,
    ) -> List[_UploadResult]:

        results: List[_UploadResult] = []

        def job(w: _WorkItem) -> _UploadResult:
            archivo = archivo_by_id.get(w.archivo_id)

            base_name = self._base_from_tif_path(w.it.full_path)

            if archivo:
                yyyy, mm = self._year_month_from_basename_or_fallback(
                    base_name, archivo, w.it.full_path
                )
            else:
                ts = datetime.fromtimestamp(os.path.getmtime(w.it.full_path))
                yyyy = f"{ts.year:04d}"
                mm = f"{ts.month:02d}"

            front_key, back_key = self._build_s3_keys(
                prestador_imed=prestador_imed,
                yyyy=yyyy,
                mm=mm,
                base_name=base_name,
            )

            estado = estado_render_by_work.get(w.archivo_id, {})

            # 🔥 render
            files = self._tif.render_bytes(
                tiff_path=w.it.full_path,
                scan=w.scan,
                pages=None,
                estado_por_codebar=estado,
            )

            fb = files.get("front_bytes")
            bb = files.get("back_bytes")

            # 🔥 upload inmediato
            if fb:
                self._storage.put_jpg(front_key, fb)
            if bb:
                self._storage.put_jpg(back_key, bb)

            return _UploadResult(
                work=w,
                front_key=front_key if fb else None,
                back_key=back_key if bb else None,
            )

        # 🔥 Un solo executor para render+upload
        with ThreadPoolExecutor(max_workers=self._upload_workers) as ex:
            futs = [ex.submit(job, w) for w in work_items]

            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as e:
                    resumen.errores.append(f"render/upload error: {e}")

        return results

    @staticmethod
    def _archivo_ya_asociado(s: Session, recepcion_id: int, archivo_id: int) -> bool:
        rid = (
            s.execute(
                select(Recetas.receta_id)
                .join(Asociacion, Asociacion.receta_id == Recetas.receta_id)
                .where(
                    Recetas.recepcion_id == int(recepcion_id),
                    Asociacion.archivo_id == int(archivo_id),
                    Asociacion.vigente.is_(True),
                )
                .limit(1)
            )
            .scalar_one_or_none()
        )
        return rid is not None

    @staticmethod
    def _is_valesalud(obra_social_nombre: str | None) -> bool:
        return "valesalud" in (obra_social_nombre or "").strip().lower()

    # -------------------------
    # MAIN (por tandas)
    # -------------------------
    def procesar(
        self,
        s: Session,
        recepcion_id: int,
        usuario_id: int,
        items: List[ProcesarItemIn],
    ) -> ProcesarResumen:

        total = ProcesarResumen()
        med_cache: Dict[str, Optional[MedicamentoDTO]] = {}
        seen_recetas: Set[str] = set()
        seen_refs: Set[str] = set()

        revision_counter = 1

        # 0) recepcion + prestador.imed
        rec: Recepcion | None = (
            s.execute(select(Recepcion).where(Recepcion.recepcion_id == recepcion_id)).scalar_one_or_none()
        )
        if not rec:
            raise RuntimeError(f"No existe la recepción {recepcion_id}")

        pr_row = (
            s.execute(select(Prestador).where(Prestador.prestador_id == rec.prestador_id)).scalar_one_or_none()
        )
        if not pr_row:
            raise RuntimeError("No existe el Prestador asociado a la recepción.")

        prestador_imed = (getattr(pr_row, "imed", "") or "").strip()
        if not prestador_imed:
            raise RuntimeError("Prestador.imed está vacío; no se puede armar key S3.")

        fecha_presentacion = rec.fecha_presentacion
        if isinstance(fecha_presentacion, datetime):
            fecha_presentacion_dt = fecha_presentacion
        else:
            fecha_presentacion_dt = datetime.fromisoformat(str(fecha_presentacion))
        os_row = s.execute(
            select(ObraSocial.nombre, ObraSocial.dias_vencimiento)
            .where(ObraSocial.obra_social_id == rec.obra_social_id)
        ).first()
        os_nombre = (os_row[0] if os_row else None)
        dias_vencimiento_raw = (os_row[1] if os_row else None)
        dias_vencimiento = int(dias_vencimiento_raw) if dias_vencimiento_raw is not None else None
        only_ref_match = self._is_valesalud(os_nombre)
        MOTIVO_DEBITO_RECETA_VENCIDA_ID = 11

        # 1) Idempotencia (se mantiene)
        items_filtrados: List[ProcesarItemIn] = []
        for it in items:
            base_name = self._base_from_tif_path(it.full_path)
            if base_name and self._exists_processed_base_in_recepcion(s, recepcion_id, base_name):
                total.ya_asociado += 1
                continue
            items_filtrados.append(it)

        if not items_filtrados:
            return total

        # 2) Procesar por tandas
        for chunk in _chunks(items_filtrados, self._chunk_size):

            resumen = ProcesarResumen()

            # 2.1) scan paralelo (solo ScanOut)
            scanned = self._parallel_scan(chunk, resumen)
            if not scanned:
                total.merge(resumen)
                continue

            # 2.2) juntar refs y match masivo (DB)
            all_refs: List[str] = []
            for x in scanned:
                all_refs.extend(x.scan.headers or [])
            match = self._match_all_refs(
                s,
                recepcion_id,
                all_refs,
                only_referencia=only_ref_match,
            )

            # 2.3) elegir work (archivo_id por tiff)
            work: List[_WorkItem] = []
            archivo_ids: List[int] = []
            revision_items: List[_ScannedItem] = []

            for x in scanned:
                refs = [self._norm_str(r) for r in (x.scan.headers or []) if self._norm_str(r)]

                if not refs:
                    resumen.sin_match += 1
                    revision_items.append(x)
                    continue

                if any(ref in match.duplicated_refs for ref in refs):
                    resumen.duplicados += 1
                    continue

                archivo: Optional[Archivo] = None
                for ref in refs:
                    a = match.ref_to_archivo.get(ref)
                    if a is not None:
                        archivo = a
                        break

                if archivo is None:
                    resumen.sin_match += 1
                    revision_items.append(x)
                    continue

                if self._archivo_ya_asociado(s, recepcion_id, archivo.archivo_id):
                    revision_items.append(x)
                    continue

                nro_rec = self._norm_str(getattr(archivo, "nro_receta", None))
                nro_ref = self._norm_str(getattr(archivo, "nro_referencia", None))

                # 🔥 duplicado en esta corrida
                if only_ref_match:
                    if nro_ref and nro_ref in seen_refs:
                        revision_items.append(x)
                        continue
                else:
                    if (nro_rec and nro_rec in seen_recetas) or (nro_ref and nro_ref in seen_refs):
                        revision_items.append(x)
                        continue

                # marcar como vistos
                if not only_ref_match and nro_rec:
                    seen_recetas.add(nro_rec)

                if nro_ref:
                    seen_refs.add(nro_ref)

                work.append(_WorkItem(it=x.it, scan=x.scan, archivo_id=int(archivo.archivo_id)))
                archivo_ids.append(int(archivo.archivo_id))

            if not work and not revision_items:
                total.merge(resumen)
                continue

            # 2.4) bulk load Archivos + Detalles
            archivos = s.execute(select(Archivo).where(Archivo.archivo_id.in_(archivo_ids))).scalars().all()
            archivo_by_id: Dict[int, Archivo] = {a.archivo_id: a for a in archivos}

            detalles = s.execute(select(ArchivoDetalle).where(ArchivoDetalle.archivo_id.in_(archivo_ids))).scalars().all()
            detalles_by_archivo: Dict[int, List[ArchivoDetalle]] = {}
            for d in detalles:
                detalles_by_archivo.setdefault(d.archivo_id, []).append(d)

            # 2.6) precomputar estados + troqueles + vencido (SIN render ni S3 todavía)
            estado_render_by_archivo_id: Dict[int, Dict[str, Literal["V","A","R"]]] = {}
            dto_cache_local = med_cache  # mismo cache por corrida

            all_codebars: set[str] = set()

            for w in work:
                for cb in (w.scan.troqueles or []):
                    cb = self._norm_str(cb)
                    if cb:
                        all_codebars.add(cb)

            missing_codebars = [
                cb for cb in all_codebars
                if cb not in med_cache
            ]

            if missing_codebars:
                batch_result = self._client.get_many_by_codebars(missing_codebars)
                for cb, dto in batch_result.items():
                    med_cache[cb] = dto

            # además juntamos data para persistencia después del upload
            recetas_to_add: List[Recetas] = []
            asoc_to_add: List[Asociacion] = []
            troqueles_to_add: List[Troqueles] = []

            # OJO: acá todavía no creamos recetas; primero subimos S3.
            # Pero para render necesitamos el estado_render_por_codebar, lo armamos por archivo_id.
            for w in work:
                archivo = archivo_by_id.get(w.archivo_id)
                if not archivo:
                    resumen.errores.append(f"{w.it.file_name}: archivo_id {w.archivo_id} no existe en DB")
                    continue

                archivo_ts = self._archivo_ts(archivo)
                esta_vencido = self._esta_vencido(archivo_ts, fecha_presentacion_dt, dias_vencimiento)
                if getattr(archivo, "vencido", False) != esta_vencido:
                    archivo.vencido = esta_vencido

                dets = detalles_by_archivo.get(w.archivo_id, [])
                importe_por_cod: Dict[str, float] = {}
                cods_detalle: Set[str] = set()
                cant_por_cod: Dict[str, int] = {}

                for d in dets:
                    ca = self._norm_str(getattr(d, "cod_medic", None))
                    if not ca:
                        continue
                    cods_detalle.add(ca)
                    importe_por_cod[ca] = importe_por_cod.get(ca, 0.0) + float(getattr(d, "importe_obs", 0) or 0)
                    cant_por_cod[ca] = cant_por_cod.get(ca, 0) + int(getattr(d, "cantidad", 0) or 0)

                counts: Dict[str, int] = dict(Counter(self._norm_str(c) for c in (w.scan.troqueles or []) if self._norm_str(c)))

                estado_render_por_codebar: Dict[str, Literal["V","A","R"]] = {}
                # los estados DB / dto / monto los vamos a recalcular al persistir (cuando ya tengamos receta_id).
                # pero DTO lo cacheamos acá, así no hacemos HTTP 2 veces.
                if counts:
                    for codebar, qty_scan in counts.items():
                        dto = med_cache.get(codebar)

                        if dto is None:
                            estado_render_por_codebar[codebar] = "A"
                            continue

                        ca = str(dto.code_alfabeta or "").strip()
                        match_detalle = bool(ca) and (ca in cods_detalle)
                        if not match_detalle:
                            estado_render_por_codebar[codebar] = "R"
                            continue

                        # render siempre V si está en detalle (tu regla)
                        estado_render_por_codebar[codebar] = "V"

                estado_render_by_archivo_id[w.archivo_id] = estado_render_por_codebar

            revision_work: List[_WorkItem] = []
            for x in revision_items:
                revision_work.append(
                    _WorkItem(
                        it=x.it,
                        scan=x.scan,
                        archivo_id=0,
                    )
                )

            # 2.7) render+upload en paralelo (usa scan + estado_render)
            uploaded = self._parallel_render_upload(
                work_items=work + revision_work,
                archivo_by_id=archivo_by_id,
                prestador_imed=prestador_imed,
                estado_render_by_work=estado_render_by_archivo_id,
                resumen=resumen,
            )

            # 2.8) persistencia DB (bulk, 1 flush)
            # armamos recetas SOLO para los que realmente subieron algo
            valid_uploaded: List[_UploadResult] = []
            for u in uploaded:
                if not u.front_key and not u.back_key:
                    resumen.errores.append(f"{u.work.it.file_name}: no se subió frente ni dorso")
                    continue
                valid_uploaded.append(u)

            if not valid_uploaded:
                total.merge(resumen)
                continue

            # crear recetas en memoria
            receta_by_archivo_id: Dict[int, Recetas] = {}
            for u in valid_uploaded:

                if u.work.archivo_id == 0:
                    nro_receta = "-"

                    receta = Recetas(
                        recepcion_id=int(recepcion_id),
                        nro_receta=nro_receta,
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
                    continue

                archivo = archivo_by_id[u.work.archivo_id]
                nro_receta = self._norm_str(getattr(archivo, "nro_receta", None)) or f"REV-{revision_counter}"

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

            s.add_all(recetas_to_add)
            s.flush()  # 1 flush por tanda

            # asociaciones + troqueles + debitos vencido
            recetas_vencidas_ids: List[int] = []

            for u in valid_uploaded:
                w = u.work

                if w.archivo_id == 0:
                    continue

                archivo = archivo_by_id[w.archivo_id]
                receta = receta_by_archivo_id[w.archivo_id]

                # asociacion
                asoc_to_add.append(Asociacion(receta_id=receta.receta_id, archivo_id=w.archivo_id, vigente=True))

                # vencido
                esta_vencido = bool(getattr(archivo, "vencido", False))
                if esta_vencido:
                    recetas_vencidas_ids.append(int(receta.receta_id))

                # troqueles (recalcular estado DB + monto con detalle)
                dets = detalles_by_archivo.get(w.archivo_id, [])
                importe_por_cod: Dict[str, float] = {}
                cods_detalle: Set[str] = set()
                cant_por_cod: Dict[str, int] = {}

                for d in dets:
                    ca = self._norm_str(getattr(d, "cod_medic", None))
                    if not ca:
                        continue
                    cods_detalle.add(ca)
                    importe_por_cod[ca] = importe_por_cod.get(ca, 0.0) + float(getattr(d, "importe_obs", 0) or 0)
                    cant_por_cod[ca] = cant_por_cod.get(ca, 0) + int(getattr(d, "cantidad", 0) or 0)

                counts: Dict[str, int] = dict(Counter(self._norm_str(c) for c in (w.scan.troqueles or []) if self._norm_str(c)))

                if counts:
                    for codebar, qty_scan in counts.items():
                        dto = med_cache.get(codebar)

                        if dto is None:
                            estado_db = EstadoTroquelEnum.A
                            code_alfabeta = 0
                            droga_concat = None
                            presentacion = None
                        else:
                            code_alfabeta = int(dto.code_alfabeta or 0)
                            droga_concat = dto.drogas_concat
                            presentacion = dto.presentacion

                            ca = str(dto.code_alfabeta or "").strip()
                            match_detalle = bool(ca) and (ca in cods_detalle)

                            if not match_detalle:
                                estado_db = EstadoTroquelEnum.R
                            else:
                                qty_det = int(cant_por_cod.get(ca, 0))
                                estado_db = EstadoTroquelEnum.V if qty_det == int(qty_scan) else EstadoTroquelEnum.R

                        monto = 0.0
                        if code_alfabeta and str(code_alfabeta) in cods_detalle:
                            monto = float(importe_por_cod.get(str(code_alfabeta), 0.0))

                        troqueles_to_add.append(
                            Troqueles(
                                receta_id=receta.receta_id,
                                codigo_barra=codebar,
                                droga=droga_concat,
                                presentacion=presentacion,
                                code_alfabeta=code_alfabeta,
                                monto=Decimal(monto),
                                cantidad=int(qty_scan),
                                estado=estado_db,
                            )
                        )

            if asoc_to_add:
                s.add_all(asoc_to_add)
            if troqueles_to_add:
                s.add_all(troqueles_to_add)


            # Debitos vencido bulk
            if recetas_vencidas_ids:
                ya_tienen = set(
                    s.execute(
                        select(Debitos.receta_id).where(
                            Debitos.motivo_debito_id == MOTIVO_DEBITO_RECETA_VENCIDA_ID,
                            Debitos.receta_id.in_(recetas_vencidas_ids),
                        )
                    ).scalars().all()
                )
                for rid in recetas_vencidas_ids:
                    if rid in ya_tienen:
                        continue
                    s.add(
                        Debitos(
                            receta_id=rid,
                            motivo_debito_id=MOTIVO_DEBITO_RECETA_VENCIDA_ID,
                            detalle=(
                                f"Vencido por {dias_vencimiento} dias (auto)"
                                if dias_vencimiento is not None
                                else "Vencido (auto)"
                            ),
                        )
                    )

            resumen.ok += len(valid_uploaded)

            total.merge(resumen)

        return total

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.recepcion_repository import RecepcionRepository
from app.db.models import Recepcion


@dataclass(frozen=True)
class RecepcionListItem:
    recepcion_id: int
    numero: int
    obra_social: str
    periodo: str
    prestador: str
    estado: str
    fecha_presentacion: object
    creado_en: Optional[object]
    imed: str
    validador: str
    dias_vencimiento: int | None
    codigo_financiador: int | None

@dataclass(frozen=True)
class PrestadorConRecepcionesItem:
    prestador_id: int
    nombre: str
    codigo: str
    imed: str
    cantidad_recepciones: int


@dataclass(frozen=True)
class RecepcionRowItem:
    recepcion_id: int
    numero: int
    obra_social: str
    fecha_presentacion: Optional[date]

class RecepcionService:
    @staticmethod
    def list_prestadores_con_recepcion(s: Session, *, periodo_id: int) -> list[PrestadorConRecepcionesItem]:
        rows = RecepcionRepository.list_prestadores_con_recepcion(
            s,
            periodo_id=int(periodo_id),
        )

        out: list[PrestadorConRecepcionesItem] = []
        for pid, nom, cod, imed, cant in rows:
            out.append(
                PrestadorConRecepcionesItem(
                    prestador_id=pid,
                    nombre=nom or "(sin nombre)",
                    codigo=cod or "",
                    imed=imed or "",
                    cantidad_recepciones=int(cant or 0),
                )
            )
        return out

    @staticmethod
    def list_recepciones(s: Session, *, periodo_id: int, prestador_id: int) -> list[RecepcionRowItem]:
        rows = RecepcionRepository.list_recepciones_por_periodo_prestador(
            s,
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
        )

        return [
            RecepcionRowItem(
                recepcion_id=r[0],
                numero=r[1],
                obra_social=r[2] or "",
                fecha_presentacion=r[3],
            )
            for r in rows
        ]

    @staticmethod
    def list(s: Session, *, all: bool = True) -> list[RecepcionListItem]:
        rows = RecepcionRepository.list_with_details(s, include_closed=all)
        out: list[RecepcionListItem] = []
        for r in rows:
            (rid, numero, os_nombre, anio, mes, quin, pres_cod, pres_nom,
             estado, fecha_rec, creado_en, imed, validador, dias_vencimiento, codigo_financiador) = r
            periodo_txt = f"{anio}-{mes:02d} Q{quin}"
            prestador_txt = f"{pres_nom or ''}"
            out.append(
                RecepcionListItem(
                    recepcion_id=rid,
                    numero=numero,
                    obra_social=os_nombre or "",
                    periodo=periodo_txt,
                    prestador=prestador_txt,
                    estado=estado or "",
                    fecha_presentacion=fecha_rec,
                    creado_en=creado_en,
                    imed=imed or "",
                    validador=(validador or "imed"),
                    dias_vencimiento=(int(dias_vencimiento) if dias_vencimiento is not None else None),
                    codigo_financiador=(int(codigo_financiador) if codigo_financiador is not None else None),
                )
            )
        return out

    @staticmethod
    def create(
            s: Session,
            obra_social_id: int,
            periodo_id: int,
            prestador_id: int,
            estado_recepcion_id: int,
            fecha_presentacion,
            observaciones: str | None = None,
            creado_por_usuario_id: int | None = None,
    ) -> Recepcion:

        if not estado_recepcion_id:
            raise ValueError("estado_recepcion es obligatorio.")

        if RecepcionRepository.exists_open_by_obra_prestador(
            s,
            obra_social_id=int(obra_social_id),
            prestador_id=int(prestador_id),
        ):
            raise RuntimeError(
                "Tiene un período anterior sin cerrar."
            )

        if RecepcionRepository.exists_same_scope(
            s,
            obra_social_id=int(obra_social_id),
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
        ):
            raise RuntimeError(
                "Ya existe una recepción para esta obra social, período y prestador."
            )

        return RecepcionRepository.create(
            s,
            obra_social_id=int(obra_social_id),
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
            estado_recepcion_id=int(estado_recepcion_id),
            fecha_presentacion=fecha_presentacion,
            observaciones=observaciones,
            creado_por_usuario_id=creado_por_usuario_id,
        )

    @staticmethod
    def delete(s: Session, recepcion_id: int) -> None:
        rec = RecepcionRepository.get(s, recepcion_id=int(recepcion_id))
        if not rec:
            raise ValueError("La recepción no existe.")
        s.delete(rec)


    @staticmethod
    def cerrar_recepcion(s: Session, recepcion_id: int) -> None:
        row = RecepcionRepository.get_cierre_context(s, recepcion_id=int(recepcion_id))
        if not row:
            raise RuntimeError(f"No existe la recepción {recepcion_id}")

        rec, dias_vencimiento = row
        dias_venc = int(dias_vencimiento) if dias_vencimiento is not None else None
        fecha_presentacion = rec.fecha_presentacion
        cutoff = None
        if dias_venc is not None and isinstance(fecha_presentacion, datetime):
            cutoff = fecha_presentacion - timedelta(days=dias_venc)

        archivos_sin_asoc = RecepcionRepository.list_archivos_sin_asociacion(
            s,
            recepcion_id=int(recepcion_id),
        )

        for a in archivos_sin_asoc:
            archivo_fecha = a.fecha
            archivo_hora = a.hora
            if archivo_fecha is None or archivo_hora is None:
                continue

            if isinstance(archivo_fecha, datetime):
                archivo_fecha = archivo_fecha.date()
            if isinstance(archivo_hora, datetime):
                archivo_hora = archivo_hora.time()

            archivo_ts = datetime.fromisoformat(f"{archivo_fecha} {archivo_hora}")
            if cutoff is not None and archivo_ts < cutoff:
                a.vencido = True

        rec.estado_recepcion_id = 2
        s.flush()

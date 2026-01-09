from __future__ import annotations

from decimal import Decimal
from datetime import date as dt_date, time as dt_time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Archivo, ArchivoDetalle


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    s = str(v).strip()
    if not s:
        return Decimal("0")
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")


def _parse_date(v: Any) -> dt_date | None:
    if not v:
        return None
    s = str(v).strip()
    if s.isdigit() and len(s) == 8:
        yyyy = int(s[0:4]); mm = int(s[4:6]); dd = int(s[6:8])
        return dt_date(yyyy, mm, dd)
    if "/" in s:
        dd, mm, yyyy = s.split("/")
        return dt_date(int(yyyy), int(mm), int(dd))
    return None


def _parse_time(v: Any) -> dt_time | None:
    if not v:
        return None
    s = str(v).strip()
    parts = s.split(":")
    if len(parts) == 2:
        hh, mm = map(int, parts)
        return dt_time(hh, mm, 0)
    if len(parts) == 3:
        hh, mm, ss = map(int, parts)
        return dt_time(hh, mm, ss)
    return None


class ArchivoService:
    @staticmethod
    def exists_by_ref(session: Session, *, nro_referencia: str) -> bool:
        stmt = select(Archivo.archivo_id).where(Archivo.nro_referencia == nro_referencia)
        return session.execute(stmt).first() is not None

    @staticmethod
    def exists_by_recepcion_and_ref(session: Session, *, recepcion_id: int, nro_referencia: str) -> bool:
        stmt = select(Archivo.archivo_id).where(
            Archivo.recepcion_id == recepcion_id,
            Archivo.nro_referencia == nro_referencia,
        )
        return session.execute(stmt).first() is not None

    @staticmethod
    def create_from_imed(
        session: Session,
        *,
        receta: dict,
        detalles: list[dict],
        recepcion_id: int | None = None,          # ✅ ahora opcional
        nro_referencia: str | None = None,        # ✅ ahora opcional
        skip_if_exists: bool = True,
        check_scope: str = "ref",                 # "ref" o "recepcion+ref"
    ) -> int:
        """
        Inserta:
        - Archivo (cabecera)
        - ArchivoDetalle (items)
        Devuelve archivo_id.

        recepcion_id puede ser NULL (lo cargás después).
        """

        # --- nro referencia: de param o desde receta ---
        if not nro_referencia:
            nro_referencia = (
                receta.get("Nro_Referencia")
                or receta.get("Nro Referencia")
                or receta.get("nro_referencia")
            )
        nro_referencia = str(nro_referencia).strip() if nro_referencia else ""

        if not nro_referencia:
            raise ValueError("La receta no trae Nro Referencia (no se puede insertar).")

        # --- control de duplicados ---
        if skip_if_exists:
            if check_scope == "recepcion+ref":
                if recepcion_id is None:
                    raise ValueError("check_scope='recepcion+ref' requiere recepcion_id.")
                if ArchivoService.exists_by_recepcion_and_ref(session, recepcion_id=recepcion_id, nro_referencia=nro_referencia):
                    raise ValueError(f"Ya existe un Archivo para ref {nro_referencia} en la recepción {recepcion_id}")
            else:
                # default: por ref global (aunque recepcion_id sea NULL)
                if ArchivoService.exists_by_ref(session, nro_referencia=nro_referencia):
                    raise ValueError(f"Ya existe un Archivo para ref {nro_referencia}")

        # --- mapeo “receta IMED” ---
        beneficiario = receta.get("Beneficiario") or receta.get("beneficiario")
        fecha_raw = receta.get("Fecha") or receta.get("fecha")
        hora_raw = receta.get("Hora") or receta.get("hora")

        nro_receta = receta.get("Nro_Receta") or receta.get("Nro Receta") or receta.get("nro_receta")
        orden_lote = receta.get("Orden_Del_Lote") or receta.get("Orden Del Lote") or receta.get("orden_lote")

        importe_gral_raw = receta.get("Importe_Gral") or receta.get("Importe Gral") or receta.get("importe_gral")
        importe_obs_raw = receta.get("Importe_Pami") or receta.get("Importe Pami") or receta.get("Importe_Obs") or receta.get("importe_obs")
        cargo_raw = receta.get("A_Cargo_Entidad") or receta.get("A Cargo Entidad") or receta.get("a_cargo_entidad")

        archivo = Archivo(
            recepcion_id=recepcion_id,  # ✅ puede ser None
            beneficiario=str(beneficiario) if beneficiario else None,
            fecha=_parse_date(fecha_raw),
            hora=_parse_time(hora_raw),
            nro_referencia=nro_referencia,
            nro_receta=str(nro_receta) if nro_receta else None,
            orden_lote=str(orden_lote) if orden_lote else None,
            importe_neto=_dec(importe_gral_raw),   # Importe Gral
            importe_obs=_dec(importe_obs_raw),     # Importe Pami -> importe_obs
            a_cargo_entidad=_dec(cargo_raw),
        )
        session.add(archivo)
        session.flush()

        # --- detalles ---
        rows: list[ArchivoDetalle] = []
        for d in detalles:
            # tu detalle viene en crudo (code/name/description/estatus/number_aut/quantity/amount_general/amount_obs/discount)

            # ejemplo: "54640 - DESLORAMAR ..." -> cod y resto
            print(d)
            cod_medic = d.get("cod_medic")

            nombre = (d.get("nombre") or "").strip() or None
            present = (d.get("presentacion") or "").strip() or None

            estado = (d.get("estado") or "").strip() or None
            nro_aut = (d.get("nro_aut") or "").strip() or None
            cant_raw = d.get("cantidad")

            imp_gral_raw = d.get("importe_gral")
            imp_obs_raw = d.get("importe_pami")  # o si tu csv trae % ahí, ajustamos abajo
            desc = (d.get("desc") or "").strip() or None

            # si amount_obs viene tipo "40%" (como tu ejemplo), guardalo como descuento si no tenés campo numérico
            if isinstance(imp_obs_raw, str) and "%" in imp_obs_raw and not desc:
                desc = imp_obs_raw.strip()
                imp_obs_raw = "0"

            rows.append(
                ArchivoDetalle(
                    archivo_id=int(archivo.archivo_id),
                    cod_medic=cod_medic,
                    nombre=nombre,
                    presentacion=present,
                    estado=estado,
                    nro_autorizacion=nro_aut,
                    cantidad=int(cant_raw) if str(cant_raw).strip().isdigit() else 0,
                    importe_neto=_dec(imp_gral_raw),
                    importe_obs=_dec(imp_obs_raw),
                    descuento=desc,
                )
            )

        if rows:
            session.add_all(rows)

        return int(archivo.archivo_id)


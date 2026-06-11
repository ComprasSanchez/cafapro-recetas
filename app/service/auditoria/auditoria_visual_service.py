from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class AsociacionData:
    asociacion_id: int
    receta_id: int
    archivo_id: int
    vigente: bool


@dataclass(frozen=True)
class RecetaData:
    receta_id: int
    nro_receta: str
    ubicacion_frente: Optional[str]
    ubicacion_dorso: Optional[str]
    fecha_prescripcion: object
    fecha_emision: object
    fecha_venta: object
    estado_receta_id: Optional[int]
    estado_seguimiento_id: Optional[int]
    vendedor_id: Optional[int]
    usuario_id: Optional[int]


@dataclass(frozen=True)
class ArchivoData:
    archivo_id: int
    nro_referencia: str
    nro_receta: str
    orden_lote: Optional[int]
    fecha: object
    hora: object
    importe_bruto: object
    importe_cobertura: object
    importe_afiliado: object


@dataclass(frozen=True)
class ArchivoDetalleData:
    archivo_detalle_id: int
    cod_medic: Optional[str]
    codigo_barra: Optional[str]
    nombre: Optional[str]
    presentacion: Optional[str]
    estado: Optional[str]
    cantidad: int
    importe_bruto: object
    importe_cobertura: object


@dataclass(frozen=True)
class TroquelData:
    troquel_id: int
    codigo_barra: str
    droga: Optional[str]
    presentacion: Optional[str]
    code_alfabeta: int
    monto: object
    cantidad: int
    estado: str


@dataclass(frozen=True)
class DebitoRow:
    debito_id: int
    motivo_debito_id: int
    motivo_codigo: str
    motivo_descripcion: str
    lado: str
    excluyente: str
    detalle: Optional[str]


@dataclass(frozen=True)
class MotivoData:
    motivo_debito_id: int
    codigo: str
    descripcion: str
    excluyente: str
    activo: bool


@dataclass(frozen=True)
class VendedorData:
    vendedor_id: int
    codigo: str
    descripcion: Optional[str]


@dataclass(frozen=True)
class AuditoriaVisualData:
    asociacion: AsociacionData
    receta: RecetaData
    archivo: ArchivoData
    troqueles: List[TroquelData]
    archivo_detalles: List[ArchivoDetalleData]
    debitos: List[DebitoRow]
    motivos_frente: List[MotivoData]
    motivos_dorso: List[MotivoData]
    has_historial_debitada: bool
    vendedor: Optional[VendedorData]


def _url(asociacion_id: int) -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/asociaciones/{asociacion_id}/auditoria-visual"


def _to_motivo(m: dict) -> MotivoData:
    return MotivoData(
        motivo_debito_id=m["motivoDebitoId"],
        codigo=m.get("codigo") or "",
        descripcion=m.get("descripcion") or "",
        excluyente=m.get("excluyente") or "N",
        activo=bool(m.get("activo", True)),
    )


class AuditoriaVisualService:
    @staticmethod
    def load_by_asociacion_id(asociacion_id: int) -> AuditoriaVisualData:
        resp = get_client().get(_url(int(asociacion_id)))
        if resp.status_code == 404:
            raise ValueError("No existe asociación")
        resp.raise_for_status()
        d = resp.json()

        a = d["asociacion"]
        r = d["receta"]
        ar = d["archivo"]

        return AuditoriaVisualData(
            asociacion=AsociacionData(
                asociacion_id=a["asociacionId"],
                receta_id=a["recetaId"],
                archivo_id=a["archivoId"],
                vigente=a["vigente"],
            ),
            receta=RecetaData(
                receta_id=r["recetaId"],
                nro_receta=r.get("nroReceta") or "",
                ubicacion_frente=r.get("ubicacionFrente"),
                ubicacion_dorso=r.get("ubicacionDorso"),
                fecha_prescripcion=r.get("fechaPrescripcion"),
                fecha_emision=r.get("fechaEmision"),
                fecha_venta=r.get("fechaVenta"),
                estado_receta_id=r.get("estadoRecetaId"),
                estado_seguimiento_id=r.get("estadoSeguimientoId"),
                vendedor_id=r.get("vendedorId"),
                usuario_id=r.get("usuarioId"),
            ),
            archivo=ArchivoData(
                archivo_id=ar["archivoId"],
                nro_referencia=ar.get("nroReferencia") or "",
                nro_receta=ar.get("nroReceta") or "",
                orden_lote=ar.get("ordenLote"),
                fecha=ar.get("fecha"),
                hora=ar.get("hora"),
                importe_bruto=ar.get("importeBruto") or 0,
                importe_cobertura=ar.get("importeCobertura") or 0,
                importe_afiliado=ar.get("importeAfiliado") or 0,
            ),
            archivo_detalles=[
                ArchivoDetalleData(
                    archivo_detalle_id=det["archivoDetalleId"],
                    cod_medic=det.get("codMedic"),
                    codigo_barra=det.get("codigoBarra"),
                    nombre=det.get("nombre"),
                    presentacion=det.get("presentacion"),
                    estado=det.get("estado"),
                    cantidad=int(det.get("cantidad") or 0),
                    importe_bruto=det.get("importeBruto") or 0,
                    importe_cobertura=det.get("importeCobertura") or 0,
                )
                for det in d.get("archivoDetalles", [])
            ],
            troqueles=[
                TroquelData(
                    troquel_id=t["troquelId"],
                    codigo_barra=t.get("codigoBarra") or "",
                    droga=t.get("droga"),
                    presentacion=t.get("presentacion"),
                    code_alfabeta=int(t.get("codeAlfabeta") or 0),
                    monto=t.get("monto") or 0,
                    cantidad=int(t.get("cantidad") or 0),
                    estado=t.get("estado") or "",
                )
                for t in d.get("troqueles", [])
            ],
            debitos=[
                DebitoRow(
                    debito_id=deb["debitoId"],
                    motivo_debito_id=deb["motivoDebitoId"],
                    motivo_codigo=deb.get("motCodigo") or "",
                    motivo_descripcion=deb.get("motDescripcion") or "",
                    lado=deb.get("lado") or "",
                    excluyente=deb.get("excluyente") or "N",
                    detalle=deb.get("detalle"),
                )
                for deb in d.get("debitos", [])
            ],
            motivos_frente=[_to_motivo(m) for m in d.get("motivosFrente", [])],
            motivos_dorso=[_to_motivo(m) for m in d.get("motivosDorso", [])],
            has_historial_debitada=bool(d.get("hasHistorialDebitada", False)),
            vendedor=(
                VendedorData(
                    vendedor_id=d["vendedor"]["vendedorId"],
                    codigo=d["vendedor"].get("codigo") or "",
                    descripcion=d["vendedor"].get("descripcion"),
                )
                if d.get("vendedor")
                else None
            ),
        )

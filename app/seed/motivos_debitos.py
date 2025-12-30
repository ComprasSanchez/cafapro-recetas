from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MotivoDebito  # ajustá el import/nombre del modelo

MOTIVOS_DEBITO = [
    {"codigo": "FIRMA_TERCERO_DIFIERE", "descripcion": "No coinciden firmas del tercero", "lado": "F", "excluyente": "S"},
    {"codigo": "SIN_SALVAR_MEDICO", "descripcion": "Sin salvar por el mèdico", "lado": "D", "excluyente": "N"},
    {"codigo": "FECHA_AUTORIZACION_2_DIAS", "descripcion": "Fecha Imed + 2 dias", "lado": "F", "excluyente": "S"},
    {"codigo": "ENMIENDA_SIN_SALVAR_MEDICO", "descripcion": "Enmienda sin salvar por el medico", "lado": "D", "excluyente": "S"},
    {"codigo": "ENMIENDA_SIN_SALVAR_FARMACIA", "descripcion": "Enmienda sin salvar por la farmacia", "lado": "D", "excluyente": "S"},
    {"codigo": "RECETA_MAL_ESTADO", "descripcion": "Receta en mal estado", "lado": "F", "excluyente": "N"},
    {"codigo": "FALTA_DIFIERE_DISPENSA", "descripcion": "Falta o difiere fecha de dispensa", "lado": "F", "excluyente": "N"},
    {"codigo": "DIFIERE_FECHA_PRESCRIPCION_AUTORIZACION", "descripcion": "Difiere fecha de Prescripción/Autorización", "lado": "F", "excluyente": "S"},
    {"codigo": "MAL_ENTREGADO", "descripcion": "Mal entregado mg/ monodroga/ form. Farmacéutica", "lado": "F", "excluyente": "S"},
    {"codigo": "FALTA_DIAGNOSTICO", "descripcion": "Falta diagnostico", "lado": "F", "excluyente": "N"},
    {"codigo": "RECETA_VENCIDA_60_DIAS", "descripcion": "Receta vencida +60 dias", "lado": "F", "excluyente": "S"},
    {"codigo": "EMISION_MAYOR_VENTA", "descripcion": "Fecha de emisión mayor a fecha de venta", "lado": "F", "excluyente": "S"},
    {"codigo": "VENTA_30_DOAS", "descripcion": "Fecha de venta +30 dias", "lado": "F", "excluyente": "S"},
    {"codigo": "FALTA_FIRMA_SELLO_MEDICO", "descripcion": "Falta firma y/o sello del médico", "lado": "F", "excluyente": "S"},
    {"codigo": "FALTA_MATRICULA_MEDIO", "descripcion": "Falta matricula del médico", "lado": "F", "excluyente": "S"},
    {"codigo": "FALTA_FIRMA_SELLO_FARMACIA", "descripcion": "Falta firma y/o sello de la farmacia", "lado": "D", "excluyente": "N"},
    {"codigo": "FALTA_TROQUEL_RP", "descripcion": "Falta troquel en RP 1/2", "lado": "F", "excluyente": "N"},
    {"codigo": "OPF_ILEGIBLE", "descripcion": "OPF ilegible", "lado": "F", "excluyente": "S"},
    {"codigo": "FALTA_OPF", "descripcion": "Falta OPF", "lado": "F", "excluyente": "S"},
    {"codigo": "RECETA_MAL_ACONDICIONADA", "descripcion": "Mal acondicionamiento de receta", "lado": "F", "excluyente": "S"},
    {"codigo": "FALTA_DATOS_RECETAS", "descripcion": "Faltan datos de la receta", "lado": "F", "excluyente": "N"},
    {"codigo": "NO_CORRESPONDE_TROQUEL_RP", "descripcion": "No corresponde troquel en RP 1/2", "lado": "F", "excluyente": "N"},
    {"codigo": "MAL_AUTORIZADO_RP", "descripcion": "Mal autorizado RP 1/2", "lado": "D", "excluyente": "S"},
    {"codigo": "RECETA_ANULADA", "descripcion": "Receta Anulada", "lado": "F", "excluyente": "S"},
    {"codigo": "MAL_FACTURADO_RP", "descripcion": "Mal facturado RP 1/2", "lado": "D", "excluyente": "S"},
    {"codigo": "FALTA_MALCONFECCIONADO_TICKET", "descripcion": "Falta ticket / confecciona mal el ticket", "lado": "D", "excluyente": "S"},
    {"codigo": "ENMIENDA_MAL_SALVADA_MEDICO", "descripcion": "Enmienda mal salvada por el médico", "lado": "D", "excluyente": "S"},
    {"codigo": "ENMIENDA_MAL_SALVADA_FARMACIA", "descripcion": "Enmienda mal salvada por la farmacia", "lado": "D", "excluyente": "N"},
    {"codigo": "FALTA_FIRMA_TERCERO_TICKET", "descripcion": "Falta firma del tercero en ticket", "lado": "D", "excluyente": "N"},
    {"codigo": "FALTA_DATOS_TERCERO", "descripcion": "Faltan datos del tercero", "lado": "D", "excluyente": "N"},
    {"codigo": "SIN_SALVAR_FARMACIA", "descripcion": "Sin salvar por la farmacia", "lado": "D", "excluyente": "N"},
]

def run(session: Session) -> None:
    for m in MOTIVOS_DEBITO:
        codigo = m["codigo"].strip()

        existente = session.execute(
            select(MotivoDebito).where(MotivoDebito.codigo == codigo)
        ).scalar_one_or_none()

        if existente:
            existente.descripcion = m["descripcion"].strip()
            existente.lado = m["lado"].strip()
            existente.excluyente = m["excluyente"]
        else:
            session.add(MotivoDebito(
                codigo=codigo,
                descripcion=m["descripcion"].strip(),
                lado=m["lado"].strip(),
                excluyente=m["excluyente"],
            ))

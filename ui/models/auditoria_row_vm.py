from dataclasses import dataclass


@dataclass
class AuditoriaRowVM:

    receta_id: int | None
    asociacion_id: int | None

    numero_receta: str
    numero_referencia: str
    nro_lote: str

    existe_receta: bool
    existe_archivo: bool

    importe_reconocido: float
    importe_oficial: float

    estado_receta_id: int
    estado_receta: str

    flag_debitos: bool

    frente_jpg: str

    @property
    def es_revision(self):
        return (not self.existe_archivo) and self.existe_receta

    @property
    def auditada(self):
        return self.estado_receta_id == 1 or self.es_revision

    @property
    def diferencia_montos(self):
        return abs(self.importe_reconocido - self.importe_oficial) > 0.009
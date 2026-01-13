import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models import Base  # tu DeclarativeBase

class VwArchivoResumenAuditoria(Base):
    __tablename__ = "vw_archivo_resumen_auditoria"
    __table_args__ = {"info": {"is_view": True}}

    archivo_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    recepcion_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    numero_receta: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    numero_referencia: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    nro_lote: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    existe_archivo: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    existe_receta: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

    importe_reconocido: Mapped[float] = mapped_column(sa.Numeric(12, 2), nullable=False)
    importe_oficial: Mapped[float] = mapped_column(sa.Numeric(12, 2), nullable=False)

    estado_receta_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

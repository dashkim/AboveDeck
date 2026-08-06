from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Peak(Base):
    __tablename__ = "peaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    elevation_m: Mapped[int | None] = mapped_column(Integer)
    prominence_m: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    feature_class: Mapped[str] = mapped_column(Text, nullable=False, server_default="Summit")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    peak_id: Mapped[int] = mapped_column(Integer, ForeignKey("peaks.id", ondelete="CASCADE"), nullable=False)
    valid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lead_hours: Mapped[float | None] = mapped_column(Float)
    above_cloud_prob: Mapped[float] = mapped_column(Float, nullable=False)
    inversion_strength: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_cloud_base_m: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False, server_default="rules-v0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

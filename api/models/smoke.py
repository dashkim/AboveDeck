from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class SmokePhrase(Base):
    __tablename__ = "smoke_phrases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    phrase: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

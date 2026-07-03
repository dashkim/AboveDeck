from datetime import date

from pydantic import BaseModel, Field


class GridCell(BaseModel):
    lat: float
    lon: float
    above_cloud_prob: float = Field(ge=0.0, le=1.0)


class GridResponse(BaseModel):
    cells: list[GridCell]
    date: date
    bbox: tuple[float, float, float, float]

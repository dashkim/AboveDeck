from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


Confidence = Literal["low", "medium", "high"]
InversionStrength = Literal["none", "possible", "strong", "excellent"]


class HourlyPrediction(BaseModel):
    valid_at: datetime
    above_cloud_prob: float = Field(ge=0.0, le=1.0)
    inversion_strength: InversionStrength
    estimated_cloud_base_m: float | None = None
    confidence: Confidence


class PeakSummary(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    elevation_m: int
    prominence_m: int | None = None
    state: str
    above_cloud_prob: float = Field(ge=0.0, le=1.0)
    inversion_strength: InversionStrength
    confidence: Confidence
    best_window_start: datetime | None = None
    best_window_end: datetime | None = None


class PeakListResponse(BaseModel):
    peaks: list[PeakSummary]
    date: date
    bbox: tuple[float, float, float, float]


class PeakDetail(PeakSummary):
    hourly: list[HourlyPrediction]


class PeakSearchResult(BaseModel):
    id: int
    name: str
    state: str
    elevation_m: int


class PeakSearchResponse(BaseModel):
    results: list[PeakSearchResult]
    query: str

from datetime import date

from fastapi import APIRouter, Depends, Query

from config import Settings
from dependencies import require_db
from schemas.peaks import PeakDetail, PeakListResponse, PeakSearchResponse

router = APIRouter(prefix="/peaks", tags=["peaks"])


@router.get("", response_model=PeakListResponse)
def list_peaks(
    bbox: str = Query(..., description="west,south,east,north"),
    date: date = Query(..., description="ISO date for predictions"),
    hour: int | None = Query(None, ge=0, le=23, description="Optional hour (0-23)"),
    _settings: Settings = Depends(require_db),
) -> PeakListResponse:
    raise NotImplementedError("Peaks query not implemented yet.")


@router.get("/search", response_model=PeakSearchResponse)
def search_peaks(
    q: str = Query(..., min_length=1, description="Peak name search query"),
    _settings: Settings = Depends(require_db),
) -> PeakSearchResponse:
    raise NotImplementedError("Peak search not implemented yet.")


@router.get("/{peak_id}", response_model=PeakDetail)
def get_peak(
    peak_id: int,
    date: date = Query(..., description="ISO date for predictions"),
    _settings: Settings = Depends(require_db),
) -> PeakDetail:
    raise NotImplementedError("Peak detail not implemented yet.")

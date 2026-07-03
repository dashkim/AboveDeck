from datetime import date

from fastapi import APIRouter, Depends, Query

from config import Settings
from dependencies import require_db
from schemas.predictions import GridResponse

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/grid", response_model=GridResponse)
def get_prediction_grid(
    bbox: str = Query(..., description="west,south,east,north"),
    date: date = Query(..., description="ISO date for predictions"),
    _settings: Settings = Depends(require_db),
) -> GridResponse:
    raise NotImplementedError("Prediction grid not implemented yet.")

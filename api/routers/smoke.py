from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from dependencies import require_db
from models.smoke import SmokePhrase

router = APIRouter(prefix="/smoke", tags=["smoke"])


class PhraseCreate(BaseModel):
    phrase: str = Field(..., min_length=1, max_length=500)


class PhraseResponse(BaseModel):
    id: int
    phrase: str
    created_at: datetime


@router.post("/phrase", response_model=PhraseResponse)
async def create_phrase(
    body: PhraseCreate,
    _settings=Depends(require_db),
    session: AsyncSession = Depends(get_session),
) -> SmokePhrase:
    row = SmokePhrase(phrase=body.phrase)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.get("/phrase/latest", response_model=PhraseResponse)
async def latest_phrase(
    _settings=Depends(require_db),
    session: AsyncSession = Depends(get_session),
) -> SmokePhrase:
    result = await session.execute(
        select(SmokePhrase).order_by(SmokePhrase.created_at.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No smoke phrases stored yet")
    return row

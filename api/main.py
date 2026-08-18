from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import health, peaks, predictions, smoke

app = FastAPI(title="AboveDeck API")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(peaks.router)
app.include_router(predictions.router)
app.include_router(smoke.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "AboveDeck API",
        "health": "/health",
        "smoke_latest": "/smoke/phrase/latest",
        "docs": "/docs",
    }

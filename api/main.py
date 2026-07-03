from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import health, peaks, predictions

app = FastAPI(title="AboveDeck API")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(peaks.router)
app.include_router(predictions.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "AboveDeck API",
        "health": "/health",
        "docs": "/docs",
    }

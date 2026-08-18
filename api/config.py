from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = ",".join(
    [
        "https://dashkim.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
)

# Live Server, Cursor preview, GitHub Pages project sites.
CORS_ORIGIN_REGEX = (
    r"https://([\w-]+\.)?github\.io"
    r"|http://localhost:\d+"
    r"|http://127\.0\.0\.1:\d+"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    cors_origins: str = DEFAULT_CORS_ORIGINS
    cors_origin_regex: str = CORS_ORIGIN_REGEX

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

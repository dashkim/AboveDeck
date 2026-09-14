"""Unit tests for async database URL normalization."""

from db import _async_database_url


def test_strips_sslmode_and_enables_ssl():
    url, args = _async_database_url(
        "postgresql://user:pass@host/db?sslmode=require&application_name=abovedeck"
    )
    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    assert "application_name=abovedeck" in url
    assert args == {"ssl": True}


def test_strips_ssl_require():
    url, args = _async_database_url("postgres://user:pass@host/db?ssl=require")
    assert url.startswith("postgresql+asyncpg://")
    assert "ssl=" not in url.split("?", 1)[-1] if "?" in url else True
    assert "sslmode" not in url
    assert args == {"ssl": True}


def test_ssl_disable_leaves_no_ssl_arg():
    url, args = _async_database_url("postgresql://user:pass@host/db?sslmode=disable")
    assert "sslmode" not in url
    assert args == {}


def test_already_asyncpg_without_ssl():
    url, args = _async_database_url("postgresql+asyncpg://user:pass@host/db")
    assert url == "postgresql+asyncpg://user:pass@host/db"
    assert args == {}

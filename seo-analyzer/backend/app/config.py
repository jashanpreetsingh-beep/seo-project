"""
Application configuration loaded from environment variables.
"""
from __future__ import annotations


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings - loaded from .env file or environment variables."""

    # App
    APP_NAME: str = "SEO Analyzer"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./seo_analyzer.db"

    # Google PageSpeed Insights API (free, 25k requests/day)
    PAGESPEED_API_KEY: str = ""

    # Anthropic Claude API (for LLM-powered analysis & recommendations)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_BASE_URL: str = ""  # Custom proxy URL (leave empty for default Anthropic API)

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Timeouts
    FETCH_TIMEOUT: int = 30  # seconds
    AUDIT_TIMEOUT: int = 120  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

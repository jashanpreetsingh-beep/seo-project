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

    # ─── LLM Provider Toggle ─────────────────────────────────────────────────
    # Set to "groq" or "anthropic" to switch providers
    LLM_PROVIDER: str = "groq"

    # Anthropic Claude API
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_BASE_URL: str = ""  # Custom proxy URL (leave empty for default Anthropic API)

    # Groq API (free tier available — fast inference on open-source models)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Groq API (alternative LLM provider)
    LLM_PROVIDER: str = "anthropic"  # "anthropic" or "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Vector Store (ChromaDB)
    CHROMA_PERSIST_DIR: str = "./chroma_db"  # Directory to persist ChromaDB data

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Timeouts
    FETCH_TIMEOUT: int = 30  # seconds
    AUDIT_TIMEOUT: int = 120  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

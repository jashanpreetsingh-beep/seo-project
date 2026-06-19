"""
FastAPI Application Entry Point.

This is where the server starts. It:
1. Creates the FastAPI app
2. Configures CORS (so React frontend can call the API)
3. Registers API routes
4. Initializes the database on startup
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes import audit_router, history_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup and shutdown."""
    # Startup: create database tables
    await init_db()
    print(f"✓ Database initialized")
    print(f"✓ SEO Analyzer API ready at http://localhost:8000")
    yield
    # Shutdown: cleanup if needed
    print("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Comprehensive SEO analysis API powered by LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React frontend to call our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(audit_router)
app.include_router(history_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "pagespeed_api": bool(settings.PAGESPEED_API_KEY),
        "anthropic_api": bool(settings.ANTHROPIC_API_KEY),
    }

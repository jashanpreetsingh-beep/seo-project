"""API Routes."""

from app.routes.audit import router as audit_router
from app.routes.history import router as history_router
from app.routes.visibility import router as visibility_router

__all__ = ["audit_router", "history_router", "visibility_router"]

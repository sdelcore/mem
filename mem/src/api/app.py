"""FastAPI application for Mem API backend."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api import routes  # noqa: E402
from src.api.exceptions import (
    DatabaseError,
    MemException,
    ResourceNotFoundError,
    ValidationError,
)
from src.config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.logging.level), format=config.logging.format
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mem API",
    description="API for video capture and data retrieval",
    version="1.0.0",
)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware (allow all origins for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(routes.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Mem API is running", "version": "1.0.0"}


# Custom exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle validation errors with 400 status code."""
    return JSONResponse(
        status_code=400, content={"error": exc.message, "code": exc.error_code}
    )


@app.exception_handler(ResourceNotFoundError)
async def not_found_exception_handler(request, exc: ResourceNotFoundError):
    """Handle resource not found errors with 404 status code."""
    return JSONResponse(
        status_code=404, content={"error": exc.message, "code": exc.error_code}
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request, exc: DatabaseError):
    """Handle database errors with 500 status code."""
    return JSONResponse(
        status_code=500, content={"error": exc.message, "code": exc.error_code}
    )


@app.exception_handler(MemException)
async def mem_exception_handler(request, exc: MemException):
    """Handle generic Mem exceptions with 500 status code."""
    return JSONResponse(
        status_code=500, content={"error": exc.message, "code": exc.error_code}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Mem API starting up...")
    # Database initialization could go here if needed


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Mem API shutting down...")

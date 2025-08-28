"""FastAPI application for Mem API backend."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import routes  # noqa: E402
from src.config import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.logging.level), format=config.logging.format)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mem API",
    description="API for video capture and data retrieval",
    version="1.0.0",
)

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

"""FastAPI application for government project (simplified)."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.core.config import settings
from src.core.database import init_db
from src.api.router import api_router
from src.middleware.error_handler import add_error_handlers
from src.middleware.rate_limiting import add_rate_limiting
from src.utils.logging import setup_logging

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting Government Auth API...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Log configuration
    logger.info(f"📊 Configuration loaded:")
    logger.info(f"   - Environment: {'Development' if settings.DEBUG else 'Production'}")
    logger.info(f"   - Database: PostgreSQL")
    logger.info(f"   - Rate Limiting: {settings.RATE_LIMIT_CALLS} calls/{settings.RATE_LIMIT_PERIOD}s")
    logger.info(f"   - Auth Rate Limiting: {settings.AUTH_RATE_LIMIT_CALLS} calls/{settings.AUTH_RATE_LIMIT_PERIOD}s")
    
    logger.info("🎯 Government Auth API started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Government Auth API...")
    logger.info("✅ Shutdown completed")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="""
        **Government Authentication API**
        
        A secure authentication system for government applications with:
        
        * **JWT-based authentication** with refresh tokens
        * **Role-based access control (RBAC)** for different government units
        * **User management** with government-specific fields (NIP, unit kerja, jabatan)
        * **Password reset** functionality
        * **Rate limiting** for security
        * **Comprehensive validation** and error handling
        
        ## Default Roles
        
        * `admin` - System Administrator
        * `inspektorat_1` to `inspektorat_4` - Inspektorat regional offices
        * `perwadag` - Perdagangan department
        * `bappeda` - Regional Planning Agency
        * `dinas_kesehatan` - Health Department
        * `dinas_pendidikan` - Education Department
        * `dinas_sosial` - Social Affairs Department
        
        ## Authentication
        
        1. **Login**: POST `/api/v1/auth/login` with email/username and password
        2. **Use Bearer token**: Include `Authorization: Bearer <token>` in headers
        3. **Refresh token**: POST `/api/v1/auth/refresh` when token expires
        
        ## Access Levels
        
        * **Public**: Login, password reset
        * **Authenticated**: View own profile, change password
        * **Admin**: Full user and role management
        * **Inspektorat**: View users and some management functions
        """,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    # CORS middleware (configure appropriately for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS_LIST,
        allow_credentials=True,
        allow_methods=settings.CORS_METHODS_LIST,
        allow_headers=settings.CORS_HEADERS_LIST,
        expose_headers=["*"],
    )

    # # Add rate limiting middleware
    # add_rate_limiting(app)

    # Di dalam create_application()
    uploads_path = Path(settings.UPLOADS_PATH)  # "static/uploads"
    uploads_path.mkdir(parents=True, exist_ok=True)  # Create if not exists

    app.mount("/static/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

    @app.middleware("http")
    async def add_cors_headers_for_static(request, call_next):
        response = await call_next(request)
        
        # Add CORS headers hanya untuk static files
        if request.url.path.startswith("/static/"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
            
        
        return response

    # Add error handlers
    add_error_handlers(app)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Root endpoint
    @app.get("/", tags=["System"])
    async def root():
        """Root endpoint with API information."""
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.VERSION,
            "status": "operational",
            "documentation": "/docs" if settings.DEBUG else "Documentation disabled in production",
            "environment": "development" if settings.DEBUG else "production"
        }

    # Health check endpoint
    @app.get("/health", tags=["System"])
    async def health_check():
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": "development" if settings.DEBUG else "production"
        }

    # API info endpoint
    @app.get("/api/v1/info", tags=["System"])
    async def api_info():
        """API information and available endpoints."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "description": "Government Authentication API",
            "features": [
                "JWT Authentication",
                "Role-based Access Control",
                "User Management",
                "Password Reset",
                "Rate Limiting",
                "Government-specific Fields"
            ],
            "endpoints": {
                "authentication": "/api/v1/auth/",
                "user_management": "/api/v1/users/",
                "role_management": "/api/v1/roles/"
            },
            "documentation": "/docs" if settings.DEBUG else None
        }

    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True
    )
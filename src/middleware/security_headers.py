"""Security headers middleware for enhanced protection."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Skip CSP for docs endpoints to avoid blocking Swagger UI
        skip_csp_paths = ["/docs", "/redoc", "/openapi.json"]
        is_docs_path = any(request.url.path.startswith(path) for path in skip_csp_paths)
        
        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Force HTTPS in production
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Referrer policy for privacy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (replace Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), accelerometer=(), "
            "gyroscope=(), speaker=(), vibrate=(), fullscreen=(self)"
        )
        
        # Skip CSP for docs to allow Swagger UI to work
        if not is_docs_path:
            # Content Security Policy - restrictive but functional
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.google.com https://www.gstatic.com",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: https: blob:",
                "connect-src 'self' https://www.google.com",
                "frame-src 'self' https://www.google.com",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'"
            ]
            
            # More restrictive CSP for production
            if not settings.DEBUG:
                csp_directives = [
                    "default-src 'self'",
                    "script-src 'self' https://www.google.com https://www.gstatic.com",
                    "style-src 'self' https://fonts.googleapis.com",
                    "font-src 'self' https://fonts.gstatic.com", 
                    "img-src 'self' data: https:",
                    "connect-src 'self' https://www.google.com",
                    "frame-src 'self' https://www.google.com",
                    "object-src 'none'",
                    "base-uri 'self'",
                    "form-action 'self'",
                    "frame-ancestors 'none'",
                    "upgrade-insecure-requests"
                ]
            
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Prevent information disclosure
        response.headers["Server"] = "Secure-Server"
        
        # Remove potentially revealing headers
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        
        return response


def add_security_headers(app):
    """Add security headers middleware to the application."""
    app.add_middleware(SecurityHeadersMiddleware)
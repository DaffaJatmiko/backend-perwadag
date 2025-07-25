# ===== src/middleware/activity_logger.py =====
"""Middleware untuk log semua activity secara otomatis."""

import time
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.database import async_session
from src.repositories.log_activity import LogActivityRepository
from src.repositories.user import UserRepository
from src.schemas.log_activity import LogActivityCreate
from src.auth.jwt import verify_token

logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware untuk log semua activity secara otomatis."""
    
    # Skip logging untuk endpoints ini
    SKIP_PATHS = {
        "/health", "/docs", "/redoc", "/openapi.json", 
        "/static", "/metrics", "/api/v1/log-activity",
        "/favicon.ico"
    }
    
    # Template untuk generate activity description - SESUAI DENGAN SEMUA ENDPOINT YANG ADA
    ACTIVITY_TEMPLATES = {
        # ===== AUTHENTICATION =====
        "POST /api/v1/auth/login": "User login",
        "POST /api/v1/auth/logout": "User logout",
        "POST /api/v1/auth/refresh": "Token refresh",
        "POST /api/v1/auth/request-password-reset": "Requested password reset",
        "POST /api/v1/auth/confirm-password-reset": "Confirmed password reset",
        "POST /api/v1/auth/change-password": "Changed password",
        
        # ===== USER MANAGEMENT =====
        "POST /api/v1/users": "Created user account",
        "PUT /api/v1/users/.*": "Updated user profile",
        "DELETE /api/v1/users/.*": "Deleted user account",
        "POST /api/v1/users/.*/activate": "Activated user account",
        "POST /api/v1/users/.*/deactivate": "Deactivated user account",
        "POST /api/v1/users/.*/reset-password": "Reset user password",
        
        # ===== SURAT TUGAS =====
        "POST /api/v1/evaluasi/surat-tugas": "Created surat tugas with auto-generation",
        "PUT /api/v1/evaluasi/surat-tugas/.*": "Updated surat tugas",
        "DELETE /api/v1/evaluasi/surat-tugas/.*": "Deleted surat tugas with cascade",
        "POST /api/v1/evaluasi/surat-tugas/.*/upload-file": "Uploaded surat tugas file",
        
        # ===== MEETINGS =====
        "PUT /api/v1/evaluasi/meeting/.*": "Updated meeting information",
        "POST /api/v1/evaluasi/meeting/.*/upload-files": "Uploaded meeting files",
        "DELETE /api/v1/evaluasi/meeting/.*/files/.*": "Deleted meeting file",
        
        # ===== SURAT PEMBERITAHUAN =====
        "PUT /api/v1/evaluasi/surat-pemberitahuan/.*": "Updated surat pemberitahuan",
        "POST /api/v1/evaluasi/surat-pemberitahuan/.*/upload-file": "Uploaded surat pemberitahuan file",
        
        # ===== MATRIKS =====
        "PUT /api/v1/evaluasi/matriks/.*": "Updated matriks with temuan-rekomendasi",
        "POST /api/v1/evaluasi/matriks/.*/upload-file": "Uploaded matriks file",
        
        # ===== LAPORAN HASIL =====
        "PUT /api/v1/evaluasi/laporan-hasil/.*": "Updated laporan hasil",
        "POST /api/v1/evaluasi/laporan-hasil/.*/upload-file": "Uploaded laporan hasil file",
        
        # ===== KUISIONER =====
        "PUT /api/v1/evaluasi/kuisioner/.*": "Updated kuisioner information",
        "POST /api/v1/evaluasi/kuisioner/.*/upload-file": "Uploaded kuisioner file",
        
        # ===== FORMAT KUISIONER (ADMIN ONLY) =====
        "POST /api/v1/evaluasi/format-kuisioner": "Created format kuisioner template",
        "PUT /api/v1/evaluasi/format-kuisioner/.*": "Updated format kuisioner template",
        "DELETE /api/v1/evaluasi/format-kuisioner/.*": "Deleted format kuisioner template",
        "POST /api/v1/evaluasi/format-kuisioner/.*/upload-file": "Uploaded format kuisioner template file",
        
        # ===== PERIODE EVALUASI =====
        "POST /api/v1/periode-evaluasi": "Created periode evaluasi with bulk penilaian generation",
        "PUT /api/v1/periode-evaluasi/.*": "Updated periode evaluasi",
        "DELETE /api/v1/periode-evaluasi/.*": "Deleted periode evaluasi with cascade",
        
        # ===== PENILAIAN RISIKO =====
        "PUT /api/v1/penilaian-risiko/.*": "Updated penilaian risiko with auto-calculation",
        "POST /api/v1/penilaian-risiko/.*/calculate": "Calculated penilaian risiko scores",
        
        # ===== EMAIL TEMPLATES =====
        "POST /api/v1/email-templates": "Created email template",
        "PUT /api/v1/email-templates/.*": "Updated email template",
        "DELETE /api/v1/email-templates/.*": "Deleted email template",
        "POST /api/v1/email-templates/.*/activate": "Activated email template",
        
        # ===== BULK OPERATIONS =====
        "POST /api/v1/penilaian-risiko/bulk/calculate": "Bulk calculated penilaian risiko",
        "POST /api/v1/evaluasi/surat-tugas/bulk/progress-check": "Bulk checked progress status",
    }
    
    # Fallback templates berdasarkan method dan module
    FALLBACK_TEMPLATES = {
        ("POST", "users"): "Created user data",
        ("PUT", "users"): "Updated user data",
        ("DELETE", "users"): "Deleted user data",
        ("POST", "evaluasi"): "Created evaluation data",
        ("PUT", "evaluasi"): "Updated evaluation data",
        ("DELETE", "evaluasi"): "Deleted evaluation data",
        ("POST", "periode-evaluasi"): "Created periode evaluation data",
        ("PUT", "periode-evaluasi"): "Updated periode evaluation data",
        ("DELETE", "periode-evaluasi"): "Deleted periode evaluation data",
        ("POST", "penilaian-risiko"): "Created penilaian risiko data",
        ("PUT", "penilaian-risiko"): "Updated penilaian risiko data",
        ("DELETE", "penilaian-risiko"): "Deleted penilaian risiko data",
    }
    
    async def dispatch(self, request: Request, call_next):
        # Filter: Only log specific methods
        if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return await call_next(request)
        
        # Filter: Skip system endpoints
        if self._should_skip_logging(request.url.path):
            return await call_next(request)
        
        # Get current user dari JWT token
        current_user = await self._get_current_user(request)
        if not current_user:
            # Skip logging jika user tidak authenticated
            return await call_next(request)
        
        # Capture request metadata
        start_time = time.time()
        ip_address = self._get_client_ip(request)
        
        # Execute actual endpoint
        response = await call_next(request)
        
        # Log activity asynchronously (non-blocking)
        if 200 <= response.status_code < 500:  # Success + client errors
            asyncio.create_task(
                self._log_activity_async(
                    request, response, current_user, 
                    ip_address, start_time
                )
            )
        
        return response
    
    def _should_skip_logging(self, path: str) -> bool:
        """Check apakah path harus di-skip dari logging."""
        return any(skip_path in path for skip_path in self.SKIP_PATHS)
    
    async def _get_current_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract current user dari JWT token."""
        try:
            # Extract Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # Extract & verify token
            token = auth_header.replace("Bearer ", "")
            payload = verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                return None
            
            # Get user from database
            async with async_session() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_by_id(user_id)
                
                if not user or not user.is_active:
                    return None
                
                return {
                    "id": user.id,
                    "nama": user.nama,
                    "role": user.role.value,
                }
                
        except Exception as e:
            logger.debug(f"Failed to get user from token: {str(e)}")
            return None
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get real client IP address."""
        # Priority order untuk reverse proxy scenarios
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        if request.client and request.client.host:
            return request.client.host
        
        return None
    
    def _generate_activity_description(self, method: str, path: str) -> str:
        """Generate activity description menggunakan templates."""
        
        # Normalize path pattern untuk matching
        normalized_path = self._normalize_path_for_matching(path)
        template_key = f"{method} {normalized_path}"
        
        # Try exact match dengan normalized path
        for pattern, description in self.ACTIVITY_TEMPLATES.items():
            if self._match_path_pattern(template_key, pattern):
                return description
        
        # Fallback ke generic description berdasarkan module
        module = self._extract_module_from_path(path)
        fallback_key = (method, module)
        
        if fallback_key in self.FALLBACK_TEMPLATES:
            return self.FALLBACK_TEMPLATES[fallback_key]
        
        # Ultimate fallback
        action_map = {
            "POST": "Created",
            "PUT": "Updated", 
            "PATCH": "Updated",
            "DELETE": "Deleted"
        }
        
        action = action_map.get(method, "Modified")
        return f"{action} {module} data"
    
    def _normalize_path_for_matching(self, path: str) -> str:
        """Normalize path untuk pattern matching."""
        # Replace UUIDs dengan placeholder
        path = re.sub(r'/[a-f0-9-]{36}', '/.*', path)
        # Replace numeric IDs dengan placeholder  
        path = re.sub(r'/\d+', '/.*', path)
        # Replace filenames dalam path
        path = re.sub(r'/files/[^/]+$', '/files/.*', path)
        return path
    
    def _match_path_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern dengan regex."""
        # Convert pattern ke regex yang proper
        regex_pattern = pattern.replace(".*", "[^/]+")
        regex_pattern = f"^{regex_pattern}$"
        
        try:
            return re.match(regex_pattern, path) is not None
        except re.error:
            return False
    
    def _extract_module_from_path(self, path: str) -> str:
        """Extract module name dari path."""
        if "/auth/" in path:
            return "authentication"
        elif "/users" in path:
            return "users"
        elif "/surat-tugas" in path:
            return "surat tugas"
        elif "/meeting" in path:
            return "meetings"
        elif "/surat-pemberitahuan" in path:
            return "surat pemberitahuan"
        elif "/matriks" in path:
            return "matriks"
        elif "/laporan-hasil" in path:
            return "laporan hasil"
        elif "/kuisioner" in path:
            return "kuisioner"
        elif "/format-kuisioner" in path:
            return "format kuisioner"
        elif "/periode-evaluasi" in path:
            return "periode evaluasi"
        elif "/penilaian-risiko" in path:
            return "penilaian risiko"
        elif "/email-templates" in path:
            return "email templates"
        elif "/evaluasi" in path:
            return "evaluation"
        else:
            return "system"
    
    async def _log_activity_async(
        self, request, response, current_user, ip_address, start_time
    ):
        """Save log activity ke database secara async."""
        try:
            # Generate activity description
            activity = self._generate_activity_description(
                request.method, 
                str(request.url.path)
            )
            
            # Create log data
            log_data = LogActivityCreate(
                user_id=current_user["id"],
                method=request.method,
                url=str(request.url.path),
                activity=activity,
                date=datetime.utcnow(),
                user_name=current_user["nama"],
                ip_address=ip_address,
                response_status=response.status_code
            )
            
            # Save to database
            async with async_session() as session:
                log_repo = LogActivityRepository(session)
                await log_repo.create(log_data)
                await session.commit()
                
        except Exception as e:
            # NEVER break aplikasi karena logging error
            logger.error(f"Failed to log activity: {str(e)}")
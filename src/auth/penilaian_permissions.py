# ===== src/auth/penilaian_permissions.py =====
"""Permission decorators khusus untuk sistem penilaian risiko."""

from typing import Dict
from fastapi import Depends, HTTPException, status

from src.auth.permissions import get_current_active_user


def require_penilaian_read_access():
    """
    Dependency untuk read access ke data penilaian risiko.
    
    Access rules:
    - Admin: Lihat semua data
    - Inspektorat: Lihat data di wilayah kerjanya
    """
    async def _check_penilaian_read_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin and Inspektorat can access penilaian risiko data."
        )
    
    return _check_penilaian_read_access


def require_penilaian_write_access():
    """
    Dependency untuk write access ke data penilaian risiko.
    
    Access rules:
    - Admin: Full CRUD semua data
    - Inspektorat: Edit data di wilayah kerjanya
    """
    async def _check_penilaian_write_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin and Inspektorat can edit penilaian risiko data."
        )
    
    return _check_penilaian_write_access


def require_periode_management_access():
    """
    Dependency untuk manage periode evaluasi.
    
    Access rules:
    - Admin: Full CRUD periode
    """
    async def _check_periode_management_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role == "ADMIN":
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin can manage periode evaluasi."
        )
    
    return _check_periode_management_access


def get_penilaian_filter_scope(current_user: Dict) -> Dict[str, any]:
    """
    Get filter scope untuk query berdasarkan role user.
    
    Returns dict yang bisa digunakan di service layer untuk filtering.
    """
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    
    if user_role == "ADMIN":
        return {
            "scope": "all",
            "user_role": user_role,
            "user_inspektorat": None,
            "user_id": None
        }
    elif user_role == "INSPEKTORAT":
        return {
            "scope": "inspektorat",
            "user_role": user_role,
            "user_inspektorat": current_user.get("inspektorat"),
            "user_id": user_id
        }
    else:
        return {"scope": "none"}


def validate_penilaian_access(
    current_user: Dict, 
    target_penilaian_data: Dict,
    action: str = "read"
) -> bool:
    """
    Validate apakah user berhak melakukan action tertentu pada penilaian data.
    
    Args:
        current_user: Current user dari JWT
        target_penilaian_data: Data penilaian yang ingin diakses (harus punya inspektorat)
        action: Jenis action (read, write)
    
    Returns:
        True jika access allowed, False jika tidak
    """
    user_role = current_user.get("role")
    user_inspektorat = current_user.get("inspektorat")
    target_inspektorat = target_penilaian_data.get("inspektorat")
    
    if user_role == "ADMIN":
        return True
    elif user_role == "INSPEKTORAT":
        # Inspektorat hanya bisa akses data di wilayah kerjanya
        return user_inspektorat == target_inspektorat
    
    return False
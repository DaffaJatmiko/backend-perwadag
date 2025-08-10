"""Permission decorators khusus untuk sistem evaluasi."""

from typing import Dict
from fastapi import Depends, HTTPException, status

from src.auth.permissions import get_current_active_user


def require_evaluasi_read_access():
    """
    Dependency untuk read access ke data evaluasi.
    
    Access rules:
    - Admin: Lihat semua data
    - Inspektorat: Lihat data di wilayah kerjanya
    - Perwadag: Lihat data milik sendiri saja
    """
    async def _check_evaluasi_read_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        # Semua role yang authenticated boleh read (dengan filtering di service layer)
        if user_role in ["ADMIN", "INSPEKTORAT", "PERWADAG", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Invalid role for evaluasi access."
        )
    
    return _check_evaluasi_read_access


def require_evaluasi_write_access():
    """
    Dependency untuk write access ke data evaluasi.
    
    Access rules:
    - Admin: Full CRUD semua data
    - Inspektorat: CRUD surat_tugas + Edit auto-generated tables
    - Perwadag: NO write access (kecuali khusus kuisioner & laporan_hasil)
    """
    async def _check_evaluasi_write_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin and Inspektorat can write evaluasi data."
        )
    
    return _check_evaluasi_write_access


def require_surat_tugas_create_access():
    """
    Dependency untuk create surat_tugas.
    
    Access rules:
    - Admin: Can create
    - Inspektorat: Can create  
    - Perwadag: NO create access
    """
    async def _check_surat_tugas_create_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin and Inspektorat can create surat tugas."
        )
    
    return _check_surat_tugas_create_access


def require_surat_tugas_delete_access():
    """
    Dependency untuk delete surat_tugas (dengan cascade).
    
    Access rules:
    - Admin: Can delete
    - Inspektorat: Can delete
    - Perwadag: NO delete access
    """
    async def _check_surat_tugas_delete_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin and Inspektorat can delete surat tugas."
        )
    
    return _check_surat_tugas_delete_access


def require_kuisioner_upload_access():
    """
    Dependency untuk upload kuisioner.
    
    Access rules:
    - Admin: Can upload
    - Inspektorat: Can upload
    - Perwadag: Can upload (milik sendiri only)
    """
    async def _check_kuisioner_upload_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT", "PERWADAG", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Invalid role for kuisioner upload."
        )
    
    return _check_kuisioner_upload_access


def require_laporan_edit_access():
    """
    Dependency untuk edit laporan_hasil.
    
    Access rules:
    - Admin: Full edit access
    - Inspektorat: Full edit access
    - Perwadag: Full edit access (milik sendiri only)
    """
    async def _check_laporan_edit_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT", "PERWADAG", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Invalid role for laporan edit."
        )
    
    return _check_laporan_edit_access


def require_format_kuisioner_access():
    """
    Dependency untuk manage format kuisioner (master templates).
    
    Access rules:
    - Admin: Full CRUD access
    - Inspektorat: NO access
    - Perwadag: NO access
    """
    async def _check_format_kuisioner_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role == "ADMIN":
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin can manage format kuisioner templates."
        )
    
    return _check_format_kuisioner_access


def require_auto_generated_edit_access():
    """
    Dependency untuk edit auto-generated tables (NOT delete).
    
    Access rules:
    - Admin: Can edit
    - Inspektorat: Can edit
    - Perwadag: NO edit access (kecuali kuisioner & laporan_hasil)
    """
    async def _check_auto_generated_edit_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admin and Inspektorat can edit auto-generated evaluasi data."
        )
    
    return _check_auto_generated_edit_access


def require_statistics_access():
    """
    Dependency untuk akses statistik evaluasi.
    
    Access rules:
    - Admin: Full statistics
    - Inspektorat: Statistics untuk wilayah kerja
    - Perwadag: Statistics milik sendiri only
    """
    async def _check_statistics_access(
        current_user: Dict = Depends(get_current_active_user)
    ) -> Dict:
        user_role = current_user.get("role")
        
        if user_role in ["ADMIN", "INSPEKTORAT", "PERWADAG", "PIMPINAN"]:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Invalid role for statistics access."
        )
    
    return _check_statistics_access


# ===== UTILITY FUNCTIONS =====

def check_evaluasi_ownership(current_user: Dict, target_user_perwadag_id: str) -> bool:
    """
    Check apakah user berhak akses ke evaluasi tertentu.
    
    Rules:
    - Admin: Access semua
    - Pimpinan: Access semua di wilayah kerjanya  # TAMBAH INI
    - Inspektorat: Access hanya yang dia assigned  # UBAH INI
    - Perwadag: Access milik sendiri only
    """
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    
    if user_role == "ADMIN":
        return True
    elif user_role == "PIMPINAN":  # TAMBAH KONDISI INI
        # Pimpinan bisa akses semua perwadag di wilayah kerjanya
        return True  # Validasi di service layer berdasarkan inspektorat
    elif user_role == "INSPEKTORAT":
        # PERLU ASSIGNMENT CHECK - akan divalidasi di service layer
        return True  # Basic check, detailed check di service
    elif user_role == "PERWADAG":
        # Perwadag hanya bisa akses milik sendiri
        return user_id == target_user_perwadag_id
    
    return False


def get_evaluasi_filter_scope(current_user: Dict) -> Dict[str, any]:
    """Get filter scope untuk query berdasarkan role user."""
    user_role = current_user.get("role")
    user_id = current_user.get("id")
    
    if user_role == "ADMIN":
        return {
            "scope": "all",
            "user_role": user_role
        }
    elif user_role == "PIMPINAN":  # TAMBAH KONDISI INI
        return {
            "scope": "inspektorat",
            "user_role": user_role,
            "user_inspektorat": current_user.get("inspektorat"),
        }
    elif user_role == "INSPEKTORAT":
        return {
            "scope": "assigned_only",  # UBAH DARI "inspektorat" KE "assigned_only"
            "user_role": user_role,
            "user_id": user_id
        }
    elif user_role == "PERWADAG":
        return {
            "scope": "own",
            "user_role": user_role,
            "user_id": user_id
        }
    
    return {"scope": "none"}


def validate_evaluasi_access(
    current_user: Dict, 
    target_evaluasi_data: Dict,
    action: str = "read"
) -> bool:
    """Validate apakah user berhak melakukan action tertentu pada evaluasi data."""
    user_role = current_user.get("role")
    target_perwadag_id = target_evaluasi_data.get("user_perwadag_id")
    
    # Basic ownership check
    if not check_evaluasi_ownership(current_user, target_perwadag_id):
        return False
    
    # Action-specific checks
    if action == "read":
        return True
    elif action == "write":
        # TAMBAH PIMPINAN
        return user_role in ["ADMIN", "INSPEKTORAT", "PIMPINAN"]
    elif action == "delete":
        # TAMBAH PIMPINAN
        return user_role in ["ADMIN", "INSPEKTORAT", "PIMPINAN"]
    elif action == "kuisioner_upload":
        return True
    elif action == "laporan_edit":
        return True
    
    return False
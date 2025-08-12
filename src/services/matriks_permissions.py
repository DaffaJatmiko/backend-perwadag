"""Helper functions untuk matriks permissions dan status flow."""

from typing import Dict, List, Optional, Any
from src.models.evaluasi_enums import MatriksStatus, TindakLanjutStatus
from src.schemas.matriks import UserPermissions


def get_user_assignment_role(surat_tugas_data: Dict[str, Any], user_id: str) -> Optional[str]:
    """
    Determine role user dalam surat tugas tertentu.
    
    Returns:
        - "ketua_tim"
        - "pengendali_teknis" 
        - "pengedali_mutu"
        - "pimpinan_inspektorat"
        - "anggota_tim"
        - None (jika tidak assigned)
    """
    import logging
    logger = logging.getLogger("uvicorn.error")
    
    # Check specific roles
    if surat_tugas_data.get('ketua_tim_id') == user_id:
        return "ketua_tim"
    if surat_tugas_data.get('pengendali_teknis_id') == user_id:
        return "pengendali_teknis"
    if surat_tugas_data.get('pengedali_mutu_id') == user_id:
        return "pengedali_mutu"
    if surat_tugas_data.get('pimpinan_inspektorat_id') == user_id:
        return "pimpinan_inspektorat"
    
    # Check anggota tim - FIXED PARSING
    anggota_tim_ids = surat_tugas_data.get('anggota_tim_ids')
    if anggota_tim_ids:
        anggota_tim_list = []
        
        if isinstance(anggota_tim_ids, str):
            # Try JSON parsing first
            import json
            try:
                anggota_tim_list = json.loads(anggota_tim_ids)
                logger.info(f"🔍 Parsed as JSON: {anggota_tim_list}")
            except:
                # If JSON fails, try comma-separated string
                anggota_tim_list = [uid.strip() for uid in anggota_tim_ids.split(',') if uid.strip()]
                logger.info(f"🔍 Parsed as comma-separated: {anggota_tim_list}")
        elif isinstance(anggota_tim_ids, list):
            anggota_tim_list = anggota_tim_ids
            logger.info(f"🔍 Already a list: {anggota_tim_list}")
        
        logger.info(f"🔍 Checking if user_id {user_id} in anggota_tim_list: {anggota_tim_list}")
        
        if user_id in anggota_tim_list:
            logger.info(f"✅ Found {user_id} as anggota_tim")
            return "anggota_tim"
        else:
            logger.info(f"❌ User {user_id} NOT found in anggota_tim")
    
    return None


def get_matrix_permissions(
    matrix_status: MatriksStatus,
    surat_tugas_data: Dict[str, Any],
    current_user: Dict[str, Any]
) -> UserPermissions:
    """Get permissions untuk user berdasarkan matrix status dan assignment."""
    
    user_id = current_user.get('id')
    user_role = current_user.get('role')
    
    # Admin dan pengedali mutu selalu bisa edit (untuk emergency)
    if user_role in ['ADMIN']:
        return UserPermissions(
            can_edit_temuan=True,
            can_change_matrix_status=True,
            can_edit_tindak_lanjut=True,
            can_change_tindak_lanjut_status=True,
            allowed_matrix_status_changes=list(MatriksStatus),
            allowed_tindak_lanjut_status_changes=list(TindakLanjutStatus)
        )
    
    # Untuk status FINISHED, hanya admin dan pengedali mutu yang bisa edit
    if matrix_status == MatriksStatus.FINISHED:
        if user_role == 'ADMIN' or get_user_assignment_role(surat_tugas_data, user_id) == "pengedali_mutu":
            return UserPermissions(
                can_edit_temuan=True,
                can_change_matrix_status=True,
                can_edit_tindak_lanjut=True,
                can_change_tindak_lanjut_status=True,
                allowed_matrix_status_changes=[MatriksStatus.VALIDATING],  # Bisa rollback
                allowed_tindak_lanjut_status_changes=list(TindakLanjutStatus)
            )
        else:
            return UserPermissions()  # No permissions
    
    # Get user assignment role
    assignment_role = get_user_assignment_role(surat_tugas_data, user_id)
    
    if not assignment_role:
        return UserPermissions()  # Not assigned, no permissions
    
    # Permissions berdasarkan status dan assignment role
    permissions = UserPermissions()
    
    if matrix_status == MatriksStatus.DRAFTING:
        if assignment_role == "anggota_tim":
            permissions.can_edit_temuan = True
            permissions.can_change_matrix_status = True
            permissions.allowed_matrix_status_changes = [MatriksStatus.CHECKING]
        elif assignment_role == "ketua_tim":
            permissions.can_change_matrix_status = True
            permissions.allowed_matrix_status_changes = [MatriksStatus.CHECKING]
    
    elif matrix_status == MatriksStatus.CHECKING:
        if assignment_role == "ketua_tim":
            permissions.can_change_matrix_status = True
            permissions.allowed_matrix_status_changes = [MatriksStatus.DRAFTING, MatriksStatus.VALIDATING]
    
    elif matrix_status == MatriksStatus.VALIDATING:
        if assignment_role == "pengendali_teknis":
            permissions.can_change_matrix_status = True
            permissions.allowed_matrix_status_changes = [MatriksStatus.DRAFTING, MatriksStatus.FINISHED]
    
    # Permissions untuk tindak lanjut (hanya jika matrix FINISHED)
    # Ini akan dihandle di level yang lebih tinggi
    
    return permissions


def get_tindak_lanjut_permissions(
    tindak_lanjut_status: Optional[TindakLanjutStatus],
    surat_tugas_data: Dict[str, Any], 
    current_user: Dict[str, Any],
    matrix_status: MatriksStatus
) -> UserPermissions:
    """Get permissions untuk tindak lanjut."""
    
    # Tindak lanjut hanya bisa diakses jika matrix sudah FINISHED
    if matrix_status != MatriksStatus.FINISHED:
        return UserPermissions()
    
    user_id = current_user.get('id')
    user_role = current_user.get('role')
    perwadag_id = surat_tugas_data.get('user_perwadag_id')
  
    print(f"🔍 TINDAK LANJUT PERMISSION DEBUG:")
    print(f"   matrix_status: {matrix_status}")
    print(f"   user_id: {user_id}")
    print(f"   user_role: {user_role}")
    print(f"   perwadag_id: {perwadag_id}")
    print(f"   tindak_lanjut_status: {tindak_lanjut_status}")
    print(f"   user_id == perwadag_id: {user_id == perwadag_id}")
    
    # Admin selalu bisa
    if user_role == 'ADMIN':
        return UserPermissions(
            can_edit_tindak_lanjut=True,
            can_change_tindak_lanjut_status=True,
            allowed_tindak_lanjut_status_changes=list(TindakLanjutStatus)
        )
    
    assignment_role = get_user_assignment_role(surat_tugas_data, user_id)
    permissions = UserPermissions()
    
    # Jika belum ada status tindak lanjut, default ke DRAFTING
    current_status = tindak_lanjut_status or TindakLanjutStatus.DRAFTING
    
    print(f"   current_status after default: {current_status}")
    
    if current_status == TindakLanjutStatus.DRAFTING:
        print(f"   🔍 Entering DRAFTING logic...")
        # Perwadag bisa edit konten dan update status ke CHECKING
        if user_id == perwadag_id:
            print(f"   ✅ User is perwadag, setting permissions...")
            permissions.can_edit_tindak_lanjut = True
            permissions.can_change_tindak_lanjut_status = True
            permissions.allowed_tindak_lanjut_status_changes = [TindakLanjutStatus.CHECKING]
        else:
            print(f"   ❌ User is NOT perwadag")
    
    elif current_status == TindakLanjutStatus.CHECKING:
        # Ketua tim bisa review dan approve/reject
        if assignment_role == "ketua_tim":
            permissions.can_edit_tindak_lanjut = True  # Bisa edit catatan_evaluator
            permissions.can_change_tindak_lanjut_status = True
            permissions.allowed_tindak_lanjut_status_changes = [
                TindakLanjutStatus.DRAFTING, 
                TindakLanjutStatus.VALIDATING
            ]
    
    elif current_status == TindakLanjutStatus.VALIDATING:
        # Pengendali teknis bisa final approve/reject
        if assignment_role == "pengendali_teknis":
            permissions.can_change_tindak_lanjut_status = True
            permissions.allowed_tindak_lanjut_status_changes = [
                TindakLanjutStatus.DRAFTING,
                TindakLanjutStatus.FINISHED
            ]
    
    elif current_status == TindakLanjutStatus.FINISHED:
        # Hanya admin dan pengedali mutu yang bisa edit
        if assignment_role in ["pengedali_mutu", "pimpinan_inspektorat"]:
            permissions.can_edit_tindak_lanjut = True
            permissions.can_change_tindak_lanjut_status = True
            permissions.allowed_tindak_lanjut_status_changes = [TindakLanjutStatus.VALIDATING]
    
    print(f"   🔍 Final permissions: {permissions}")

    
    return permissions


def should_hide_temuan_for_perwadag(
    matrix_status: MatriksStatus,
    current_user: Dict[str, Any],
    surat_tugas_data: Dict[str, Any]
) -> bool:
    """
    Determine apakah harus hide temuan data untuk perwadag.
    
    Returns True jika harus di-hide (kosongkan response)
    """
    user_role = current_user.get('role')
    
    # Hanya berlaku untuk PERWADAG
    if user_role != 'PERWADAG':
        return False
    
    # Hide jika matrix belum FINISHED
    return matrix_status != MatriksStatus.FINISHED
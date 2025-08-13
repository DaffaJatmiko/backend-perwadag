# ===== src/services/matriks_permissions.py =====
"""
Enhanced permissions system for matrix evaluasi dengan support untuk:
1. Status-based permissions (DRAFTING, CHECKING, VALIDATING, FINISHED)  
2. Multiple role assignments per user
3. Admin special access dengan workflow respect
"""

from typing import Dict, List, Optional, Set, Any
from src.schemas.matriks import UserPermissions
from src.models.evaluasi_enums import MatriksStatus, TindakLanjutStatus


def get_user_assignment_role(current_user: Dict, surat_tugas_data: Dict) -> Set[str]:
    """
    Get all roles that user has in this surat tugas.
    User bisa punya multiple roles dalam surat tugas yang sama.
    
    Returns:
        Set of roles like {'ANGGOTA_TIM', 'PENGENDALI_TEKNIS'} etc.
    """
    user_id = current_user.get('id')
    user_roles = set()
    
    print(f"🔍 DEBUG get_user_assignment_role:")
    print(f"   user_id: {user_id}")
    print(f"   surat_tugas_data keys: {list(surat_tugas_data.keys())}")
    
    # Check primary role assignments
    if surat_tugas_data.get('user_perwadag_id') == user_id:
        user_roles.add('PERWADAG')
        print(f"   ✅ Found PERWADAG role")
        
    if surat_tugas_data.get('ketua_tim_id') == user_id:
        user_roles.add('KETUA_TIM')
        print(f"   ✅ Found KETUA_TIM role")
        
    if surat_tugas_data.get('pengendali_teknis_id') == user_id:
        user_roles.add('PENGENDALI_TEKNIS')
        print(f"   ✅ Found PENGENDALI_TEKNIS role")
        
    if surat_tugas_data.get('pengedali_mutu_id') == user_id:
        user_roles.add('PENGEDALI_MUTU')
        print(f"   ✅ Found PENGEDALI_MUTU role")
        
    if surat_tugas_data.get('pimpinan_inspektorat_id') == user_id:
        user_roles.add('PIMPINAN_INSPEKTORAT')
        print(f"   ✅ Found PIMPINAN_INSPEKTORAT role")
    
    # Check anggota tim (array)
    anggota_tim_ids = surat_tugas_data.get('anggota_tim_ids', [])
    print(f"   anggota_tim_ids: {anggota_tim_ids}")
    if anggota_tim_ids and user_id in anggota_tim_ids:
        user_roles.add('ANGGOTA_TIM')
        print(f"   ✅ Found ANGGOTA_TIM role")
    
    print(f"   🎯 Final user_roles: {user_roles}")
    return user_roles


def get_matrix_permissions(
    matrix_status: MatriksStatus, 
    surat_tugas_data: Dict, 
    current_user: Dict
) -> UserPermissions:
    """
    Get matrix permissions berdasarkan status dan user assignments.
    
    Logic:
    1. Admin bisa semua, TAPI tetap respect workflow status
    2. Users lain based on assignments dan status
    3. Multiple role assignments dikombinasi (union permissions)
    """
    
    user_id = current_user.get('id')
    user_role = current_user.get('role')  # System role: ADMIN, INSPEKTORAT, etc.
    
    # Get assignment roles in this surat tugas
    assignment_roles = get_user_assignment_role(current_user, surat_tugas_data)
    
    # Default permissions
    permissions = UserPermissions()
    
    # ===== ADMIN SPECIAL HANDLING =====
    if user_role == 'ADMIN':
        # Admin gets all permissions but RESPECTS WORKFLOW STATUS
        permissions = _get_admin_permissions_by_status(matrix_status)
        return permissions
    
    # ===== REGULAR USER PERMISSIONS =====
    # Combine permissions from all assignment roles
    all_permissions = []
    
    for role in assignment_roles:
        role_perms = _get_role_permissions_by_status(role, matrix_status)
        all_permissions.append(role_perms)
    
    # Union all permissions (any role can do = user can do)
    if all_permissions:
        permissions = _combine_permissions(all_permissions)
    
    return permissions


def _get_admin_permissions_by_status(matrix_status: MatriksStatus) -> UserPermissions:
    """
    Admin permissions yang RESPECT workflow status DAN hierarki.
    Admin bisa semua tapi mengikuti business logic workflow yang benar.
    """
    
    if matrix_status == MatriksStatus.DRAFTING:
        return UserPermissions(
            can_edit_temuan=True,  # Admin bisa edit temuan di drafting
            can_change_matrix_status=True,  # Admin bisa promote seperti anggota tim
            can_edit_tindak_lanjut=False,  # Belum waktunya tindak lanjut
            can_change_tindak_lanjut_status=False,
            allowed_matrix_status_changes=[MatriksStatus.CHECKING],  # Follow anggota tim flow
            allowed_tindak_lanjut_status_changes=[]
        )
        
    elif matrix_status == MatriksStatus.CHECKING:
        return UserPermissions(
            can_edit_temuan=False,  # ❌ Admin juga tidak bisa edit temuan di checking!
            can_change_matrix_status=True,  # Admin bisa approve/reject seperti ketua tim
            can_edit_tindak_lanjut=False,  # Belum waktunya
            can_change_tindak_lanjut_status=False,
            allowed_matrix_status_changes=[MatriksStatus.DRAFTING, MatriksStatus.VALIDATING],  # Follow ketua tim flow
            allowed_tindak_lanjut_status_changes=[]
        )
        
    elif matrix_status == MatriksStatus.VALIDATING:
        return UserPermissions(
            can_edit_temuan=False,  # ❌ Tidak bisa edit temuan
            can_change_matrix_status=True,  # Admin bisa final approve seperti pengendali teknis
            can_edit_tindak_lanjut=False,  # Belum waktunya
            can_change_tindak_lanjut_status=False,
            allowed_matrix_status_changes=[MatriksStatus.DRAFTING, MatriksStatus.FINISHED],  # Follow pengendali teknis flow
            allowed_tindak_lanjut_status_changes=[]
        )
        
    elif matrix_status == MatriksStatus.FINISHED:
        return UserPermissions(
            can_edit_temuan=False,  # ❌ LOCKED! Admin juga tidak bisa edit temuan
            can_change_matrix_status=True,  # Emergency reopen (admin special privilege)
            can_edit_tindak_lanjut=True,  # Emergency tindak lanjut edit
            can_change_tindak_lanjut_status=True,  # Emergency status change
            allowed_matrix_status_changes=[MatriksStatus.VALIDATING],  # Emergency reopen
            allowed_tindak_lanjut_status_changes=[
                TindakLanjutStatus.DRAFTING, TindakLanjutStatus.CHECKING, 
                TindakLanjutStatus.VALIDATING, TindakLanjutStatus.FINISHED
            ]
        )
    
    return UserPermissions()  # Default no permissions


def _get_role_permissions_by_status(assignment_role: str, matrix_status: MatriksStatus) -> UserPermissions:
    """
    Get permissions for specific assignment role berdasarkan status.
    """
    
    # ===== ANGGOTA TIM =====
    if assignment_role == 'ANGGOTA_TIM':
        if matrix_status == MatriksStatus.DRAFTING:
            return UserPermissions(
                can_edit_temuan=True,  # ✅ Bisa edit temuan saat drafting
                can_change_matrix_status=True,  # ✅ FIXED! Anggota tim bisa promote ke checking
                can_edit_tindak_lanjut=False,
                can_change_tindak_lanjut_status=False,
                allowed_matrix_status_changes=[MatriksStatus.CHECKING],  # ✅ Anggota tim submit ke ketua
                allowed_tindak_lanjut_status_changes=[]
            )
        else:
            # Di status lain, anggota tim tidak bisa apa-apa (sudah diserahkan ke ketua)
            return UserPermissions()
    
    # ===== KETUA TIM =====  
    elif assignment_role == 'KETUA_TIM':
        if matrix_status == MatriksStatus.DRAFTING:
            return UserPermissions(
                can_edit_temuan=True,  # Ketua tim bisa bantu edit temuan
                can_change_matrix_status=False,  # ❌ FIXED! Ketua tim TIDAK bisa promote dari drafting
                can_edit_tindak_lanjut=False,
                can_change_tindak_lanjut_status=False,
                allowed_matrix_status_changes=[],  # ❌ Harus menunggu anggota tim selesai
                allowed_tindak_lanjut_status_changes=[]
            )
        elif matrix_status == MatriksStatus.CHECKING:
            return UserPermissions(
                can_edit_temuan=False,  # ❌ Tidak bisa edit temuan di checking
                can_change_matrix_status=True,  # ✅ Bisa approve/reject (ini tugas ketua tim)
                can_edit_tindak_lanjut=False,
                can_change_tindak_lanjut_status=False,
                allowed_matrix_status_changes=[MatriksStatus.DRAFTING, MatriksStatus.VALIDATING],
                allowed_tindak_lanjut_status_changes=[]
            )
        else:
            return UserPermissions()
    
    # ===== PENGENDALI TEKNIS =====
    elif assignment_role == 'PENGENDALI_TEKNIS':
        if matrix_status == MatriksStatus.VALIDATING:
            return UserPermissions(
                can_edit_temuan=False,  # Tidak bisa edit temuan
                can_change_matrix_status=True,  # Final approve/reject
                can_edit_tindak_lanjut=False,
                can_change_tindak_lanjut_status=False,
                allowed_matrix_status_changes=[MatriksStatus.DRAFTING, MatriksStatus.FINISHED],
                allowed_tindak_lanjut_status_changes=[]
            )
        else:
            return UserPermissions()
    
    # ===== PENGEDALI MUTU =====
    elif assignment_role == 'PENGEDALI_MUTU':
        # Pengedali mutu bisa emergency access tapi terbatas
        if matrix_status == MatriksStatus.FINISHED:
            return UserPermissions(
                can_edit_temuan=False,  # Tidak bisa edit temuan
                can_change_matrix_status=False,  # Tidak bisa ubah matrix status
                can_edit_tindak_lanjut=True,  # Bisa edit tindak lanjut
                can_change_tindak_lanjut_status=True,  # Bisa ubah status tindak lanjut
                allowed_matrix_status_changes=[],
                allowed_tindak_lanjut_status_changes=[
                    TindakLanjutStatus.DRAFTING, TindakLanjutStatus.CHECKING,
                    TindakLanjutStatus.VALIDATING, TindakLanjutStatus.FINISHED
                ]
            )
        else:
            return UserPermissions()
    
    # ===== PERWADAG & PIMPINAN INSPEKTORAT =====
    # Mereka tidak punya akses ke matrix operations, hanya tindak lanjut
    elif assignment_role in ['PERWADAG', 'PIMPINAN_INSPEKTORAT']:
        return UserPermissions()  # No matrix permissions
    
    return UserPermissions()  # Default


def _combine_permissions(permissions_list: List[UserPermissions]) -> UserPermissions:
    """
    Combine multiple permissions dengan union logic.
    Jika salah satu role bisa, maka user bisa.
    """
    if not permissions_list:
        return UserPermissions()
    
    # Union all boolean permissions
    combined = UserPermissions(
        can_edit_temuan=any(p.can_edit_temuan for p in permissions_list),
        can_change_matrix_status=any(p.can_change_matrix_status for p in permissions_list),
        can_edit_tindak_lanjut=any(p.can_edit_tindak_lanjut for p in permissions_list),
        can_change_tindak_lanjut_status=any(p.can_change_tindak_lanjut_status for p in permissions_list)
    )
    
    # Union allowed status changes
    all_matrix_changes = set()
    all_tindak_lanjut_changes = set()
    
    for perm in permissions_list:
        all_matrix_changes.update(perm.allowed_matrix_status_changes)
        all_tindak_lanjut_changes.update(perm.allowed_tindak_lanjut_status_changes)
    
    combined.allowed_matrix_status_changes = list(all_matrix_changes)
    combined.allowed_tindak_lanjut_status_changes = list(all_tindak_lanjut_changes)
    
    return combined


def get_tindak_lanjut_permissions(
    global_tindak_lanjut_status: Optional[TindakLanjutStatus],
    surat_tugas_data: Dict,
    current_user: Dict,
    matrix_status: MatriksStatus
) -> UserPermissions:
    """Get tindak lanjut permissions berdasarkan GLOBAL status dan assignments."""
  
    print(f"🔍 DEBUG get_tindak_lanjut_permissions:")
    print(f"   global_tindak_lanjut_status: {global_tindak_lanjut_status}")
    print(f"   matrix_status: {matrix_status}")
    print(f"   user_role: {current_user.get('role')}")
    
    # Prerequisite: Matrix harus FINISHED dulu
    if matrix_status != MatriksStatus.FINISHED:
        return UserPermissions()  # No tindak lanjut permissions
    
    user_role = current_user.get('role')
    assignment_roles = get_user_assignment_role(current_user, surat_tugas_data)
    
    # Default status jika belum ada
    if global_tindak_lanjut_status is None:
        global_tindak_lanjut_status = TindakLanjutStatus.DRAFTING
    
    # ===== ADMIN (FIXED: Respect current status) =====
    if user_role == 'ADMIN':
        # ✅ FIX: Admin permissions based on CURRENT status
        if global_tindak_lanjut_status == TindakLanjutStatus.DRAFTING:
            return UserPermissions(
                can_edit_tindak_lanjut=True,
                can_change_tindak_lanjut_status=True,
                allowed_tindak_lanjut_status_changes=[TindakLanjutStatus.CHECKING]  # ✅ Only next step
            )
        elif global_tindak_lanjut_status == TindakLanjutStatus.CHECKING:
            return UserPermissions(
                can_edit_tindak_lanjut=True,
                can_change_tindak_lanjut_status=True,
                allowed_tindak_lanjut_status_changes=[
                    TindakLanjutStatus.DRAFTING,    # Reject
                    TindakLanjutStatus.VALIDATING   # Approve
                ]
            )
        elif global_tindak_lanjut_status == TindakLanjutStatus.VALIDATING:
            return UserPermissions(
                can_edit_tindak_lanjut=True,
                can_change_tindak_lanjut_status=True,
                allowed_tindak_lanjut_status_changes=[
                    TindakLanjutStatus.DRAFTING,  # Reject
                    TindakLanjutStatus.FINISHED   # Approve
                ]
            )
        elif global_tindak_lanjut_status == TindakLanjutStatus.FINISHED:
            return UserPermissions(
                can_edit_tindak_lanjut=True,  # Emergency edit
                can_change_tindak_lanjut_status=True,  # Emergency reopen
                allowed_tindak_lanjut_status_changes=[TindakLanjutStatus.VALIDATING]  # Emergency reopen
            )
    
    # ===== REGULAR USERS =====
    permissions_list = []
    
    for role in assignment_roles:
        print(f"   🔍 Checking permissions for role: {role}")
        role_perms = _get_tindak_lanjut_role_permissions(role, global_tindak_lanjut_status)
        print(f"   📋 Role {role} permissions: {role_perms}")
        permissions_list.append(role_perms)
    
    if permissions_list:
        final_perms = _combine_permissions(permissions_list)
        print(f"   🎯 Final combined permissions: {final_perms}")
        return final_perms
    
    print(f"   ❌ No permissions found")
    return UserPermissions()


def _get_tindak_lanjut_role_permissions(
    assignment_role: str, 
    tindak_lanjut_status: TindakLanjutStatus
) -> UserPermissions:
    """
    Get tindak lanjut permissions for specific assignment role.
    """
    
    # ===== PERWADAG =====
    if assignment_role == 'PERWADAG':
        if tindak_lanjut_status == TindakLanjutStatus.DRAFTING:
            return UserPermissions(
                can_edit_tindak_lanjut=True,  # Bisa edit content
                can_change_tindak_lanjut_status=True,  # Bisa submit
                allowed_tindak_lanjut_status_changes=[TindakLanjutStatus.CHECKING]
            )
        else:
            return UserPermissions()  # Tidak bisa edit di status lain
    
    # ===== KETUA TIM =====
    elif assignment_role == 'KETUA_TIM':
        if tindak_lanjut_status == TindakLanjutStatus.CHECKING:
            return UserPermissions(
                can_edit_tindak_lanjut=True,  # Bisa edit catatan evaluator
                can_change_tindak_lanjut_status=True,  # Bisa approve/reject
                allowed_tindak_lanjut_status_changes=[
                    TindakLanjutStatus.DRAFTING, TindakLanjutStatus.VALIDATING
                ]
            )
        else:
            return UserPermissions()
    
    # ===== PENGENDALI TEKNIS =====
    elif assignment_role == 'PENGENDALI_TEKNIS':
        if tindak_lanjut_status == TindakLanjutStatus.VALIDATING:
            return UserPermissions(
                can_edit_tindak_lanjut=False,  # Tidak edit content
                can_change_tindak_lanjut_status=True,  # Final approve/reject
                allowed_tindak_lanjut_status_changes=[
                    TindakLanjutStatus.DRAFTING, TindakLanjutStatus.FINISHED
                ]
            )
        else:
            return UserPermissions()
    
    # ===== PENGEDALI MUTU =====
    elif assignment_role == 'PENGEDALI_MUTU':
        # Pengedali mutu bisa emergency access
        return UserPermissions(
            can_edit_tindak_lanjut=True,
            can_change_tindak_lanjut_status=True,
            allowed_tindak_lanjut_status_changes=[
                TindakLanjutStatus.DRAFTING, TindakLanjutStatus.CHECKING,
                TindakLanjutStatus.VALIDATING, TindakLanjutStatus.FINISHED
            ]
        )
    
    return UserPermissions()


def should_hide_temuan_for_perwadag(
    matrix_status: MatriksStatus,
    current_user: Dict,
    surat_tugas_data: Dict
) -> bool:
    """
    Check apakah temuan harus disembunyikan untuk perwadag.
    Perwadag tidak boleh lihat temuan sebelum matrix FINISHED.
    """
    assignment_roles = get_user_assignment_role(current_user, surat_tugas_data)
    
    # Jika bukan perwadag, tidak perlu hide
    if 'PERWADAG' not in assignment_roles:
        return False
    
    # Jika admin, tidak perlu hide
    if current_user.get('role') == 'ADMIN':
        return False
    
    # Jika matrix belum finished, hide dari perwadag
    return matrix_status != MatriksStatus.FINISHED
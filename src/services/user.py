"""Simplified User service tanpa Role tables."""

from typing import Optional, List
from fastapi import HTTPException, status
from src.repositories.user import UserRepository
from src.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, 
    UserChangePassword, MessageResponse, PerwadagListResponse, PerwadagSummary, UserSummary
)
from src.schemas.filters import UserFilterParams, UsernameGenerationPreview, UsernameGenerationResponse
from src.auth.jwt import get_password_hash, verify_password
from src.models.user import User
from src.models.enums import UserRole
from src.utils.username_generator import generate_username_from_name_and_inspektorat, generate_available_username
from src.core.redis import redis_mark_role_changed

class UserService:
    """Simplified user service dengan single table approach."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        # No more role_repo needed!
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create user dengan debug username generation."""
        
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Validate inspektorat requirements
        if user_data.role == UserRole.INSPEKTORAT:
            if not user_data.inspektorat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,  
                    detail="Inspektorat diperlukan untuk role inspektorat"
                )
        elif user_data.role == UserRole.PERWADAG:
            if not user_data.inspektorat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inspektorat diperlukan untuk role perwadag"
                )
        
        # 2. Validate email uniqueness
        if user_data.email and await self.user_repo.email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar"
            )
        
        # 3. Generate username dengan debug
        logger.info(f"Generating username for: {user_data.nama}, role: {user_data.role}")
        username = self._generate_username_by_role(user_data.nama, user_data.role, user_data.inspektorat)
        logger.info(f"Generated username: {username}")
        
        # 4. Check username availability dengan debug
        username_exists = await self.user_repo.username_exists(username)
        logger.info(f"Username '{username}' exists: {username_exists}")
        
        if username_exists:
            logger.info(f"Username conflict detected, generating alternative...")
            try:
                username = await self._generate_available_username(
                    user_data.nama, user_data.role, user_data.inspektorat
                )
                logger.info(f"Alternative username generated: {username}")
            except Exception as e:
                logger.error(f"Error generating alternative username: {str(e)}")
                # Fallback dengan timestamp
                import time
                username = f"{username}_{int(time.time() % 10000)}"
                logger.info(f"Fallback username: {username}")
        
        # 5. Final check sebelum create
        final_check = await self.user_repo.username_exists(username)
        logger.info(f"Final username check for '{username}': {final_check}")
        
        if final_check:
            # Emergency fallback
            import uuid
            username = f"{username}_{str(uuid.uuid4())[:8]}"
            logger.warning(f"Emergency fallback username: {username}")
        
        # 6. Create user
        try:
            user = await self.user_repo.create(user_data, username)
            logger.info(f"User created successfully with username: {username}")
        except Exception as e:
            logger.error(f"Failed to create user with username '{username}': {str(e)}")
            raise e
        
        # 7. Convert Model → Schema Response
        return UserResponse.from_user_model(user)
    
    async def get_user_or_404(self, user_id: str) -> UserResponse:
        """Get user by ID or raise 404."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        return UserResponse.from_user_model(user)
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> UserResponse:
        """Update user dengan CASCADE UPDATE untuk data denormalized - SIMPLE VERSION."""
        
        # 1. Check if user exists
        existing_user = await self.user_repo.get_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        
        # 2. Validate email uniqueness if being updated
        if user_data.email and await self.user_repo.email_exists(user_data.email, exclude_user_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar"
            )
        
        # 3. Handle role and inspektorat validation properly
        old_role = existing_user.role
        new_role = user_data.role if user_data.role else old_role
        
        # Check if role is changing to one that requires inspektorat
        if new_role in [UserRole.INSPEKTORAT, UserRole.PERWADAG]:
            inspektorat_value = user_data.inspektorat if user_data.inspektorat is not None else existing_user.inspektorat
            
            if not inspektorat_value or not inspektorat_value.strip():
                role_name = "inspektorat" if new_role == UserRole.INSPEKTORAT else "perwadag"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Inspektorat diperlukan untuk role '{role_name}'. Silakan kirim field 'inspektorat' bersama dengan 'role'."
                )
        elif new_role == UserRole.ADMIN and old_role != UserRole.ADMIN:
            if user_data.inspektorat is None:
                user_data.inspektorat = None
        
        # 🎯 4. DETECT & EXECUTE CASCADE UPDATES (hanya untuk PERWADAG)
        cascade_results = {'total_affected': 0, 'details': []}
        
        if existing_user.role == UserRole.PERWADAG:
            try:
                # Check nama change
                if user_data.nama and user_data.nama != existing_user.nama:
                    affected = await self.user_repo.update_cascade_nama_perwadag(user_id, user_data.nama)
                    cascade_results['total_affected'] += affected
                    cascade_results['details'].append(f"Updated nama_perwadag in {affected} surat_tugas records")
                
                # Check inspektorat change
                if (user_data.inspektorat is not None and 
                    user_data.inspektorat != existing_user.inspektorat):
                    
                    affected = await self.user_repo.update_cascade_inspektorat_perwadag(user_id, user_data.inspektorat)
                    cascade_results['total_affected'] += affected['total']
                    cascade_results['details'].append(f"Updated inspektorat in {affected['surat_tugas']} surat_tugas and {affected['penilaian_risiko']} penilaian_risiko records")
                
                # Log cascade results
                if cascade_results['total_affected'] > 0:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Cascade update for user {existing_user.nama}: {cascade_results['total_affected']} records updated")
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Cascade update failed for user {user_id}: {str(e)}")
                
                # Rollback user update
                await self.user_repo.session.rollback()
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal mengupdate user dan data terkait. Perubahan dibatalkan."
                )
        
        # 5. Update user in database
        updated_user = await self.user_repo.update(user_id, user_data)
        
        # 6. Check if role changed, mark for re-login
        if user_data.role and old_role != user_data.role:
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                await redis_mark_role_changed(user_id, ttl_seconds=86400)
                logger.info(f"Role changed: {user_id} from {old_role.value} to {user_data.role.value}")
            except Exception as e:
                logger.error(f"Failed to mark role change for user {user_id}: {str(e)}")
                # Don't fail the update if Redis fails, just log
        
        # 7. Convert Model → Schema Response
        return UserResponse.from_user_model(updated_user)
    
    async def change_password(self, user_id: str, password_data: UserChangePassword) -> MessageResponse:
        """Change user password."""
        # 1. Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        
        # 2. Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password saat ini salah"
            )
        
        # 3. Check if new password is different
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password baru harus berbeda dari password saat ini"
            )
        
        # 4. Update password
        new_hashed_password = get_password_hash(password_data.new_password)
        success = await self.user_repo.update_password(user_id, new_hashed_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal memperbarui password"
            )
        
        return MessageResponse(message="Password berhasil diubah")
    
    async def reset_user_password(self, user_id: str) -> MessageResponse:
        """Reset user password to default (admin only)."""
        # 1. Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        
        # 2. Reset to default password
        default_password = "@Kemendag123"
        new_hashed_password = get_password_hash(default_password)
        success = await self.user_repo.update_password(user_id, new_hashed_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal mereset password"
            )
        
        return MessageResponse(message=f"Password direset ke default untuk user {user.nama}")
    
    async def delete_user(self, user_id: str, current_user_id: str) -> MessageResponse:
        """Delete user dengan dependency checking."""
        
        # Prevent admin from deleting themselves
        if current_user_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        
        # ✅ CHECK DEPENDENCIES untuk PERWADAG
        if user.role == UserRole.PERWADAG:
            surat_tugas_count = await self._count_user_surat_tugas(user_id)
            
            if surat_tugas_count > 0:
                # ❌ BLOCK DELETE
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tidak dapat menghapus user. Masih ada {surat_tugas_count} surat tugas yang terkait dengan user ini. Gunakan fitur deactivate sebagai alternatif."
                )
        
        # Check if user is admin (prevent deleting last admin)
        if user.role == UserRole.ADMIN:
            admin_users = await self.user_repo.get_users_by_role(UserRole.ADMIN)
            if len(admin_users) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tidak dapat menghapus user admin terakhir"
                )
        
        # ✅ SAFE TO DELETE
        await self.user_repo.soft_delete(user_id)
        return MessageResponse(message=f"User {user.nama} berhasil dihapus")
    
    async def get_all_users_with_filters(self, filters: UserFilterParams) -> UserListResponse:
        """Get users dengan error handling untuk data bermasalah."""
        
        # 1. Get users from repository
        users, total = await self.user_repo.get_all_users_filtered(filters)
        
        # 2. Convert models ke responses dengan error handling
        user_responses = []
        problematic_users = []
        
        for user in users:
            try:
                user_response = UserResponse.from_user_model(user)
                user_responses.append(user_response)
            except Exception as e:
                # Log user bermasalah tapi jangan stop proses
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to convert user {user.id} ({user.username}): {str(e)}")
                logger.error(f"User data: nama='{user.nama}', role={user.role}, inspektorat='{user.inspektorat}', email='{user.email}'")
                
                problematic_users.append({
                    "id": user.id,
                    "username": user.username,
                    "error": str(e)
                })
        
        # 3. Log summary jika ada user bermasalah
        if problematic_users:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Found {len(problematic_users)} problematic users that couldn't be converted")
            
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0

        return UserListResponse(
            items=user_responses,
            total=len(user_responses),  # Use actual converted count
            page=filters.page,
            size=filters.size,
            pages=pages
        )
    
    async def get_users_by_role(self, role: UserRole) -> List[UserResponse]:
        """Get users by role (simplified)."""
        users = await self.user_repo.get_users_by_role(role)
        return [UserResponse.from_user_model(user) for user in users]
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user untuk login."""
        # 1. Get user by username
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None
        
        # 2. Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun user dinonaktifkan"
            )
        
        # 3. Verify password
        if not verify_password(password, user.hashed_password):
            return None
        
        # 4. Update last login
        await self.user_repo.update_last_login(user.id)
        
        return user
    
    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        return await self.user_repo.get_user_statistics()
    
    async def preview_username_generation(self, preview_data: UsernameGenerationPreview) -> UsernameGenerationResponse:
        """Preview username generation."""
        # REMOVE tanggal_lahir parsing
        
        # Generate username
        if preview_data.role == UserRole.PERWADAG:
            username = self._generate_perwadag_username(preview_data.nama)
        else:
            if not preview_data.inspektorat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inspektorat diperlukan untuk role admin dan inspektorat"
                )
            username = generate_username_from_name_and_inspektorat(
                preview_data.nama, preview_data.inspektorat
            )
        
        # Check availability
        is_available = not await self.user_repo.username_exists(username)
        
        # Generate alternatives if needed
        alternatives = []
        if not is_available:
            if preview_data.role != UserRole.PERWADAG:
                # Try conflict resolution
                conflict_username = generate_username_with_conflict_resolution(
                    preview_data.nama, preview_data.inspektorat
                )
                alternatives.append(conflict_username)
            
            # Add numbered alternatives
            alternatives.extend(
                await self._generate_username_alternatives_simple(username, count=4)
            )
        
        return UsernameGenerationResponse(
            original_nama=preview_data.nama,
            inspektorat=preview_data.inspektorat,
            role=preview_data.role,
            generated_username=username,
            is_available=is_available,
            suggested_alternatives=alternatives
        )
    
    async def activate_user(self, user_id: str) -> UserResponse:
        """Activate user."""
        user_data = UserUpdate(is_active=True)
        return await self.update_user(user_id, user_data)
    
    async def deactivate_user(self, user_id: str) -> UserResponse:
        """Deactivate user."""
        # Check if it's the last admin
        user = await self.user_repo.get_by_id(user_id)
        if user and user.role == UserRole.ADMIN:
            admin_users = await self.user_repo.get_users_by_role(UserRole.ADMIN)
            active_admins = [u for u in admin_users if u.is_active and u.id != user_id]
            if len(active_admins) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tidak dapat menonaktifkan user admin aktif terakhir"
                )
        
        user_data = UserUpdate(is_active=False)
        return await self.update_user(user_id, user_data)
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _generate_username_by_role(self, nama: str, role: UserRole, inspektorat: Optional[str] = None) -> str:
        """Generate username berdasarkan role."""
        
        if role in [UserRole.ADMIN, UserRole.INSPEKTORAT, UserRole.PIMPINAN]:  # TAMBAH PIMPINAN
            if not inspektorat:
                raise ValueError(f"Inspektorat required untuk role {role.value}")
            
            # PIMPINAN MENGGUNAKAN FORMAT YANG SAMA seperti INSPEKTORAT
            return generate_username_from_name_and_inspektorat(nama, inspektorat)
        
        elif role == UserRole.PERWADAG:
            return self._generate_perwadag_username(nama)
        
        else:
            raise ValueError(f"Unknown role: {role}")
    
    def _generate_perwadag_username(self, nama: str) -> str:
        """Generate username untuk perwadag dari nama."""
        # Normalize nama perwadag
        # "ITPC Lagos – Nigeria" -> "itpc_lagos"
        # "Atdag Moscow – Rusia" -> "atdag_moscow"
        
        import re
        import unicodedata
        
        # Remove unicode and normalize
        nama = unicodedata.normalize('NFD', nama)
        nama = ''.join(c for c in nama if unicodedata.category(c) != 'Mn')
        
        # Convert to lowercase
        nama = nama.lower()
        
        # Split by common separators and take first two meaningful parts
        parts = re.split(r'[–—\-\s]+', nama)
        meaningful_parts = [part.strip() for part in parts if part.strip() and len(part.strip()) > 1]
        
        if len(meaningful_parts) >= 2:
            username = f"{meaningful_parts[0]}_{meaningful_parts[1]}"
        else:
            username = meaningful_parts[0] if meaningful_parts else "perwadag"
        
        # Clean username
        username = re.sub(r'[^a-z0-9_]', '', username)
        return username[:50]  # Limit length

    def _generate_admin_username(self, nama: str) -> str:
        """Generate simple username untuk admin dari nama."""
        import re
        import unicodedata
        
        # Normalize dan lowercase
        nama = unicodedata.normalize('NFD', nama)
        nama = ''.join(c for c in nama if unicodedata.category(c) != 'Mn')
        nama = nama.lower()
        
        # Split kata dan bersihkan
        words = nama.split()
        clean_words = []
        
        for word in words:
            clean_word = re.sub(r'[^a-z0-9]', '', word)
            if clean_word:
                clean_words.append(clean_word)
        
        if not clean_words:
            return "admin"
        elif len(clean_words) == 1:
            return clean_words[0]  # "administrator" -> "administrator"
        else:
            return f"{clean_words[0]}_{clean_words[1]}"  # "admin sistem" -> "admin_sistem"
    
    async def _generate_available_username(self, nama: str, role: UserRole, inspektorat: str = None) -> str:
        """Generate available username dengan fallback."""
        if role == UserRole.PERWADAG:
            # Use existing perwadag logic
            base_username = self._generate_perwadag_username(nama)
            alternatives = await self._generate_username_alternatives_perwadag(nama, count=10)
        else:
            # Use new inspektorat logic
            if not inspektorat:
                raise ValueError("Inspektorat diperlukan untuk role admin/inspektorat")
            
            result = await generate_available_username(
                nama, inspektorat, role, self.user_repo.username_exists
            )
            return result["username"]
        
        # Fallback for perwadag
        for username in alternatives:
            if not await self.user_repo.username_exists(username):
                return username
        
        # Ultimate fallback
        import time
        return f"{base_username}{int(time.time()) % 1000}"
    
    async def _generate_username_alternatives(self, nama: str, tanggal_lahir, role: UserRole, count: int = 5) -> List[str]:
        """Generate username alternatives."""
        base_username = self._generate_username_by_role(nama, tanggal_lahir, role)
        alternatives = []
        
        # Add number suffixes
        for i in range(1, count + 1):
            alternatives.append(f"{base_username}{i}")
        
        # Add letter suffixes
        for letter in ['a', 'b', 'c', 'd', 'e']:
            if len(alternatives) < count:
                alternatives.append(f"{base_username}{letter}")
        
        return alternatives[:count]

    async def search_perwadag_users(
        self, 
        search: str = None,
        inspektorat: str = None,
        is_active: bool = True,
        page: int = 1,
        size: int = 50
    ) -> PerwadagListResponse:
        """Search perwadag users dengan response yang konsisten."""
        
        # Get users dari repository dengan pagination
        users, total = await self.user_repo.search_perwadag_users_paginated(
            search, inspektorat, is_active, page, size
        )
        
        # Convert ke PerwadagSummary
        perwadag_list = [PerwadagSummary.from_user_model(user) for user in users]
        
        # Calculate pages
        pages = (total + size - 1) // size if total > 0 else 0
        
        return PerwadagListResponse(
            items=perwadag_list,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

    async def _generate_username_alternatives_simple(self, base_username: str, count: int = 5) -> List[str]:
        """Generate simple numbered alternatives."""
        alternatives = []
        for i in range(1, count + 1):
            alternatives.append(f"{base_username}{i}")
        return alternatives

    async def _count_user_surat_tugas(self, user_id: str) -> int:
        """Count surat tugas yang terkait dengan user."""
        from sqlalchemy import select, func, and_
        from src.models.surat_tugas import SuratTugas
        
        # Gunakan session dari user_repo
        session = self.user_repo.session
        
        query = select(func.count(SuratTugas.id)).where(
            and_(
                SuratTugas.user_perwadag_id == user_id,
                SuratTugas.deleted_at.is_(None)
            )
        )
        
        result = await session.execute(query)
        return result.scalar() or 0

    async def get_users_by_inspektorat_and_roles(
        self, 
        inspektorat: str, 
        roles: List[UserRole]
    ) -> List[UserSummary]:
        """Get users by inspektorat and specific roles."""
        
        # GUNAKAN METHOD YANG SUDAH ADA
        users = await self.user_repo.get_users_by_inspektorat_and_roles(inspektorat, roles)
        
        return [
            UserSummary(
                id=user.id,
                nama=user.nama,
                username=user.username,
                role=user.role.value,
                inspektorat=user.inspektorat,
                jabatan=user.jabatan
            )
            for user in users
        ]
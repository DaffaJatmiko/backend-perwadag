"""Repository untuk surat tugas."""

from typing import List, Optional, Tuple, Dict, Any, Union
from datetime import datetime, date
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.schemas.surat_tugas import SuratTugasCreate, SuratTugasUpdate
from src.schemas.filters import SuratTugasFilterParams


class SuratTugasRepository:
    """Repository untuk operasi surat tugas."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ===== CREATE OPERATIONS =====
    
    async def create(self, surat_tugas_data: Union[SuratTugasCreate, dict], file_path: str) -> SuratTugas:
        """
        Create surat tugas baru dengan assignment fields.
        
        Args:
            surat_tugas_data: SuratTugasCreate object atau dict (yang sudah include pimpinan_inspektorat_id)
            file_path: Path file surat tugas
        """
        
        # Convert to dict if it's SuratTugasCreate object
        if isinstance(surat_tugas_data, SuratTugasCreate):
            data_dict = surat_tugas_data.dict()
        else:
            data_dict = surat_tugas_data
        
        # Get perwadag info
        perwadag = await self.get_perwadag_by_id(data_dict['user_perwadag_id'])
        if not perwadag:
            raise ValueError("Perwadag not found")
        
        # Convert anggota_tim_ids list to string
        anggota_tim_ids_str = None
        if data_dict.get('anggota_tim_ids'):
            if isinstance(data_dict['anggota_tim_ids'], list):
                anggota_tim_ids_str = ','.join(data_dict['anggota_tim_ids'])
            else:
                anggota_tim_ids_str = data_dict['anggota_tim_ids']
        
        # Create surat tugas instance dengan field baru
        surat_tugas = SuratTugas(
            user_perwadag_id=data_dict['user_perwadag_id'],
            nama_perwadag=perwadag.nama,
            inspektorat=perwadag.inspektorat,
            tanggal_evaluasi_mulai=data_dict['tanggal_evaluasi_mulai'],
            tanggal_evaluasi_selesai=data_dict['tanggal_evaluasi_selesai'],
            no_surat=data_dict['no_surat'],
            
            # GUNAKAN field ID baru:
            pengedali_mutu_id=data_dict['pengedali_mutu_id'],
            pengendali_teknis_id=data_dict['pengendali_teknis_id'],
            ketua_tim_id=data_dict['ketua_tim_id'],
            anggota_tim_ids=anggota_tim_ids_str,
            pimpinan_inspektorat_id=data_dict['pimpinan_inspektorat_id'],  # Ini sekarang ada dari service
            
            file_surat_tugas=file_path
        )
        
        self.session.add(surat_tugas)
        await self.session.commit()
        await self.session.refresh(surat_tugas)
        return surat_tugas
    
    # ===== READ OPERATIONS =====
    
    async def get_by_id(self, surat_tugas_id: str) -> Optional[SuratTugas]:
        """Get surat tugas by ID."""
        query = select(SuratTugas).where(
            and_(SuratTugas.id == surat_tugas_id, SuratTugas.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_no_surat(self, no_surat: str) -> Optional[SuratTugas]:
        """Get surat tugas by nomor surat."""
        query = select(SuratTugas).where(
            and_(SuratTugas.no_surat == no_surat, SuratTugas.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(
        self, 
        filters: SuratTugasFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[SuratTugas], int]:
        """Get all surat tugas dengan filtering berdasarkan role."""
        
        # Build base query
        query = select(SuratTugas).where(SuratTugas.deleted_at.is_(None))
        
        # Apply role-based filtering
        if user_role == "PERWADAG":
            # Perwadag hanya bisa lihat milik sendiri
            query = query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "PIMPINAN" and user_inspektorat:
            # Pimpinan bisa lihat semua di wilayah kerjanya
            query = query.where(SuratTugas.inspektorat == user_inspektorat)
        elif user_role == "INSPEKTORAT" and user_id:
            # Inspektorat hanya bisa lihat yang dia assigned
            query = query.where(
                or_(
                    SuratTugas.pengedali_mutu_id == user_id,
                    SuratTugas.pengendali_teknis_id == user_id,
                    SuratTugas.ketua_tim_id == user_id,
                    SuratTugas.anggota_tim_ids.like(f"%{user_id}%")
                )
            )
        # Admin bisa lihat semua
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    SuratTugas.nama_perwadag.ilike(search_term),
                    SuratTugas.no_surat.ilike(search_term),
                    SuratTugas.nama_pengedali_mutu.ilike(search_term),
                    SuratTugas.nama_pengendali_teknis.ilike(search_term),
                    SuratTugas.nama_ketua_tim.ilike(search_term)
                )
            )
        
        # Apply specific filters
        if filters.inspektorat:
            query = query.where(SuratTugas.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        if filters.user_perwadag_id:
            query = query.where(SuratTugas.user_perwadag_id == filters.user_perwadag_id)
        
        # Date filters
        if filters.tahun_evaluasi:
            query = query.where(
                func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == filters.tahun_evaluasi
            )
        
        # if filters.tanggal_mulai_from:
        #     query = query.where(SuratTugas.tanggal_evaluasi_mulai >= filters.tanggal_mulai_from)
        
        # if filters.tanggal_mulai_to:
        #     query = query.where(SuratTugas.tanggal_evaluasi_mulai <= filters.tanggal_mulai_to)
        
        # Status filters
        if filters.is_active is not None:
            today = date.today()
            if filters.is_active:
                query = query.where(
                    and_(
                        SuratTugas.tanggal_evaluasi_mulai <= today,
                        SuratTugas.tanggal_evaluasi_selesai >= today
                    )
                )
            else:
                query = query.where(
                    or_(
                        SuratTugas.tanggal_evaluasi_mulai > today,
                        SuratTugas.tanggal_evaluasi_selesai < today
                    )
                )
        
        if filters.has_file is not None:
            if filters.has_file:
                query = query.where(and_(
                    SuratTugas.file_surat_tugas.is_not(None),
                    SuratTugas.file_surat_tugas != ""
                ))
            else:
                query = query.where(or_(
                    SuratTugas.file_surat_tugas.is_(None),
                    SuratTugas.file_surat_tugas == ""
                ))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        offset = (filters.page - 1) * filters.size
        query = (
            query
            .offset(offset)
            .limit(filters.size)
            .order_by(SuratTugas.created_at.desc())
        )
        
        # Execute query
        result = await self.session.execute(query)
        surat_tugas_list = result.scalars().all()
        
        return list(surat_tugas_list), total
    
    async def get_by_perwadag_id(self, user_perwadag_id: str) -> List[SuratTugas]:
        """Get all surat tugas untuk perwadag tertentu."""
        query = select(SuratTugas).where(
            and_(
                SuratTugas.user_perwadag_id == user_perwadag_id,
                SuratTugas.deleted_at.is_(None)
            )
        ).order_by(SuratTugas.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_inspektorat(self, inspektorat: str) -> List[SuratTugas]:
        """Get all surat tugas untuk inspektorat tertentu."""
        query = select(SuratTugas).where(
            and_(
                SuratTugas.inspektorat == inspektorat,
                SuratTugas.deleted_at.is_(None)
            )
        ).order_by(SuratTugas.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    # ===== UPDATE OPERATIONS =====
    
    async def update(self, surat_tugas_id: str, surat_tugas_data: SuratTugasUpdate) -> Optional[SuratTugas]:
        """Update surat tugas - FIXED to match create method."""
        surat_tugas = await self.get_by_id(surat_tugas_id)
        if not surat_tugas:
            return None
        
        # Update fields
        update_data = surat_tugas_data.model_dump(exclude_unset=True)
        
        # 🔥 TAMBAHAN: Convert anggota_tim_ids SAMA SEPERTI CREATE METHOD
        if 'anggota_tim_ids' in update_data:
            anggota_tim_list = update_data['anggota_tim_ids']
            if anggota_tim_list is not None:
                if anggota_tim_list:  # Non-empty list
                    # SAMA seperti create: ','.join(surat_tugas_data.anggota_tim_ids)
                    update_data['anggota_tim_ids'] = ','.join(anggota_tim_list)
                else:  # Empty list
                    update_data['anggota_tim_ids'] = None
        
        # Apply updates
        for key, value in update_data.items():
            setattr(surat_tugas, key, value)
        
        surat_tugas.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(surat_tugas)
        return surat_tugas
    
    async def update_file_path(self, surat_tugas_id: str, file_path: str) -> Optional[SuratTugas]:
        """Update file path surat tugas."""
        surat_tugas = await self.get_by_id(surat_tugas_id)
        if not surat_tugas:
            return None
        
        surat_tugas.file_surat_tugas = file_path
        surat_tugas.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(surat_tugas)
        return surat_tugas
    
    # ===== DELETE OPERATIONS =====
    
    async def soft_delete(self, surat_tugas_id: str) -> bool:
        """Soft delete surat tugas by ID."""
        from datetime import datetime
        
        surat_tugas = await self.get_by_id(surat_tugas_id)
        if not surat_tugas:
            return False
        
        surat_tugas.deleted_at = datetime.utcnow()
        surat_tugas.updated_at = datetime.utcnow()
        # JANGAN COMMIT - biarkan transaction context yang handle
        return True
    
    async def hard_delete(self, surat_tugas_id: str) -> bool:
        """Hard delete surat tugas."""
        query = delete(SuratTugas).where(SuratTugas.id == surat_tugas_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    # ===== VALIDATION OPERATIONS =====
    
    async def no_surat_exists(self, no_surat: str, exclude_id: Optional[str] = None) -> bool:
        """Check if nomor surat already exists."""
        query = select(SuratTugas.id).where(
            and_(
                SuratTugas.no_surat == no_surat
            )
        )
        
        if exclude_id:
            query = query.where(SuratTugas.id != exclude_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_perwadag_by_id(self, user_id: str) -> Optional[User]:
        """Get user perwadag by ID."""
        from src.models.enums import UserRole
        
        query = select(User).where(
            and_(
                User.id == user_id,
                # User.role == UserRole.PERWADAG,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    # ===== STATISTICS =====   
    async def get_dashboard_completion_data(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[SuratTugas]:
        """
        Get surat tugas data untuk dashboard completion statistics.
        
        Mengembalikan list surat tugas dengan filtering berdasarkan role dan year.
        Method ini akan digunakan service untuk menghitung completion statistics
        dari related records secara manual.
        """
        
        # Build base query berdasarkan role
        query = select(SuratTugas).where(SuratTugas.deleted_at.is_(None))
        
        # Apply role-based filtering (sama seperti get_all_filtered)
        if user_role == "PERWADAG":
            query = query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "INSPEKTORAT" and user_inspektorat:
            query = query.where(SuratTugas.inspektorat == user_inspektorat)
        # Admin bisa lihat semua
        
        # Apply year filter jika ada (sama seperti get_all_filtered)
        if year:
            query = query.where(
                func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == year
            )
        
        # Order by created_at desc untuk recent data
        query = query.order_by(SuratTugas.created_at.desc())
        
        # Execute query
        result = await self.session.execute(query)
        surat_tugas_list = result.scalars().all()
        
        return list(surat_tugas_list)

    async def clear_file_path(self, surat_tugas_id: str) -> Optional[SuratTugas]:
        """Clear file path (set to empty string)."""
        surat_tugas = await self.get_by_id(surat_tugas_id)
        if not surat_tugas:
            return None
        
        surat_tugas.file_surat_tugas = ""
        surat_tugas.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(surat_tugas)
        return surat_tugas
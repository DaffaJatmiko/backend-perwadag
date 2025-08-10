"""Safe Laporan Hasil repository - menghindari property object error."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func, update, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.laporan_hasil import LaporanHasil
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.schemas.laporan_hasil import LaporanHasilCreate, LaporanHasilUpdate
from src.schemas.filters import LaporanHasilFilterParams


class LaporanHasilRepository:
    """Safe repository untuk operasi laporan hasil - NO PROPERTY OBJECTS."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, laporan_hasil_data: LaporanHasilCreate) -> LaporanHasil:
        """Create laporan hasil baru."""
        laporan_hasil = LaporanHasil(
            surat_tugas_id=laporan_hasil_data.surat_tugas_id
        )
        
        self.session.add(laporan_hasil)
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil
    
    async def get_by_id(self, laporan_hasil_id: str) -> Optional[LaporanHasil]:
        """Get laporan hasil by ID."""
        query = select(LaporanHasil).where(
            and_(LaporanHasil.id == laporan_hasil_id, LaporanHasil.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[LaporanHasil]:
        """Get laporan hasil by surat tugas ID."""
        query = select(LaporanHasil).where(
            and_(
                LaporanHasil.surat_tugas_id == surat_tugas_id,
                LaporanHasil.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(
        self,
        filters: LaporanHasilFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all laporan hasil dengan enriched data - SAFE VERSION."""
        
        # 🔥 STEP 1: Fetch laporan hasil dengan relationship loading (SAFE METHOD)
        laporan_query = (
            select(LaporanHasil)
            .join(SuratTugas, LaporanHasil.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
            .where(
                and_(
                    LaporanHasil.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None)
                )
            )
        )
        
        # Role-based filtering
        if user_role == "PERWADAG" and user_id:
            laporan_query = laporan_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "PIMPINAN" and user_inspektorat:
            laporan_query = laporan_query.where(SuratTugas.inspektorat == user_inspektorat)
        elif user_role == "INSPEKTORAT" and user_id:
            # Assignment-based filtering
            laporan_query = laporan_query.where(
                or_(
                    SuratTugas.pengedali_mutu_id == user_id,
                    SuratTugas.pengendali_teknis_id == user_id,
                    SuratTugas.ketua_tim_id == user_id,
                    SuratTugas.anggota_tim_ids.like(f"%{user_id}%")
                )
            )
            
        # Apply filters - FIXED field names sesuai model
        if filters.search:
            search_term = f"%{filters.search}%"
            laporan_query = laporan_query.where(
                or_(
                    LaporanHasil.nomor_laporan.ilike(search_term),
                    SuratTugas.no_surat.ilike(search_term),
                    SuratTugas.nama_perwadag.ilike(search_term),
                    User.nama.ilike(search_term)
                )
            )
        
        if filters.inspektorat:
            laporan_query = laporan_query.where(SuratTugas.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        if filters.user_perwadag_id:
            laporan_query = laporan_query.where(SuratTugas.user_perwadag_id == filters.user_perwadag_id)
        
        if filters.tahun_evaluasi:
            laporan_query = laporan_query.where(func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == filters.tahun_evaluasi)
        
        # Add surat_tugas_id filter if available
        if hasattr(filters, 'surat_tugas_id') and filters.surat_tugas_id:
            laporan_query = laporan_query.where(LaporanHasil.surat_tugas_id == filters.surat_tugas_id)
        
        # Add nomor_laporan filter if available
        if hasattr(filters, 'nomor_laporan') and filters.nomor_laporan:
            laporan_query = laporan_query.where(LaporanHasil.nomor_laporan.ilike(f"%{filters.nomor_laporan}%"))
        
        # FIXED: Use correct field name file_laporan_hasil
        if filters.has_file is not None:
            if filters.has_file:
                laporan_query = laporan_query.where(LaporanHasil.file_laporan_hasil.is_not(None))
            else:
                laporan_query = laporan_query.where(LaporanHasil.file_laporan_hasil.is_(None))
        
        if filters.has_nomor is not None:
            if filters.has_nomor:
                laporan_query = laporan_query.where(LaporanHasil.nomor_laporan.is_not(None))
            else:
                laporan_query = laporan_query.where(LaporanHasil.nomor_laporan.is_(None))
        
        # Add has_tanggal filter if available
        if hasattr(filters, 'has_tanggal') and filters.has_tanggal is not None:
            if filters.has_tanggal:
                laporan_query = laporan_query.where(LaporanHasil.tanggal_laporan.is_not(None))
            else:
                laporan_query = laporan_query.where(LaporanHasil.tanggal_laporan.is_(None))
        
        if filters.is_completed is not None:
            if filters.is_completed:
                # Completed: has file, nomor, and tanggal
                laporan_query = laporan_query.where(
                    and_(
                        LaporanHasil.file_laporan_hasil.is_not(None),
                        LaporanHasil.nomor_laporan.is_not(None),
                        LaporanHasil.tanggal_laporan.is_not(None)
                    )
                )
            else:
                # Not completed: missing any of the required fields
                laporan_query = laporan_query.where(
                    or_(
                        LaporanHasil.file_laporan_hasil.is_(None),
                        LaporanHasil.nomor_laporan.is_(None),
                        LaporanHasil.tanggal_laporan.is_(None)
                    )
                )
        
        # Date range filters
        # if filters.created_from:
        #     laporan_query = laporan_query.where(LaporanHasil.created_at >= filters.created_from)
        # if filters.created_to:
        #     laporan_query = laporan_query.where(LaporanHasil.created_at <= filters.created_to)
        
        # Add tanggal_laporan filters if available
        if hasattr(filters, 'tanggal_laporan_from') and filters.tanggal_laporan_from:
            laporan_query = laporan_query.where(LaporanHasil.tanggal_laporan >= filters.tanggal_laporan_from)
        if hasattr(filters, 'tanggal_laporan_to') and filters.tanggal_laporan_to:
            laporan_query = laporan_query.where(LaporanHasil.tanggal_laporan <= filters.tanggal_laporan_to)
        
        # Add tanggal_evaluasi filters if available
        if hasattr(filters, 'tanggal_evaluasi_from') and filters.tanggal_evaluasi_from:
            laporan_query = laporan_query.where(SuratTugas.tanggal_evaluasi_mulai >= filters.tanggal_evaluasi_from)
        if hasattr(filters, 'tanggal_evaluasi_to') and filters.tanggal_evaluasi_to:
            laporan_query = laporan_query.where(SuratTugas.tanggal_evaluasi_selesai <= filters.tanggal_evaluasi_to)
        
        # 🔥 STEP 2: Count total (SAFE)
        count_query = select(func.count()).select_from(laporan_query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()
        
        # 🔥 STEP 3: Apply pagination dan ordering
        laporan_query = laporan_query.order_by(LaporanHasil.created_at.desc())
        laporan_query = laporan_query.offset((filters.page - 1) * filters.size).limit(filters.size)
        
        # 🔥 STEP 4: Execute query - Fetch LaporanHasil objects
        result = await self.session.execute(laporan_query)
        laporan_list = result.scalars().all()
        
        # 🔥 STEP 5: Manually fetch related data untuk setiap laporan
        enriched_results = []
        
        for laporan in laporan_list:
            # Fetch surat tugas manually
            st_query = select(SuratTugas).where(SuratTugas.id == laporan.surat_tugas_id)
            st_result = await self.session.execute(st_query)
            surat_tugas = st_result.scalar_one_or_none()
            
            if not surat_tugas:
                continue
            
            # Fetch user manually
            user_query = select(User).where(User.id == surat_tugas.user_perwadag_id)
            user_result = await self.session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                continue
            
            # Build laporan data (SAFE - akses langsung attribute)
            laporan_data = {
                'id': laporan.id,
                'surat_tugas_id': laporan.surat_tugas_id,
                'nomor_laporan': laporan.nomor_laporan,
                'tanggal_laporan': laporan.tanggal_laporan,
                'file_laporan_hasil': laporan.file_laporan_hasil,
                'created_at': laporan.created_at,
                'updated_at': laporan.updated_at,
                'created_by': laporan.created_by,
                'updated_by': laporan.updated_by
            }
            
            # Build surat tugas data (SAFE - akses langsung attribute)
            surat_tugas_data = {
                'no_surat': surat_tugas.no_surat,
                'nama_perwadag': surat_tugas.nama_perwadag,
                'inspektorat': surat_tugas.inspektorat,
                'tanggal_evaluasi_mulai': surat_tugas.tanggal_evaluasi_mulai,
                'tanggal_evaluasi_selesai': surat_tugas.tanggal_evaluasi_selesai,
                'tahun_evaluasi': surat_tugas.tahun_evaluasi,
                'perwadag_nama': user.nama
            }
            
            enriched_results.append({
                'laporan_hasil': laporan_data,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total
    
    async def update(self, laporan_hasil_id: str, update_data: LaporanHasilUpdate) -> Optional[LaporanHasil]:
        """Update laporan hasil."""
        laporan_hasil = await self.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(laporan_hasil, key, value)
        
        laporan_hasil.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil
    
    async def update_file_path(self, laporan_hasil_id: str, file_path: str) -> Optional[LaporanHasil]:
        """Update file path - FIXED field name."""
        laporan_hasil = await self.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            return None
        
        laporan_hasil.file_laporan_hasil = file_path  # FIXED field name
        laporan_hasil.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics untuk laporan hasil - SIMPLE VERSION."""
        
        # Simple count query tanpa complex aggregations
        base_query = (
            select(LaporanHasil)
            .join(SuratTugas, LaporanHasil.surat_tugas_id == SuratTugas.id)
            .where(
                and_(
                    LaporanHasil.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None)
                )
            )
        )
        
        # Apply role-based filtering
        if user_role == "perwadag" and user_id:
            base_query = base_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "inspektorat" and user_inspektorat:
            base_query = base_query.where(SuratTugas.inspektorat == user_inspektorat)
        
        # Simple total count
        total_result = await self.session.execute(select(func.count()).select_from(base_query.subquery()))
        total = total_result.scalar()
        
        # Basic statistics (simplified to avoid aggregation issues)
        return {
            'total': total or 0,
            'has_file': 0,  # Placeholder
            'has_nomor': 0,  # Placeholder
            'completed': 0,  # Placeholder
            'completion_rate': 0.0
        }

    async def soft_delete(self, laporan_hasil_id: str) -> bool:
        """Soft delete laporan hasil by ID."""
        from datetime import datetime
        
        laporan_hasil = await self.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            return False
        
        laporan_hasil.deleted_at = datetime.utcnow()
        laporan_hasil.updated_at = datetime.utcnow()
        # JANGAN COMMIT - biarkan transaction context yang handle
        return True

    async def clear_file_path(self, laporan_hasil_id: str) -> Optional[LaporanHasil]:
        """Clear file path (set to None)."""
        laporan_hasil = await self.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            return None
        
        laporan_hasil.file_laporan_hasil = None
        laporan_hasil.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil

    async def check_nomor_laporan_exists(
        self, 
        nomor_laporan: str, 
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check apakah nomor laporan sudah exists di database.
        
        Args:
            nomor_laporan: Nomor laporan yang akan dicek
            exclude_id: ID laporan hasil yang dikecualikan (untuk update case)
        
        Returns:
            bool: True jika nomor laporan sudah exists, False jika belum
        """
        if not nomor_laporan or nomor_laporan.strip() == "":
            return False
        
        # Clean nomor laporan
        nomor_laporan = nomor_laporan.strip()
        
        # Build query
        query = select(LaporanHasil.id).where(
            and_(
                LaporanHasil.nomor_laporan == nomor_laporan,
                LaporanHasil.deleted_at.is_(None)
            )
        )
        
        # Exclude current record jika update
        if exclude_id:
            query = query.where(LaporanHasil.id != exclude_id)
        
        result = await self.session.execute(query)
        existing_id = result.scalar_one_or_none()
        
        return existing_id is not None
"""Safe Matriks repository - menghindari property object error."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func, update, delete, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.matriks import Matriks
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.schemas.matriks import MatriksCreate, MatriksUpdate
from src.schemas.filters import MatriksFilterParams


class MatriksRepository:
    """Safe repository untuk operasi matriks - NO PROPERTY OBJECTS."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, matriks_data: MatriksCreate) -> Matriks:
        """Create matriks baru."""
        matriks = Matriks(
            surat_tugas_id=matriks_data.surat_tugas_id
        )
        
        self.session.add(matriks)
        await self.session.commit()
        await self.session.refresh(matriks)
        return matriks
    
    async def get_by_id(self, matriks_id: str) -> Optional[Matriks]:
        """Get matriks by ID."""
        query = select(Matriks).where(
            and_(Matriks.id == matriks_id, Matriks.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[Matriks]:
        """Get matriks by surat tugas ID."""
        query = select(Matriks).where(
            and_(
                Matriks.surat_tugas_id == surat_tugas_id,
                Matriks.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(
        self,
        filters: MatriksFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all matriks dengan enriched data - SAFE VERSION."""
        
        # 🔥 STEP 1: Fetch matriks dengan relationship loading (SAFE METHOD)
        matriks_query = (
            select(Matriks)
            .join(SuratTugas, Matriks.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
            .where(
                and_(
                    Matriks.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None)
                )
            )
        )
        
        # Role-based filtering
        if user_role == "PERWADAG" and user_id:
            matriks_query = matriks_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "INSPEKTORAT" and user_inspektorat:
            matriks_query = matriks_query.where(SuratTugas.inspektorat == user_inspektorat)
        
        # Apply filters - FIXED field names
        if filters.search:
            search_term = f"%{filters.search}%"
            matriks_query = matriks_query.where(
                or_(
                    SuratTugas.no_surat.ilike(search_term),
                    SuratTugas.nama_perwadag.ilike(search_term),
                    User.nama.ilike(search_term)
                )
            )
        
        if filters.inspektorat:
            matriks_query = matriks_query.where(SuratTugas.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        if filters.user_perwadag_id:
            matriks_query = matriks_query.where(SuratTugas.user_perwadag_id == filters.user_perwadag_id)
        
        if filters.tahun_evaluasi:
            matriks_query = matriks_query.where(
                func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == filters.tahun_evaluasi
            )        
        # Add surat_tugas_id filter if available
        if hasattr(filters, 'surat_tugas_id') and filters.surat_tugas_id:
            matriks_query = matriks_query.where(Matriks.surat_tugas_id == filters.surat_tugas_id)
        
        if filters.has_file is not None:
            if filters.has_file:
                matriks_query = matriks_query.where(Matriks.file_dokumen_matriks.is_not(None))
            else:
                matriks_query = matriks_query.where(Matriks.file_dokumen_matriks.is_(None))
        
        # Removed has_nomor filter - not available in MatriksFilterParams
        
        if filters.is_completed is not None:
            if filters.is_completed:
                # Completed: has file (since no nomor_matriks field exists)
                matriks_query = matriks_query.where(
                    and_(
                        Matriks.file_dokumen_matriks.is_not(None),
                        Matriks.file_dokumen_matriks != ""
                    )
                )
            else:
                # Not completed: no file or empty file
                matriks_query = matriks_query.where(
                    or_(
                        Matriks.file_dokumen_matriks.is_(None),
                        Matriks.file_dokumen_matriks == ""
                    )
                )
        
        # Date range filters untuk created_at
        # if filters.created_from:
        #     matriks_query = matriks_query.where(Matriks.created_at >= filters.created_from)
        # if filters.created_to:
        #     matriks_query = matriks_query.where(Matriks.created_at <= filters.created_to)
        # if hasattr(filters, 'tanggal_evaluasi_from') and filters.tanggal_evaluasi_from:
        #     matriks_query = matriks_query.where(SuratTugas.tanggal_evaluasi_mulai >= filters.tanggal_evaluasi_from)
        # if hasattr(filters, 'tanggal_evaluasi_to') and filters.tanggal_evaluasi_to:
        #     matriks_query = matriks_query.where(SuratTugas.tanggal_evaluasi_selesai <= filters.tanggal_evaluasi_to)
        
        # 🔥 STEP 2: Count total (SAFE)
        count_query = select(func.count()).select_from(matriks_query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()
        
        # 🔥 STEP 3: Apply pagination dan ordering
        matriks_query = matriks_query.order_by(Matriks.created_at.desc())
        matriks_query = matriks_query.offset((filters.page - 1) * filters.size).limit(filters.size)
        
        # 🔥 STEP 4: Execute query - Fetch Matriks objects
        result = await self.session.execute(matriks_query)
        matriks_list = result.scalars().all()
        
        # 🔥 STEP 5: Manually fetch related data untuk setiap matriks
        enriched_results = []
        
        for matriks in matriks_list:
            # Fetch surat tugas manually
            st_query = select(SuratTugas).where(SuratTugas.id == matriks.surat_tugas_id)
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
            
            # Build matriks data (SAFE - akses langsung attribute dengan field yang benar)
            matriks_data = {
                'id': matriks.id,
                'surat_tugas_id': matriks.surat_tugas_id,
                'file_dokumen_matriks': matriks.file_dokumen_matriks,
                'temuan_rekomendasi': getattr(matriks, 'temuan_rekomendasi', None), 
                'created_at': matriks.created_at,
                'updated_at': matriks.updated_at,
                'created_by': matriks.created_by,
                'updated_by': matriks.updated_by
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
                'matriks': matriks_data,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total
    
    async def update(self, matriks_id: str, update_data: MatriksUpdate) -> Optional[Matriks]:
        """Update matriks."""
        matriks = await self.get_by_id(matriks_id)
        if not matriks:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(matriks, key, value)
        
        matriks.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(matriks)
        return matriks
    
    async def update_file_path(self, matriks_id: str, file_path: str) -> Optional[Matriks]:
        """Update file path - FIXED field name."""
        matriks = await self.get_by_id(matriks_id)
        if not matriks:
            return None
        
        matriks.file_dokumen_matriks = file_path
        matriks.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(matriks)
        return matriks

    async def update_temuan_rekomendasi(
        self, 
        matriks_id: str, 
        items: List[Dict[str, str]]
    ) -> Optional[Matriks]:
        """Update temuan-rekomendasi dengan REPLACE strategy."""
        
        matriks = await self.get_by_id(matriks_id)
        if not matriks:
            return None
        
        # REPLACE strategy - replace all old data with new data
        matriks.set_temuan_rekomendasi_items(items)
        matriks.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(matriks)
        return matriks
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics untuk matriks - SIMPLE VERSION with correct field names."""
        
        # Simple count query tanpa complex aggregations
        base_query = (
            select(Matriks)
            .join(SuratTugas, Matriks.surat_tugas_id == SuratTugas.id)
            .where(
                and_(
                    Matriks.deleted_at.is_(None),
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
        # Since model only has file_dokumen_matriks field, completion = has file
        return {
            'total': total or 0,
            'has_file': 0,  # Placeholder - would need separate query
            'completed': 0,  # Placeholder - would need separate query
            'completion_rate': 0.0
        }
    
    async def soft_delete(self, matriks_id: str) -> bool:
        """Soft delete matriks by ID."""
        from datetime import datetime
        
        matriks = await self.get_by_id(matriks_id)
        if not matriks:
            return False
        
        matriks.deleted_at = datetime.utcnow()
        matriks.updated_at = datetime.utcnow()
        # JANGAN COMMIT - biarkan transaction context yang handle
        return True
    
    async def delete_by_surat_tugas_id(self, surat_tugas_id: str) -> int:
        """Soft delete semua matriks untuk surat tugas tertentu."""
        query = (
            update(Matriks)
            .where(
                and_(
                    Matriks.surat_tugas_id == surat_tugas_id,
                    Matriks.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow())
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount
"""Safe Kuisioner repository - menghindari property object error."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func, update, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.kuisioner import Kuisioner
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.schemas.kuisioner import KuisionerCreate, KuisionerUpdate
from src.schemas.filters import KuisionerFilterParams


class KuisionerRepository:
    """Safe repository untuk operasi kuisioner - NO PROPERTY OBJECTS."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, kuisioner_data: KuisionerCreate) -> Kuisioner:
        """Create kuisioner baru."""
        kuisioner = Kuisioner(
            surat_tugas_id=kuisioner_data.surat_tugas_id
        )
        
        self.session.add(kuisioner)
        await self.session.commit()
        await self.session.refresh(kuisioner)
        return kuisioner
    
    async def get_by_id(self, kuisioner_id: str) -> Optional[Kuisioner]:
        """Get kuisioner by ID."""
        query = select(Kuisioner).where(
            and_(Kuisioner.id == kuisioner_id, Kuisioner.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[Kuisioner]:
        """Get kuisioner by surat tugas ID."""
        query = select(Kuisioner).where(
            and_(
                Kuisioner.surat_tugas_id == surat_tugas_id,
                Kuisioner.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(
        self,
        filters: KuisionerFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all kuisioner dengan enriched data - SAFE VERSION."""
        
        # 🔥 STEP 1: Fetch kuisioner dengan relationship loading (SAFE METHOD)
        kuisioner_query = (
            select(Kuisioner)
            .join(SuratTugas, Kuisioner.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
            .where(
                and_(
                    Kuisioner.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None)
                )
            )
        )
        
        # Role-based filtering
        if user_role == "PERWADAG" and user_id:
            kuisioner_query = kuisioner_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "INSPEKTORAT" and user_inspektorat:
            kuisioner_query = kuisioner_query.where(SuratTugas.inspektorat == user_inspektorat)
        
        # Apply filters - FIXED field names sesuai model
        if filters.search:
            search_term = f"%{filters.search}%"
            kuisioner_query = kuisioner_query.where(
                or_(
                    SuratTugas.no_surat.ilike(search_term),
                    SuratTugas.nama_perwadag.ilike(search_term),
                    User.nama.ilike(search_term)
                )
            )
        
        if filters.inspektorat:
            kuisioner_query = kuisioner_query.where(SuratTugas.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        if filters.user_perwadag_id:
            kuisioner_query = kuisioner_query.where(SuratTugas.user_perwadag_id == filters.user_perwadag_id)
        
        if filters.tahun_evaluasi:
            kuisioner_query = kuisioner_query.where(func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == filters.tahun_evaluasi)
        
        # Add surat_tugas_id filter if available
        if hasattr(filters, 'surat_tugas_id') and filters.surat_tugas_id:
            kuisioner_query = kuisioner_query.where(Kuisioner.surat_tugas_id == filters.surat_tugas_id)
        
        # FIXED: Use correct field name file_kuisioner (bukan file_dokumen atau nomor_kuisioner)
        if filters.has_file is not None:
            if filters.has_file:
                kuisioner_query = kuisioner_query.where(Kuisioner.file_kuisioner.is_not(None))
            else:
                kuisioner_query = kuisioner_query.where(Kuisioner.file_kuisioner.is_(None))
        
        # Note: Model Kuisioner tidak punya nomor_kuisioner field, hanya file_kuisioner
        # Jadi has_nomor filter tidak applicable
        
        if filters.is_completed is not None:
            if filters.is_completed:
                # Completed: has file only (since no nomor field)
                kuisioner_query = kuisioner_query.where(
                    and_(
                        Kuisioner.file_kuisioner.is_not(None),
                        Kuisioner.file_kuisioner != ""
                    )
                )
            else:
                # Not completed: no file or empty file
                kuisioner_query = kuisioner_query.where(
                    or_(
                        Kuisioner.file_kuisioner.is_(None),
                        Kuisioner.file_kuisioner == ""
                    )
                )
        
        # Date range filters
        if filters.created_from:
            kuisioner_query = kuisioner_query.where(Kuisioner.created_at >= filters.created_from)
        if filters.created_to:
            kuisioner_query = kuisioner_query.where(Kuisioner.created_at <= filters.created_to)
        
        # Add tanggal_evaluasi filters if available
        if hasattr(filters, 'tanggal_evaluasi_from') and filters.tanggal_evaluasi_from:
            kuisioner_query = kuisioner_query.where(SuratTugas.tanggal_evaluasi_mulai >= filters.tanggal_evaluasi_from)
        if hasattr(filters, 'tanggal_evaluasi_to') and filters.tanggal_evaluasi_to:
            kuisioner_query = kuisioner_query.where(SuratTugas.tanggal_evaluasi_selesai <= filters.tanggal_evaluasi_to)
        
        # 🔥 STEP 2: Count total (SAFE)
        count_query = select(func.count()).select_from(kuisioner_query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()
        
        # 🔥 STEP 3: Apply pagination dan ordering
        kuisioner_query = kuisioner_query.order_by(Kuisioner.created_at.desc())
        kuisioner_query = kuisioner_query.offset((filters.page - 1) * filters.size).limit(filters.size)
        
        # 🔥 STEP 4: Execute query - Fetch Kuisioner objects
        result = await self.session.execute(kuisioner_query)
        kuisioner_list = result.scalars().all()
        
        # 🔥 STEP 5: Manually fetch related data untuk setiap kuisioner
        enriched_results = []
        
        for kuisioner in kuisioner_list:
            # Fetch surat tugas manually
            st_query = select(SuratTugas).where(SuratTugas.id == kuisioner.surat_tugas_id)
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
            
            # Build kuisioner data (SAFE - akses langsung attribute)
            kuisioner_data = {
                'id': kuisioner.id,
                'surat_tugas_id': kuisioner.surat_tugas_id,
                'tanggal_kuisioner': kuisioner.tanggal_kuisioner,
                'file_kuisioner': kuisioner.file_kuisioner,
                'created_at': kuisioner.created_at,
                'updated_at': kuisioner.updated_at,
                'created_by': kuisioner.created_by,
                'updated_by': kuisioner.updated_by
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
                'kuisioner': kuisioner_data,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total
    
    async def update(self, kuisioner_id: str, update_data: KuisionerUpdate) -> Optional[Kuisioner]:
        """Update kuisioner."""
        kuisioner = await self.get_by_id(kuisioner_id)
        if not kuisioner:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(kuisioner, key, value)
        
        kuisioner.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(kuisioner)
        return kuisioner
    
    async def update_file_path(self, kuisioner_id: str, file_path: str) -> Optional[Kuisioner]:
        """Update file path - FIXED field name."""
        kuisioner = await self.get_by_id(kuisioner_id)
        if not kuisioner:
            return None
        
        kuisioner.file_kuisioner = file_path  # FIXED field name
        kuisioner.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(kuisioner)
        return kuisioner
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics untuk kuisioner - SIMPLE VERSION."""
        
        # Simple count query tanpa complex aggregations
        base_query = (
            select(Kuisioner)
            .join(SuratTugas, Kuisioner.surat_tugas_id == SuratTugas.id)
            .where(
                and_(
                    Kuisioner.deleted_at.is_(None),
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
        # Since model only has file_kuisioner field, completion = has file
        return {
            'total': total or 0,
            'has_file': 0,  # Placeholder
            'completed': 0,  # Placeholder
            'completion_rate': 0.0
        }
        
    async def soft_delete(self, kuisioner_id: str) -> bool:
        """Soft delete kuisioner by ID."""
        from datetime import datetime
        
        kuisioner = await self.get_by_id(kuisioner_id)
        if not kuisioner:
            return False
        
        kuisioner.deleted_at = datetime.utcnow()
        kuisioner.updated_at = datetime.utcnow()
        # JANGAN COMMIT - biarkan transaction context yang handle
        return True
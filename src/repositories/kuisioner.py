# ===== src/repositories/kuisioner.py =====
"""Repository untuk kuisioner."""

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, date
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.kuisioner import Kuisioner
from src.schemas.kuisioner import KuisionerCreate, KuisionerUpdate
from src.schemas.filters import KuisionerFilterParams


class KuisionerRepository:
    """Repository untuk operasi kuisioner."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, kuisioner_data: KuisionerCreate) -> Kuisioner:
        """Create kuisioner baru (auto-generated)."""
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
    
    async def update_file_path(self, kuisioner_id: str, file_path: str) -> Optional[Kuisioner]:
        """Update file path."""
        kuisioner = await self.get_by_id(kuisioner_id)
        if not kuisioner:
            return None
        
        kuisioner.file_kuisioner = file_path
        kuisioner.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(kuisioner)
        return kuisioner
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(Kuisioner)
            .where(
                and_(
                    Kuisioner.surat_tugas_id == surat_tugas_id,
                    Kuisioner.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount

async def get_all_filtered(
    self,
    filters: KuisionerFilterParams,
    user_role: str,
    user_inspektorat: Optional[str] = None,
    user_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Get all kuisioner dengan filtering dan JOIN ke surat tugas - LENGKAP IMPLEMENTATION."""
    
    # Build base query dengan JOIN
    query = (
        select(
            Kuisioner,
            SuratTugas.no_surat,
            SuratTugas.nama_perwadag,
            SuratTugas.inspektorat,
            SuratTugas.tanggal_evaluasi_mulai,
            SuratTugas.tanggal_evaluasi_selesai,
            User.nama.label('perwadag_nama')
        )
        .select_from(
            Kuisioner
            .join(SuratTugas, Kuisioner.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
        )
        .where(
            and_(
                Kuisioner.deleted_at.is_(None),
                SuratTugas.deleted_at.is_(None),
                User.deleted_at.is_(None)
            )
        )
    )
    
    # Apply role-based filtering
    if user_role == "PERWADAG":
        query = query.where(SuratTugas.user_perwadag_id == user_id)
    elif user_role == "INSPEKTORAT" and user_inspektorat:
        query = query.where(SuratTugas.inspektorat == user_inspektorat)
    # Admin dapat melihat semua
    
    # Apply filters
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.where(
            or_(
                SuratTugas.nama_perwadag.ilike(search_term),
                SuratTugas.no_surat.ilike(search_term),
                SuratTugas.inspektorat.ilike(search_term),
                User.nama.ilike(search_term)
            )
        )
    
    if filters.inspektorat:
        query = query.where(SuratTugas.inspektorat.ilike(f"%{filters.inspektorat}%"))
    
    if filters.user_perwadag_id:
        query = query.where(SuratTugas.user_perwadag_id == filters.user_perwadag_id)
    
    if filters.tahun_evaluasi:
        query = query.where(
            func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == filters.tahun_evaluasi
        )
    
    if filters.surat_tugas_id:
        query = query.where(Kuisioner.surat_tugas_id == filters.surat_tugas_id)
    
    # Status filters
    if filters.has_file is not None:
        if filters.has_file:
            query = query.where(
                and_(
                    Kuisioner.file_kuisioner.is_not(None),
                    Kuisioner.file_kuisioner != ""
                )
            )
        else:
            query = query.where(
                or_(
                    Kuisioner.file_kuisioner.is_(None),
                    Kuisioner.file_kuisioner == ""
                )
            )
    
    if filters.is_completed is not None:
        if filters.is_completed:
            query = query.where(
                and_(
                    Kuisioner.file_kuisioner.is_not(None),
                    Kuisioner.file_kuisioner != ""
                )
            )
        else:
            query = query.where(
                or_(
                    Kuisioner.file_kuisioner.is_(None),
                    Kuisioner.file_kuisioner == ""
                )
            )
    
    # Date range filters
    if filters.created_from:
        query = query.where(Kuisioner.created_at >= filters.created_from)
    
    if filters.created_to:
        query = query.where(Kuisioner.created_at <= filters.created_to)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await self.session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    offset = (filters.page - 1) * filters.size
    query = (
        query
        .offset(offset)
        .limit(filters.size)
        .order_by(Kuisioner.created_at.desc())
    )
    
    # Execute query
    result = await self.session.execute(query)
    rows = result.all()
    
    # Convert to list of dictionaries with enriched data
    enriched_results = []
    for row in rows:
        kuisioner = row[0]  # Kuisioner object
        surat_tugas_data = {
            'no_surat': row[1],
            'nama_perwadag': row[2],
            'inspektorat': row[3],
            'tanggal_evaluasi_mulai': row[4],
            'tanggal_evaluasi_selesai': row[5],
            'perwadag_nama': row[6],
            'tahun_evaluasi': row[4].year,
            'durasi_evaluasi': (row[5] - row[4]).days + 1
        }
        
        enriched_results.append({
            'kuisioner': kuisioner,
            'surat_tugas_data': surat_tugas_data
        })
    
    return enriched_results, total


async def get_statistics(
    self,
    user_role: str,
    user_inspektorat: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get statistics untuk kuisioner - LENGKAP IMPLEMENTATION."""
    
    # Base query untuk statistics
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
    if user_role == "PERWADAG":
        base_query = base_query.where(SuratTugas.user_perwadag_id == user_id)
    elif user_role == "INSPEKTORAT" and user_inspektorat:
        base_query = base_query.where(SuratTugas.inspektorat == user_inspektorat)
    
    # Total count
    total_query = select(func.count()).select_from(base_query.subquery())
    total_result = await self.session.execute(total_query)
    total_records = total_result.scalar() or 0
    
    # Completed count
    completed_query = select(func.count()).select_from(
        base_query.where(
            and_(
                Kuisioner.file_kuisioner.is_not(None),
                Kuisioner.file_kuisioner != ""
            )
        ).subquery()
    )
    completed_result = await self.session.execute(completed_query)
    completed_records = completed_result.scalar() or 0
    
    # Calculate completion rate
    completion_rate = (completed_records / total_records * 100) if total_records > 0 else 0
    
    return {
        "total_records": total_records,
        "completed_records": completed_records,
        "with_files": completed_records,
        "without_files": total_records - completed_records,
        "completion_rate": round(completion_rate, 2),
        "last_updated": datetime.utcnow()
    }


# ===== src/repositories/matriks.py =====
"""Repository untuk matriks."""

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, date
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.matriks import Matriks
from src.schemas.matriks import MatriksCreate, MatriksUpdate
from src.schemas.filters import MatriksFilterParams

class MatriksRepository:
    """Repository untuk operasi matriks."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, matriks_data: MatriksCreate) -> Matriks:
        """Create matriks baru (auto-generated)."""
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
    
    async def update_file_path(self, matriks_id: str, file_path: str) -> Optional[Matriks]:
        """Update file path."""
        matriks = await self.get_by_id(matriks_id)
        if not matriks:
            return None
        
        matriks.file_dokumen_matriks = file_path
        matriks.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(matriks)
        return matriks
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(Matriks)
            .where(
                and_(
                    Matriks.surat_tugas_id == surat_tugas_id,
                    Matriks.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount

    async def get_all_filtered(
        self,
        filters: MatriksFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all matriks dengan filtering dan JOIN ke surat tugas - LENGKAP IMPLEMENTATION."""
        
        # Build base query dengan JOIN
        query = (
            select(
                Matriks,
                SuratTugas.no_surat,
                SuratTugas.nama_perwadag,
                SuratTugas.inspektorat,
                SuratTugas.tanggal_evaluasi_mulai,
                SuratTugas.tanggal_evaluasi_selesai,
                User.nama.label('perwadag_nama')
            )
            .select_from(
                Matriks
                .join(SuratTugas, Matriks.surat_tugas_id == SuratTugas.id)
                .join(User, SuratTugas.user_perwadag_id == User.id)
            )
            .where(
                and_(
                    Matriks.deleted_at.is_(None),
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
            query = query.where(Matriks.surat_tugas_id == filters.surat_tugas_id)
        
        # Status filters
        if filters.has_file is not None:
            if filters.has_file:
                query = query.where(
                    and_(
                        Matriks.file_dokumen_matriks.is_not(None),
                        Matriks.file_dokumen_matriks != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        Matriks.file_dokumen_matriks.is_(None),
                        Matriks.file_dokumen_matriks == ""
                    )
                )
        
        if filters.is_completed is not None:
            if filters.is_completed:
                query = query.where(
                    and_(
                        Matriks.file_dokumen_matriks.is_not(None),
                        Matriks.file_dokumen_matriks != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        Matriks.file_dokumen_matriks.is_(None),
                        Matriks.file_dokumen_matriks == ""
                    )
                )
        
        # Date range filters
        if filters.created_from:
            query = query.where(Matriks.created_at >= filters.created_from)
        
        if filters.created_to:
            query = query.where(Matriks.created_at <= filters.created_to)
        
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
            .order_by(Matriks.created_at.desc())
        )
        
        # Execute query
        result = await self.session.execute(query)
        rows = result.all()
        
        # Convert to list of dictionaries with enriched data
        enriched_results = []
        for row in rows:
            matriks = row[0]  # Matriks object
            surat_tugas_data = {
                'no_surat': row[1],
                'nama_perwadag': row[2],
                'inspektorat': row[3],
                'tanggal_evaluasi_mulai': row[4],
                'tanggal_evaluasi_selesai': row[5],
                'perwadag_nama': row[6],
                'tahun_evaluasi': row[4].year,
                'durasi_evaluasi': (row[5] - row[4]).days + 1,
                'evaluation_status': _get_evaluation_status(row[4], row[5]),
                'is_evaluation_active': _is_evaluation_active(row[4], row[5])
            }
            
            enriched_results.append({
                'matriks': matriks,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total


    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics untuk matriks - LENGKAP IMPLEMENTATION."""
        
        # Base query untuk statistics
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
                    Matriks.file_dokumen_matriks.is_not(None),
                    Matriks.file_dokumen_matriks != ""
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


    # TAMBAHKAN utility functions ini ke bagian bawah file:

    def _get_evaluation_status(tanggal_mulai: date, tanggal_selesai: date) -> str:
        """Helper untuk menentukan status evaluasi."""
        today = date.today()
        
        if tanggal_mulai > today:
            return "upcoming"
        elif tanggal_mulai <= today <= tanggal_selesai:
            return "active"
        else:
            return "completed"


    def _is_evaluation_active(tanggal_mulai: date, tanggal_selesai: date) -> bool:
        """Helper untuk check apakah evaluasi sedang aktif."""
        today = date.today()
        return tanggal_mulai <= today <= tanggal_selesai
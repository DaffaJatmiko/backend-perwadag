"""Repository untuk laporan hasil."""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy import select, and_, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.laporan_hasil import LaporanHasil
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.schemas.laporan_hasil import LaporanHasilCreate, LaporanHasilUpdate
from src.schemas.filters import LaporanHasilFilterParams


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


class LaporanHasilRepository:
    """Repository untuk operasi laporan hasil."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, laporan_hasil_data: LaporanHasilCreate) -> LaporanHasil:
        """Create laporan hasil baru (auto-generated)."""
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
        """Update file path."""
        laporan_hasil = await self.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            return None
        
        laporan_hasil.file_laporan_hasil = file_path
        laporan_hasil.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(LaporanHasil)
            .where(
                and_(
                    LaporanHasil.surat_tugas_id == surat_tugas_id,
                    LaporanHasil.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount

    async def get_all_filtered(
        self,
        filters: LaporanHasilFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all laporan hasil dengan filtering dan JOIN ke surat tugas."""
        
        # Build base query dengan JOIN
        query = (
            select(
                LaporanHasil,
                SuratTugas.no_surat,
                SuratTugas.nama_perwadag,
                SuratTugas.inspektorat,
                SuratTugas.tanggal_evaluasi_mulai,
                SuratTugas.tanggal_evaluasi_selesai,
                User.nama.label('perwadag_nama')
            )
            .select_from(LaporanHasil)
            .join(SuratTugas, LaporanHasil.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
            .where(
                and_(
                    LaporanHasil.deleted_at.is_(None),
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
                    LaporanHasil.nomor_laporan.ilike(search_term),
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
            query = query.where(LaporanHasil.surat_tugas_id == filters.surat_tugas_id)
        
        if filters.nomor_laporan:
            query = query.where(LaporanHasil.nomor_laporan.ilike(f"%{filters.nomor_laporan}%"))
        
        # Status filters
        if filters.has_file is not None:
            if filters.has_file:
                query = query.where(
                    and_(
                        LaporanHasil.file_laporan_hasil.is_not(None),
                        LaporanHasil.file_laporan_hasil != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        LaporanHasil.file_laporan_hasil.is_(None),
                        LaporanHasil.file_laporan_hasil == ""
                    )
                )
        
        if filters.has_nomor is not None:
            if filters.has_nomor:
                query = query.where(
                    and_(
                        LaporanHasil.nomor_laporan.is_not(None),
                        LaporanHasil.nomor_laporan != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        LaporanHasil.nomor_laporan.is_(None),
                        LaporanHasil.nomor_laporan == ""
                    )
                )
        
        if filters.has_tanggal is not None:
            if filters.has_tanggal:
                query = query.where(LaporanHasil.tanggal_laporan.is_not(None))
            else:
                query = query.where(LaporanHasil.tanggal_laporan.is_(None))
        
        if filters.is_completed is not None:
            # Completion = has nomor, tanggal, and file
            if filters.is_completed:
                query = query.where(
                    and_(
                        LaporanHasil.nomor_laporan.is_not(None),
                        LaporanHasil.nomor_laporan != "",
                        LaporanHasil.tanggal_laporan.is_not(None),
                        LaporanHasil.file_laporan_hasil.is_not(None),
                        LaporanHasil.file_laporan_hasil != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        LaporanHasil.nomor_laporan.is_(None),
                        LaporanHasil.nomor_laporan == "",
                        LaporanHasil.tanggal_laporan.is_(None),
                        LaporanHasil.file_laporan_hasil.is_(None),
                        LaporanHasil.file_laporan_hasil == ""
                    )
                )
        
        # Date range filters
        if filters.tanggal_laporan_from:
            query = query.where(LaporanHasil.tanggal_laporan >= filters.tanggal_laporan_from)
        
        if filters.tanggal_laporan_to:
            query = query.where(LaporanHasil.tanggal_laporan <= filters.tanggal_laporan_to)
        
        if filters.created_from:
            query = query.where(LaporanHasil.created_at >= filters.created_from)
        
        if filters.created_to:
            query = query.where(LaporanHasil.created_at <= filters.created_to)
        
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
            .order_by(LaporanHasil.created_at.desc())
        )
        
        # Execute query
        result = await self.session.execute(query)
        rows = result.all()
        
        # Convert to list of dictionaries with enriched data
        enriched_results = []
        for row in rows:
            laporan_hasil = row[0]  # LaporanHasil object
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
                'laporan_hasil': laporan_hasil,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total

    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics untuk laporan hasil."""
        
        # Base query untuk statistics
        base_query = (
            select(LaporanHasil)
            .join(SuratTugas, LaporanHasil.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
            .where(
                and_(
                    LaporanHasil.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None),
                    User.deleted_at.is_(None)
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
        
        # Completed count (has nomor, tanggal, and file)
        completed_query = select(func.count()).select_from(
            base_query.where(
                and_(
                    LaporanHasil.nomor_laporan.is_not(None),
                    LaporanHasil.nomor_laporan != "",
                    LaporanHasil.tanggal_laporan.is_not(None),
                    LaporanHasil.file_laporan_hasil.is_not(None),
                    LaporanHasil.file_laporan_hasil != ""
                )
            ).subquery()
        )
        completed_result = await self.session.execute(completed_query)
        completed_records = completed_result.scalar() or 0
        
        # With files count
        files_query = select(func.count()).select_from(
            base_query.where(
                and_(
                    LaporanHasil.file_laporan_hasil.is_not(None),
                    LaporanHasil.file_laporan_hasil != ""
                )
            ).subquery()
        )
        files_result = await self.session.execute(files_query)
        with_files = files_result.scalar() or 0
        
        # Overdue count (evaluation completed but no laporan)
        today = date.today()
        overdue_query = (
            select(func.count())
            .select_from(
                base_query.where(
                    and_(
                        SuratTugas.tanggal_evaluasi_selesai < today,
                        or_(
                            LaporanHasil.nomor_laporan.is_(None),
                            LaporanHasil.nomor_laporan == "",
                            LaporanHasil.tanggal_laporan.is_(None),
                            LaporanHasil.file_laporan_hasil.is_(None),
                            LaporanHasil.file_laporan_hasil == ""
                        )
                    )
                ).subquery()
            )
        )
        overdue_result = await self.session.execute(overdue_query)
        overdue_records = overdue_result.scalar() or 0
        
        # Calculate completion rate
        completion_rate = (completed_records / total_records * 100) if total_records > 0 else 0
        
        return {
            "total_records": total_records,
            "completed_records": completed_records,
            "with_files": with_files,
            "without_files": total_records - with_files,
            "overdue_records": overdue_records,
            "completion_rate": round(completion_rate, 2),
            "last_updated": datetime.utcnow()
        }
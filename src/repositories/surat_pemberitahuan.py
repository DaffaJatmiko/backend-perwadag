"""Repository untuk surat pemberitahuan."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.surat_pemberitahuan import SuratPemberitahuan
from src.models.surat_tugas import SuratTugas  # ADD THIS IMPORT
from src.models.user import User  # ADD THIS IMPORT
from src.schemas.surat_pemberitahuan import SuratPemberitahuanCreate, SuratPemberitahuanUpdate
from src.schemas.filters import SuratPemberitahuanFilterParams


class SuratPemberitahuanRepository:
    """Repository untuk operasi surat pemberitahuan."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, surat_pemberitahuan_data: SuratPemberitahuanCreate) -> SuratPemberitahuan:
        """Create surat pemberitahuan baru (auto-generated)."""
        surat_pemberitahuan = SuratPemberitahuan(
            surat_tugas_id=surat_pemberitahuan_data.surat_tugas_id
        )
        
        self.session.add(surat_pemberitahuan)
        await self.session.commit()
        await self.session.refresh(surat_pemberitahuan)
        return surat_pemberitahuan
    
    async def get_by_id(self, surat_pemberitahuan_id: str) -> Optional[SuratPemberitahuan]:
        """Get surat pemberitahuan by ID."""
        query = select(SuratPemberitahuan).where(
            and_(SuratPemberitahuan.id == surat_pemberitahuan_id, SuratPemberitahuan.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[SuratPemberitahuan]:
        """Get surat pemberitahuan by surat tugas ID."""
        query = select(SuratPemberitahuan).where(
            and_(
                SuratPemberitahuan.surat_tugas_id == surat_tugas_id,
                SuratPemberitahuan.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, surat_pemberitahuan_id: str, update_data: SuratPemberitahuanUpdate) -> Optional[SuratPemberitahuan]:
        """Update surat pemberitahuan."""
        surat_pemberitahuan = await self.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(surat_pemberitahuan, key, value)
        
        surat_pemberitahuan.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(surat_pemberitahuan)
        return surat_pemberitahuan
    
    async def update_file_path(self, surat_pemberitahuan_id: str, file_path: str) -> Optional[SuratPemberitahuan]:
        """Update file path."""
        surat_pemberitahuan = await self.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            return None
        
        surat_pemberitahuan.file_dokumen = file_path
        surat_pemberitahuan.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(surat_pemberitahuan)
        return surat_pemberitahuan
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(SuratPemberitahuan)
            .where(
                and_(
                    SuratPemberitahuan.surat_tugas_id == surat_tugas_id,
                    SuratPemberitahuan.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount

    async def soft_delete(self, surat_pemberitahuan_id: str) -> bool:
        """Soft delete surat pemberitahuan by ID."""
        from datetime import datetime
        
        surat_pemberitahuan = await self.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            return False
        
        surat_pemberitahuan.deleted_at = datetime.utcnow()
        surat_pemberitahuan.updated_at = datetime.utcnow()
        # JANGAN COMMIT - biarkan transaction context yang handle
        return True

    async def get_all_filtered(
        self,
        filters: SuratPemberitahuanFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all surat pemberitahuan dengan filtering dan JOIN ke surat tugas."""
        
        # Build base query dengan JOIN
        query = (
            select(
                SuratPemberitahuan,
                SuratTugas.id.label('surat_tugas_id'),
                SuratTugas.no_surat,
                SuratTugas.nama_perwadag,
                SuratTugas.inspektorat,
                SuratTugas.tanggal_evaluasi_mulai,
                SuratTugas.tanggal_evaluasi_selesai,
                SuratTugas.user_perwadag_id,
                User.nama.label('perwadag_nama')
            )
            .select_from(SuratPemberitahuan)
            .join(SuratTugas, SuratPemberitahuan.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
            .where(
                and_(
                    SuratPemberitahuan.deleted_at.is_(None),
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
            query = query.where(SuratPemberitahuan.surat_tugas_id == filters.surat_tugas_id)
        
        # Status filters
        if filters.has_file is not None:
            if filters.has_file:
                query = query.where(
                    and_(
                        SuratPemberitahuan.file_dokumen.is_not(None),
                        SuratPemberitahuan.file_dokumen != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        SuratPemberitahuan.file_dokumen.is_(None),
                        SuratPemberitahuan.file_dokumen == ""
                    )
                )
        
        if filters.has_date is not None:
            if filters.has_date:
                query = query.where(SuratPemberitahuan.tanggal_surat_pemberitahuan.is_not(None))
            else:
                query = query.where(SuratPemberitahuan.tanggal_surat_pemberitahuan.is_(None))
        
        if filters.is_completed is not None:
            # Completion = has both date and file
            if filters.is_completed:
                query = query.where(
                    and_(
                        SuratPemberitahuan.tanggal_surat_pemberitahuan.is_not(None),
                        SuratPemberitahuan.file_dokumen.is_not(None),
                        SuratPemberitahuan.file_dokumen != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        SuratPemberitahuan.tanggal_surat_pemberitahuan.is_(None),
                        SuratPemberitahuan.file_dokumen.is_(None),
                        SuratPemberitahuan.file_dokumen == ""
                    )
                )
        
        # Date range filters
        # if filters.tanggal_from:
        #     query = query.where(SuratPemberitahuan.tanggal_surat_pemberitahuan >= filters.tanggal_from)
        
        # if filters.tanggal_to:
        #     query = query.where(SuratPemberitahuan.tanggal_surat_pemberitahuan <= filters.tanggal_to)
        
        # if filters.created_from:
        #     query = query.where(SuratPemberitahuan.created_at >= filters.created_from)
        
        # if filters.created_to:
        #     query = query.where(SuratPemberitahuan.created_at <= filters.created_to)
        
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
            .order_by(SuratPemberitahuan.created_at.desc())
        )
        
        # Execute query
        result = await self.session.execute(query)
        rows = result.all()
        
        # Convert to list of dictionaries with enriched data
        enriched_results = []
        for row in rows:
            surat_pemberitahuan = row[0]  # SuratPemberitahuan object
            
            # Calculate derived fields
            tanggal_mulai = row[5]  # tanggal_evaluasi_mulai
            tanggal_selesai = row[6]  # tanggal_evaluasi_selesai
            
            # Calculate tahun_evaluasi
            tahun_evaluasi = tanggal_mulai.year if tanggal_mulai else None
            
            # Calculate durasi_evaluasi
            durasi_evaluasi = None
            if tanggal_mulai and tanggal_selesai:
                durasi_evaluasi = (tanggal_selesai - tanggal_mulai).days + 1
            
            # Calculate evaluation_status and is_evaluation_active
            from datetime import datetime
            current_date = datetime.now().date()
            evaluation_status = "PENDING"
            is_evaluation_active = False
            
            if tanggal_mulai and tanggal_selesai:
                if current_date < tanggal_mulai:
                    evaluation_status = "PENDING"
                elif tanggal_mulai <= current_date <= tanggal_selesai:
                    evaluation_status = "ACTIVE"
                    is_evaluation_active = True
                else:
                    evaluation_status = "COMPLETED"
            
            surat_tugas_data = {
                'id': row[1],  # surat_tugas_id
                'no_surat': row[2],
                'nama_perwadag': row[3],
                'inspektorat': row[4],
                'tanggal_evaluasi_mulai': tanggal_mulai,
                'tanggal_evaluasi_selesai': tanggal_selesai,
                'user_perwadag_id': row[7],
                'perwadag_nama': row[8],
                'tahun_evaluasi': tahun_evaluasi,
                'durasi_evaluasi': durasi_evaluasi,
                'evaluation_status': evaluation_status,
                'is_evaluation_active': is_evaluation_active
            }
            
            enriched_results.append({
                'surat_pemberitahuan': surat_pemberitahuan,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics untuk surat pemberitahuan."""
        
        # Base query untuk statistics
        base_query = (
            select(SuratPemberitahuan)
            .join(SuratTugas, SuratPemberitahuan.surat_tugas_id == SuratTugas.id)
            .where(
                and_(
                    SuratPemberitahuan.deleted_at.is_(None),
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
                    SuratPemberitahuan.tanggal_surat_pemberitahuan.is_not(None),
                    SuratPemberitahuan.file_dokumen.is_not(None),
                    SuratPemberitahuan.file_dokumen != ""
                )
            ).subquery()
        )
        completed_result = await self.session.execute(completed_query)
        completed_records = completed_result.scalar() or 0
        
        # With files count
        files_query = select(func.count()).select_from(
            base_query.where(
                and_(
                    SuratPemberitahuan.file_dokumen.is_not(None),
                    SuratPemberitahuan.file_dokumen != ""
                )
            ).subquery()
        )
        files_result = await self.session.execute(files_query)
        with_files = files_result.scalar() or 0
        
        # Calculate completion rate
        completion_rate = (completed_records / total_records * 100) if total_records > 0 else 0
        
        return {
            "total_records": total_records,
            "completed_records": completed_records,
            "with_files": with_files,
            "without_files": total_records - with_files,
            "completion_rate": round(completion_rate, 2),
            "last_updated": datetime.utcnow()
        }
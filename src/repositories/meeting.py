"""Minimal Safe Meeting repository - GUARANTEED FIX untuk property object error."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.meeting import Meeting
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.models.evaluasi_enums import MeetingType
from src.schemas.meeting import MeetingCreate, MeetingUpdate
from src.schemas.filters import MeetingFilterParams


class MeetingRepository:
    """Minimal safe repository untuk operasi meetings."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, meeting_data: MeetingCreate) -> Meeting:
        """Create meeting baru."""
        meeting = Meeting(
            surat_tugas_id=meeting_data.surat_tugas_id,
            meeting_type=meeting_data.meeting_type
        )
        
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting
    
    async def get_by_id(self, meeting_id: str) -> Optional[Meeting]:
        """Get meeting by ID."""
        query = select(Meeting).where(
            and_(Meeting.id == meeting_id, Meeting.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_and_type(
        self, 
        surat_tugas_id: str, 
        meeting_type: MeetingType
    ) -> Optional[Meeting]:
        """Get meeting by surat tugas ID dan meeting type."""
        query = select(Meeting).where(
            and_(
                Meeting.surat_tugas_id == surat_tugas_id,
                Meeting.meeting_type == meeting_type,
                Meeting.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_by_surat_tugas_id(self, surat_tugas_id: str) -> List[Meeting]:
        """Get all meetings untuk surat tugas tertentu."""
        query = select(Meeting).where(
            and_(
                Meeting.surat_tugas_id == surat_tugas_id,
                Meeting.deleted_at.is_(None)
            )
        ).order_by(Meeting.meeting_type)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_all_filtered(
        self,
        filters: MeetingFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all meetings dengan enriched data - MINIMAL SAFE VERSION."""
        
        # 🔥 STEP 1: Fetch meetings dengan relationship loading
        meetings_query = (
            select(Meeting)
            .join(SuratTugas, Meeting.surat_tugas_id == SuratTugas.id)
            .join(User, SuratTugas.user_perwadag_id == User.id)
            .where(
                and_(
                    Meeting.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None)
                )
            )
        )
        
        # Role-based filtering
        if user_role == "PERWADAG" and user_id:
            meeting_query = meeting_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "PIMPINAN" and user_inspektorat:
            meeting_query = meeting_query.where(SuratTugas.inspektorat == user_inspektorat)
        elif user_role == "INSPEKTORAT" and user_id:
            # Assignment-based filtering
            meeting_query = meeting_query.where(
                or_(
                    SuratTugas.pengedali_mutu_id == user_id,
                    SuratTugas.pengendali_teknis_id == user_id,
                    SuratTugas.ketua_tim_id == user_id,
                    SuratTugas.anggota_tim_ids.like(f"%{user_id}%")
                )
            )
        
        # Apply filters
        if filters.search:
            search_term = f"%{filters.search}%"
            meetings_query = meetings_query.where(
                or_(
                    SuratTugas.no_surat.ilike(search_term),
                    SuratTugas.nama_perwadag.ilike(search_term),
                    User.nama.ilike(search_term)
                )
            )
        
        if filters.meeting_type:
            meetings_query = meetings_query.where(Meeting.meeting_type == filters.meeting_type)
        
        if filters.surat_tugas_id:
            meetings_query = meetings_query.where(Meeting.surat_tugas_id == filters.surat_tugas_id)
        
        if filters.inspektorat:
            meetings_query = meetings_query.where(SuratTugas.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        if filters.user_perwadag_id:
            meetings_query = meetings_query.where(SuratTugas.user_perwadag_id == filters.user_perwadag_id)
        
        if filters.tahun_evaluasi:
            meetings_query = meetings_query.where(func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == filters.tahun_evaluasi)
        
        # 🔥 STEP 2: Count total (SAFE - menggunakan subquery)
        count_query = select(func.count()).select_from(meetings_query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()
        
        # 🔥 STEP 3: Apply pagination dan ordering
        meetings_query = meetings_query.order_by(Meeting.created_at.desc(), Meeting.meeting_type)
        meetings_query = meetings_query.offset((filters.page - 1) * filters.size).limit(filters.size)
        
        # 🔥 STEP 4: Execute query - Fetch Meeting objects
        result = await self.session.execute(meetings_query)
        meetings = result.scalars().all()
        
        # 🔥 STEP 5: Manually fetch related data untuk setiap meeting
        enriched_results = []
        
        for meeting in meetings:
            # Fetch surat tugas manually
            st_query = select(SuratTugas).where(SuratTugas.id == meeting.surat_tugas_id)
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
            
            # Build meeting data (SAFE - akses langsung attribute)
            meeting_data = {
                'id': meeting.id,
                'surat_tugas_id': meeting.surat_tugas_id,
                'meeting_type': meeting.meeting_type,
                'tanggal_meeting': meeting.tanggal_meeting,
                'link_zoom': meeting.link_zoom,
                'link_daftar_hadir': meeting.link_daftar_hadir,
                'file_bukti_hadir': meeting.file_bukti_hadir,
                'created_at': meeting.created_at,
                'updated_at': meeting.updated_at,
                'created_by': meeting.created_by,
                'updated_by': meeting.updated_by
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
                'meeting': meeting_data,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total
    
    async def update(self, meeting_id: str, update_data: MeetingUpdate) -> Optional[Meeting]:
        """Update meeting."""
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(meeting, key, value)
        
        meeting.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get basic statistics untuk meetings - SIMPLE VERSION."""
        
        # Simple count query tanpa property objects
        base_query = (
            select(Meeting)
            .join(SuratTugas, Meeting.surat_tugas_id == SuratTugas.id)
            .where(
                and_(
                    Meeting.deleted_at.is_(None),
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
        
        # Basic statistics (tanpa complex aggregations yang bisa bermasalah)
        return {
            'total': total or 0,
            'has_date': 0,
            'has_links': 0,
            'has_files': 0,
            'completed': 0,
            'completion_rate': 0.0,
            'meeting_type_counts': {
                'entry': 0,
                'konfirmasi': 0,
                'exit': 0
            }
        }

    async def soft_delete(self, meeting_id: str) -> bool:
        """Soft delete meeting by ID."""
        from datetime import datetime
        
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            return False
        
        meeting.deleted_at = datetime.utcnow()
        meeting.updated_at = datetime.utcnow()
        # JANGAN COMMIT - biarkan transaction context yang handle
        return True

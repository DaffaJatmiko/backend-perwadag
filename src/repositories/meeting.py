"""Repository untuk meetings."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.meeting import Meeting
from src.models.evaluasi_enums import MeetingType
from src.schemas.meeting import MeetingCreate, MeetingUpdate
from src.schemas.filters import MeetingFilterParams


class MeetingRepository:
    """Repository untuk operasi meetings."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ===== CREATE OPERATIONS =====
    
    async def create(self, meeting_data: MeetingCreate) -> Meeting:
        """Create meeting baru (untuk auto-generate)."""
        meeting = Meeting(
            surat_tugas_id=meeting_data.surat_tugas_id,
            meeting_type=meeting_data.meeting_type
            # Semua field lain akan None/empty sampai di-update
        )
        
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting
    
    async def create_all_meetings_for_surat_tugas(self, surat_tugas_id: str) -> List[Meeting]:
        """Create semua 3 meetings untuk surat tugas baru."""
        meetings = []
        
        for meeting_type in [MeetingType.ENTRY, MeetingType.KONFIRMASI, MeetingType.EXIT]:
            meeting = Meeting(
                surat_tugas_id=surat_tugas_id,
                meeting_type=meeting_type
            )
            meetings.append(meeting)
            self.session.add(meeting)
        
        await self.session.commit()
        
        # Refresh all meetings
        for meeting in meetings:
            await self.session.refresh(meeting)
        
        return meetings
    
    # ===== READ OPERATIONS =====
    
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
        """Get meeting by surat tugas ID dan type."""
        query = select(Meeting).where(
            and_(
                Meeting.surat_tugas_id == surat_tugas_id,
                Meeting.meeting_type == meeting_type,
                Meeting.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_by_surat_tugas(self, surat_tugas_id: str) -> List[Meeting]:
        """Get all meetings untuk surat tugas tertentu."""
        query = select(Meeting).where(
            and_(
                Meeting.surat_tugas_id == surat_tugas_id,
                Meeting.deleted_at.is_(None)
            )
        ).order_by(Meeting.meeting_type)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_all_filtered(
        self,
        filters: MeetingFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all meetings dengan filtering dan JOIN ke surat tugas."""
        
        # Build base query dengan JOIN
        query = (
            select(
                Meeting,
                SuratTugas.no_surat,
                SuratTugas.nama_perwadag,
                SuratTugas.inspektorat,
                SuratTugas.tanggal_evaluasi_mulai,
                SuratTugas.tanggal_evaluasi_selesai,
                User.nama.label('perwadag_nama')
            )
            .select_from(
                Meeting
                .join(SuratTugas, Meeting.surat_tugas_id == SuratTugas.id)
                .join(User, SuratTugas.user_perwadag_id == User.id)
            )
            .where(
                and_(
                    Meeting.deleted_at.is_(None),
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
        
        # Apply filters
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    SuratTugas.nama_perwadag.ilike(search_term),
                    SuratTugas.no_surat.ilike(search_term),
                    SuratTugas.inspektorat.ilike(search_term),
                    Meeting.link_zoom.ilike(search_term),
                    Meeting.link_daftar_hadir.ilike(search_term)
                )
            )
        
        if filters.surat_tugas_id:
            query = query.where(Meeting.surat_tugas_id == filters.surat_tugas_id)
        
        if filters.meeting_type:
            query = query.where(Meeting.meeting_type == filters.meeting_type)
        
        if filters.meeting_types:
            query = query.where(Meeting.meeting_type.in_(filters.meeting_types))
        
        if filters.inspektorat:
            query = query.where(SuratTugas.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        if filters.user_perwadag_id:
            query = query.where(SuratTugas.user_perwadag_id == filters.user_perwadag_id)
        
        if filters.tahun_evaluasi:
            query = query.where(
                func.extract('year', SuratTugas.tanggal_evaluasi_mulai) == filters.tahun_evaluasi
            )
        
        # Meeting-specific filters
        if filters.has_tanggal is not None:
            if filters.has_tanggal:
                query = query.where(Meeting.tanggal_meeting.is_not(None))
            else:
                query = query.where(Meeting.tanggal_meeting.is_(None))
        
        if filters.has_zoom_link is not None:
            if filters.has_zoom_link:
                query = query.where(
                    and_(
                        Meeting.link_zoom.is_not(None),
                        Meeting.link_zoom != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        Meeting.link_zoom.is_(None),
                        Meeting.link_zoom == ""
                    )
                )
        
        if filters.has_daftar_hadir_link is not None:
            if filters.has_daftar_hadir_link:
                query = query.where(
                    and_(
                        Meeting.link_daftar_hadir.is_not(None),
                        Meeting.link_daftar_hadir != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        Meeting.link_daftar_hadir.is_(None),
                        Meeting.link_daftar_hadir == ""
                    )
                )
        
        if filters.has_file is not None:
            if filters.has_file:
                query = query.where(
                    and_(
                        Meeting.file_bukti_hadir.is_not(None),
                        func.json_length(Meeting.file_bukti_hadir) > 0
                    )
                )
            else:
                query = query.where(
                    or_(
                        Meeting.file_bukti_hadir.is_(None),
                        func.json_length(Meeting.file_bukti_hadir) == 0
                    )
                )
        
        # File count filters
        if filters.file_count_min is not None:
            query = query.where(func.json_length(Meeting.file_bukti_hadir) >= filters.file_count_min)
        
        if filters.file_count_max is not None:
            query = query.where(func.json_length(Meeting.file_bukti_hadir) <= filters.file_count_max)
        
        # Date filters
        if filters.tanggal_meeting_from:
            query = query.where(Meeting.tanggal_meeting >= filters.tanggal_meeting_from)
        
        if filters.tanggal_meeting_to:
            query = query.where(Meeting.tanggal_meeting <= filters.tanggal_meeting_to)
        
        # Progress filters
        if filters.progress_min is not None or filters.progress_max is not None:
            # This would require calculating progress percentage in SQL
            # For now, we'll apply this filter in the service layer
            pass
        
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
            .order_by(Meeting.meeting_type, Meeting.created_at.desc())
        )
        
        # Execute query
        result = await self.session.execute(query)
        rows = result.all()
        
        # Convert to enriched results
        enriched_results = []
        for row in rows:
            meeting = row[0]
            surat_tugas_data = {
                'no_surat': row[1],
                'nama_perwadag': row[2],
                'inspektorat': row[3],
                'tanggal_evaluasi_mulai': row[4],
                'tanggal_evaluasi_selesai': row[5],
                'perwadag_nama': row[6]
            }
            
            enriched_results.append({
                'meeting': meeting,
                'surat_tugas_data': surat_tugas_data
            })
        
        return enriched_results, total
    
    # ===== UPDATE OPERATIONS =====
    
    async def update(self, meeting_id: str, meeting_data: MeetingUpdate) -> Optional[Meeting]:
        """Update meeting."""
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            return None
        
        # Update fields
        update_data = meeting_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(meeting, key, value)
        
        meeting.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting
    
    async def add_files(
        self, 
        meeting_id: str, 
        file_infos: List[Dict[str, Any]]
    ) -> Optional[Meeting]:
        """Add multiple files to meeting."""
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            return None
        
        # Initialize file_bukti_hadir if None
        if meeting.file_bukti_hadir is None:
            meeting.file_bukti_hadir = []
        
        # Add new files
        meeting.file_bukti_hadir.extend(file_infos)
        meeting.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting
    
    async def remove_file(self, meeting_id: str, filename: str) -> Optional[Meeting]:
        """Remove specific file from meeting."""
        meeting = await self.get_by_id(meeting_id)
        if not meeting or not meeting.file_bukti_hadir:
            return None
        
        # Remove file by filename
        original_length = len(meeting.file_bukti_hadir)
        meeting.file_bukti_hadir = [
            file_info for file_info in meeting.file_bukti_hadir
            if file_info.get('filename') != filename
        ]
        
        if len(meeting.file_bukti_hadir) < original_length:
            meeting.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(meeting)
        
        return meeting
    
    async def clear_all_files(self, meeting_id: str) -> Optional[Meeting]:
        """Clear all files from meeting."""
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            return None
        
        meeting.file_bukti_hadir = []
        meeting.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting
    
    # ===== DELETE OPERATIONS =====
    
    async def soft_delete(self, meeting_id: str) -> Optional[Meeting]:
        """Soft delete meeting."""
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            return None
        
        meeting.deleted_at = datetime.utcnow()
        meeting.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return meeting
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete all meetings untuk surat tugas tertentu."""
        query = (
            update(Meeting)
            .where(
                and_(
                    Meeting.surat_tugas_id == surat_tugas_id,
                    Meeting.deleted_at.is_(None)
                )
            )
            .values(
                deleted_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount
    
    async def hard_delete(self, meeting_id: str) -> bool:
        """Hard delete meeting."""
        query = delete(Meeting).where(Meeting.id == meeting_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    # ===== STATISTICS =====
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistik meetings berdasarkan role."""
        
        from src.models.surat_tugas import SuratTugas
        
        # Base query berdasarkan role
        base_query = select(Meeting).join(SuratTugas).where(
            and_(
                Meeting.deleted_at.is_(None),
                SuratTugas.deleted_at.is_(None)
            )
        )
        
        if user_role == "PERWADAG":
            base_query = base_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "INSPEKTORAT" and user_inspektorat:
            base_query = base_query.where(SuratTugas.inspektorat == user_inspektorat)
        
        # Total meetings
        total_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(total_query)
        total_meetings = total_result.scalar() or 0
        
        # Completed meetings (yang ada tanggal)
        completed_query = select(func.count()).select_from(
            base_query.where(Meeting.tanggal_meeting.is_not(None)).subquery()
        )
        completed_result = await self.session.execute(completed_query)
        completed_meetings = completed_result.scalar() or 0
        
        # Meetings with files
        files_query = select(func.count()).select_from(
            base_query.where(
                and_(
                    Meeting.file_bukti_hadir.is_not(None),
                    func.json_length(Meeting.file_bukti_hadir) > 0
                )
            ).subquery()
        )
        files_result = await self.session.execute(files_query)
        meetings_with_files = files_result.scalar() or 0
        
        # Meetings with zoom
        zoom_query = select(func.count()).select_from(
            base_query.where(
                and_(
                    Meeting.link_zoom.is_not(None),
                    Meeting.link_zoom != ""
                )
            ).subquery()
        )
        zoom_result = await self.session.execute(zoom_query)
        meetings_with_zoom = zoom_result.scalar() or 0
        
        # Count by type
        type_query = (
            select(Meeting.meeting_type, func.count().label('count'))
            .select_from(base_query.subquery())
            .group_by(Meeting.meeting_type)
        )
        type_result = await self.session.execute(type_query)
        meetings_by_type = {row.meeting_type.value: row.count for row in type_result.all()}
        
        # Completion rate
        completion_rate = 0.0
        if total_meetings > 0:
            completion_rate = (completed_meetings / total_meetings) * 100
        
        return {
            "total_meetings": total_meetings,
            "completed_meetings": completed_meetings,
            "meetings_with_files": meetings_with_files,
            "meetings_with_zoom": meetings_with_zoom,
            "meetings_by_type": meetings_by_type,
            "completion_rate": round(completion_rate, 2)
        }
    
    # ===== VALIDATION =====
    
    async def meeting_exists_for_surat_tugas(
        self, 
        surat_tugas_id: str, 
        meeting_type: MeetingType
    ) -> bool:
        """Check if meeting exists untuk surat tugas dan type tertentu."""
        query = select(Meeting.id).where(
            and_(
                Meeting.surat_tugas_id == surat_tugas_id,
                Meeting.meeting_type == meeting_type,
                Meeting.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_file_paths_for_deletion(self, meeting_id: str) -> List[str]:
        """Get all file paths dalam meeting untuk deletion."""
        meeting = await self.get_by_id(meeting_id)
        if not meeting or not meeting.file_bukti_hadir:
            return []
        
        return [
            file_info.get('path') for file_info in meeting.file_bukti_hadir
            if file_info.get('path')
        ]

    
    async def get_meetings_by_type_summary(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary of meetings grouped by type."""
        
        # Base query
        base_query = (
            select(Meeting.meeting_type, func.count().label('count'))
            .join(SuratTugas, Meeting.surat_tugas_id == SuratTugas.id)
            .where(
                and_(
                    Meeting.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None)
                )
            )
            .group_by(Meeting.meeting_type)
        )
        
        # Apply role-based filtering
        if user_role == "PERWADAG":
            base_query = base_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "INSPEKTORAT" and user_inspektorat:
            base_query = base_query.where(SuratTugas.inspektorat == user_inspektorat)
        
        result = await self.session.execute(base_query)
        by_type = {row.meeting_type.value: row.count for row in result.all()}
        
        # Get completion summary
        completed_query = (
            select(Meeting.meeting_type, func.count().label('count'))
            .join(SuratTugas, Meeting.surat_tugas_id == SuratTugas.id)
            .where(
                and_(
                    Meeting.deleted_at.is_(None),
                    SuratTugas.deleted_at.is_(None),
                    Meeting.tanggal_meeting.is_not(None)
                )
            )
            .group_by(Meeting.meeting_type)
        )
        
        if user_role == "PERWADAG":
            completed_query = completed_query.where(SuratTugas.user_perwadag_id == user_id)
        elif user_role == "INSPEKTORAT" and user_inspektorat:
            completed_query = completed_query.where(SuratTugas.inspektorat == user_inspektorat)
        
        completed_result = await self.session.execute(completed_query)
        completed_by_type = {row.meeting_type.value: row.count for row in completed_result.all()}
        
        return {
            "by_type_summary": by_type,
            "completed_by_type": completed_by_type,
            "total_meetings": sum(by_type.values()),
            "total_completed": sum(completed_by_type.values())
        }

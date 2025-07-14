# ===== src/services/meeting.py =====
"""Service untuk meetings dengan multiple file handling."""

from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile

from src.repositories.meeting import MeetingRepository
from src.schemas.meeting import (
    MeetingUpdate, MeetingResponse, MeetingListResponse, 
    MeetingFileUploadResponse, MeetingsByTypeResponse
)
from src.schemas.filters import MeetingFilterParams
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager
from src.models.evaluasi_enums import MeetingType


class MeetingService:
    """Service untuk meeting operations dengan multiple file handling."""
    
    def __init__(self, meeting_repo: MeetingRepository):
        self.meeting_repo = meeting_repo
    
    async def get_meeting_or_404(self, meeting_id: str) -> MeetingResponse:
        """Get meeting by ID atau raise 404."""
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )
        return self._build_meeting_response(meeting)
    
    async def get_meetings_by_surat_tugas(self, surat_tugas_id: str) -> MeetingsByTypeResponse:
        """Get all meetings untuk surat tugas grouped by type."""
        meetings = await self.meeting_repo.get_all_by_surat_tugas(surat_tugas_id)
        
        meetings_by_type = {
            "entry_meeting": None,
            "konfirmasi_meeting": None,
            "exit_meeting": None
        }
        
        for meeting in meetings:
            meeting_response = self._build_meeting_response(meeting)
            if meeting.meeting_type == MeetingType.ENTRY:
                meetings_by_type["entry_meeting"] = meeting_response
            elif meeting.meeting_type == MeetingType.KONFIRMASI:
                meetings_by_type["konfirmasi_meeting"] = meeting_response
            elif meeting.meeting_type == MeetingType.EXIT:
                meetings_by_type["exit_meeting"] = meeting_response
        
        return MeetingsByTypeResponse(**meetings_by_type)
    
    async def update_meeting(
        self, 
        meeting_id: str, 
        meeting_data: MeetingUpdate,
        user_id: str
    ) -> MeetingResponse:
        """Update meeting information."""
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )
        
        updated_meeting = await self.meeting_repo.update(meeting_id, meeting_data)
        return self._build_meeting_response(updated_meeting)
    
    async def upload_meeting_files(
        self,
        meeting_id: str,
        files: List[UploadFile],
        uploaded_by: str,
        replace_existing: bool = False
    ) -> MeetingFileUploadResponse:
        """Upload multiple files ke meeting."""
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )
        
        # Clear existing files if replace mode
        if replace_existing and meeting.file_bukti_hadir:
            # Delete old files from storage
            for file_info in meeting.file_bukti_hadir:
                if file_info.get('path'):
                    evaluasi_file_manager.delete_file(file_info['path'])
            # Clear from database
            await self.meeting_repo.clear_all_files(meeting_id)
        
        # Upload new files
        uploaded_file_infos = await evaluasi_file_manager.upload_meeting_files(
            files, meeting_id, meeting.meeting_type.value, uploaded_by
        )
        
        # Add files to database
        updated_meeting = await self.meeting_repo.add_files(meeting_id, uploaded_file_infos)
        
        return MeetingFileUploadResponse(
            success=True,
            message=f"Successfully uploaded {len(uploaded_file_infos)} files",
            meeting_id=meeting_id,
            uploaded_files=uploaded_file_infos,
            total_uploaded=len(uploaded_file_infos),
            total_files_now=updated_meeting.total_files_uploaded,
            data={"uploaded_files": uploaded_file_infos}
        )
    
    async def delete_meeting_file(
        self,
        meeting_id: str,
        filename: str,
        user_id: str
    ) -> SuccessResponse:
        """Delete specific file dari meeting."""
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )
        
        # Find file info
        file_info = meeting.get_file_by_filename(filename)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete from storage
        if file_info.get('path'):
            evaluasi_file_manager.delete_file(file_info['path'])
        
        # Remove from database
        updated_meeting = await self.meeting_repo.remove_file(meeting_id, filename)
        
        return SuccessResponse(
            success=True,
            message=f"File {filename} deleted successfully",
            data={
                "deleted_filename": filename,
                "remaining_files": updated_meeting.total_files_uploaded
            }
        )
    
    def _build_meeting_response(self, meeting) -> MeetingResponse:
        """Build MeetingResponse from model."""
        file_infos = []
        if meeting.file_bukti_hadir:
            for file_info in meeting.file_bukti_hadir:
                file_infos.append({
                    "filename": file_info.get("filename"),
                    "original_filename": file_info.get("original_filename"),
                    "path": file_info.get("path"),
                    "url": file_info.get("url"),
                    "size": file_info.get("size"),
                    "uploaded_at": file_info.get("uploaded_at"),
                    "uploaded_by": file_info.get("uploaded_by")
                })
        
        return MeetingResponse(
            id=meeting.id,
            surat_tugas_id=meeting.surat_tugas_id,
            meeting_type=meeting.meeting_type,
            meeting_type_display=meeting.meeting_type_display,
            tanggal_meeting=meeting.tanggal_meeting,
            link_zoom=meeting.link_zoom,
            link_daftar_hadir=meeting.link_daftar_hadir,
            file_bukti_hadir=file_infos if file_infos else None,
            is_completed=meeting.is_completed(),
            has_files=meeting.has_files(),
            has_zoom_link=meeting.has_zoom_link(),
            has_daftar_hadir_link=meeting.has_daftar_hadir_link(),
            completion_percentage=meeting.get_completion_percentage(),
            total_files_uploaded=meeting.total_files_uploaded,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at
        )

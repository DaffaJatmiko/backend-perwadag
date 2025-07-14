# ===== src/services/meeting.py =====
"""Service untuk meetings dengan multiple file handling."""

from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse

from src.repositories.meeting import MeetingRepository
from src.schemas.meeting import (
    MeetingUpdate, MeetingResponse, MeetingListResponse, 
    MeetingFileUploadResponse, MeetingsByTypeResponse
)
from src.schemas.filters import MeetingFilterParams
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager
from src.models.evaluasi_enums import MeetingType
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)


class MeetingService:
    """Service untuk meeting operations dengan multiple file handling."""
    
    def __init__(self, meeting_repo: MeetingRepository):
        self.meeting_repo = meeting_repo

    async def get_all_meetings(
        self,
        filters: MeetingFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> MeetingListResponse:
        """Get all meetings dengan enriched data."""
        
        enriched_results, total = await self.meeting_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build enriched responses
        responses = []
        for result in enriched_results:
            meeting = result['meeting']
            surat_tugas_data = result['surat_tugas_data']
            
            response = await self._build_enriched_meeting_response(meeting, surat_tugas_data)
            responses.append(response)
        
        # Get type summary
        type_summary = await self.meeting_repo.get_meetings_by_type_summary(
            user_role, user_inspektorat, user_id
        )
        
        # Build pagination
        pagination = PaginationInfo.create(filters.page, filters.size, total)
        
        # Build statistics
        module_stats = ModuleStatistics(
            total_records=type_summary["total_meetings"],
            completed_records=type_summary["total_completed"],
            with_files=0,  # Will be calculated separately
            without_files=0,
            completion_rate=(type_summary["total_completed"] / max(type_summary["total_meetings"], 1)) * 100,
            last_updated=datetime.utcnow()
        )
        
        return MeetingListResponse(
            meetings=responses,
            pagination=pagination,
            statistics=module_stats,
            by_type_summary=type_summary["by_type_summary"],
            by_status_summary=type_summary["completed_by_type"]
        )
    
    async def get_meeting_or_404(self, meeting_id: str) -> MeetingResponse:
        """Get meeting by ID atau raise 404."""
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )
        return self._build_meeting_response(meeting)
    
    async def get_meetings_by_surat_tugas(
        self, 
        surat_tugas_id: str,
        session
    ) -> MeetingsByTypeResponse:
        """Get meetings grouped by type untuk satu surat tugas."""
        
        # Get all meetings untuk surat tugas ini
        meetings = await self.meeting_repo.get_all_by_surat_tugas(surat_tugas_id)
        
        # Get surat tugas info
        surat_tugas_data = await get_surat_tugas_basic_info(session, surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas not found"
            )
        
        # Group by type
        meetings_by_type = {
            "entry_meeting": None,
            "konfirmasi_meeting": None,
            "exit_meeting": None
        }
        
        completed_count = 0
        for meeting in meetings:
            response = await self._build_enriched_meeting_response(meeting, surat_tugas_data)
            
            if meeting.meeting_type == MeetingType.ENTRY:
                meetings_by_type["entry_meeting"] = response
            elif meeting.meeting_type == MeetingType.KONFIRMASI:
                meetings_by_type["konfirmasi_meeting"] = response
            elif meeting.meeting_type == MeetingType.EXIT:
                meetings_by_type["exit_meeting"] = response
            
            if meeting.is_completed():
                completed_count += 1
        
        # Build surat tugas info
        surat_tugas_info = SuratTugasBasicInfo(**surat_tugas_data)
        
        # Calculate progress
        progress_percentage = int((completed_count / 3) * 100)
        
        # Determine next meeting type
        next_meeting_type = None
        if not meetings_by_type["entry_meeting"] or not meetings_by_type["entry_meeting"].is_completed:
            next_meeting_type = "entry"
        elif not meetings_by_type["konfirmasi_meeting"] or not meetings_by_type["konfirmasi_meeting"].is_completed:
            next_meeting_type = "konfirmasi"
        elif not meetings_by_type["exit_meeting"] or not meetings_by_type["exit_meeting"].is_completed:
            next_meeting_type = "exit"
        
        return MeetingsByTypeResponse(
            entry_meeting=meetings_by_type["entry_meeting"],
            konfirmasi_meeting=meetings_by_type["konfirmasi_meeting"],
            exit_meeting=meetings_by_type["exit_meeting"],
            total_meetings=3,
            completed_meetings=completed_count,
            progress_percentage=progress_percentage,
            next_meeting_type=next_meeting_type,
            surat_tugas_info=surat_tugas_info
        )
    
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

    async def download_meeting_file(
        self, 
        meeting_id: str, 
        filename: str,
        download_type: str = "download"
    ) -> FileResponse:
        """Download specific meeting file."""
        
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting or not meeting.file_bukti_hadir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting or file not found"
            )
        
        # Find specific file
        target_file = None
        for file_info in meeting.file_bukti_hadir:
            if file_info.get('filename') == filename:
                target_file = file_info
                break
        
        if not target_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in meeting"
            )
        
        return evaluasi_file_manager.get_file_download_response(
            file_path=target_file['path'],
            original_filename=target_file.get('original_filename', filename),
            download_type=download_type
        )
    
    async def download_all_meeting_files(
        self, 
        meeting_id: str
    ) -> FileResponse:
        """Download all meeting files as ZIP."""
        
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting or not meeting.file_bukti_hadir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting or files not found"
            )
        
        # Get all file paths
        file_paths = [file_info['path'] for file_info in meeting.file_bukti_hadir]
        
        # Create ZIP
        zip_name = f"meeting_{meeting.meeting_type.value}_{meeting_id}"
        zip_path = evaluasi_file_manager.create_zip_archive(file_paths, zip_name)
        
        return FileResponse(
            path=zip_path,
            media_type='application/zip',
            filename=f"{zip_name}.zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_name}.zip"'}
        )
    
    async def _build_enriched_meeting_response(
        self, 
        meeting, 
        surat_tugas_data: Dict[str, Any]
    ) -> MeetingResponse:
        """Build enriched meeting response."""
        
        # Build surat tugas info
        surat_tugas_info = SuratTugasBasicInfo(**surat_tugas_data)
        
        # Build enhanced file info
        enhanced_files = []
        total_size_mb = 0.0
        
        if meeting.file_bukti_hadir:
            for file_info in meeting.file_bukti_hadir:
                file_path = file_info.get('path')
                if file_path:
                    detailed_info = evaluasi_file_manager.get_file_info(file_path)
                    if detailed_info:
                        enhanced_file = MeetingFileInfo(
                            filename=file_info['filename'],
                            original_filename=file_info.get('original_filename', file_info['filename']),
                            path=file_info['path'],
                            size=detailed_info['size'],
                            size_mb=detailed_info['size_mb'],
                            content_type=detailed_info['content_type'],
                            uploaded_at=datetime.fromisoformat(file_info['uploaded_at']),
                            uploaded_by=file_info['uploaded_by'],
                            download_url=f"/api/v1/evaluasi/meetings/{meeting.id}/download/{file_info['filename']}",
                            view_url=f"/api/v1/evaluasi/meetings/{meeting.id}/view/{file_info['filename']}" if detailed_info['is_viewable'] else None,
                            is_viewable=detailed_info['is_viewable']
                        )
                        enhanced_files.append(enhanced_file)
                        total_size_mb += detailed_info['size_mb']
        
        # Calculate contextual info
        today = date.today()
        tanggal_mulai = surat_tugas_data['tanggal_evaluasi_mulai']
        tanggal_selesai = surat_tugas_data['tanggal_evaluasi_selesai']
        
        days_until_evaluation = None
        if tanggal_mulai > today:
            days_until_evaluation = (tanggal_mulai - today).days
        
        is_evaluation_period = tanggal_mulai <= today <= tanggal_selesai
        
        # Determine meeting order
        meeting_order_map = {
            MeetingType.ENTRY: 1,
            MeetingType.KONFIRMASI: 2,
            MeetingType.EXIT: 3
        }
        meeting_order = meeting_order_map.get(meeting.meeting_type, 1)
        
        return MeetingResponse(
            id=meeting.id,
            surat_tugas_id=meeting.surat_tugas_id,
            meeting_type=meeting.meeting_type,
            meeting_type_display=meeting.meeting_type_display,
            tanggal_meeting=meeting.tanggal_meeting,
            link_zoom=meeting.link_zoom,
            link_daftar_hadir=meeting.link_daftar_hadir,
            file_bukti_hadir=enhanced_files,
            total_files_uploaded=len(enhanced_files),
            total_files_size_mb=round(total_size_mb, 2),
            is_completed=meeting.is_completed(),
            has_files=meeting.has_files(),
            has_zoom_link=meeting.has_zoom_link(),
            has_daftar_hadir_link=meeting.has_daftar_hadir_link(),
            completion_percentage=meeting.get_completion_percentage(),
            surat_tugas_info=surat_tugas_info,
            nama_perwadag=surat_tugas_data['nama_perwadag'],
            inspektorat=surat_tugas_data['inspektorat'],
            tanggal_evaluasi_mulai=tanggal_mulai,
            tanggal_evaluasi_selesai=tanggal_selesai,
            tahun_evaluasi=surat_tugas_data['tahun_evaluasi'],
            evaluation_status=surat_tugas_data['evaluation_status'],
            days_until_evaluation=days_until_evaluation,
            is_evaluation_period=is_evaluation_period,
            meeting_order=meeting_order,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
            created_by=meeting.created_by,
            updated_by=meeting.updated_by
        )

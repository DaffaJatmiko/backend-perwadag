# ===== src/api/endpoints/meetings.py =====
"""API endpoints untuk meetings dengan multiple file support."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.meeting import MeetingRepository
from src.services.meeting import MeetingService
from src.schemas.meeting import (
    MeetingUpdate, MeetingResponse, MeetingsByTypeResponse,
    MeetingFileUploadResponse
)
from src.schemas.common import SuccessResponse
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access
)

router = APIRouter()


async def get_meeting_service(session: AsyncSession = Depends(get_db)) -> MeetingService:
    """Dependency untuk MeetingService."""
    meeting_repo = MeetingRepository(session)
    return MeetingService(meeting_repo)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """Get meeting by ID dengan file info."""
    return await meeting_service.get_meeting_or_404(meeting_id)


@router.get("/surat-tugas/{surat_tugas_id}", response_model=MeetingsByTypeResponse)
async def get_meetings_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """Get all meetings untuk surat tugas grouped by type."""
    return await meeting_service.get_meetings_by_surat_tugas(surat_tugas_id)


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    current_user: dict = Depends(require_auto_generated_edit_access()),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    Update meeting information.
    
    **Accessible by**: Admin dan Inspektorat
    **Updatable**: tanggal_meeting, link_zoom, link_daftar_hadir
    """
    return await meeting_service.update_meeting(meeting_id, meeting_data, current_user["id"])


@router.post("/{meeting_id}/upload-files", response_model=MeetingFileUploadResponse)
async def upload_meeting_files(
    meeting_id: str,
    files: List[UploadFile] = File(..., description="Multiple files bukti hadir"),
    replace_existing: bool = Form(False, description="Replace all existing files"),
    current_user: dict = Depends(require_auto_generated_edit_access()),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    Upload multiple files bukti hadir ke meeting.
    
    **Accessible by**: Admin dan Inspektorat
    **File Types**: PDF, DOC, DOCX, JPG, PNG
    **Max Size**: 15MB per file
    **Behavior**: Add to existing files atau replace semua
    """
    return await meeting_service.upload_meeting_files(
        meeting_id, files, current_user["id"], replace_existing
    )


@router.delete("/{meeting_id}/files/{filename}", response_model=SuccessResponse)
async def delete_meeting_file(
    meeting_id: str,
    filename: str,
    current_user: dict = Depends(require_auto_generated_edit_access()),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """Delete specific file dari meeting."""
    return await meeting_service.delete_meeting_file(meeting_id, filename, current_user["id"])


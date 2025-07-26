# ===== MEETING ENDPOINTS (FINAL) =====
"""Meeting endpoints dengan semua file operations - LENGKAP."""

from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.meeting import MeetingRepository
from src.services.meeting import MeetingService
from src.schemas.meeting import (
    MeetingUpdate, MeetingResponse, MeetingListResponse,
    MeetingFileUploadResponse, MeetingFileDeleteResponse
)
from src.schemas.filters import MeetingFilterParams
from src.models.evaluasi_enums import MeetingType
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access, get_evaluasi_filter_scope
)
from src.schemas.shared import FileDeleteResponse

router = APIRouter()


async def get_meeting_service(session: AsyncSession = Depends(get_db)) -> MeetingService:
    """Dependency untuk MeetingService."""
    meeting_repo = MeetingRepository(session)
    return MeetingService(meeting_repo)


@router.get("/", response_model=MeetingListResponse)
async def get_all_meetings(
    filters: MeetingFilterParams = Depends(),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """
    Get all meetings dengan filtering dan enriched data.
    
    **Essential Filters Only:**
    - page, size, search
    - surat_tugas_id, meeting_type
    - inspektorat, user_perwadag_id, tahun_evaluasi
    - include_statistics
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
      
    return await service.get_all_meetings(
        filters=filters,
        user_role=filter_scope["user_role"],
        user_inspektorat=filter_scope.get("user_inspektorat"),
        user_id=filter_scope.get("user_id")
    )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Get meeting by ID dengan enriched data dan file information."""
    return await service.get_meeting_or_404(meeting_id)


@router.get("/surat-tugas/{surat_tugas_id}/type/{meeting_type}", response_model=MeetingResponse)
async def get_meeting_by_surat_tugas_and_type(
    surat_tugas_id: str,
    meeting_type: MeetingType,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Get meeting by surat tugas ID dan meeting type."""
    result = await service.get_by_surat_tugas_and_type(surat_tugas_id, meeting_type)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return result


@router.get("/surat-tugas/{surat_tugas_id}", response_model=List[MeetingResponse])
async def get_all_meetings_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Get all meetings untuk surat tugas tertentu (entry, konfirmasi, exit)."""
    return await service.get_all_by_surat_tugas_id(surat_tugas_id)


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    update_data: MeetingUpdate,
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Update meeting (tanggal, zoom link, daftar hadir link)."""
    return await service.update_meeting(meeting_id, update_data, current_user["id"])


# ===== FILE OPERATIONS ENDPOINTS =====
@router.post("/{meeting_id}/upload-files", response_model=MeetingFileUploadResponse)
async def upload_meeting_files(
    meeting_id: str,
    files: List[UploadFile] = File(..., description="Multiple files untuk meeting"),
    replace_existing: bool = Query(False, description="Replace existing files or add to existing"),
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Upload multiple files ke meeting."""
    return await service.upload_files(meeting_id, files, current_user["id"], replace_existing)


@router.delete("/{meeting_id}/files/{filename}", response_model=FileDeleteResponse)
async def delete_meeting_file(
    meeting_id: str,
    filename: str = Path(..., description="Filename to delete"),
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Delete specific file dari meeting."""
    return await service.delete_file(meeting_id, filename, current_user["id"], current_user)


@router.get("/{meeting_id}/files/{filename}/download", response_class=FileResponse)
async def download_meeting_file(
    meeting_id: str = Path(..., description="Meeting ID"),
    filename: str = Path(..., description="Filename to download"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Download specific file dari meeting."""
    return await service.download_file(meeting_id, filename, download_type="download")


@router.get("/{meeting_id}/files/{filename}/view", response_class=FileResponse)
async def view_meeting_file(
    meeting_id: str = Path(..., description="Meeting ID"),
    filename: str = Path(..., description="Filename to view"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """View/preview specific file dari meeting in browser."""
    return await service.download_file(meeting_id, filename, download_type="view")


@router.get("/{meeting_id}/files/download-all", response_class=FileResponse)
async def download_all_meeting_files(
    meeting_id: str = Path(..., description="Meeting ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MeetingService = Depends(get_meeting_service)
):
    """Download all files dari meeting sebagai ZIP archive."""
    return await service.download_all_files(meeting_id)
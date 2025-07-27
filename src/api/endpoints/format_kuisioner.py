# ===== src/api/endpoints/format_kuisioner.py =====
"""API endpoints untuk format kuisioner master templates."""

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.format_kuisioner import FormatKuisionerRepository
from src.services.format_kuisioner import FormatKuisionerService
from src.schemas.format_kuisioner import (
    FormatKuisionerCreate, FormatKuisionerUpdate, FormatKuisionerResponse,
    FormatKuisionerListResponse, FormatKuisionerFileUploadResponse
)
from src.schemas.filters import FormatKuisionerFilterParams
from src.schemas.common import SuccessResponse
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_format_kuisioner_access
)
from src.schemas.shared import FileDeleteResponse


router = APIRouter()


async def get_format_kuisioner_service(session: AsyncSession = Depends(get_db)) -> FormatKuisionerService:
    """Dependency untuk FormatKuisionerService."""
    format_kuisioner_repo = FormatKuisionerRepository(session)
    return FormatKuisionerService(format_kuisioner_repo)


@router.post("/", response_model=FormatKuisionerResponse, status_code=201)
async def create_format_kuisioner(
    nama_template: str = Form(..., description="Nama template kuisioner"),
    tahun: int = Form(..., description="Tahun berlaku template"),
    deskripsi: str = Form(None, description="Deskripsi template"),
    file: UploadFile = File(..., description="File template kuisioner"),
    current_user: dict = Depends(require_format_kuisioner_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """
    Create format kuisioner master template.
    
    **Accessible by**: Admin only
    **File Types**: PDF, DOC, DOCX, XLS, XLSX
    """
    format_kuisioner_data = FormatKuisionerCreate(
        nama_template=nama_template,
        tahun=tahun,
        deskripsi=deskripsi
    )
    return await service.create_format_kuisioner(format_kuisioner_data, file, current_user["id"])


@router.get("/", response_model=FormatKuisionerListResponse)
async def get_all_format_kuisioner(
    filters: FormatKuisionerFilterParams = Depends(),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """Get all format kuisioner dengan filtering."""
    return await service.get_all_format_kuisioner(filters)


# 🔥 PENTING: LETAKKAN /active SEBELUM /{format_kuisioner_id}
@router.get("/active", response_model=FormatKuisionerResponse)
async def get_active_template(
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """Get currently active format kuisioner template."""
    template = await service.get_active_template()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tidak ada template format kuisioner yang aktif"
        )
    return template


@router.get("/tahun/{tahun}")
async def get_format_kuisioner_by_tahun(
    tahun: int,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """Get format kuisioner untuk tahun tertentu."""
    templates = await service.get_by_tahun(tahun)
    return {
        "tahun": tahun,
        "templates": templates,
        "total": len(templates)
    }


@router.get("/{format_kuisioner_id}", response_model=FormatKuisionerResponse)
async def get_format_kuisioner(
    format_kuisioner_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """Get format kuisioner by ID."""
    return await service.get_format_kuisioner_or_404(format_kuisioner_id)


@router.put("/{format_kuisioner_id}", response_model=FormatKuisionerResponse)
async def update_format_kuisioner(
    format_kuisioner_id: str,
    update_data: FormatKuisionerUpdate,
    current_user: dict = Depends(require_format_kuisioner_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """Update format kuisioner - Admin only."""
    return await service.update_format_kuisioner(format_kuisioner_id, update_data, current_user["id"])


@router.post("/{format_kuisioner_id}/activate", response_model=FormatKuisionerResponse)
async def activate_template(
    format_kuisioner_id: str,
    current_user: dict = Depends(require_format_kuisioner_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """
    Activate format kuisioner template - Admin only.
    
    Activates the specified template and automatically deactivates all others.
    Only one template can be active at a time.
    """
    return await service.activate_template(format_kuisioner_id)


@router.post("/{format_kuisioner_id}/upload-file", response_model=FormatKuisionerFileUploadResponse)
async def upload_format_kuisioner_file(
    format_kuisioner_id: str,
    file: UploadFile = File(..., description="File template kuisioner baru"),
    current_user: dict = Depends(require_format_kuisioner_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """Upload atau replace template file - Admin only."""
    return await service.upload_template_file(format_kuisioner_id, file, current_user["id"])


@router.delete("/{format_kuisioner_id}", response_model=SuccessResponse)
async def delete_format_kuisioner(
    format_kuisioner_id: str,
    current_user: dict = Depends(require_format_kuisioner_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """Delete format kuisioner - Admin only."""
    return await service.delete_format_kuisioner(format_kuisioner_id, current_user["id"])


@router.get("/download/{format_kuisioner_id}")
async def download_format_kuisioner(
    format_kuisioner_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """
    Download template kuisioner.
    
    **Returns**: Redirect ke file URL atau direct file download
    """
    format_kuisioner = await service.get_format_kuisioner_or_404(format_kuisioner_id)
    
    if not format_kuisioner.is_downloadable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template file not available for download"
        )
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=format_kuisioner.file_urls.file_url if format_kuisioner.file_urls else "")


# ===== UTILITY ENDPOINTS =====

@router.get("/admin/statistics")
async def get_format_kuisioner_statistics(
    current_user: dict = Depends(require_format_kuisioner_access()),
    session: AsyncSession = Depends(get_db)
):
    """Get statistics template kuisioner - Admin only."""
    from sqlalchemy import select, func, and_
    from src.models.format_kuisioner import FormatKuisioner
    
    # Total templates
    total_query = select(func.count()).select_from(FormatKuisioner).where(FormatKuisioner.deleted_at.is_(None))
    total_result = await session.execute(total_query)
    total_templates = total_result.scalar() or 0
    
    # Templates by year
    year_query = (
        select(FormatKuisioner.tahun, func.count().label('count'))
        .where(FormatKuisioner.deleted_at.is_(None))
        .group_by(FormatKuisioner.tahun)
        .order_by(FormatKuisioner.tahun.desc())
    )
    year_result = await session.execute(year_query)
    templates_by_year = {row.tahun: row.count for row in year_result.all()}
    
    # Templates with files
    files_query = select(func.count()).select_from(FormatKuisioner).where(
        and_(
            FormatKuisioner.deleted_at.is_(None),
            FormatKuisioner.link_template.is_not(None),
            FormatKuisioner.link_template != ""
        )
    )
    files_result = await session.execute(files_query)
    templates_with_files = files_result.scalar() or 0
    
    # Active template
    active_query = select(func.count()).select_from(FormatKuisioner).where(
        and_(
            FormatKuisioner.deleted_at.is_(None),
            FormatKuisioner.is_active == True
        )
    )
    active_result = await session.execute(active_query)
    active_templates = active_result.scalar() or 0
    
    return {
        "total_templates": total_templates,
        "templates_by_year": templates_by_year,
        "templates_with_files": templates_with_files,
        "templates_without_files": total_templates - templates_with_files,
        "active_templates": active_templates,
        "completion_rate": round((templates_with_files / max(total_templates, 1)) * 100, 2)
    }


@router.delete("/{format_kuisioner_id}/files/{filename}", response_model=FileDeleteResponse)
async def delete_format_kuisioner_file(
    format_kuisioner_id: str,
    filename: str = Path(..., description="Filename to delete"),
    current_user: dict = Depends(require_format_kuisioner_access()),
    service: FormatKuisionerService = Depends(get_format_kuisioner_service)
):
    """
    Delete format kuisioner file by filename.
    
    **Accessible by**: Admin only
    
    **Parameters**:
    - format_kuisioner_id: ID format kuisioner
    - filename: Nama file yang akan dihapus (harus exact match)
    """
    return await service.delete_file_by_filename(
        format_kuisioner_id, filename, current_user["id"], current_user
    )
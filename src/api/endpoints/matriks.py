# ===== src/api/endpoints/matriks.py =====
"""Enhanced API endpoints untuk matriks evaluasi."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.matriks import MatriksRepository
from src.services.matriks import MatriksService
from src.schemas.matriks import (
    MatriksUpdate, MatriksResponse,
    MatriksFileUploadResponse, MatriksListResponse
)
from src.schemas.filters import MatriksFilterParams
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access, get_evaluasi_filter_scope
)
from src.schemas.shared import FileDeleteResponse

router = APIRouter()


async def get_matriks_service(session: AsyncSession = Depends(get_db)) -> MatriksService:
    """Dependency untuk MatriksService."""
    matriks_repo = MatriksRepository(session)
    return MatriksService(matriks_repo)


@router.get("/", response_model=MatriksListResponse)
async def get_all_matriks(
    filters: MatriksFilterParams = Depends(),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Get all matriks dengan comprehensive filtering dan enriched data.
    
    **Role-based Access:**
    - **Admin**: Semua data matriks
    - **Inspektorat**: Data di wilayah kerjanya
    - **Perwadag**: Data milik sendiri only
    
    **Enhanced Features:**
    - Include tanggal evaluasi, nama perwadag, inspektorat dari surat tugas
    - File download/view URLs
    - Completion statistics
    - Advanced filtering options
    
    **Query Parameters:**
    - **Basic**: page, size, search
    - **Surat Tugas Related**: inspektorat, user_perwadag_id, tahun_evaluasi
    - **Status**: has_file, has_nomor, is_completed
    - **Date Range**: created_from, created_to, tanggal_evaluasi_from, tanggal_evaluasi_to
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
      
    return await service.get_all_matriks(
        filters=filters,
        user_role=filter_scope["user_role"],
        user_inspektorat=filter_scope.get("user_inspektorat"),
        user_id=filter_scope.get("user_id")
    )


@router.get("/{matriks_id}", response_model=MatriksResponse)
async def get_matriks(
    matriks_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Get matriks by ID dengan enriched data."""
    return await service.get_matriks_or_404(matriks_id)


@router.get("/surat-tugas/{surat_tugas_id}", response_model=MatriksResponse)
async def get_matriks_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Get matriks by surat tugas ID."""
    result = await service.get_by_surat_tugas_id(surat_tugas_id)
    if not result:
        raise HTTPException(status_code=404, detail="Matriks not found")
    return result


@router.put("/{matriks_id}", response_model=MatriksResponse)
async def update_matriks(
    matriks_id: str,
    update_data: MatriksUpdate,
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Update matriks dengan temuan-rekomendasi support.

    **Accessible by**: Admin dan Inspektorat

    **Features:**
    - Update temuan dan rekomendasi (REPLACE strategy)
    - Maksimal 20 pasang temuan-rekomendasi
    - Date access validation

    **Example Request:**
    ```json
    {
        "temuan_rekomendasi": {
            "items": [
                {
                    "temuan": "Belum ada prosedur standar untuk evaluasi",
                    "rekomendasi": "Membuat SOP evaluasi yang jelas dan terstruktur"
                },
                {
                    "temuan": "Dokumentasi kurang lengkap",
                    "rekomendasi": "Melengkapi dokumentasi sesuai standar yang berlaku"
                }
            ]
        }
    }
    ```

    **Strategy**: REPLACE - Data lama akan diganti dengan data baru
    
    **Validation**:
    - Temuan dan rekomendasi tidak boleh kosong
    - Maksimal 20 pasang data
    - Hanya bisa update jika evaluasi belum selesai
    
    **Response**: Enriched matriks data dengan summary temuan-rekomendasi
    """
    return await service.update_matriks(matriks_id, update_data, current_user["id"])


@router.post("/{matriks_id}/upload-file", response_model=MatriksFileUploadResponse)
async def upload_matriks_file(
    matriks_id: str,
    file: UploadFile = File(..., description="File matriks"),
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Upload file matriks."""
    return await service.upload_file(matriks_id, file, current_user["id"])


@router.get("/{matriks_id}/download", response_class=FileResponse)
async def download_matriks_file(
    matriks_id: str = Path(..., description="Matriks ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Download matriks file.
    
    **Response**: File download dengan proper headers
    **Access Control**: Role-based access dengan ownership validation
    """
    return await service.download_file(matriks_id, download_type="download")

@router.delete("/{matriks_id}/files/{filename}", response_model=FileDeleteResponse)
async def delete_matriks_file(
    matriks_id: str,
    filename: str = Path(..., description="Filename to delete"),
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Delete matriks file by filename.
    
    **Accessible by**: Admin dan Inspektorat
    
    **Date Validation**: Cannot delete after evaluation period ends
    
    **Parameters**:
    - matriks_id: ID matriks
    - filename: Nama file yang akan dihapus (harus exact match)
    """
    return await service.delete_file(
        matriks_id, filename, current_user["id"], current_user
    )


@router.get("/{matriks_id}/view", response_class=FileResponse)
async def view_matriks_file(
    matriks_id: str = Path(..., description="Matriks ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    View/preview matriks file in browser.
    
    **Response**: File view dengan inline content disposition untuk PDF/images
    **Use Case**: Preview file tanpa download untuk supported file types
    """
    return await service.download_file(matriks_id, download_type="view")
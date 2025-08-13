# ===== src/api/endpoints/matriks.py =====
"""Enhanced API endpoints untuk matriks evaluasi."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.matriks import MatriksRepository
from src.services.matriks import MatriksService
from src.schemas.matriks import (
    MatriksUpdate, MatriksResponse,
    MatriksFileUploadResponse, MatriksListResponse, MatriksStatusUpdate, TindakLanjutStatus, TindakLanjutStatusUpdate, TindakLanjutUpdate
)
from src.schemas.filters import MatriksFilterParams
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access, get_evaluasi_filter_scope
)
from src.schemas.shared import FileDeleteResponse

router = APIRouter()


async def get_matriks_service(session: AsyncSession = Depends(get_db)) -> MatriksService:
    """Dependency untuk MatriksService dengan semua repo yang dibutuhkan."""
    from src.repositories.surat_tugas import SuratTugasRepository
    from src.repositories.meeting import MeetingRepository
    
    matriks_repo = MatriksRepository(session)
    surat_tugas_repo = SuratTugasRepository(session)
    meeting_repo = MeetingRepository(session)
    
    return MatriksService(
        matriks_repo=matriks_repo,
        surat_tugas_repo=surat_tugas_repo,
        meeting_repo=meeting_repo
    )


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
        user_id=filter_scope.get("user_id"),
        current_user=current_user
    )


@router.get("/{matriks_id}", response_model=MatriksResponse)
async def get_matriks(
    matriks_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Get matriks by ID dengan enriched data."""
    return await service.get_matriks_or_404(matriks_id, current_user)


@router.get("/surat-tugas/{surat_tugas_id}", response_model=MatriksResponse)
async def get_matriks_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Get matriks by surat tugas ID."""
    result = await service.get_by_surat_tugas_id(surat_tugas_id, current_user)
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
    Update matriks dengan kondisi-kriteria-rekomendasi support dan conflict detection.

    **Accessible by**: Admin dan Inspektorat

    **Features:**
    - Update kondisi, kriteria dan rekomendasi (REPLACE strategy)
    - Maksimal 20 set kondisi-kriteria-rekomendasi
    - Date access validation
    - **NEW: Conflict detection untuk mencegah race condition**

    **Example Request:**
    ```json
    {
        "temuan_rekomendasi": {
            "items": [
                {
                    "kondisi": "Sistem pencatatan perdagangan masih menggunakan buku manual dan belum terintegrasi",
                    "kriteria": "Sesuai Permendagri No. 20/2021, sistem pencatatan harus digital dan terintegrasi",
                    "rekomendasi": "Implementasi sistem pencatatan digital terintegrasi dengan database terpusat"
                },
                {
                    "kondisi": "Dokumen perizinan pedagang tersebar di berbagai file fisik tanpa backup",
                    "kriteria": "Standar ISO 27001 mengharuskan backup data digital untuk dokumen penting",
                    "rekomendasi": "Membuat sistem backup digital dan database perizinan yang mudah diakses"
                }
            ]
        },
        "expected_temuan_version": 0
    }
    ```

    **3-Field Structure:**
    - **Kondisi**: Situasi/keadaan yang ditemukan saat evaluasi
    - **Kriteria**: Standar/aturan/ketentuan yang harus dipenuhi
    - **Rekomendasi**: Saran perbaikan untuk memenuhi kriteria

    **Conflict Detection:**
    - **expected_temuan_version**: Version yang diharapkan (dari GET response)
    - Jika version tidak match → Error 409 Conflict
    - **Workflow**: GET matriks → ambil `temuan_version` → kirim sebagai `expected_temuan_version`

    **Strategy**: REPLACE - Data lama akan diganti dengan data baru
    
    **Validation**:
    - Kondisi, kriteria, dan rekomendasi tidak boleh kosong
    - Maksimal 20 set data
    - Hanya bisa update jika evaluasi belum selesai
    - Version harus match untuk mencegah race condition
    
    **Error Responses**:
    - **409 Conflict**: "Data telah diubah oleh user lain. Silakan refresh halaman dan coba lagi."
    - **403 Forbidden**: Akses ditolak (evaluasi sudah selesai)
    - **422 Validation Error**: Data tidak valid
    
    **Response**: Enriched matriks data dengan summary kondisi-kriteria-rekomendasi dan `temuan_version` terbaru

    **Multi-User Workflow:**
    1. User A: GET `/matriks/{id}` → dapat `temuan_version: 0`
    2. User B: GET `/matriks/{id}` → dapat `temuan_version: 0`
    3. User A: PUT dengan `expected_temuan_version: 0` → **Success** (version jadi 1)
    4. User B: PUT dengan `expected_temuan_version: 0` → **Error 409** (version sudah 1)
    5. User B: GET ulang → dapat `temuan_version: 1` → PUT dengan version 1 → **Success**
    """
    return await service.update_matriks(
        matriks_id, 
        update_data, 
        current_user['id'],
        current_user  
    )

@router.put("/{matriks_id}/status", response_model=MatriksResponse)
async def update_matrix_status(
    matriks_id: str,
    status_data: MatriksStatusUpdate,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Update status flow matriks evaluasi.
    
    **Status Flow:**
    - **DRAFTING** → **CHECKING**: Anggota tim selesai input temuan
    - **CHECKING** → **VALIDATING**: Ketua tim approve
    - **CHECKING** → **DRAFTING**: Ketua tim reject untuk revisi
    - **VALIDATING** → **FINISHED**: Pengendali teknis final approve  
    - **VALIDATING** → **DRAFTING**: Pengendali teknis reject untuk revisi
    
    **Permissions:**
    - **DRAFTING**: Ketua tim bisa ubah ke CHECKING
    - **CHECKING**: Ketua tim bisa ubah ke DRAFTING/VALIDATING
    - **VALIDATING**: Pengendali teknis bisa ubah ke DRAFTING/FINISHED
    - **FINISHED**: Hanya admin/pengedali mutu untuk emergency
    """
    return await service.update_matrix_status(matriks_id, status_data, current_user)

@router.put("/{matriks_id}/tindak-lanjut/status", response_model=MatriksResponse)
async def update_global_tindak_lanjut_status(
    matriks_id: str,
    status_data: TindakLanjutStatusUpdate,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Update GLOBAL tindak lanjut status for entire matrix.
    
    **Single Button**: One status change affects all items.
    **Workflow**: DRAFTING → CHECKING → VALIDATING → FINISHED
    """
    return await service.update_global_tindak_lanjut_status(matriks_id, status_data, current_user)

@router.put("/{matriks_id}/tindak-lanjut/{item_id}", response_model=MatriksResponse) 
async def update_tindak_lanjut(
    matriks_id: str,
    item_id: int,
    tindak_lanjut_data: TindakLanjutUpdate,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Update konten tindak lanjut untuk item temuan tertentu.
    
    **Requirements:**
    - Matriks harus status FINISHED
    - User sesuai dengan permission berdasarkan status tindak lanjut
    
    **Fields yang bisa diupdate:**
    - **tindak_lanjut**: Narasi tindak lanjut (oleh Perwadag)
    - **dokumen_pendukung_tindak_lanjut**: Link dokumen (oleh Perwadag)  
    - **catatan_evaluator**: Catatan ketua tim (oleh Ketua Tim)
    
    **Permissions berdasarkan status:**
    - **DRAFTING**: Hanya Perwadag yang bisa edit
    - **CHECKING**: Hanya Ketua Tim yang bisa edit catatan_evaluator
    - **VALIDATING**: Tidak ada yang bisa edit konten
    - **FINISHED**: Hanya admin/pengedali mutu untuk emergency
    """
    return await service.update_tindak_lanjut_content(matriks_id, item_id, tindak_lanjut_data, current_user)



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

@router.get("/{matriks_id}/pdf", response_class=Response)
async def generate_matriks_pdf(
    matriks_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """
    Generate PDF matriks evaluasi.
    
    **Response**: Binary PDF data untuk download atau preview
    **Access Control**: Sama dengan read access - semua yang terlibat di evaluasi
    """
    try:
        # Generate PDF
        pdf_bytes = await service.generate_pdf(matriks_id, current_user)
        
        # Get matriks info for filename
        matriks = await service.get_matriks_or_404(matriks_id, current_user)
        
        # Create filename
        nama_perwadag = matriks.nama_perwadag.replace(' ', '_').replace('/', '_')
        tahun = matriks.tahun_evaluasi
        filename = f"matriks_evaluasi_{nama_perwadag}_{tahun}.pdf"
        
        # Return PDF response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal generate PDF: {str(e)}"
        )

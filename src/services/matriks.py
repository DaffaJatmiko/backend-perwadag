# ===== src/services/matriks.py =====
"""Enhanced service untuk matriks evaluasi."""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, and_ 

from src.repositories.matriks import MatriksRepository
from src.schemas.matriks import (
    MatriksUpdate, MatriksResponse,
    MatriksFileUploadResponse, MatriksListResponse
)
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)
from src.schemas.filters import MatriksFilterParams
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.utils.evaluation_date_validator import validate_matriks_date_access
from src.schemas.matriks import TemuanRekomendasiSummary, MatriksStatusUpdate, TindakLanjutUpdate, TindakLanjutStatusUpdate, UserPermissions
from src.schemas.shared import FileDeleteResponse
from src.models.evaluasi_enums import MatriksStatus, TindakLanjutStatus
from src.services.matriks_permissions import (
    get_matrix_permissions, get_tindak_lanjut_permissions, 
    should_hide_temuan_for_perwadag, get_user_assignment_role
)


class MatriksService:
    """Enhanced service untuk matriks operations."""
    
    def __init__(self, matriks_repo: MatriksRepository):
        self.matriks_repo = matriks_repo

    async def get_all_matriks(
        self,
        filters: MatriksFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None,
        current_user: Optional[dict] = None
    ) -> MatriksListResponse:
        """Get all matriks dengan enriched data."""
        
        # Get enriched data dari repository
        enriched_results, total = await self.matriks_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build responses
        matriks_responses = []
        for result in enriched_results:
            response = await self._build_enriched_response(
                result['matriks'], 
                result['surat_tugas_data'],
                current_user
            )
            matriks_responses.append(response)
        
        # Build pagination
        
        # Get statistics
        statistics = None
        if filters.include_statistics:
            stats_data = await self.matriks_repo.get_statistics(
                user_role, user_inspektorat, user_id
            )
            statistics = ModuleStatistics(
                total=stats_data['total'],
                completed=stats_data['completed'],
                completion_rate=stats_data['completion_rate'],
                has_file=stats_data['has_file'],
                module_specific_stats={}
            )
        
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0

        response = MatriksListResponse(
            items=matriks_responses,  # ✅ matriks → items
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )

        if filters.include_statistics:
            response.statistics = statistics

        return response
    
    async def get_matriks_or_404(self, matriks_id: str, current_user: Optional[dict] = None) -> MatriksResponse:
        """Get matriks by ID dengan enriched data dan permission checking."""
        
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(matriks.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        # Pass current_user ke _build_enriched_response
        return await self._build_enriched_response(matriks, surat_tugas_data, current_user)
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str, current_user: Optional[dict] = None) -> Optional[MatriksResponse]:
        """Get matriks by surat tugas ID."""
        
        matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
        if not matriks:
            return None
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_tugas_id)
        if not surat_tugas_data:
            return None
        
        # Pass current_user ke _build_enriched_response
        return await self._build_enriched_response(matriks, surat_tugas_data, current_user)
    
    async def update_matriks(
        self, 
        matriks_id: str, 
        update_data: MatriksUpdate, 
        updated_by: str,
        current_user: Optional[dict] = None
    ) -> MatriksResponse:
        """Update matriks dengan kondisi-kriteria-rekomendasi support."""
        
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(matriks.surat_tugas_id)
        
        # Date validation
        validate_matriks_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="update"
        )
        
        # Update temuan-rekomendasi if provided
        if update_data.temuan_rekomendasi is not None:
            items = [item.model_dump() for item in update_data.temuan_rekomendasi.items]
            updated_matriks, success = await self.matriks_repo.update_temuan_rekomendasi(
                matriks_id, items, update_data.expected_temuan_version
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Data telah diubah oleh user lain. Silakan refresh halaman dan coba lagi."
                )
        else:
            # No temuan-rekomendasi update, just refresh
            updated_matriks = matriks
        
        # Set updated_by
        updated_matriks.updated_by = updated_by
        await self.matriks_repo.session.commit()
        
        return await self.get_matriks_or_404(matriks_id, current_user)

    async def update_matrix_status(
        self,
        matrix_id: str,
        status_data: MatriksStatusUpdate,
        current_user: dict
    ) -> MatriksResponse:
        """Update status matriks dengan validasi permission."""
        
        # Get matrix dan surat tugas data
        matrix = await self.matriks_repo.get_by_id(matrix_id)
        if not matrix:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(matrix.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        # Check permissions
        permissions = get_matrix_permissions(matrix.status, surat_tugas_data, current_user)
        if not permissions.can_change_matrix_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses untuk mengubah status matriks"
            )
        
        # Validate status transition
        if status_data.status not in permissions.allowed_matrix_status_changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tidak dapat mengubah status dari {matrix.status} ke {status_data.status}"
            )
        
        # Update status
        matrix.status = status_data.status
        matrix.updated_by = current_user['id']
        
        await self.matriks_repo.session.commit()
        
        return await self.get_matriks_or_404(matrix_id, current_user)
    
    async def update_tindak_lanjut(
        self,
        matrix_id: str,
        item_id: int,
        tindak_lanjut_data: TindakLanjutUpdate,
        current_user: dict
    ) -> MatriksResponse:
        """Update tindak lanjut untuk item tertentu."""
        
        # Get matrix dan surat tugas data
        matrix = await self.matriks_repo.get_by_id(matrix_id)
        if not matrix:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(matrix.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        # Get current tindak lanjut data untuk item ini
        current_tindak_lanjut = matrix.get_tindak_lanjut_item(item_id)
        current_status = None
        if current_tindak_lanjut:
            current_status = current_tindak_lanjut.get('status_tindak_lanjut')
        
        # Check permissions
        permissions = get_tindak_lanjut_permissions(
            current_status, surat_tugas_data, current_user, matrix.status
        )
        if not permissions.can_edit_tindak_lanjut:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses untuk mengubah tindak lanjut"
            )
        
        # Update item
        success = matrix.update_tindak_lanjut_item(
            item_id=item_id,
            tindak_lanjut=tindak_lanjut_data.tindak_lanjut,
            dokumen_pendukung=tindak_lanjut_data.dokumen_pendukung_tindak_lanjut,
            catatan_evaluator=tindak_lanjut_data.catatan_evaluator
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item dengan ID {item_id} tidak ditemukan"
            )
        
        matrix.updated_by = current_user['id']
        await self.matriks_repo.session.commit()
        
        return await self.get_matriks_or_404(matrix_id, current_user)
    
    async def update_tindak_lanjut_status(
        self,
        matrix_id: str,
        item_id: int,
        status_data: TindakLanjutStatusUpdate,
        current_user: dict
    ) -> MatriksResponse:
        """Update status tindak lanjut untuk item tertentu."""
        
        # Get matrix dan surat tugas data
        matrix = await self.matriks_repo.get_by_id(matrix_id)
        if not matrix:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(matrix.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        # Get current tindak lanjut data
        current_tindak_lanjut = matrix.get_tindak_lanjut_item(item_id)
        current_status = None
        if current_tindak_lanjut:
            current_status = current_tindak_lanjut.get('status_tindak_lanjut')
        
        # Check permissions
        permissions = get_tindak_lanjut_permissions(
            current_status, surat_tugas_data, current_user, matrix.status
        )
        if not permissions.can_change_tindak_lanjut_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses untuk mengubah status tindak lanjut"
            )
        
        # Validate status transition
        if status_data.status_tindak_lanjut not in permissions.allowed_tindak_lanjut_status_changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tidak dapat mengubah status tindak lanjut ke {status_data.status_tindak_lanjut}"
            )
        
        # Update status
        success = matrix.update_tindak_lanjut_item(
            item_id=item_id,
            status_tindak_lanjut=status_data.status_tindak_lanjut
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item dengan ID {item_id} tidak ditemukan"
            )
        
        matrix.updated_by = current_user['id']
        await self.matriks_repo.session.commit()
        
        return await self.get_matriks_or_404(matrix_id, current_user)
    
    async def upload_file(
        self, 
        matriks_id: str, 
        file: UploadFile, 
        uploaded_by: str
    ) -> MatriksFileUploadResponse:
        """Upload file matriks."""
        
        # Validate matriks exists
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )

        surat_tugas_data = await self._get_surat_tugas_basic_info(matriks.surat_tugas_id)
        
        # 🔥 VALIDASI AKSES TANGGAL
        validate_matriks_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="upload"
        )
        
        try:
            # 🔥 FIX: Correct parameter order - file first, then surat_tugas_id
            file_path = await evaluasi_file_manager.upload_matriks_file(
                file, matriks.surat_tugas_id  # Fixed: file first, surat_tugas_id second
            )
            
            # Update file path di database
            updated_matriks = await self.matriks_repo.update_file_path(matriks_id, file_path)
            if not updated_matriks:
                # Cleanup uploaded file jika database update gagal
                evaluasi_file_manager.delete_file(file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal memperbarui path file di database"
                )
            
            # Set uploaded_by
            updated_matriks.updated_by = uploaded_by
            await self.matriks_repo.session.commit()
            
            # Build file URL
            file_url = evaluasi_file_manager.get_file_url(file_path)
            
            return MatriksFileUploadResponse(
                success=True,
                message="File berhasil diunggah",
                matriks_id=matriks_id,
                file_path=file_path,
                file_url=file_url
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (like validation errors from file manager)
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal mengunggah file: {str(e)}"
            )
    
    async def download_file(
        self, 
        matriks_id: str, 
        download_type: str = "download"
    ) -> FileResponse:
        """Download atau view file matriks."""
        
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )
        
        if not matriks.file_dokumen_matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        # 🔥 FIX: Use get_file_download_response instead of download_file
        return evaluasi_file_manager.get_file_download_response(
            file_path=matriks.file_dokumen_matriks,
            original_filename=None,  # Will use filename from path
            download_type=download_type
        )

    async def delete_file(
        self,
        matriks_id: str,
        filename: str,
        deleted_by: str,
        current_user: dict = None
    ) -> FileDeleteResponse:
        """Delete file matriks by filename."""
        
        # 1. Get matriks
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks tidak ditemukan"
            )
        
        # 2. Check file exists
        if not matriks.file_dokumen_matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tidak ada file untuk dihapus"
            )
        
        # 3. Get surat tugas data untuk date validation
        surat_tugas_data = await self._get_surat_tugas_basic_info(matriks.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas terkait tidak ditemukan"
            )
        
        # 4. Date validation
        from src.utils.evaluation_date_validator import validate_matriks_date_access
        validate_matriks_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="delete file"
        )
        
        # 5. Validate filename matches
        current_filename = evaluasi_file_manager.extract_filename_from_path(matriks.file_dokumen_matriks)
        if current_filename != filename:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' tidak ditemukan"
            )
        
        try:
            # 6. Store file path for deletion
            file_to_delete = matriks.file_dokumen_matriks
            
            # 7. Clear database field FIRST
            updated_matriks = await self.matriks_repo.update_file_path(matriks_id, None)
            if not updated_matriks:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal memperbarui database"
                )
            
            # 8. Set deleted_by
            updated_matriks.updated_by = deleted_by
            await self.matriks_repo.session.commit()
            
            # 9. Delete file from storage
            storage_deleted = evaluasi_file_manager.delete_file(file_to_delete)
            
            return FileDeleteResponse(
                success=True,
                message=f"File '{filename}' berhasil dihapus",
                entity_id=matriks_id,
                deleted_filename=filename,
                file_type="single",
                remaining_files=0,
                storage_deleted=storage_deleted,
                database_updated=True
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghapus file: {str(e)}"
            )
    
    async def _build_enriched_response(
        self, 
        matriks, 
        surat_tugas_data: Dict[str, Any],
        current_user: Optional[Dict[str, Any]] = None
    ) -> MatriksResponse:
        """Build enriched response dengan permission checking dan conditional data."""
        
        # Extract data dari matriks (bisa dict atau object)
        if isinstance(matriks, dict):
            matriks_id = matriks['id']
            surat_tugas_id = matriks['surat_tugas_id']
            file_dokumen_matriks = matriks.get('file_dokumen_matriks')
            created_at = matriks['created_at']
            updated_at = matriks.get('updated_at')
            created_by = matriks.get('created_by')
            updated_by = matriks.get('updated_by')
            matrix_status = matriks.get('status', MatriksStatus.DRAFTING)
            
            # Create temporary object untuk method calls
            from src.models.matriks import Matriks
            temp_matriks = Matriks()
            temp_matriks.temuan_rekomendasi = matriks.get('temuan_rekomendasi')
            temp_matriks.status = matrix_status
            temp_matriks.temuan_version = matriks.get('temuan_version', 0)
            matriks_obj = temp_matriks
        else:
            matriks_id = matriks.id
            surat_tugas_id = matriks.surat_tugas_id
            file_dokumen_matriks = matriks.file_dokumen_matriks
            created_at = matriks.created_at
            updated_at = matriks.updated_at
            created_by = matriks.created_by
            updated_by = matriks.updated_by
            matrix_status = matriks.status
            matriks_obj = matriks
        
        # Build file URLs dan metadata
        file_urls = None
        file_metadata = None
        if file_dokumen_matriks:
            file_urls = FileUrls(
                file_url=f"/api/matriks/{matriks_id}/file/view",
                view_url=f"/api/matriks/{matriks_id}/file/view",
                download_url=f"/api/matriks/{matriks_id}/file/download"
            )
            
            file_info = evaluasi_file_manager.get_file_info(file_dokumen_matriks)
            if file_info:
                file_metadata = FileMetadata(
                    filename=file_info['filename'],
                    original_filename=file_info.get('original_filename'),
                    size=file_info['size'],
                    size_mb=round(file_info['size'] / 1024 / 1024, 2),
                    content_type=file_info.get('content_type', 'application/octet-stream'),
                    extension=file_info.get('extension', ''),
                    uploaded_at=updated_at or created_at,
                    uploaded_by=updated_by,
                    is_viewable=file_info.get('content_type', '').startswith(('image/', 'application/pdf'))
                )
        
        # Build surat tugas basic info
        surat_tugas_info = SuratTugasBasicInfo(
            id=surat_tugas_id,
            no_surat=surat_tugas_data['no_surat'],
            nama_perwadag=surat_tugas_data['nama_perwadag'],
            inspektorat=surat_tugas_data['inspektorat'],
            tanggal_evaluasi_mulai=surat_tugas_data['tanggal_evaluasi_mulai'],
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            tahun_evaluasi=surat_tugas_data['tahun_evaluasi'],
            durasi_evaluasi=(surat_tugas_data['tanggal_evaluasi_selesai'] - surat_tugas_data['tanggal_evaluasi_mulai']).days + 1,
            evaluation_status=surat_tugas_data.get('evaluation_status', 'active'),
            is_evaluation_active=True
        )
        
        # Get permissions untuk current user
        matrix_permissions = UserPermissions()
        tindak_lanjut_permissions = UserPermissions()
        is_editable = False
        
        if current_user:
            print(f"🔍 DEBUG _build_enriched_response:")
            print(f"   current_user: {current_user}")
            print(f"   surat_tugas_data keys: {list(surat_tugas_data.keys())}")
            print(f"   surat_tugas_data: {surat_tugas_data}")
            
            matrix_permissions = get_matrix_permissions(matrix_status, surat_tugas_data, current_user)
            print(f"   matrix_permissions: {matrix_permissions}")
            
            # Get tindak lanjut permissions (sample dari item pertama)
            items = matriks_obj.get_temuan_rekomendasi_items() if matriks_obj else []
            if items:
                first_item = items[0]
                tl_status = first_item.get('status_tindak_lanjut')
                tindak_lanjut_permissions = get_tindak_lanjut_permissions(
                    tl_status, surat_tugas_data, current_user, matrix_status
                )
            else:
                # Jika tidak ada items, tetap panggil dengan None
                tindak_lanjut_permissions = get_tindak_lanjut_permissions(
                    None, surat_tugas_data, current_user, matrix_status
                )
            
            # ✅ SEKARANG hitung is_editable SETELAH semua permissions didapat
            is_editable = (
                matrix_permissions.can_edit_temuan or 
                matrix_permissions.can_change_matrix_status or
                tindak_lanjut_permissions.can_edit_tindak_lanjut or
                tindak_lanjut_permissions.can_change_tindak_lanjut_status
            )
            
            print(f"   🔍 Final is_editable: {is_editable}")
        
        # Combine permissions
        combined_permissions = UserPermissions(
            can_edit_temuan=matrix_permissions.can_edit_temuan,
            can_change_matrix_status=matrix_permissions.can_change_matrix_status,
            can_edit_tindak_lanjut=tindak_lanjut_permissions.can_edit_tindak_lanjut,
            can_change_tindak_lanjut_status=tindak_lanjut_permissions.can_change_tindak_lanjut_status,
            allowed_matrix_status_changes=matrix_permissions.allowed_matrix_status_changes,
            allowed_tindak_lanjut_status_changes=tindak_lanjut_permissions.allowed_tindak_lanjut_status_changes
        )
        
        # Calculate completion
        has_file = bool(file_dokumen_matriks)
        has_temuan_rekomendasi = False
        temuan_rekomendasi_summary = None
        
        # Handle temuan data berdasarkan user permission
        if matriks_obj and hasattr(matriks_obj, 'get_temuan_rekomendasi_summary'):
            # Check apakah harus hide untuk perwadag
            should_hide = False
            if current_user:
                should_hide = should_hide_temuan_for_perwadag(
                    matrix_status, current_user, surat_tugas_data
                )
            
            if not should_hide:
                summary_data = matriks_obj.get_temuan_rekomendasi_summary()
                if summary_data and summary_data.get('data'):
                    has_temuan_rekomendasi = True
                    temuan_rekomendasi_summary = TemuanRekomendasiSummary(data=summary_data['data'])
        
        completion_percentage = 0
        if has_file and has_temuan_rekomendasi:
            completion_percentage = 100
        elif has_file or has_temuan_rekomendasi:
            completion_percentage = 50
        

        return MatriksResponse(
            id=matriks_id,
            surat_tugas_id=surat_tugas_id,
            surat_tugas_info=surat_tugas_info,
            file_dokumen=file_dokumen_matriks,  # ← GANTI dari file_dokumen_matriks
            file_urls=file_urls,
            file_metadata=file_metadata,
            status=matrix_status,
            is_editable=is_editable,
            user_permissions=combined_permissions,
            has_file=has_file,
            has_temuan_rekomendasi=has_temuan_rekomendasi,
            temuan_rekomendasi_summary=temuan_rekomendasi_summary,
            completion_percentage=completion_percentage,
            is_completed=(completion_percentage == 100),
            temuan_version=getattr(matriks_obj, 'temuan_version', 0),
            
            # ← TAMBAH FIELD-FIELD FLATTENED INI:
            nama_perwadag=surat_tugas_data['nama_perwadag'],
            inspektorat=surat_tugas_data['inspektorat'],
            tanggal_evaluasi_mulai=surat_tugas_data['tanggal_evaluasi_mulai'],
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            tahun_evaluasi=surat_tugas_data['tahun_evaluasi'],
            evaluation_status=surat_tugas_data.get('evaluation_status', 'active'),
            
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by
        )

    async def _get_surat_tugas_basic_info(self, surat_tugas_id: str) -> Optional[Dict[str, Any]]:
            """Get surat tugas basic info dengan field yang lengkap."""
            
            # Query langsung ke database untuk memastikan semua field ada
            from sqlalchemy import select, and_
            from src.models.surat_tugas import SuratTugas
            from src.models.user import User
            
            query = (
                select(
                    SuratTugas.no_surat,
                    SuratTugas.nama_perwadag,
                    SuratTugas.inspektorat,
                    SuratTugas.tanggal_evaluasi_mulai,
                    SuratTugas.tanggal_evaluasi_selesai,
                    SuratTugas.user_perwadag_id,
                    SuratTugas.ketua_tim_id,
                    SuratTugas.pengendali_teknis_id,
                    SuratTugas.pengedali_mutu_id,
                    SuratTugas.pimpinan_inspektorat_id,
                    SuratTugas.anggota_tim_ids,
                    User.nama.label('perwadag_nama')
                )
                .join(User, SuratTugas.user_perwadag_id == User.id)
                .where(
                    and_(
                        SuratTugas.id == surat_tugas_id,
                        SuratTugas.deleted_at.is_(None)
                    )
                )
            )
            
            result = await self.matriks_repo.session.execute(query)
            row = result.fetchone()
            
            if not row:
                return None
            
            # Calculate tahun_evaluasi dari tanggal_evaluasi_mulai
            tahun_evaluasi = row[3].year if row[3] else None  # row[3] = tanggal_evaluasi_mulai
            
            return {
                'no_surat': row[0],
                'nama_perwadag': row[1], 
                'inspektorat': row[2],
                'tanggal_evaluasi_mulai': row[3],
                'tanggal_evaluasi_selesai': row[4],
                'user_perwadag_id': row[5],
                'ketua_tim_id': row[6],
                'pengendali_teknis_id': row[7],
                'pengedali_mutu_id': row[8],
                'pimpinan_inspektorat_id': row[9],
                'anggota_tim_ids': row[10],
                'tahun_evaluasi': tahun_evaluasi,
                'perwadag_nama': row[11],
                'evaluation_status': 'active'
            }

    # async def _get_surat_tugas_basic_info(self, surat_tugas_id: str) -> Optional[Dict[str, Any]]:
    #     """Get basic surat tugas information - FIXED SQL query."""
        
    #     # 🔥 FIX: Remove tahun_evaluasi from select since it's a property
    #     query = (
    #         select(
    #             SuratTugas.no_surat,
    #             SuratTugas.nama_perwadag,
    #             SuratTugas.inspektorat,
    #             SuratTugas.tanggal_evaluasi_mulai,
    #             SuratTugas.tanggal_evaluasi_selesai,
    #             # SuratTugas.tahun_evaluasi,  # 🔥 REMOVED - this is a property
    #             User.nama.label('perwadag_nama')
    #         )
    #         .join(User, SuratTugas.user_perwadag_id == User.id)
    #         .where(
    #             and_(
    #                 SuratTugas.id == surat_tugas_id,
    #                 SuratTugas.deleted_at.is_(None)
    #             )
    #         )
    #     )
        
    #     result = await self.matriks_repo.session.execute(query)
    #     row = result.fetchone()
        
    #     if not row:
    #         return None
        
    #     # Calculate tahun_evaluasi from tanggal_evaluasi_mulai
    #     tahun_evaluasi = row[3].year if row[3] else None  # row[3] = tanggal_evaluasi_mulai
        
    #     return {
    #         'no_surat': row[0],
    #         'nama_perwadag': row[1],
    #         'inspektorat': row[2],
    #         'tanggal_evaluasi_mulai': row[3],
    #         'tanggal_evaluasi_selesai': row[4],
    #         'tahun_evaluasi': tahun_evaluasi,  # Calculated value
    #         'perwadag_nama': row[5],  # Adjusted index
    #         'evaluation_status': 'active'
    #     }

    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics - FIXED untuk model yang actual."""
        
        stats_data = await self.matriks_repo.get_statistics(
            user_role, user_inspektorat, user_id
        )
        
        # 🔥 FIX: Remove has_nomor since model doesn't have nomor_matriks field
        return {
            'total': stats_data['total'],
            'completed': stats_data['completed'],
            'completion_rate': stats_data['completion_rate'],
            'has_file': stats_data['has_file']
            # Removed 'has_nomor' since field doesn't exist
        }
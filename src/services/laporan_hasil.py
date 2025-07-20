# ===== src/services/laporan_hasil.py =====
"""Enhanced service untuk laporan hasil evaluasi - COMPLETELY FIXED."""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, and_

from src.repositories.laporan_hasil import LaporanHasilRepository
from src.schemas.laporan_hasil import (
    LaporanHasilUpdate, LaporanHasilResponse,
    LaporanHasilFileUploadResponse, LaporanHasilListResponse
)
from src.utils.evaluasi_files import evaluasi_file_manager
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)
from src.schemas.filters import LaporanHasilFilterParams
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.utils.evaluation_date_validator import validate_laporan_hasil_date_access



class LaporanHasilService:
    """Enhanced service untuk laporan hasil operations - COMPLETELY FIXED."""
    
    def __init__(self, laporan_hasil_repo: LaporanHasilRepository):
        self.laporan_hasil_repo = laporan_hasil_repo

    async def get_all_laporan_hasil(
        self,
        filters: LaporanHasilFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> LaporanHasilListResponse:
        """Get all laporan hasil dengan enriched data."""
        
        enriched_results, total = await self.laporan_hasil_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build responses
        laporan_hasil_responses = []
        for result in enriched_results:
            response = await self._build_enriched_response(
                result['laporan_hasil'], 
                result['surat_tugas_data']
            )
            laporan_hasil_responses.append(response)
        
        
        # Get statistics if available
        statistics = None
        if hasattr(filters, 'include_statistics') and filters.include_statistics:
            stats_data = await self.laporan_hasil_repo.get_statistics(
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

        response = LaporanHasilListResponse(
            items=laporan_hasil_responses,  # ✅ laporan_hasil → items
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )

        if hasattr(filters, 'include_statistics') and filters.include_statistics:
            response.statistics = statistics

        return response
    
    async def get_laporan_hasil_or_404(self, laporan_hasil_id: str) -> LaporanHasilResponse:
        """Get laporan hasil by ID dengan enriched data."""
        laporan_hasil = await self.laporan_hasil_repo.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil tidak ditemukan"
            )
        
        # Get surat tugas data
        surat_tugas_data = await self._get_surat_tugas_basic_info(laporan_hasil.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas terkait tidak ditemukan"
            )
        
        return await self._build_enriched_response(laporan_hasil, surat_tugas_data)
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[LaporanHasilResponse]:
        """Get laporan hasil by surat tugas ID."""
        laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas_id)
        if not laporan_hasil:
            return None
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_tugas_id)
        if not surat_tugas_data:
            return None
        
        return await self._build_enriched_response(laporan_hasil, surat_tugas_data)
    
    async def update_laporan_hasil(
        self, 
        laporan_hasil_id: str, 
        update_data: LaporanHasilUpdate, 
        updated_by: str
    ) -> LaporanHasilResponse:
        """Update laporan hasil."""
        laporan_hasil = await self.laporan_hasil_repo.update(laporan_hasil_id, update_data)
        if not laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil tidak ditemukan"
            )

        surat_tugas_data = await self._get_surat_tugas_basic_info(laporan_hasil.surat_tugas_id)
        
        # 🔥 VALIDASI AKSES TANGGAL
        validate_laporan_hasil_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="update"
        )

        # Set updated_by
        laporan_hasil.updated_by = updated_by
        await self.laporan_hasil_repo.session.commit()
        
        return await self.get_laporan_hasil_or_404(laporan_hasil_id)
    
    async def upload_file(
        self, 
        laporan_hasil_id: str, 
        file: UploadFile, 
        uploaded_by: str,
        current_user: dict = None
    ) -> LaporanHasilFileUploadResponse:
        """Upload file laporan hasil - FIXED."""
        
        laporan_hasil = await self.laporan_hasil_repo.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil tidak ditemukan"
            )

        surat_tugas_data = await self._get_surat_tugas_basic_info(laporan_hasil.surat_tugas_id)
        
        # 🔥 VALIDASI AKSES TANGGAL
        validate_laporan_hasil_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="upload"
        )

        # 🔥 ADD: Permission check untuk PERWADAG
        if current_user and current_user.get("role") == "PERWADAG":
            # Get surat tugas info untuk check nama_perwadag
            surat_tugas_data = await self._get_surat_tugas_basic_info(laporan_hasil.surat_tugas_id)
            if not surat_tugas_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Surat tugas terkait tidak ditemukan"
                )
            
            user_nama = current_user.get("nama")
            surat_tugas_nama_perwadag = surat_tugas_data.get("nama_perwadag")
            
            if user_nama != surat_tugas_nama_perwadag:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Akses ditolak: Anda hanya dapat mengunggah file untuk laporan hasil Anda sendiri. "
                          f"Yang diharapkan: {surat_tugas_nama_perwadag}, Yang diterima: {user_nama}"
                )
        try:
            # 🔥 FIX: Correct parameter order - file first, then surat_tugas_id
            file_path = await evaluasi_file_manager.upload_laporan_file(
                file, laporan_hasil.surat_tugas_id  # Fixed: file first, surat_tugas_id second
            )
            
            # Update file path di database
            updated_laporan_hasil = await self.laporan_hasil_repo.update_file_path(laporan_hasil_id, file_path)
            if not updated_laporan_hasil:
                # Cleanup uploaded file if database update fails
                evaluasi_file_manager.delete_file(file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal memperbarui path file di database"
                )
            
            # Set uploaded_by
            updated_laporan_hasil.updated_by = uploaded_by
            await self.laporan_hasil_repo.session.commit()
            
            # Build file URL
            file_url = evaluasi_file_manager.get_file_url(file_path)
            
            return LaporanHasilFileUploadResponse(
                success=True,
                message="File berhasil diunggah",
                laporan_hasil_id=laporan_hasil_id,
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
        laporan_hasil_id: str, 
        download_type: str = "download"
    ) -> FileResponse:
        """Download atau view file laporan hasil - FIXED."""
        
        laporan_hasil = await self.laporan_hasil_repo.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil tidak ditemukan"
            )
        
        if not laporan_hasil.file_laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        # 🔥 FIX: Use get_file_download_response instead of download_file
        return evaluasi_file_manager.get_file_download_response(
            file_path=laporan_hasil.file_laporan_hasil,
            original_filename=None,  # Will use filename from path
            download_type=download_type
        )
    
    async def delete_file(
        self, 
        laporan_hasil_id: str, 
        deleted_by: str
    ) -> Dict[str, Any]:
        """Delete file laporan hasil - NEW METHOD."""
        
        laporan_hasil = await self.laporan_hasil_repo.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil tidak ditemukan"
            )
        
        if not laporan_hasil.file_laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tidak ada file untuk dihapus"
            )
        
        try:
            # Store file path for deletion
            file_to_delete = laporan_hasil.file_laporan_hasil
            
            # Clear file path from database
            updated_laporan_hasil = await self.laporan_hasil_repo.update_file_path(laporan_hasil_id, None)
            if not updated_laporan_hasil:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal memperbarui database"
                )
            
            # Delete file from storage
            success = evaluasi_file_manager.delete_file(file_to_delete)
            
            # Set deleted_by
            updated_laporan_hasil.updated_by = deleted_by
            await self.laporan_hasil_repo.session.commit()
            
            return {
                "success": True,
                "message": "File berhasil dihapus",
                "laporan_hasil_id": laporan_hasil_id,
                "deleted_file": file_to_delete,
                "storage_deleted": success
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghapus file: {str(e)}"
            )
    
    async def _get_surat_tugas_basic_info(self, surat_tugas_id: str) -> Optional[Dict[str, Any]]:
        """Get basic surat tugas information - FIXED SQL query."""
        
        # 🔥 FIX: Remove tahun_evaluasi from select since it might be a property
        query = (
            select(
                SuratTugas.no_surat,
                SuratTugas.nama_perwadag,
                SuratTugas.inspektorat,
                SuratTugas.tanggal_evaluasi_mulai,
                SuratTugas.tanggal_evaluasi_selesai,
                # SuratTugas.tahun_evaluasi,  # 🔥 REMOVED - might be property
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
        
        result = await self.laporan_hasil_repo.session.execute(query)
        row = result.fetchone()
        
        if not row:
            return None
        
        # Calculate tahun_evaluasi from tanggal_evaluasi_mulai
        tahun_evaluasi = row[3].year if row[3] else None  # row[3] = tanggal_evaluasi_mulai
        
        return {
            'no_surat': row[0],
            'nama_perwadag': row[1],
            'inspektorat': row[2],
            'tanggal_evaluasi_mulai': row[3],
            'tanggal_evaluasi_selesai': row[4],
            'tahun_evaluasi': tahun_evaluasi,  # Calculated value
            'perwadag_nama': row[5],  # Adjusted index
            'evaluation_status': 'active'
        }
    
    async def _build_enriched_response(
        self, 
        laporan_hasil, 
        surat_tugas_data: Dict[str, Any]
    ) -> LaporanHasilResponse:
        """Build enriched response - COMPLETELY FIXED."""
        
        # Handle dict vs object dan field name yang benar
        if isinstance(laporan_hasil, dict):
            # Repository return dict
            laporan_id = laporan_hasil.get('id')
            surat_tugas_id = laporan_hasil.get('surat_tugas_id')
            nomor_laporan = laporan_hasil.get('nomor_laporan')
            tanggal_laporan = laporan_hasil.get('tanggal_laporan')
            file_laporan_hasil = laporan_hasil.get('file_laporan_hasil')
            created_at = laporan_hasil.get('created_at')
            updated_at = laporan_hasil.get('updated_at')
            created_by = laporan_hasil.get('created_by')
            updated_by = laporan_hasil.get('updated_by')
        else:
            # Repository return object
            laporan_id = laporan_hasil.id
            surat_tugas_id = laporan_hasil.surat_tugas_id
            nomor_laporan = laporan_hasil.nomor_laporan
            tanggal_laporan = laporan_hasil.tanggal_laporan
            file_laporan_hasil = laporan_hasil.file_laporan_hasil
            created_at = laporan_hasil.created_at
            updated_at = laporan_hasil.updated_at
            created_by = laporan_hasil.created_by
            updated_by = laporan_hasil.updated_by
        
        # Build file information - FIXED: Remove await
        file_urls = None
        file_metadata = None
        
        if file_laporan_hasil:
            file_urls = FileUrls(
                file_url=evaluasi_file_manager.get_file_url(file_laporan_hasil),
                download_url=f"/api/v1/laporan-hasil/{laporan_id}/download",
                view_url=f"/api/v1/laporan-hasil/{laporan_id}/view"
            )
            
            # 🔥 FIX: Remove await - get_file_info is NOT async
            file_info = evaluasi_file_manager.get_file_info(file_laporan_hasil)
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
        
        # Calculate completion dengan field yang benar
        has_file = bool(file_laporan_hasil)
        has_nomor = bool(nomor_laporan)
        has_tanggal = bool(tanggal_laporan)
        is_completed = has_file and has_nomor and has_tanggal  # Model requires all 3
        
        # Calculate completion percentage (3 fields: nomor, tanggal, file)
        completed_items = 0
        if has_nomor:
            completed_items += 1
        if has_tanggal:
            completed_items += 1
        if has_file:
            completed_items += 1
        completion_percentage = int((completed_items / 3) * 100)
        
        return LaporanHasilResponse(
            # Basic fields
            id=str(laporan_id),
            surat_tugas_id=str(surat_tugas_id),
            nomor_laporan=nomor_laporan,
            tanggal_laporan=tanggal_laporan,
            file_dokumen=file_laporan_hasil,  # Map to response field name
            
            # Enhanced file information
            file_urls=file_urls,
            file_metadata=file_metadata,
            
            # Status information
            is_completed=is_completed,
            has_file=has_file,
            has_nomor=has_nomor,
            completion_percentage=completion_percentage,
            
            # Enriched surat tugas data
            surat_tugas_info=surat_tugas_info,
            nama_perwadag=surat_tugas_data['perwadag_nama'],
            inspektorat=surat_tugas_data['inspektorat'],
            tanggal_evaluasi_mulai=surat_tugas_data['tanggal_evaluasi_mulai'],
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            tahun_evaluasi=surat_tugas_data['tahun_evaluasi'],
            evaluation_status=surat_tugas_data.get('evaluation_status', 'active'),
            
            # Audit information
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by
        )
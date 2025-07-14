# ===== src/services/surat_pemberitahuan.py =====
"""Service untuk surat pemberitahuan."""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse

from src.repositories.surat_pemberitahuan import SuratPemberitahuanRepository
from src.schemas.surat_pemberitahuan import (
    SuratPemberitahuanUpdate, SuratPemberitahuanResponse,
    SuratPemberitahuanFileUploadResponse, SuratPemberitahuanListResponse
)
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)
from src.schemas.filters import SuratPemberitahuanFilterParams

class SuratPemberitahuanService:
    """Service untuk surat pemberitahuan operations."""
    
    def __init__(self, surat_pemberitahuan_repo: SuratPemberitahuanRepository):
        self.surat_pemberitahuan_repo = surat_pemberitahuan_repo

    async def get_all_surat_pemberitahuan(
        self,
        filters: SuratPemberitahuanFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> SuratPemberitahuanListResponse:
        """Get all surat pemberitahuan dengan enriched data."""
        
        # Get filtered data dari repository
        enriched_results, total = await self.surat_pemberitahuan_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build enriched responses
        responses = []
        for result in enriched_results:
            surat_pemberitahuan = result['surat_pemberitahuan']
            surat_tugas_data = result['surat_tugas_data']
            
            response = await self._build_enriched_response(surat_pemberitahuan, surat_tugas_data)
            responses.append(response)
        
        # Get statistics
        statistics = await self.surat_pemberitahuan_repo.get_statistics(
            user_role, user_inspektorat, user_id
        )
        
        # Build module statistics
        module_stats = ModuleStatistics(
            total_records=statistics["total_records"],
            completed_records=statistics["completed_records"],
            with_files=statistics["with_files"],
            without_files=statistics["without_files"],
            completion_rate=statistics["completion_rate"],
            last_updated=statistics["last_updated"]
        )
        
        # Build pagination info
        pagination = PaginationInfo.create(filters.page, filters.size, total)
        
        return SuratPemberitahuanListResponse(
            surat_pemberitahuan=responses,
            pagination=pagination,
            statistics=module_stats
        )
    
    async def get_surat_pemberitahuan_or_404(
        self, 
        surat_pemberitahuan_id: str,
        session
    ) -> SuratPemberitahuanResponse:
        """Get surat pemberitahuan by ID dengan enriched data."""
        
        # Get surat pemberitahuan
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat pemberitahuan not found"
            )
        
        # Get surat tugas basic info
        surat_tugas_data = await get_surat_tugas_basic_info(session, surat_pemberitahuan.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related surat tugas not found"
            )
        
        return await self._build_enriched_response(surat_pemberitahuan, surat_tugas_data)
    
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[SuratPemberitahuanResponse]:
        """Get surat pemberitahuan by surat tugas ID."""
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas_id)
        if surat_pemberitahuan:
            return self._build_response(surat_pemberitahuan)
        return None
    
    async def update_surat_pemberitahuan(
        self, 
        surat_pemberitahuan_id: str,
        update_data: SuratPemberitahuanUpdate,
        user_id: str
    ) -> SuratPemberitahuanResponse:
        """Update surat pemberitahuan."""
        updated = await self.surat_pemberitahuan_repo.update(surat_pemberitahuan_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat pemberitahuan not found"
            )
        return self._build_response(updated)
    
    async def upload_file(
        self,
        surat_pemberitahuan_id: str,
        file: UploadFile,
        user_id: str
    ) -> SuratPemberitahuanFileUploadResponse:
        """Upload file surat pemberitahuan."""
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat pemberitahuan not found"
            )
        
        # Delete old file if exists
        if surat_pemberitahuan.file_dokumen:
            evaluasi_file_manager.delete_file(surat_pemberitahuan.file_dokumen)
        
        # Upload new file
        file_path = await evaluasi_file_manager.upload_pemberitahuan_file(file, surat_pemberitahuan.surat_tugas_id)
        
        # Update database
        await self.surat_pemberitahuan_repo.update_file_path(surat_pemberitahuan_id, file_path)
        
        return SuratPemberitahuanFileUploadResponse(
            success=True,
            message="File uploaded successfully",
            surat_pemberitahuan_id=surat_pemberitahuan_id,
            file_path=file_path,
            file_url=evaluasi_file_manager.get_file_url(file_path),
            data={"file_path": file_path}
        )
    
    def _build_response(self, surat_pemberitahuan) -> SuratPemberitahuanResponse:
        """Build response from model."""
        return SuratPemberitahuanResponse(
            id=surat_pemberitahuan.id,
            surat_tugas_id=surat_pemberitahuan.surat_tugas_id,
            tanggal_surat_pemberitahuan=surat_pemberitahuan.tanggal_surat_pemberitahuan,
            file_dokumen=surat_pemberitahuan.file_dokumen,
            file_dokumen_url=evaluasi_file_manager.get_file_url(surat_pemberitahuan.file_dokumen) if surat_pemberitahuan.file_dokumen else None,
            is_completed=surat_pemberitahuan.is_completed(),
            has_file=surat_pemberitahuan.has_file(),
            has_date=surat_pemberitahuan.has_date(),
            completion_percentage=surat_pemberitahuan.get_completion_percentage(),
            created_at=surat_pemberitahuan.created_at,
            updated_at=surat_pemberitahuan.updated_at
        )

    async def download_file(
        self, 
        surat_pemberitahuan_id: str, 
        download_type: str = "download"
    ) -> FileResponse:
        """Download surat pemberitahuan file."""
        
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan or not surat_pemberitahuan.file_dokumen:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Get original filename untuk download
        original_filename = f"surat_pemberitahuan_{surat_pemberitahuan.surat_tugas_id}"
        
        return evaluasi_file_manager.get_file_download_response(
            file_path=surat_pemberitahuan.file_dokumen,
            original_filename=original_filename,
            download_type=download_type
        )
    
    async def _build_enriched_response(
        self, 
        surat_pemberitahuan, 
        surat_tugas_data: Dict[str, Any]
    ) -> SuratPemberitahuanResponse:
        """Build enriched response dengan surat tugas data."""
        
        # Build surat tugas basic info
        surat_tugas_info = SuratTugasBasicInfo(
            id=surat_tugas_data['id'],
            no_surat=surat_tugas_data['no_surat'],
            nama_perwadag=surat_tugas_data['nama_perwadag'],
            inspektorat=surat_tugas_data['inspektorat'],
            tanggal_evaluasi_mulai=surat_tugas_data['tanggal_evaluasi_mulai'],
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            tahun_evaluasi=surat_tugas_data['tahun_evaluasi'],
            durasi_evaluasi=surat_tugas_data['durasi_evaluasi'],
            evaluation_status=surat_tugas_data['evaluation_status'],
            is_evaluation_active=surat_tugas_data['is_evaluation_active']
        )
        
        # Build file URLs and metadata
        file_urls = None
        file_metadata = None
        
        if surat_pemberitahuan.file_dokumen:
            file_info = evaluasi_file_manager.get_file_info(surat_pemberitahuan.file_dokumen)
            if file_info:
                file_urls = FileUrls(
                    file_url=file_info['url'],
                    download_url=f"/api/v1/evaluasi/surat-pemberitahuan/{surat_pemberitahuan.id}/download",
                    view_url=f"/api/v1/evaluasi/surat-pemberitahuan/{surat_pemberitahuan.id}/view"
                )
                
                file_metadata = FileMetadata(
                    filename=file_info['filename'],
                    size=file_info['size'],
                    size_mb=file_info['size_mb'],
                    content_type=file_info['content_type'],
                    extension=file_info['extension'],
                    uploaded_at=surat_pemberitahuan.created_at,
                    is_viewable=file_info['is_viewable']
                )
        
        return SuratPemberitahuanResponse(
            id=surat_pemberitahuan.id,
            surat_tugas_id=surat_pemberitahuan.surat_tugas_id,
            tanggal_surat_pemberitahuan=surat_pemberitahuan.tanggal_surat_pemberitahuan,
            file_dokumen=surat_pemberitahuan.file_dokumen,
            file_urls=file_urls,
            file_metadata=file_metadata,
            is_completed=surat_pemberitahuan.is_completed(),
            has_file=surat_pemberitahuan.has_file(),
            has_date=surat_pemberitahuan.has_date(),
            completion_percentage=surat_pemberitahuan.get_completion_percentage(),
            surat_tugas_info=surat_tugas_info,
            nama_perwadag=surat_tugas_data['nama_perwadag'],
            inspektorat=surat_tugas_data['inspektorat'],
            tanggal_evaluasi_mulai=surat_tugas_data['tanggal_evaluasi_mulai'],
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            tahun_evaluasi=surat_tugas_data['tahun_evaluasi'],
            evaluation_status=surat_tugas_data['evaluation_status'],
            created_at=surat_pemberitahuan.created_at,
            updated_at=surat_pemberitahuan.updated_at,
            created_by=surat_pemberitahuan.created_by,
            updated_by=surat_pemberitahuan.updated_by
        )
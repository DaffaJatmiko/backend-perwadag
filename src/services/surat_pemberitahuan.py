# ===== src/services/surat_pemberitahuan.py =====
"""Service untuk surat pemberitahuan."""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from sqlalchemy import select, and_

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
from src.utils.evaluation_date_validator import validate_surat_pemberitahuan_date_access


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
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0

        response = SuratPemberitahuanListResponse(
            items=responses,  # ✅ surat_pemberitahuan → items
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
        response.statistics = module_stats
        return response
    
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
        updated_by: str
    ) -> SuratPemberitahuanResponse:
        """Update surat pemberitahuan dengan date validation."""
        
        # 1. Get surat pemberitahuan
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat pemberitahuan tidak ditemukan"
            )
        
        # 2. Get surat tugas info untuk date validation
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_pemberitahuan.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas terkait tidak ditemukan"
            )
        
        # 3. 🔥 VALIDASI AKSES TANGGAL
        from src.utils.evaluation_date_validator import validate_surat_pemberitahuan_date_access
        validate_surat_pemberitahuan_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="update"
        )
        
        # 4. Update surat pemberitahuan
        updated_surat_pemberitahuan = await self.surat_pemberitahuan_repo.update(surat_pemberitahuan_id, update_data)
        if not updated_surat_pemberitahuan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gagal mengupdate surat pemberitahuan"
            )
        
        # Set updated_by
        updated_surat_pemberitahuan.updated_by = updated_by
        await self.surat_pemberitahuan_repo.session.commit()
        
        # 5. Return enriched response
        return await self._build_enriched_response(updated_surat_pemberitahuan, surat_tugas_data)
    
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
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_pemberitahuan.surat_tugas_id)
        
        # 🔥 VALIDASI AKSES TANGGAL
        validate_surat_pemberitahuan_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="upload"
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
    
    async def _get_surat_tugas_basic_info(self, surat_tugas_id: str) -> Optional[Dict[str, Any]]:
        """Get basic surat tugas information untuk enriched response."""
        query = (
            select(
                SuratTugas.no_surat,
                SuratTugas.nama_perwadag,
                SuratTugas.inspektorat,
                SuratTugas.tanggal_evaluasi_mulai,
                SuratTugas.tanggal_evaluasi_selesai,
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
        
        result = await self.surat_pemberitahuan_repo.session.execute(query)
        row = result.fetchone()
        
        if not row:
            return None
        
        return {
            'no_surat': row[0],
            'nama_perwadag': row[1],
            'inspektorat': row[2],
            'tanggal_evaluasi_mulai': row[3],
            'tanggal_evaluasi_selesai': row[4],
            'tahun_evaluasi': row[3].year,
            'perwadag_nama': row[5],
            'evaluation_status': 'active'
        }

    async def _build_enriched_response(
        self, 
        surat_pemberitahuan, 
        surat_tugas_data: Dict[str, Any]
    ) -> SuratPemberitahuanResponse:
        """Build enriched response dengan surat tugas data dan file information."""
        
        # Build file information
        file_urls = None
        file_metadata = None
        
        if surat_pemberitahuan.file_dokumen:
            file_info = evaluasi_file_manager.get_file_info(surat_pemberitahuan.file_dokumen)
            
            file_urls = FileUrls(
                file_url=evaluasi_file_manager.get_file_url(surat_pemberitahuan.file_dokumen),
                download_url=f"/api/v1/evaluasi/surat-pemberitahuan/{surat_pemberitahuan.id}/download",
                view_url=f"/api/v1/evaluasi/surat-pemberitahuan/{surat_pemberitahuan.id}/view"
            )
            
            if file_info:
                file_metadata = FileMetadata(
                    filename=file_info['filename'],
                    original_filename=file_info.get('original_filename'),
                    size=file_info['size'],
                    size_mb=round(file_info['size'] / 1024 / 1024, 2),
                    content_type=file_info.get('content_type', 'application/octet-stream'),
                    extension=file_info.get('extension', ''),
                    uploaded_at=surat_pemberitahuan.updated_at or surat_pemberitahuan.created_at,
                    uploaded_by=surat_pemberitahuan.updated_by,
                    is_viewable=file_info.get('content_type', '').startswith(('image/', 'application/pdf'))
                )
        
        # Build surat tugas basic info
        surat_tugas_info = SuratTugasBasicInfo(
            id=surat_pemberitahuan.surat_tugas_id,
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
            nama_perwadag=surat_tugas_data['perwadag_nama'],
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
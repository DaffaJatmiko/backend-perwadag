# ===== src/services/surat_pemberitahuan.py =====
"""Service untuk surat pemberitahuan."""

from typing import Optional
from fastapi import HTTPException, status, UploadFile

from src.repositories.surat_pemberitahuan import SuratPemberitahuanRepository
from src.schemas.surat_pemberitahuan import (
    SuratPemberitahuanUpdate, SuratPemberitahuanResponse,
    SuratPemberitahuanFileUploadResponse
)
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager


class SuratPemberitahuanService:
    """Service untuk surat pemberitahuan operations."""
    
    def __init__(self, surat_pemberitahuan_repo: SuratPemberitahuanRepository):
        self.surat_pemberitahuan_repo = surat_pemberitahuan_repo
    
    async def get_surat_pemberitahuan_or_404(self, surat_pemberitahuan_id: str) -> SuratPemberitahuanResponse:
        """Get surat pemberitahuan by ID atau raise 404."""
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat pemberitahuan not found"
            )
        return self._build_response(surat_pemberitahuan)
    
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
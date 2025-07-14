# ===== src/services/laporan_hasil.py =====
"""Service untuk laporan hasil."""

from typing import Optional
from fastapi import HTTPException, status, UploadFile

from src.repositories.laporan_hasil import LaporanHasilRepository
from src.schemas.laporan_hasil import (
    LaporanHasilUpdate, LaporanHasilResponse, LaporanHasilFileUploadResponse
)
from src.utils.evaluasi_files import evaluasi_file_manager


class LaporanHasilService:
    """Service untuk laporan hasil operations."""
    
    def __init__(self, laporan_hasil_repo: LaporanHasilRepository):
        self.laporan_hasil_repo = laporan_hasil_repo
    
    async def get_laporan_hasil_or_404(self, laporan_hasil_id: str) -> LaporanHasilResponse:
        """Get laporan hasil by ID atau raise 404."""
        laporan_hasil = await self.laporan_hasil_repo.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil not found"
            )
        return self._build_response(laporan_hasil)
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[LaporanHasilResponse]:
        """Get laporan hasil by surat tugas ID."""
        laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas_id)
        if laporan_hasil:
            return self._build_response(laporan_hasil)
        return None
    
    async def update_laporan_hasil(
        self, 
        laporan_hasil_id: str,
        update_data: LaporanHasilUpdate,
        user_id: str
    ) -> LaporanHasilResponse:
        """Update laporan hasil - PERWADAG dapat full edit."""
        updated = await self.laporan_hasil_repo.update(laporan_hasil_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil not found"
            )
        return self._build_response(updated)
    
    async def upload_file(
        self,
        laporan_hasil_id: str,
        file: UploadFile,
        user_id: str
    ) -> LaporanHasilFileUploadResponse:
        """Upload file laporan hasil."""
        laporan_hasil = await self.laporan_hasil_repo.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Laporan hasil not found"
            )
        
        # Delete old file if exists
        if laporan_hasil.file_laporan_hasil:
            evaluasi_file_manager.delete_file(laporan_hasil.file_laporan_hasil)
        
        # Upload new file
        file_path = await evaluasi_file_manager.upload_laporan_file(file, laporan_hasil.surat_tugas_id)
        
        # Update database
        await self.laporan_hasil_repo.update_file_path(laporan_hasil_id, file_path)
        
        return LaporanHasilFileUploadResponse(
            success=True,
            message="File uploaded successfully",
            laporan_hasil_id=laporan_hasil_id,
            file_path=file_path,
            file_url=evaluasi_file_manager.get_file_url(file_path),
            data={"file_path": file_path}
        )
    
    def _build_response(self, laporan_hasil) -> LaporanHasilResponse:
        """Build response from model."""
        return LaporanHasilResponse(
            id=laporan_hasil.id,
            surat_tugas_id=laporan_hasil.surat_tugas_id,
            nomor_laporan=laporan_hasil.nomor_laporan,
            tanggal_laporan=laporan_hasil.tanggal_laporan,
            file_laporan_hasil=laporan_hasil.file_laporan_hasil,
            file_laporan_hasil_url=evaluasi_file_manager.get_file_url(laporan_hasil.file_laporan_hasil) if laporan_hasil.file_laporan_hasil else None,
            is_completed=laporan_hasil.is_completed(),
            has_file=laporan_hasil.has_file(),
            has_nomor_laporan=laporan_hasil.has_nomor_laporan(),
            has_tanggal_laporan=laporan_hasil.has_tanggal_laporan(),
            completion_percentage=laporan_hasil.get_completion_percentage(),
            created_at=laporan_hasil.created_at,
            updated_at=laporan_hasil.updated_at
        )

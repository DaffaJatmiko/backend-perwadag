# ===== src/services/matriks.py =====
"""Service untuk matriks."""

from typing import Optional
from fastapi import HTTPException, status, UploadFile

from src.repositories.matriks import MatriksRepository
from src.schemas.matriks import MatriksResponse, MatriksFileUploadResponse
from src.utils.evaluasi_files import evaluasi_file_manager


class MatriksService:
    """Service untuk matriks operations."""
    
    def __init__(self, matriks_repo: MatriksRepository):
        self.matriks_repo = matriks_repo
    
    async def get_matriks_or_404(self, matriks_id: str) -> MatriksResponse:
        """Get matriks by ID atau raise 404."""
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks not found"
            )
        return self._build_response(matriks)
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[MatriksResponse]:
        """Get matriks by surat tugas ID."""
        matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
        if matriks:
            return self._build_response(matriks)
        return None
    
    async def upload_file(
        self,
        matriks_id: str,
        file: UploadFile,
        user_id: str
    ) -> MatriksFileUploadResponse:
        """Upload file matriks."""
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks not found"
            )
        
        # Delete old file if exists
        if matriks.file_dokumen_matriks:
            evaluasi_file_manager.delete_file(matriks.file_dokumen_matriks)
        
        # Upload new file
        file_path = await evaluasi_file_manager.upload_matriks_file(file, matriks.surat_tugas_id)
        
        # Update database
        await self.matriks_repo.update_file_path(matriks_id, file_path)
        
        return MatriksFileUploadResponse(
            success=True,
            message="File uploaded successfully",
            matriks_id=matriks_id,
            file_path=file_path,
            file_url=evaluasi_file_manager.get_file_url(file_path),
            data={"file_path": file_path}
        )
    
    def _build_response(self, matriks) -> MatriksResponse:
        """Build response from model."""
        return MatriksResponse(
            id=matriks.id,
            surat_tugas_id=matriks.surat_tugas_id,
            file_dokumen_matriks=matriks.file_dokumen_matriks,
            file_dokumen_matriks_url=evaluasi_file_manager.get_file_url(matriks.file_dokumen_matriks) if matriks.file_dokumen_matriks else None,
            is_completed=matriks.is_completed(),
            has_file=matriks.has_file(),
            completion_percentage=matriks.get_completion_percentage(),
            created_at=matriks.created_at,
            updated_at=matriks.updated_at
        )


# ===== src/services/kuisioner.py =====
"""Service untuk kuisioner."""

from typing import Optional
from fastapi import HTTPException, status, UploadFile

from src.repositories.kuisioner import KuisionerRepository
from src.schemas.kuisioner import KuisionerResponse, KuisionerFileUploadResponse
from src.utils.evaluasi_files import evaluasi_file_manager


class KuisionerService:
    """Service untuk kuisioner operations."""
    
    def __init__(self, kuisioner_repo: KuisionerRepository):
        self.kuisioner_repo = kuisioner_repo
    
    async def get_kuisioner_or_404(self, kuisioner_id: str) -> KuisionerResponse:
        """Get kuisioner by ID atau raise 404."""
        kuisioner = await self.kuisioner_repo.get_by_id(kuisioner_id)
        if not kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kuisioner not found"
            )
        return self._build_response(kuisioner)
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[KuisionerResponse]:
        """Get kuisioner by surat tugas ID."""
        kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas_id)
        if kuisioner:
            return self._build_response(kuisioner)
        return None
    
    async def upload_file(
        self,
        kuisioner_id: str,
        file: UploadFile,
        user_id: str
    ) -> KuisionerFileUploadResponse:
        """Upload file kuisioner - PERWADAG dapat upload."""
        kuisioner = await self.kuisioner_repo.get_by_id(kuisioner_id)
        if not kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kuisioner not found"
            )
        
        # Delete old file if exists
        if kuisioner.file_kuisioner:
            evaluasi_file_manager.delete_file(kuisioner.file_kuisioner)
        
        # Upload new file
        file_path = await evaluasi_file_manager.upload_kuisioner_file(file, kuisioner.surat_tugas_id)
        
        # Update database
        await self.kuisioner_repo.update_file_path(kuisioner_id, file_path)
        
        return KuisionerFileUploadResponse(
            success=True,
            message="File uploaded successfully",
            kuisioner_id=kuisioner_id,
            file_path=file_path,
            file_url=evaluasi_file_manager.get_file_url(file_path),
            data={"file_path": file_path}
        )
    
    def _build_response(self, kuisioner) -> KuisionerResponse:
        """Build response from model."""
        return KuisionerResponse(
            id=kuisioner.id,
            surat_tugas_id=kuisioner.surat_tugas_id,
            file_kuisioner=kuisioner.file_kuisioner,
            file_kuisioner_url=evaluasi_file_manager.get_file_url(kuisioner.file_kuisioner) if kuisioner.file_kuisioner else None,
            is_completed=kuisioner.is_completed(),
            has_file=kuisioner.has_file(),
            completion_percentage=kuisioner.get_completion_percentage(),
            created_at=kuisioner.created_at,
            updated_at=kuisioner.updated_at
        )

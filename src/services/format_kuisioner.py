# ===== src/services/format_kuisioner.py =====
"""Service untuk format kuisioner master templates."""

from typing import List
from fastapi import HTTPException, status, UploadFile

from src.repositories.format_kuisioner import FormatKuisionerRepository
from src.schemas.format_kuisioner import (
    FormatKuisionerCreate, FormatKuisionerUpdate, FormatKuisionerResponse,
    FormatKuisionerListResponse, FormatKuisionerFileUploadResponse
)
from src.schemas.filters import FormatKuisionerFilterParams
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager


class FormatKuisionerService:
    """Service untuk format kuisioner master template management."""
    
    def __init__(self, format_kuisioner_repo: FormatKuisionerRepository):
        self.format_kuisioner_repo = format_kuisioner_repo
    
    async def create_format_kuisioner(
        self,
        format_kuisioner_data: FormatKuisionerCreate,
        file: UploadFile,
        user_id: str
    ) -> FormatKuisionerResponse:
        """Create format kuisioner baru dengan file upload."""
        
        # Check if template dengan nama sama sudah exists untuk tahun tersebut
        if await self.format_kuisioner_repo.template_exists_for_year(
            format_kuisioner_data.nama_template,
            format_kuisioner_data.tahun
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template '{format_kuisioner_data.nama_template}' already exists for year {format_kuisioner_data.tahun}"
            )
        
        # Upload file
        file_path = await evaluasi_file_manager.upload_format_kuisioner(file, format_kuisioner_data.tahun)
        
        try:
            # Create record
            format_kuisioner = await self.format_kuisioner_repo.create(format_kuisioner_data, file_path)
            return self._build_response(format_kuisioner)
            
        except Exception as e:
            # Cleanup file if database operation fails
            evaluasi_file_manager.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create format kuisioner: {str(e)}"
            )
    
    async def get_format_kuisioner_or_404(self, format_kuisioner_id: str) -> FormatKuisionerResponse:
        """Get format kuisioner by ID atau raise 404."""
        format_kuisioner = await self.format_kuisioner_repo.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Format kuisioner not found"
            )
        return self._build_response(format_kuisioner)
    
    async def get_all_format_kuisioner(self, filters: FormatKuisionerFilterParams) -> FormatKuisionerListResponse:
        """Get all format kuisioner dengan filtering."""
        format_kuisioner_list, total = await self.format_kuisioner_repo.get_all_filtered(filters)
        
        # Build responses
        responses = [self._build_response(fk) for fk in format_kuisioner_list]
        
        # Calculate pages
        pages = (total + filters.size - 1) // filters.size
        
        return FormatKuisionerListResponse(
            format_kuisioner=responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
    
    async def get_by_tahun(self, tahun: int) -> List[FormatKuisionerResponse]:
        """Get all format kuisioner untuk tahun tertentu."""
        format_kuisioner_list = await self.format_kuisioner_repo.get_by_tahun(tahun)
        return [self._build_response(fk) for fk in format_kuisioner_list]
    
    async def update_format_kuisioner(
        self,
        format_kuisioner_id: str,
        update_data: FormatKuisionerUpdate,
        user_id: str
    ) -> FormatKuisionerResponse:
        """Update format kuisioner."""
        format_kuisioner = await self.format_kuisioner_repo.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Format kuisioner not found"
            )
        
        # Check nama template uniqueness untuk tahun tersebut jika diupdate
        if update_data.nama_template or update_data.tahun:
            new_nama = update_data.nama_template or format_kuisioner.nama_template
            new_tahun = update_data.tahun or format_kuisioner.tahun
            
            if await self.format_kuisioner_repo.template_exists_for_year(
                new_nama, new_tahun, exclude_id=format_kuisioner_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Template '{new_nama}' already exists for year {new_tahun}"
                )
        
        updated = await self.format_kuisioner_repo.update(format_kuisioner_id, update_data)
        return self._build_response(updated)
    
    async def upload_template_file(
        self,
        format_kuisioner_id: str,
        file: UploadFile,
        user_id: str
    ) -> FormatKuisionerFileUploadResponse:
        """Upload or replace template file."""
        format_kuisioner = await self.format_kuisioner_repo.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Format kuisioner not found"
            )
        
        # Delete old file if exists
        if format_kuisioner.link_template:
            evaluasi_file_manager.delete_file(format_kuisioner.link_template)
        
        # Upload new file
        file_path = await evaluasi_file_manager.upload_format_kuisioner(file, format_kuisioner.tahun)
        
        # Update database
        await self.format_kuisioner_repo.update_file_path(format_kuisioner_id, file_path)
        
        return FormatKuisionerFileUploadResponse(
            success=True,
            message="Template file uploaded successfully",
            format_kuisioner_id=format_kuisioner_id,
            file_path=file_path,
            file_url=evaluasi_file_manager.get_file_url(file_path),
            data={"file_path": file_path}
        )
    
    async def delete_format_kuisioner(self, format_kuisioner_id: str, user_id: str) -> SuccessResponse:
        """Delete format kuisioner (admin only)."""
        format_kuisioner = await self.format_kuisioner_repo.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Format kuisioner not found"
            )
        
        # Delete file from storage
        if format_kuisioner.link_template:
            evaluasi_file_manager.delete_file(format_kuisioner.link_template)
        
        # Soft delete from database
        await self.format_kuisioner_repo.soft_delete(format_kuisioner_id)
        
        return SuccessResponse(
            success=True,
            message=f"Format kuisioner '{format_kuisioner.nama_template}' deleted successfully",
            data={"deleted_id": format_kuisioner_id}
        )
    
    def _build_response(self, format_kuisioner) -> FormatKuisionerResponse:
        """Build response from model."""
        return FormatKuisionerResponse(
            id=format_kuisioner.id,
            nama_template=format_kuisioner.nama_template,
            deskripsi=format_kuisioner.deskripsi,
            tahun=format_kuisioner.tahun,
            link_template=format_kuisioner.link_template,
            link_template_url=evaluasi_file_manager.get_file_url(format_kuisioner.link_template) if format_kuisioner.link_template else "",
            display_name=format_kuisioner.display_name,
            has_file=format_kuisioner.has_file(),
            is_downloadable=format_kuisioner.is_downloadable(),
            file_extension=format_kuisioner.get_file_extension(),
            created_at=format_kuisioner.created_at,
            updated_at=format_kuisioner.updated_at
        )
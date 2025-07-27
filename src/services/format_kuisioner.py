# ===== src/services/format_kuisioner.py =====
"""Service untuk format kuisioner master templates - FIXED."""

from typing import List, Dict, Optional
from datetime import datetime
from fastapi import HTTPException, status, UploadFile

from src.repositories.format_kuisioner import FormatKuisionerRepository
from src.schemas.format_kuisioner import (
    FormatKuisionerCreate, FormatKuisionerUpdate, FormatKuisionerResponse,
    FormatKuisionerListResponse, FormatKuisionerFileUploadResponse
)
from src.schemas.filters import FormatKuisionerFilterParams
from src.schemas.common import SuccessResponse
from src.schemas.shared import PaginationInfo, ModuleStatistics, FileUrls, FileMetadata
from src.utils.evaluasi_files import evaluasi_file_manager
from src.schemas.shared import FileDeleteResponse



class FormatKuisionerService:
    """Service untuk format kuisioner master template management - COMPLETELY FIXED."""
    
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
                detail=f"Template '{format_kuisioner_data.nama_template}' sudah ada untuk tahun {format_kuisioner_data.tahun}"
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
                detail=f"Gagal membuat format kuisioner: {str(e)}"
            )
    
    async def get_format_kuisioner_or_404(self, format_kuisioner_id: str) -> FormatKuisionerResponse:
        """Get format kuisioner by ID atau raise 404."""
        format_kuisioner = await self.format_kuisioner_repo.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Format kuisioner tidak ditemukan"
            )
        return self._build_response(format_kuisioner)
    
    async def get_all_format_kuisioner(self, filters: FormatKuisionerFilterParams) -> FormatKuisionerListResponse:
        """Get all format kuisioner dengan filtering - COMPLETELY FIXED."""
        format_kuisioner_list, total = await self.format_kuisioner_repo.get_all_filtered(filters)
        
        # Build responses
        responses = [self._build_response(fk) for fk in format_kuisioner_list]
        
        # 🔥 FIX: Build by_year_summary
        by_year_summary = {}
        current_year = datetime.now().year
        current_year_count = 0
        
        for fk in format_kuisioner_list:
            year = fk.tahun
            by_year_summary[year] = by_year_summary.get(year, 0) + 1
            if year == current_year:
                current_year_count += 1
        
        # 🔥 FIX: Build statistics if available
        statistics = None
        if hasattr(filters, 'include_statistics') and filters.include_statistics:
            statistics = ModuleStatistics(
                total=total,
                completed=len([fk for fk in format_kuisioner_list if fk.link_template]),
                completion_rate=len([fk for fk in format_kuisioner_list if fk.link_template]) / total * 100 if total > 0 else 0,
                has_file=len([fk for fk in format_kuisioner_list if fk.link_template]),
                module_specific_stats={
                    'by_year': by_year_summary,
                    'current_year_templates': current_year_count
                }
            )
        
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0

        response = FormatKuisionerListResponse(
            items=responses,  # ✅ format_kuisioner → items
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )

        if hasattr(filters, 'include_statistics') and filters.include_statistics:
            response.statistics = statistics

        # response.by_year_summary = by_year_summary
        # ❌ HAPUS: current_year_templates

        return response
    
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
                detail="Format kuisioner tidak ditemukan"
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
                    detail=f"Template '{new_nama}' sudah ada untuk tahun {new_tahun}"
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
                detail="Format kuisioner tidak ditemukan"
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
            message="File template berhasil diunggah",
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
                detail="Format kuisioner tidak ditemukan"
            )
        
        # Delete file from storage
        if format_kuisioner.link_template:
            evaluasi_file_manager.delete_file(format_kuisioner.link_template)
        
        # Soft delete from database
        await self.format_kuisioner_repo.soft_delete(format_kuisioner_id)
        
        return SuccessResponse(
            success=True,
            message=f"Format kuisioner '{format_kuisioner.nama_template}' berhasil dihapus",
            data={"deleted_id": format_kuisioner_id}
        )

    async def delete_file_by_filename(
        self,
        format_kuisioner_id: str,
        filename: str,
        deleted_by: str,
        current_user: dict = None
    ) -> FileDeleteResponse:
        """Delete file format kuisioner by filename."""
        
        # 1. Get format kuisioner
        format_kuisioner = await self.format_kuisioner_repo.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Format kuisioner tidak ditemukan"
            )
        
        # 2. Check file exists
        if not format_kuisioner.link_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tidak ada file untuk dihapus"
            )
        
        # 3. Validate filename matches
        current_filename = evaluasi_file_manager.extract_filename_from_path(format_kuisioner.link_template)
        if current_filename != filename:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' tidak ditemukan"
            )
        
        try:
            # 4. Store file path for deletion
            file_to_delete = format_kuisioner.link_template
            
            # 5. Clear database field FIRST
            updated_format_kuisioner = await self.format_kuisioner_repo.update_file_path(format_kuisioner_id, "")
            if not updated_format_kuisioner:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal memperbarui database"
                )
            
            # 6. Set deleted_by
            updated_format_kuisioner.updated_by = deleted_by
            await self.format_kuisioner_repo.session.commit()
            
            # 7. Delete file from storage
            storage_deleted = evaluasi_file_manager.delete_file(file_to_delete)
            
            return FileDeleteResponse(
                success=True,
                message=f"File '{filename}' berhasil dihapus",
                entity_id=format_kuisioner_id,
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

    async def get_active_template(self) -> Optional[FormatKuisionerResponse]:
        """Get active format kuisioner template."""
        template = await self.format_kuisioner_repo.get_active_template()
        if not template:
            return None
        return self._build_response(template)

    async def activate_template(self, format_kuisioner_id: str) -> FormatKuisionerResponse:
        """Activate format kuisioner template (auto-deactivate others)."""
        format_kuisioner = await self.format_kuisioner_repo.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Format kuisioner tidak ditemukan"
            )
        
        activated = await self.format_kuisioner_repo.activate_template(format_kuisioner_id)
        return self._build_response(activated)
    
    def _build_response(self, format_kuisioner) -> FormatKuisionerResponse:
        """Build response from model - ENHANCED."""
        
        # Enhanced file information
        file_urls = None
        file_metadata = None
        
        if format_kuisioner.link_template:
            file_urls = FileUrls(
                file_url=evaluasi_file_manager.get_file_url(format_kuisioner.link_template),
                download_url=f"/api/v1/evaluasi/format-kuisioner/{format_kuisioner.id}/download",
                view_url=f"/api/v1/evaluasi/format-kuisioner/{format_kuisioner.id}/view"
            )
            
            # Get file info - FIXED: Remove await
            file_info = evaluasi_file_manager.get_file_info(format_kuisioner.link_template)
            if file_info:
                file_metadata = FileMetadata(
                    filename=file_info['filename'],
                    original_filename=file_info.get('original_filename'),
                    size=file_info['size'],
                    size_mb=round(file_info['size'] / 1024 / 1024, 2),
                    content_type=file_info.get('content_type', 'application/octet-stream'),
                    extension=file_info.get('extension', ''),
                    uploaded_at=format_kuisioner.updated_at or format_kuisioner.created_at,
                    uploaded_by=getattr(format_kuisioner, 'updated_by', None),
                    is_viewable=file_info.get('content_type', '').startswith(('image/', 'application/pdf'))
                )
        
        # Mock usage statistics (implement proper tracking if needed)
        usage_count = 0
        last_used = None
        
        return FormatKuisionerResponse(
            # Basic fields
            id=format_kuisioner.id,
            nama_template=format_kuisioner.nama_template,
            deskripsi=format_kuisioner.deskripsi,
            tahun=format_kuisioner.tahun,
            link_template=format_kuisioner.link_template or "",
            
            # Enhanced file information
            file_urls=file_urls,
            file_metadata=file_metadata,
            
            # Computed fields
            display_name=getattr(format_kuisioner, 'display_name', format_kuisioner.nama_template),
            has_file=bool(format_kuisioner.link_template),
            is_downloadable=bool(format_kuisioner.link_template),
            is_active=format_kuisioner.is_active,
            
            # Usage statistics
            usage_count=usage_count,
            last_used=last_used,
            
            # Audit information
            created_at=format_kuisioner.created_at,
            updated_at=format_kuisioner.updated_at,
            created_by=getattr(format_kuisioner, 'created_by', None),
            updated_by=getattr(format_kuisioner, 'updated_by', None)
        )
# ===== src/services/kuisioner.py =====
"""Enhanced service untuk kuisioner evaluasi."""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, and_

from src.repositories.kuisioner import KuisionerRepository
from src.schemas.kuisioner import (
    KuisionerUpdate, KuisionerResponse,
    KuisionerFileUploadResponse, KuisionerListResponse
)
from src.utils.evaluasi_files import evaluasi_file_manager
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)
from src.schemas.filters import KuisionerFilterParams
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.utils.evaluation_date_validator import validate_kuisioner_date_access


class KuisionerService:
    """Enhanced service untuk kuisioner operations."""
    
    def __init__(self, kuisioner_repo: KuisionerRepository):
        self.kuisioner_repo = kuisioner_repo

    async def get_all_kuisioner(
        self,
        filters: KuisionerFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> KuisionerListResponse:
        """Get all kuisioner dengan enriched data - FIXED."""
        
        enriched_results, total = await self.kuisioner_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build responses
        kuisioner_responses = []
        for result in enriched_results:
            response = await self._build_enriched_response(
                result['kuisioner'], 
                result['surat_tugas_data']
            )
            kuisioner_responses.append(response)
        
        # Build pagination
        
        # 🔥 FIX: Remove include_statistics (not available in filter params)
        statistics = None
        
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0

        response = KuisionerListResponse(
            items=kuisioner_responses,  # ✅ kuisioner → items
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )

        # Statistics biasanya None di kuisioner, jadi bisa skip
        return response

    
    async def get_kuisioner_or_404(self, kuisioner_id: str) -> KuisionerResponse:
        """Get kuisioner by ID dengan enriched data."""
        kuisioner = await self.kuisioner_repo.get_by_id(kuisioner_id)
        if not kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kuisioner tidak ditemukan"
            )
        
        # Get surat tugas data
        surat_tugas_data = await self._get_surat_tugas_basic_info(kuisioner.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas terkait tidak ditemukan"
            )
        
        return await self._build_enriched_response(kuisioner, surat_tugas_data)
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[KuisionerResponse]:
        """Get kuisioner by surat tugas ID."""
        kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas_id)
        if not kuisioner:
            return None
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_tugas_id)
        if not surat_tugas_data:
            return None
        
        return await self._build_enriched_response(kuisioner, surat_tugas_data)
    
    async def update_kuisioner(
        self, 
        kuisioner_id: str, 
        update_data: KuisionerUpdate, 
        updated_by: str
    ) -> KuisionerResponse:
        """Update kuisioner."""
        kuisioner = await self.kuisioner_repo.update(kuisioner_id, update_data)
        if not kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kuisioner tidak ditemukan"
            )

        surat_tugas_data = await self._get_surat_tugas_basic_info(kuisioner.surat_tugas_id)
        
        # 🔥 VALIDASI AKSES TANGGAL
        validate_kuisioner_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="update"
        )
        
        # Set updated_by
        kuisioner.updated_by = updated_by
        await self.kuisioner_repo.session.commit()
        
        return await self.get_kuisioner_or_404(kuisioner_id)
    
    async def upload_file(
        self, 
        kuisioner_id: str, 
        file: UploadFile, 
        uploaded_by: str,
        current_user: dict = None
    ) -> KuisionerFileUploadResponse:
        """Upload file kuisioner."""
        
        kuisioner = await self.kuisioner_repo.get_by_id(kuisioner_id)
        if not kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kuisioner tidak ditemukan"
            )

        surat_tugas_data = await self._get_surat_tugas_basic_info(kuisioner.surat_tugas_id)
        
        # 🔥 VALIDASI AKSES TANGGAL
        validate_kuisioner_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="upload"
        )

        # 🔥 ADD: Permission check untuk PERWADAG
        if current_user and current_user.get("role") == "PERWADAG":
            # Get surat tugas info untuk check nama_perwadag
            surat_tugas_data = await self._get_surat_tugas_basic_info(kuisioner.surat_tugas_id)
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
                    detail=f"Akses ditolak: Anda hanya dapat mengunggah file kuisioner untuk evaluasi Anda sendiri. "
                          f"Yang diharapkan: {surat_tugas_nama_perwadag}, Yang diterima: {user_nama}"
                )
        try:
            # 🔥 FIX: Correct parameter order - file first, then surat_tugas_id
            file_path = await evaluasi_file_manager.upload_kuisioner_file(
                file, kuisioner.surat_tugas_id  # Fixed: file first, surat_tugas_id second
            )
            
            # Update file path di database
            updated_kuisioner = await self.kuisioner_repo.update_file_path(kuisioner_id, file_path)
            if not updated_kuisioner:
                # Cleanup uploaded file if database update fails
                evaluasi_file_manager.delete_file(file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal memperbarui path file di database"
                )
            
            # Set uploaded_by
            updated_kuisioner.updated_by = uploaded_by
            await self.kuisioner_repo.session.commit()
            
            # Build file URL
            file_url = evaluasi_file_manager.get_file_url(file_path)
            
            return KuisionerFileUploadResponse(
                success=True,
                message="File berhasil diunggah",
                kuisioner_id=kuisioner_id,
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
        kuisioner_id: str, 
        download_type: str = "download"
    ) -> FileResponse:
        """Download atau view file kuisioner."""
        
        kuisioner = await self.kuisioner_repo.get_by_id(kuisioner_id)
        if not kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kuisioner tidak ditemukan"
            )
        
        if not kuisioner.file_kuisioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        # 🔥 FIX: Use get_file_download_response instead of download_file
        return evaluasi_file_manager.get_file_download_response(
            file_path=kuisioner.file_kuisioner,
            original_filename=None,  # Will use filename from path
            download_type=download_type
        )
    

    async def _get_surat_tugas_basic_info(self, surat_tugas_id: str) -> Optional[Dict[str, Any]]:
        """Get basic surat tugas information - FIXED SQL query."""
        
        # 🔥 FIX: Remove tahun_evaluasi from select since it's a property
        query = (
            select(
                SuratTugas.no_surat,
                SuratTugas.nama_perwadag,
                SuratTugas.inspektorat,
                SuratTugas.tanggal_evaluasi_mulai,
                SuratTugas.tanggal_evaluasi_selesai,
                # SuratTugas.tahun_evaluasi,  # 🔥 REMOVED - this is a property, not a column
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
        
        result = await self.kuisioner_repo.session.execute(query)
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
            'perwadag_nama': row[5],  # Adjusted index (was row[6], now row[5])
            'evaluation_status': 'active'
        }
    
    async def _build_enriched_response(
        self, 
        kuisioner, 
        surat_tugas_data: Dict[str, Any]
    ) -> KuisionerResponse:
        """Build enriched response - UPDATED dengan tanggal_kuisioner."""
        
        # Handle dict vs object dan field name yang benar
        if isinstance(kuisioner, dict):
            # Repository return dict
            kuisioner_id = kuisioner.get('id')
            surat_tugas_id = kuisioner.get('surat_tugas_id')
            tanggal_kuisioner = kuisioner.get('tanggal_kuisioner')  # 🔥 NEW field
            file_kuisioner = kuisioner.get('file_kuisioner')
            created_at = kuisioner.get('created_at')
            updated_at = kuisioner.get('updated_at')
            created_by = kuisioner.get('created_by')
            updated_by = kuisioner.get('updated_by')
        else:
            # Repository return object
            kuisioner_id = kuisioner.id
            surat_tugas_id = kuisioner.surat_tugas_id
            tanggal_kuisioner = kuisioner.tanggal_kuisioner  # 🔥 NEW field
            file_kuisioner = kuisioner.file_kuisioner
            created_at = kuisioner.created_at
            updated_at = kuisioner.updated_at
            created_by = kuisioner.created_by
            updated_by = kuisioner.updated_by
        
        # Build file information - FIXED: Remove await
        file_urls = None
        file_metadata = None
        
        if file_kuisioner:
            file_urls = FileUrls(
                file_url=evaluasi_file_manager.get_file_url(file_kuisioner),
                download_url=f"/api/v1/kuisioner/{kuisioner_id}/download",
                view_url=f"/api/v1/kuisioner/{kuisioner_id}/view"
            )
            
            # Remove await - get_file_info is NOT async
            file_info = evaluasi_file_manager.get_file_info(file_kuisioner)
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
        
        # 🔥 UPDATED: Calculate completion dengan tanggal_kuisioner
        has_file = bool(file_kuisioner)
        has_tanggal = bool(tanggal_kuisioner)  # 🔥 NEW field
        is_completed = has_file and has_tanggal  # 🔥 UPDATED: Requires both fields
        
        # Calculate completion percentage (2 fields: tanggal + file)
        completed_items = 0
        if has_tanggal:
            completed_items += 1
        if has_file:
            completed_items += 1
        completion_percentage = int((completed_items / 2) * 100)  # 🔥 UPDATED: Divide by 2 instead of 1
        
        return KuisionerResponse(
            # Basic fields - UPDATED
            id=str(kuisioner_id),
            surat_tugas_id=str(surat_tugas_id),
            tanggal_kuisioner=tanggal_kuisioner,  # 🔥 NEW field
            file_dokumen=file_kuisioner,  # Map to response field name
            
            # Enhanced file information
            file_urls=file_urls,
            file_metadata=file_metadata,
            
            # Status information - UPDATED
            is_completed=is_completed,
            has_file=has_file,
            has_tanggal=has_tanggal,  # 🔥 NEW field
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
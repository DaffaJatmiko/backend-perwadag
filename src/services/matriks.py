# ===== src/services/matriks.py =====
"""Enhanced service untuk matriks evaluasi."""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, and_ 

from src.repositories.matriks import MatriksRepository
from src.schemas.matriks import (
    MatriksUpdate, MatriksResponse,
    MatriksFileUploadResponse, MatriksListResponse
)
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)
from src.schemas.filters import MatriksFilterParams
from src.models.surat_tugas import SuratTugas
from src.models.user import User

class MatriksService:
    """Enhanced service untuk matriks operations."""
    
    def __init__(self, matriks_repo: MatriksRepository):
        self.matriks_repo = matriks_repo

    async def get_all_matriks(
        self,
        filters: MatriksFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> MatriksListResponse:
        """Get all matriks dengan enriched data."""
        
        # Get enriched data dari repository
        enriched_results, total = await self.matriks_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build responses
        matriks_responses = []
        for result in enriched_results:
            response = await self._build_enriched_response(
                result['matriks'], 
                result['surat_tugas_data']
            )
            matriks_responses.append(response)
        
        # Build pagination
        pagination = PaginationInfo.create(filters.page, filters.size, total)
        
        # Get statistics
        statistics = None
        if filters.include_statistics:
            stats_data = await self.matriks_repo.get_statistics(
                user_role, user_inspektorat, user_id
            )
            statistics = ModuleStatistics(
                total=stats_data['total'],
                completed=stats_data['completed'],
                completion_rate=stats_data['completion_rate'],
                has_file=stats_data['has_file'],
                module_specific_stats={}
            )
        
        return MatriksListResponse(
            matriks=matriks_responses,
            pagination=pagination,
            statistics=statistics
        )
    
    async def get_matriks_or_404(self, matriks_id: str) -> MatriksResponse:
        """Get matriks by ID dengan enriched data."""
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks not found"
            )
        
        # Get surat tugas data untuk enrichment
        surat_tugas_data = await self._get_surat_tugas_basic_info(matriks.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related surat tugas not found"
            )
        
        return await self._build_enriched_response(matriks, surat_tugas_data)
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[MatriksResponse]:
        """Get matriks by surat tugas ID."""
        matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
        if not matriks:
            return None
        
        # 🔥 FIX: Use instance method instead of standalone function
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_tugas_id)
        if not surat_tugas_data:
            return None
        
        return await self._build_enriched_response(matriks, surat_tugas_data)
    
    async def update_matriks(
        self, 
        matriks_id: str, 
        update_data: MatriksUpdate, 
        updated_by: str
    ) -> MatriksResponse:
        """Update matriks."""
        matriks = await self.matriks_repo.update(matriks_id, update_data)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks not found"
            )
        
        # Set updated_by
        matriks.updated_by = updated_by
        await self.matriks_repo.session.commit()
        
        return await self.get_matriks_or_404(matriks_id)
    
    async def upload_file(
        self, 
        matriks_id: str, 
        file: UploadFile, 
        uploaded_by: str
    ) -> MatriksFileUploadResponse:
        """Upload file matriks."""
        
        # Validate matriks exists
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks not found"
            )
        
        try:
            # 🔥 FIX: Correct parameter order - file first, then surat_tugas_id
            file_path = await evaluasi_file_manager.upload_matriks_file(
                file, matriks.surat_tugas_id  # Fixed: file first, surat_tugas_id second
            )
            
            # Update file path di database
            updated_matriks = await self.matriks_repo.update_file_path(matriks_id, file_path)
            if not updated_matriks:
                # Cleanup uploaded file jika database update gagal
                evaluasi_file_manager.delete_file(file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update file path in database"
                )
            
            # Set uploaded_by
            updated_matriks.updated_by = uploaded_by
            await self.matriks_repo.session.commit()
            
            # Build file URL
            file_url = evaluasi_file_manager.get_file_url(file_path)
            
            return MatriksFileUploadResponse(
                success=True,
                message="File uploaded successfully",
                matriks_id=matriks_id,
                file_path=file_path,
                file_url=file_url
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (like validation errors from file manager)
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )
    
    async def download_file(
        self, 
        matriks_id: str, 
        download_type: str = "download"
    ) -> FileResponse:
        """Download atau view file matriks."""
        
        matriks = await self.matriks_repo.get_by_id(matriks_id)
        if not matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matriks not found"
            )
        
        if not matriks.file_dokumen_matriks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # 🔥 FIX: Use get_file_download_response instead of download_file
        return evaluasi_file_manager.get_file_download_response(
            file_path=matriks.file_dokumen_matriks,
            original_filename=None,  # Will use filename from path
            download_type=download_type
        )
    
    async def _build_enriched_response(
        self, 
        matriks, 
        surat_tugas_data: Dict[str, Any]
    ) -> MatriksResponse:
        """Build enriched response dengan file URLs dan surat tugas data - FIXED."""
        
        # Handle dict vs object dan field name yang benar
        if isinstance(matriks, dict):
            # Repository return dict
            matriks_id = matriks.get('id')
            surat_tugas_id = matriks.get('surat_tugas_id')
            file_dokumen_matriks = matriks.get('file_dokumen_matriks')
            created_at = matriks.get('created_at')
            updated_at = matriks.get('updated_at')
            created_by = matriks.get('created_by')
            updated_by = matriks.get('updated_by')
        else:
            # Repository return object
            matriks_id = matriks.id
            surat_tugas_id = matriks.surat_tugas_id
            file_dokumen_matriks = getattr(matriks, 'file_dokumen_matriks', None)
            created_at = matriks.created_at
            updated_at = matriks.updated_at
            created_by = matriks.created_by
            updated_by = matriks.updated_by
        
        # Build file information - FIXED: Remove await
        file_urls = None
        file_metadata = None
        
        if file_dokumen_matriks:
            file_urls = FileUrls(
                file_url=evaluasi_file_manager.get_file_url(file_dokumen_matriks),
                download_url=f"/api/v1/matriks/{matriks_id}/download",
                view_url=f"/api/v1/matriks/{matriks_id}/view"
            )
            
            # 🔥 FIX: Remove await - get_file_info is NOT async
            file_info = evaluasi_file_manager.get_file_info(file_dokumen_matriks)
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
        
        # Calculate completion - model only has file, no nomor_matriks field
        has_file = bool(file_dokumen_matriks)
        has_nomor = False  # Model doesn't have nomor_matriks field
        is_completed = has_file  # Completion = has file only
        
        completion_percentage = 100 if has_file else 0
        
        return MatriksResponse(
            # Basic fields
            id=str(matriks_id),
            surat_tugas_id=str(surat_tugas_id),
            nomor_matriks=None,  # Model doesn't have this field
            file_dokumen=file_dokumen_matriks,  # Map to expected response field name
            
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
                # SuratTugas.tahun_evaluasi,  # 🔥 REMOVED - this is a property
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
        
        result = await self.matriks_repo.session.execute(query)
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

    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics - FIXED untuk model yang actual."""
        
        stats_data = await self.matriks_repo.get_statistics(
            user_role, user_inspektorat, user_id
        )
        
        # 🔥 FIX: Remove has_nomor since model doesn't have nomor_matriks field
        return {
            'total': stats_data['total'],
            'completed': stats_data['completed'],
            'completion_rate': stats_data['completion_rate'],
            'has_file': stats_data['has_file']
            # Removed 'has_nomor' since field doesn't exist
        }
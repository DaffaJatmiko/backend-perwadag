# ===== src/services/meeting.py (FINAL FIXED) =====
"""Meeting service dengan file operations menggunakan file_bukti_hadir."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, and_

from src.repositories.meeting import MeetingRepository
from src.schemas.meeting import (
    MeetingUpdate, MeetingResponse, MeetingListResponse,
    MeetingFileUploadResponse, MeetingFileDeleteResponse,
    MeetingFileInfo, MeetingFilesInfo, UploadedFileInfo
)
from src.utils.evaluasi_files import evaluasi_file_manager
from src.schemas.shared import (
    SuratTugasBasicInfo, PaginationInfo, ModuleStatistics
)
from src.schemas.filters import MeetingFilterParams
from src.models.surat_tugas import SuratTugas
from src.models.user import User
from src.models.evaluasi_enums import MeetingType
from src.utils.evaluation_date_validator import validate_meeting_date_access



class MeetingService:
    """Enhanced service untuk meeting operations dengan file_bukti_hadir."""
    
    def __init__(self, meeting_repo: MeetingRepository):
        self.meeting_repo = meeting_repo

    async def get_all_meetings(
        self,
        filters: MeetingFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> MeetingListResponse:
        """Get all meetings dengan enriched data."""
        
        enriched_results, total = await self.meeting_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build responses
        meeting_responses = []
        for result in enriched_results:
            response = await self._build_enriched_response(
                result['meeting'], 
                result['surat_tugas_data']
            )
            meeting_responses.append(response)
        
        # 🔥 SIMPLIFIED: Create response directly
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0
        
        response = MeetingListResponse(
            items=meeting_responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
        
        # 🔥 SIMPLIFIED: Add statistics only if requested
        if filters.include_statistics:
            stats_data = await self.meeting_repo.get_statistics(
                user_role, user_inspektorat, user_id
            )
            response.statistics = ModuleStatistics(
                total_records=stats_data['total'],
                completed_records=stats_data['completed'],
                with_files=stats_data['has_files'],
                without_files=stats_data['total'] - stats_data['has_files'],
                completion_rate=stats_data['completion_rate'],
                last_updated=datetime.utcnow()
            )
        
        return response
    
    async def get_meeting_or_404(self, meeting_id: str) -> MeetingResponse:
        """Get meeting by ID dengan enriched data."""
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting tidak ditemukan"
            )
        
        # Get surat tugas data
        surat_tugas_data = await self._get_surat_tugas_basic_info(meeting.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas terkait tidak ditemukan"
            )
        
        # Convert meeting object to dict for consistency
        meeting_data = {
            'id': meeting.id,
            'surat_tugas_id': meeting.surat_tugas_id,
            'meeting_type': meeting.meeting_type,
            'tanggal_meeting': meeting.tanggal_meeting,
            'link_zoom': meeting.link_zoom,
            'link_daftar_hadir': meeting.link_daftar_hadir,
            'file_bukti_hadir': meeting.file_bukti_hadir,
            'created_at': meeting.created_at,
            'updated_at': meeting.updated_at,
            'created_by': meeting.created_by,
            'updated_by': meeting.updated_by
        }
        
        return await self._build_enriched_response(meeting_data, surat_tugas_data)
    
    async def get_by_surat_tugas_and_type(
        self, 
        surat_tugas_id: str, 
        meeting_type: MeetingType
    ) -> Optional[MeetingResponse]:
        """Get meeting by surat tugas ID dan meeting type."""
        meeting = await self.meeting_repo.get_by_surat_tugas_and_type(surat_tugas_id, meeting_type)
        if not meeting:
            return None
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_tugas_id)
        if not surat_tugas_data:
            return None
        
        # Convert to dict
        meeting_data = {
            'id': meeting.id,
            'surat_tugas_id': meeting.surat_tugas_id,
            'meeting_type': meeting.meeting_type,
            'tanggal_meeting': meeting.tanggal_meeting,
            'link_zoom': meeting.link_zoom,
            'link_daftar_hadir': meeting.link_daftar_hadir,
            'file_bukti_hadir': meeting.file_bukti_hadir,
            'created_at': meeting.created_at,
            'updated_at': meeting.updated_at,
            'created_by': meeting.created_by,
            'updated_by': meeting.updated_by
        }
        
        return await self._build_enriched_response(meeting_data, surat_tugas_data)
    
    async def get_all_by_surat_tugas_id(self, surat_tugas_id: str) -> List[MeetingResponse]:
        """Get all meetings untuk surat tugas tertentu."""
        meetings = await self.meeting_repo.get_all_by_surat_tugas_id(surat_tugas_id)
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(surat_tugas_id)
        if not surat_tugas_data:
            return []
        
        responses = []
        for meeting in meetings:
            # Convert to dict
            meeting_data = {
                'id': meeting.id,
                'surat_tugas_id': meeting.surat_tugas_id,
                'meeting_type': meeting.meeting_type,
                'tanggal_meeting': meeting.tanggal_meeting,
                'link_zoom': meeting.link_zoom,
                'link_daftar_hadir': meeting.link_daftar_hadir,
                'file_bukti_hadir': meeting.file_bukti_hadir,
                'created_at': meeting.created_at,
                'updated_at': meeting.updated_at,
                'created_by': meeting.created_by,
                'updated_by': meeting.updated_by
            }
            
            response = await self._build_enriched_response(meeting_data, surat_tugas_data)
            responses.append(response)
        
        return responses
    
    async def update_meeting(
        self, 
        meeting_id: str, 
        update_data: MeetingUpdate, 
        updated_by: str
    ) -> MeetingResponse:
        """Update meeting dengan date validation."""
        
        # 1. Get meeting dan surat tugas info
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting tidak ditemukan"
            )
        
        # 2. Get tanggal evaluasi dari surat tugas
        surat_tugas_data = await self._get_surat_tugas_basic_info(meeting.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas terkait tidak ditemukan"
            )
        
        # 3. 🔥 VALIDASI AKSES TANGGAL - CEK APAKAH MASIH BISA EDIT
        validate_meeting_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="update"
        )
        
        # 4. Lanjutkan update jika validasi berhasil
        updated_meeting = await self.meeting_repo.update(meeting_id, update_data)
        updated_meeting.updated_by = updated_by
        await self.meeting_repo.session.commit()
        
        return await self.get_meeting_or_404(meeting_id)
    
    # ===== FILE OPERATIONS =====
    async def upload_files(
        self, 
        meeting_id: str, 
        files: List[UploadFile], 
        uploaded_by: str,
        replace_existing: bool = False
    ) -> MeetingFileUploadResponse:
        """Upload multiple files ke meeting."""
        
        # 1. Get meeting dan surat tugas info
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting tidak ditemukan"
            )
        
        surat_tugas_data = await self._get_surat_tugas_basic_info(meeting.surat_tugas_id)
        if not surat_tugas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas terkait tidak ditemukan"
            )
        
        # 2. 🔥 VALIDASI AKSES TANGGAL - CEK APAKAH MASIH BISA UPLOAD
        validate_meeting_date_access(
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            operation="upload"
        )

        
        try:
            # Get existing files
            existing_files = meeting.file_bukti_hadir or []
            if replace_existing:
                # Delete existing files dari storage
                for file_info in existing_files:
                    if file_info.get('path'):
                        evaluasi_file_manager.delete_file(file_info['path'])
                existing_files = []
            
            # 🔥 FIX: Convert enum value to lowercase untuk matching directory
            meeting_type_folder = meeting.meeting_type.value.lower()  # ENTRY -> entry
            
            # Upload new files menggunakan method yang sudah ada
            uploaded_file_infos = await evaluasi_file_manager.upload_meeting_files(
                files=files,
                meeting_id=meeting_id,
                meeting_type=meeting_type_folder,  # 🔥 FIXED: lowercase
                uploaded_by=uploaded_by
            )
            
            # Convert format dari file manager ke format database
            processed_files = []
            uploaded_files_response = []
            total_size = 0
            
            for file_info in uploaded_file_infos:
                # Ensure consistent data types
                file_size = file_info.get('size', 0)
                if isinstance(file_size, str):
                    try:
                        file_size = int(file_size)
                    except (ValueError, TypeError):
                        file_size = 0
                
                # Format untuk database
                processed_file = {
                    'filename': file_info['filename'],
                    'original_filename': file_info['original_filename'],
                    'path': file_info['path'],
                    'size': file_size,
                    'content_type': self._get_content_type_from_filename(file_info['original_filename']),
                    'uploaded_at': file_info['uploaded_at'],
                    'uploaded_by': file_info['uploaded_by']
                }
                processed_files.append(processed_file)
                total_size += file_size
                
                # Format untuk response menggunakan UploadedFileInfo schema
                file_size_mb = round(file_size / 1024 / 1024, 2) if file_size > 0 else 0.0
                
                uploaded_file_response = UploadedFileInfo(
                    filename=file_info['filename'],
                    original_filename=file_info['original_filename'],
                    path=file_info['path'],
                    size=file_size,
                    size_mb=file_size_mb,
                    content_type=self._get_content_type_from_filename(file_info['original_filename']),
                    uploaded_at=file_info['uploaded_at'],
                    uploaded_by=file_info['uploaded_by']
                )
                uploaded_files_response.append(uploaded_file_response)
            
            # Update meeting dengan new files
            all_files = existing_files + processed_files
            meeting.file_bukti_hadir = all_files
            meeting.updated_by = uploaded_by
            meeting.updated_at = datetime.utcnow()
            await self.meeting_repo.session.commit()
            
            total_size_mb = round(sum(f.get('size', 0) for f in all_files) / 1024 / 1024, 2)
            
            return MeetingFileUploadResponse(
                success=True,
                message=f"Berhasil mengunggah {len(processed_files)} file",
                meeting_id=meeting_id,
                uploaded_files=uploaded_files_response,  # Use UploadedFileInfo objects
                total_files=len(all_files),
                total_size_mb=total_size_mb
            )
            
        except HTTPException:
            # Re-raise HTTPException dari file manager
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal mengunggah file: {str(e)}"
            )

    def _get_content_type_from_filename(self, filename: str) -> str:
        """Get content type from filename."""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'

    async def delete_file(
        self, 
        meeting_id: str, 
        filename: str,
        deleted_by: str
    ) -> MeetingFileDeleteResponse:
        """Delete specific file dari meeting."""
        
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting tidak ditemukan"
            )
        
        if not meeting.file_bukti_hadir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        try:
            # Find and remove file
            file_to_delete = None
            updated_files = []
            
            for file_info in meeting.file_bukti_hadir:
                if file_info.get('filename') == filename:
                    file_to_delete = file_info
                else:
                    updated_files.append(file_info)
            
            if not file_to_delete:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File tidak ditemukan"
                )
            
            # Delete file from storage using file manager
            if file_to_delete.get('path'):
                success = evaluasi_file_manager.delete_file(file_to_delete['path'])
                if not success:
                    # File might not exist in storage, but we'll continue to update database
                    pass
            
            # Update meeting
            meeting.file_bukti_hadir = updated_files
            meeting.updated_by = deleted_by
            meeting.updated_at = datetime.utcnow()
            await self.meeting_repo.session.commit()
            
            return MeetingFileDeleteResponse(
                success=True,
                message=f"File {filename} berhasil dihapus",
                meeting_id=meeting_id,
                deleted_file=filename,
                remaining_files=len(updated_files)
            )
            
        except HTTPException:
            # Re-raise HTTPException
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghapus file: {str(e)}"
            )
    
    async def download_file(
        self, 
        meeting_id: str, 
        filename: str,
        download_type: str = "download"
    ) -> FileResponse:
        """Download specific file dari meeting."""
        
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting tidak ditemukan"
            )
        
        if not meeting.file_bukti_hadir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        # Find file
        file_info = None
        for file_data in meeting.file_bukti_hadir:
            if file_data.get('filename') == filename:
                file_info = file_data
                break
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        # Use file manager's download method
        return evaluasi_file_manager.get_file_download_response(
            file_path=file_info['path'],
            original_filename=file_info.get('original_filename', filename),
            download_type=download_type
        )

    async def download_all_files(
        self, 
        meeting_id: str
    ) -> FileResponse:
        """Download all files dari meeting sebagai ZIP."""
        
        meeting = await self.meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting tidak ditemukan"
            )
        
        if not meeting.file_bukti_hadir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        # Get all file paths
        file_paths = [
            file_info.get('path') 
            for file_info in meeting.file_bukti_hadir 
            if file_info.get('path') and evaluasi_file_manager.file_exists(file_info['path'])
        ]
        
        if not file_paths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Path file yang valid tidak ditemukan"
            )
        
        # Create ZIP using file manager
        zip_path = evaluasi_file_manager.create_zip_archive(
            file_paths=file_paths,
            zip_name=f"meeting_{meeting_id}_files"
        )
        
        # Return ZIP file
        return FileResponse(
            path=zip_path,
            media_type='application/zip',
            filename=f"meeting_{meeting_id}_files.zip",
            headers={
                "Content-Disposition": f'attachment; filename="meeting_{meeting_id}_files.zip"'
            }
        )
    
    # ===== HELPER METHODS =====
    def _get_meeting_type_display(self, meeting_type: str) -> str:
        """Get display name untuk meeting type."""
        display_map = {
            'entry': 'Entry Meeting',
            'konfirmasi': 'Konfirmasi Meeting', 
            'exit': 'Exit Meeting'
        }
        return display_map.get(meeting_type, meeting_type.title())
    
    def _get_meeting_order(self, meeting_type: str) -> int:
        """Get order number untuk meeting dalam workflow."""
        order_map = {
            'entry': 1,
            'konfirmasi': 2,
            'exit': 3
        }
        return order_map.get(meeting_type, 0)
    
    async def _get_surat_tugas_basic_info(self, surat_tugas_id: str) -> Optional[Dict[str, Any]]:
        """Get basic surat tugas information."""
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
        
        result = await self.meeting_repo.session.execute(query)
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
        meeting_data: Dict[str, Any],
        surat_tugas_data: Dict[str, Any]
    ) -> MeetingResponse:
        """Build enriched response dengan file URLs dan surat tugas data."""
        
        # Build files information dari file_bukti_hadir
        files_info = None
        files = []
        
        if meeting_data.get('file_bukti_hadir'):
            for file_data in meeting_data['file_bukti_hadir']:
                file_info = MeetingFileInfo(
                    filename=file_data['filename'],
                    original_filename=file_data.get('original_filename', file_data['filename']),
                    path=file_data['path'],
                    size=file_data.get('size', 0),
                    size_mb=round(file_data.get('size', 0) / 1024 / 1024, 2),
                    content_type=file_data.get('content_type', 'application/octet-stream'),
                    uploaded_at=datetime.fromisoformat(file_data.get('uploaded_at', meeting_data['created_at'].isoformat())),
                    uploaded_by=file_data.get('uploaded_by'),
                    file_url=evaluasi_file_manager.get_file_url(file_data['path']),
                    download_url=f"/api/v1/meetings/{meeting_data['id']}/files/{file_data['filename']}/download",
                    view_url=f"/api/v1/meetings/{meeting_data['id']}/files/{file_data['filename']}/view" if file_data.get('content_type', '').startswith(('image/', 'application/pdf')) else None,
                    is_viewable=file_data.get('content_type', '').startswith(('image/', 'application/pdf'))
                )
                files.append(file_info)
            
            if files:
                total_size = sum(f.size for f in files)
                files_info = MeetingFilesInfo(
                    files=files,
                    total_files=len(files),
                    total_size=total_size,
                    total_size_mb=round(total_size / 1024 / 1024, 2),
                    download_all_url=f"/api/v1/meetings/{meeting_data['id']}/files/download-all"
                )
        
        # Build surat tugas basic info
        surat_tugas_info = SuratTugasBasicInfo(
            id=meeting_data['surat_tugas_id'],
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
        
        # Calculate completion
        has_files = bool(files)
        has_date = bool(meeting_data.get('tanggal_meeting'))
        has_links = bool(meeting_data.get('link_zoom') or meeting_data.get('link_daftar_hadir'))
        is_completed = has_files and has_date and has_links
        
        completion_percentage = 0
        if has_date:
            completion_percentage += 34
        if has_files:
            completion_percentage += 33
        if has_links:
            completion_percentage += 33
        
        return MeetingResponse(
            # Basic fields
            id=str(meeting_data['id']),
            surat_tugas_id=str(meeting_data['surat_tugas_id']),
            meeting_type=meeting_data['meeting_type'],
            tanggal_meeting=meeting_data.get('tanggal_meeting'),
            link_zoom=meeting_data.get('link_zoom'),
            link_daftar_hadir=meeting_data.get('link_daftar_hadir'),
            
            # Enhanced file information
            files_info=files_info,
            
            # Status information
            is_completed=is_completed,
            has_files=has_files,
            has_date=has_date,
            has_links=has_links,
            completion_percentage=completion_percentage,
            
            # Meeting type display
            meeting_type_display=self._get_meeting_type_display(meeting_data['meeting_type'].value),
            meeting_order=self._get_meeting_order(meeting_data['meeting_type'].value),
            
            # Enriched surat tugas data
            surat_tugas_info=surat_tugas_info,
            nama_perwadag=surat_tugas_data['perwadag_nama'],
            inspektorat=surat_tugas_data['inspektorat'],
            tanggal_evaluasi_mulai=surat_tugas_data['tanggal_evaluasi_mulai'],
            tanggal_evaluasi_selesai=surat_tugas_data['tanggal_evaluasi_selesai'],
            tahun_evaluasi=surat_tugas_data['tahun_evaluasi'],
            evaluation_status=surat_tugas_data.get('evaluation_status', 'active'),
            
            # Audit information
            created_at=meeting_data['created_at'],
            updated_at=meeting_data.get('updated_at'),
            created_by=meeting_data.get('created_by'),
            updated_by=meeting_data.get('updated_by')
        )
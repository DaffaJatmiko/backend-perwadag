"""Extended file utilities untuk sistem evaluasi perwadag dengan download capabilities."""

import os
import uuid
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from src.models.evaluasi_enums import FileType
from src.core.config import settings


class EvaluasiFileManager:
    """Extended utility class untuk manage file evaluasi dengan download capabilities."""
    
    def __init__(self):
        self.base_path = Path(settings.UPLOADS_PATH) / "evaluasi"
        self.base_url = "/static/uploads/evaluasi"
        
        # Ensure directories exist
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create all required directories."""
        directories = [
            "surat-tugas",
            "surat-pemberitahuan", 
            "meetings/entry",
            "meetings/konfirmasi",
            "meetings/exit",
            "matriks",
            "laporan-hasil",
            "kuisioner",
            "format-kuisioner"
        ]
        
        for directory in directories:
            dir_path = self.base_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename dengan timestamp dan UUID."""
        file_ext = Path(original_filename).suffix
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}{file_ext}"
    
    def _validate_file(self, file: UploadFile, file_type: FileType) -> None:
        """Validate file type dan size."""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = FileType.get_allowed_extensions(file_type.value)
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Check file size (jika bisa diperiksa)
        max_size = FileType.get_max_file_size(file_type.value)
        if hasattr(file.file, 'seek'):
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds maximum allowed size ({max_size / (1024*1024):.1f}MB)"
                )
    
    async def _save_file(self, file: UploadFile, folder: str, filename: str) -> str:
        """Save file to specified folder."""
        file_path = self.base_path / folder / filename
        
        # Write file
        try:
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
        
        # Return relative path for URL
        return f"{folder}/{filename}"
    
    def _get_file_url(self, relative_path: str) -> str:
        """Get full URL for file."""
        return f"{self.base_url}/{relative_path}".replace("\\", "/")
    
    def _delete_file(self, relative_path: str) -> bool:
        """Delete file from storage."""
        try:
            file_path = self.base_path / relative_path
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    # =========================
    # NEW: FILE DOWNLOAD & VIEW METHODS
    # =========================
    
    def _get_content_type(self, file_path: str) -> str:
        """Get content type for file."""
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'
    
    def _get_safe_filename(self, original_filename: str) -> str:
        """Get safe filename for download."""
        # Remove path separators and dangerous characters
        safe_name = os.path.basename(original_filename)
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in '._-')
        return safe_name or "download"

    def extract_filename_from_path(self, file_path: str) -> str:
        """Extract filename dari full path."""
        if not file_path:
            return ""
        return os.path.basename(file_path)

    def get_filename_for_single_file_entity(self, file_path: str) -> Optional[str]:
        """Get filename untuk single file entity."""
        if not file_path:
            return None
        return self.extract_filename_from_path(file_path)
    
    def get_file_download_response(
        self, 
        file_path: str, 
        original_filename: str = None,
        download_type: str = "download"  # "download" or "view"
    ) -> FileResponse:
        """
        Get file download response dengan proper headers.
        
        Args:
            file_path: Relative path dari base_path
            original_filename: Original filename untuk download
            download_type: "download" untuk force download, "view" untuk inline
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Determine content type
        content_type = self._get_content_type(str(full_path))
        
        # Determine filename
        if original_filename:
            filename = self._get_safe_filename(original_filename)
        else:
            filename = self._get_safe_filename(full_path.name)
        
        # Determine content disposition
        if download_type == "view" and content_type.startswith(('image/', 'application/pdf', 'text/')):
            # Inline viewing untuk file types yang bisa di-preview
            disposition = "inline"
        else:
            # Force download
            disposition = "attachment"
        
        return FileResponse(
            path=str(full_path),
            media_type=content_type,
            filename=filename,
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache"
            }
        )
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive file information."""
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return None
        
        stat = full_path.stat()
        content_type = self._get_content_type(str(full_path))
        
        return {
            "path": file_path,
            "url": self._get_file_url(file_path),
            "download_url": f"/api/v1/files/download/{file_path}",  # Will be implemented
            "view_url": f"/api/v1/files/view/{file_path}",
            "filename": full_path.name,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "content_type": content_type,
            "extension": full_path.suffix.lower(),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_viewable": content_type.startswith(('image/', 'application/pdf', 'text/'))
        }
    
    def create_zip_archive(self, file_paths: List[str], zip_name: str) -> str:
        """Create ZIP archive dari multiple files."""
        import zipfile
        import tempfile
        
        # Create temporary zip file
        temp_dir = Path(tempfile.gettempdir())
        zip_path = temp_dir / f"{zip_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    full_path = self.base_path / file_path
                    if full_path.exists():
                        # Add file to zip dengan nama yang clean
                        arcname = self._get_safe_filename(full_path.name)
                        zipf.write(full_path, arcname)
            
            return str(zip_path)
        except Exception as e:
            if zip_path.exists():
                zip_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create ZIP archive: {str(e)}"
            )
    
    # =========================
    # EXISTING UPLOAD METHODS (UNCHANGED)
    # =========================
    
    async def upload_surat_tugas_file(self, file: UploadFile, surat_tugas_id: str) -> str:
        """Upload file surat tugas."""
        self._validate_file(file, FileType.SURAT_TUGAS)
        filename = self._generate_unique_filename(file.filename)
        relative_path = await self._save_file(file, "surat-tugas", filename)
        return relative_path
    
    async def upload_pemberitahuan_file(self, file: UploadFile, surat_tugas_id: str) -> str:
        """Upload file surat pemberitahuan."""
        self._validate_file(file, FileType.SURAT_PEMBERITAHUAN)
        filename = self._generate_unique_filename(file.filename)
        relative_path = await self._save_file(file, "surat-pemberitahuan", filename)
        return relative_path
    
    async def upload_matriks_file(self, file: UploadFile, surat_tugas_id: str) -> str:
        """Upload file matriks."""
        self._validate_file(file, FileType.MATRIKS)
        filename = self._generate_unique_filename(file.filename)
        relative_path = await self._save_file(file, "matriks", filename)
        return relative_path
    
    async def upload_laporan_file(self, file: UploadFile, surat_tugas_id: str) -> str:
        """Upload file laporan hasil."""
        self._validate_file(file, FileType.LAPORAN_HASIL)
        filename = self._generate_unique_filename(file.filename)
        relative_path = await self._save_file(file, "laporan-hasil", filename)
        return relative_path
    
    async def upload_kuisioner_file(self, file: UploadFile, surat_tugas_id: str) -> str:
        """Upload file kuisioner."""
        self._validate_file(file, FileType.KUISIONER)
        filename = self._generate_unique_filename(file.filename)
        relative_path = await self._save_file(file, "kuisioner", filename)
        return relative_path
    
    async def upload_format_kuisioner(self, file: UploadFile, tahun: int) -> str:
        """Upload template format kuisioner."""
        self._validate_file(file, FileType.FORMAT_KUISIONER)
        filename = self._generate_unique_filename(file.filename)
        relative_path = await self._save_file(file, "format-kuisioner", filename)
        return relative_path
    
    async def upload_meeting_files(
        self, 
        files: List[UploadFile], 
        meeting_id: str, 
        meeting_type: str,
        uploaded_by: str
    ) -> List[Dict[str, Any]]:
        """Upload multiple files untuk meeting bukti hadir."""
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        uploaded_files = []
        folder = f"meetings/{meeting_type}"
        
        for file in files:
            try:
                # Validate each file
                self._validate_file(file, FileType.MEETING_BUKTI)
                
                # Generate unique filename
                filename = self._generate_unique_filename(file.filename)
                
                # Save file
                relative_path = await self._save_file(file, folder, filename)
                
                # Get file size
                file_size = 0
                if hasattr(file.file, 'seek'):
                    file.file.seek(0, 2)
                    file_size = file.file.tell()
                    file.file.seek(0)
                
                # Create file info
                file_info = {
                    "filename": filename,
                    "original_filename": file.filename,
                    "path": relative_path,
                    "url": self._get_file_url(relative_path),
                    "size": file_size,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "uploaded_by": uploaded_by
                }
                
                uploaded_files.append(file_info)
                
            except HTTPException:
                # Clean up any successfully uploaded files jika ada yang error
                for uploaded_file in uploaded_files:
                    self._delete_file(uploaded_file["path"])
                raise
            except Exception as e:
                # Clean up any successfully uploaded files
                for uploaded_file in uploaded_files:
                    self._delete_file(uploaded_file["path"])
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload files: {str(e)}"
                )
        
        return uploaded_files
    
    # =========================
    # FILE OPERATIONS (EXISTING + NEW)
    # =========================
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage."""
        return self._delete_file(file_path)
    
    def delete_multiple_files(self, file_paths: List[str]) -> Dict[str, int]:
        """Delete multiple files, return success/failure counts."""
        deleted_count = 0
        failed_count = 0
        
        for file_path in file_paths:
            if self._delete_file(file_path):
                deleted_count += 1
            else:
                failed_count += 1
        
        return {
            "deleted": deleted_count,
            "failed": failed_count,
            "total": len(file_paths)
        }
    
    def get_file_url(self, file_path: str) -> str:
        """Get full URL for file."""
        if not file_path:
            return ""
        return self._get_file_url(file_path)
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        if not file_path:
            return False
        full_path = self.base_path / file_path
        return full_path.exists()
    
    def get_file_size_mb(self, file_path: str) -> Optional[float]:
        """Get file size in MB."""
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            return None
        
        size_bytes = full_path.stat().st_size
        return round(size_bytes / (1024 * 1024), 2)
    
    def cleanup_orphaned_files(self, valid_file_paths: List[str]) -> Dict[str, int]:
        """Clean up files that are not referenced in database."""
        deleted_count = 0
        total_count = 0
        
        # Scan all directories
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                total_count += 1
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.base_path)
                relative_path_str = str(relative_path).replace("\\", "/")
                
                # If file not in valid paths, delete it
                if relative_path_str not in valid_file_paths:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
        
        return {
            "total_files": total_count,
            "deleted_files": deleted_count,
            "kept_files": total_count - deleted_count
        }


# Global instance
evaluasi_file_manager = EvaluasiFileManager()
"""Model untuk meetings dalam proses evaluasi."""

from typing import Optional, List, Dict, Any
from datetime import date
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy import Enum as SQLEnum, UniqueConstraint
import uuid as uuid_lib

from src.models.base import BaseModel
from src.models.evaluasi_enums import MeetingType


class Meeting(BaseModel, SQLModel, table=True):
    """Model untuk semua jenis meeting (entry, konfirmasi, exit)."""
    
    __tablename__ = "meetings"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    surat_tugas_id: str = Field(
        foreign_key="surat_tugas.id",
        index=True,
        max_length=36,
        description="ID surat tugas terkait"
    )
    
    meeting_type: MeetingType = Field(
        sa_column=Column(SQLEnum(MeetingType), nullable=False, index=True),
        description="Jenis meeting: entry, konfirmasi, atau exit"
    )
    
    tanggal_meeting: Optional[date] = Field(
        default=None,
        description="Tanggal pelaksanaan meeting"
    )
    
    link_zoom: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Link Zoom meeting"
    )
    
    link_daftar_hadir: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Link Google Form daftar hadir"
    )
    
    file_bukti_hadir: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Array file bukti hadir (multiple files)"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('surat_tugas_id', 'meeting_type', name='unique_meeting_per_surat_tugas'),
    )
    
    @property
    def meeting_type_display(self) -> str:
        """Get display name untuk meeting type."""
        return MeetingType.get_display_name(self.meeting_type.value)
    
    @property
    def total_files_uploaded(self) -> int:
        """Get total jumlah file yang diupload."""
        return len(self.file_bukti_hadir) if self.file_bukti_hadir else 0
    
    def is_completed(self) -> bool:
        """Check apakah meeting sudah completed (minimal ada tanggal)."""
        return self.tanggal_meeting is not None
    
    def has_files(self) -> bool:
        """Check apakah sudah ada file yang diupload."""
        return self.file_bukti_hadir is not None and len(self.file_bukti_hadir) > 0
    
    def has_zoom_link(self) -> bool:
        """Check apakah sudah ada zoom link."""
        return self.link_zoom is not None and self.link_zoom.strip() != ""
    
    def has_daftar_hadir_link(self) -> bool:
        """Check apakah sudah ada link daftar hadir."""
        return self.link_daftar_hadir is not None and self.link_daftar_hadir.strip() != ""
    
    def get_completion_percentage(self) -> int:
        """Get completion percentage (0-100)."""
        completed_items = 0
        total_items = 4  # tanggal, zoom, daftar_hadir, files
        
        if self.tanggal_meeting is not None:
            completed_items += 1
        if self.has_zoom_link():
            completed_items += 1
        if self.has_daftar_hadir_link():
            completed_items += 1
        if self.has_files():
            completed_items += 1
        
        return int((completed_items / total_items) * 100)
    
    def get_file_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get specific file by filename."""
        if not self.file_bukti_hadir:
            return None
        
        for file_info in self.file_bukti_hadir:
            if file_info.get('filename') == filename:
                return file_info
        return None
    
    def add_file_info(self, file_info: Dict[str, Any]) -> None:
        """Add file info to bukti hadir list."""
        if self.file_bukti_hadir is None:
            self.file_bukti_hadir = []
        self.file_bukti_hadir.append(file_info)
    
    def remove_file_by_filename(self, filename: str) -> bool:
        """Remove file by filename, return True if removed."""
        if not self.file_bukti_hadir:
            return False
        
        original_length = len(self.file_bukti_hadir)
        self.file_bukti_hadir = [
            file_info for file_info in self.file_bukti_hadir 
            if file_info.get('filename') != filename
        ]
        return len(self.file_bukti_hadir) < original_length
    
    def clear_all_files(self) -> List[str]:
        """Clear all files and return list of file paths for deletion."""
        if not self.file_bukti_hadir:
            return []
        
        file_paths = [file_info.get('path') for file_info in self.file_bukti_hadir if file_info.get('path')]
        self.file_bukti_hadir = []
        return file_paths
    
    def get_file_paths(self) -> List[str]:
        """Get all file paths for deletion purposes."""
        if not self.file_bukti_hadir:
            return []
        
        return [file_info.get('path') for file_info in self.file_bukti_hadir if file_info.get('path')]
    
    def __repr__(self) -> str:
        return f"<Meeting(type={self.meeting_type.value}, surat_tugas_id={self.surat_tugas_id}, completed={self.is_completed()})>"
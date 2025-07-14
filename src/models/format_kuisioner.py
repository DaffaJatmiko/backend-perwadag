"""Model untuk template/format kuisioner master."""

from typing import Optional
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class FormatKuisioner(BaseModel, SQLModel, table=True):
    """Model untuk template/format kuisioner master."""
    
    __tablename__ = "format_kuisioner"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    nama_template: str = Field(
        max_length=200,
        index=True,
        description="Nama template kuisioner"
    )
    
    deskripsi: Optional[str] = Field(
        default=None,
        description="Deskripsi template"
    )
    
    tahun: int = Field(
        index=True,
        description="Tahun berlaku template"
    )
    
    link_template: str = Field(
        max_length=500,
        description="Link ke file template (URL/Path)"
    )
    
    def is_active_for_year(self, year: int) -> bool:
        """Check apakah template aktif untuk tahun tertentu."""
        return self.tahun == year
    
    def has_file(self) -> bool:
        """Check apakah sudah ada file template."""
        return self.link_template is not None and self.link_template.strip() != ""
    
    def get_file_extension(self) -> Optional[str]:
        """Get file extension dari link template."""
        if not self.has_file():
            return None
        
        try:
            from pathlib import Path
            return Path(self.link_template).suffix.lower()
        except Exception:
            return None
    
    def is_downloadable(self) -> bool:
        """Check apakah template bisa didownload."""
        return self.has_file() and not self.deleted_at
    
    def clear_file(self) -> Optional[str]:
        """Clear file and return file path for deletion."""
        if self.link_template:
            file_path = self.link_template
            self.link_template = ""
            return file_path
        return None
    
    @property
    def display_name(self) -> str:
        """Get display name dengan tahun."""
        return f"{self.nama_template} ({self.tahun})"
    
    def __repr__(self) -> str:
        return f"<FormatKuisioner(nama={self.nama_template}, tahun={self.tahun})>"
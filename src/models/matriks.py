"""Model untuk matriks rekomendasi hasil evaluasi."""

from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class Matriks(BaseModel, SQLModel, table=True):
    """Model untuk matriks rekomendasi hasil evaluasi."""
    
    __tablename__ = "matriks"
    
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
    
    file_dokumen_matriks: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Path file matriks rekomendasi"
    )

    temuan_rekomendasi: Optional[str] = Field(
        default=None,
        description="JSON data untuk pasangan temuan dan rekomendasi",
    )
    
    def is_completed(self) -> bool:
        """Check apakah matriks sudah completed."""
        return (
            self.file_dokumen_matriks is not None and
            self.file_dokumen_matriks.strip() != ""
        )
    
    def has_file(self) -> bool:
        """Check apakah sudah ada file yang diupload."""
        return self.file_dokumen_matriks is not None and self.file_dokumen_matriks.strip() != ""
    
    def get_completion_percentage(self) -> int:
        """Get completion percentage (0-100)."""
        return 100 if self.is_completed() else 0
    
    def clear_file(self) -> Optional[str]:
        """Clear file and return file path for deletion."""
        if self.file_dokumen_matriks:
            file_path = self.file_dokumen_matriks
            self.file_dokumen_matriks = None
            return file_path
        return None

    def get_temuan_rekomendasi_items(self) -> List[Dict[str, str]]:
        """Parse JSON ke list of temuan-rekomendasi pairs."""
        if not self.temuan_rekomendasi:
            return []
        
        try:
            import json
            data = json.loads(self.temuan_rekomendasi)
            return data.get('items', [])
        except (json.JSONDecodeError, TypeError):
            return []

    def set_temuan_rekomendasi_items(self, items: List[Dict[str, str]]) -> None:
        """Set JSON data - REPLACE strategy."""
        import json
        from datetime import datetime
        
        validated_items = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
                
            temuan = str(item.get('temuan', '')).strip()
            rekomendasi = str(item.get('rekomendasi', '')).strip()
            
            if temuan and rekomendasi:
                validated_items.append({
                    'id': i + 1,
                    'temuan': temuan,
                    'rekomendasi': rekomendasi
                })
        
        self.temuan_rekomendasi = json.dumps({
            'items': validated_items,
            'total': len(validated_items),
            'last_updated': datetime.utcnow().isoformat()
        }, ensure_ascii=False)

    def has_temuan_rekomendasi(self) -> bool:
        """Check apakah ada data temuan-rekomendasi - SIMPLIFIED."""
        items = self.get_temuan_rekomendasi_items()
        return len(items) > 0

    def get_temuan_rekomendasi_summary(self) -> Dict[str, Any]:
        """Get summary untuk display - SIMPLIFIED."""
        items = self.get_temuan_rekomendasi_items()
        
        return {
            'data': items  # Return all items, not just preview
        }

    def clear_temuan_rekomendasi(self) -> None:
        """Clear all temuan-rekomendasi data."""
        self.temuan_rekomendasi = None
    
    def __repr__(self) -> str:
        return f"<Matriks(surat_tugas_id={self.surat_tugas_id}, completed={self.is_completed()})>"
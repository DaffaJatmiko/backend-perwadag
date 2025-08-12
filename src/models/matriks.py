"""Model untuk matriks rekomendasi hasil evaluasi."""

from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel
import uuid as uuid_lib
from sqlalchemy import Column, Enum as SQLEnum  # ✅ ADD: Import Enum

from src.models.base import BaseModel
from src.models.evaluasi_enums import MatriksStatus, TindakLanjutStatus


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

    temuan_version: int = Field(
        default=0,
        description="Version number untuk conflict detection pada temuan"
    )

    status: MatriksStatus = Field(
        default=MatriksStatus.DRAFTING,
        sa_column=Column(SQLEnum(MatriksStatus, name='matriks_status'), nullable=False, default='DRAFTING'),
        description="Status flow evaluasi berjenjang"
    )

    # ✅ FIX: Consistent SQLModel syntax untuk global tindak lanjut status
    status_tindak_lanjut: Optional[TindakLanjutStatus] = Field(
        default=None,
        sa_column=Column(SQLEnum(TindakLanjutStatus, name='tindaklanjutstatus'), nullable=True),
        description="Global tindak lanjut status for entire matrix"
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

    def get_temuan_rekomendasi_items(self) -> List[Dict[str, Any]]:
        """
        Parse JSON ke list of kondisi-kriteria-rekomendasi sets.
        
        Returns:
            List of dicts with keys: id, kondisi, kriteria, rekomendasi, tindak_lanjut, etc.
        """
        if not self.temuan_rekomendasi:
            return []
        
        try:
            import json
            data = json.loads(self.temuan_rekomendasi)
            return data.get('items', [])
        except (json.JSONDecodeError, TypeError):
            return []

    def set_temuan_rekomendasi_items(
        self, 
        items: List[Dict[str, str]], 
        expected_version: Optional[int] = None
    ) -> bool:
        """
        Set JSON data dengan 3-field structure - CONFLICT-SAFE VERSION.
        
        Args:
            items: List of dicts dengan keys: kondisi, kriteria, rekomendasi
            expected_version: Expected version untuk conflict detection
            
        Returns:
            bool: True jika berhasil, False jika ada conflict
        """
        # Check version conflict
        if expected_version is not None and self.temuan_version != expected_version:
            return False  # Conflict detected!
        
        import json
        from datetime import datetime
        
        validated_items = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
                
            kondisi = str(item.get('kondisi', '')).strip()
            kriteria = str(item.get('kriteria', '')).strip()
            rekomendasi = str(item.get('rekomendasi', '')).strip()
            
            # Validate all 3 fields are present
            if kondisi and kriteria and rekomendasi:
                validated_items.append({
                    'id': i + 1,
                    'kondisi': kondisi,
                    'kriteria': kriteria,
                    'rekomendasi': rekomendasi,
                    # ✅ ADD: Tindak lanjut fields (empty by default)
                    'tindak_lanjut': '',
                    'dokumen_pendukung_tindak_lanjut': '',
                    'catatan_evaluator': ''
                    # ❌ NO individual status_tindak_lanjut
                })
        
        self.temuan_rekomendasi = json.dumps({
            'items': validated_items,
            'total': len(validated_items),
            'last_updated': datetime.utcnow().isoformat(),
            'structure_version': '3-field'
        }, ensure_ascii=False)
        
        # INCREMENT VERSION
        self.temuan_version += 1
        
        return True

    def has_temuan_rekomendasi(self) -> bool:
        """Check apakah ada data kondisi-kriteria-rekomendasi."""
        items = self.get_temuan_rekomendasi_items()
        return len(items) > 0

    def get_temuan_rekomendasi_summary(self) -> Dict[str, Any]:
        """
        Get summary untuk display dengan 3-field structure.
        
        Returns:
            Dict with 'data' key containing all kondisi-kriteria-rekomendasi items
        """
        items = self.get_temuan_rekomendasi_items()
        
        return {
            'data': items  # Return all items dengan kondisi, kriteria, rekomendasi, tindak_lanjut
        }

    def clear_temuan_rekomendasi(self) -> None:
        """Clear all kondisi-kriteria-rekomendasi data."""
        self.temuan_rekomendasi = None

    def update_tindak_lanjut_item(self, item_id: int, **kwargs) -> bool:
        """
        Update individual tindak lanjut item content ONLY (no status).
        
        Args:
            item_id: ID of item to update
            **kwargs: tindak_lanjut, dokumen_pendukung, catatan_evaluator
            
        Returns:
            bool: True if item found and updated, False otherwise
        """
        if not self.temuan_rekomendasi:
            return False
        
        try:
            import json
            data = json.loads(self.temuan_rekomendasi)
            
            if 'items' not in data:
                return False
            
            # Find and update the specific item
            for item in data['items']:
                if item.get('id') == item_id:
                    # Update content fields only
                    if 'tindak_lanjut' in kwargs:
                        item['tindak_lanjut'] = kwargs['tindak_lanjut'] or ''
                    if 'dokumen_pendukung' in kwargs:
                        item['dokumen_pendukung_tindak_lanjut'] = kwargs['dokumen_pendukung'] or ''
                    if 'catatan_evaluator' in kwargs:
                        item['catatan_evaluator'] = kwargs['catatan_evaluator'] or ''
                    
                    # ❌ REMOVED: status_tindak_lanjut logic (now global)
                    
                    # Save back to JSON
                    self.temuan_rekomendasi = json.dumps(data, ensure_ascii=False)
                    return True
            
            return False
            
        except (json.JSONDecodeError, TypeError):
            return False
    
    def get_tindak_lanjut_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get tindak lanjut data untuk item tertentu."""
        items = self.get_temuan_rekomendasi_items()
        for item in items:
            if item.get('id') == item_id:
                return {
                    'tindak_lanjut': item.get('tindak_lanjut', ''),
                    'dokumen_pendukung_tindak_lanjut': item.get('dokumen_pendukung_tindak_lanjut', ''),
                    'catatan_evaluator': item.get('catatan_evaluator', ''),
                    # ❌ REMOVED: status_tindak_lanjut (now global)
                }
        return None

    def get_or_set_default_tindak_lanjut_status(self) -> TindakLanjutStatus:
        """
        Get status_tindak_lanjut, auto-set DRAFTING if NULL and matrix is FINISHED.
        
        ✅ IMPORTANT: This method MODIFIES the object if auto-set happens.
        Service layer should save to database after calling this.
        """
        if self.status_tindak_lanjut is None:
            if self.status == MatriksStatus.FINISHED:
                # ✅ AUTO-SET: NULL → DRAFTING when matrix is FINISHED
                self.status_tindak_lanjut = TindakLanjutStatus.DRAFTING
                print(f"🔄 Auto-set tindak lanjut status: NULL → DRAFTING for matrix {self.id}")
            else:
                # Matrix belum FINISHED, return default tapi jangan save
                return TindakLanjutStatus.DRAFTING
        
        return self.status_tindak_lanjut

    def __repr__(self) -> str:
        return f"<Matriks(surat_tugas_id={self.surat_tugas_id}, completed={self.is_completed()})>"
# ===== src/repositories/laporan_hasil.py =====
"""Repository untuk laporan hasil."""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.laporan_hasil import LaporanHasil
from src.schemas.laporan_hasil import LaporanHasilCreate, LaporanHasilUpdate


class LaporanHasilRepository:
    """Repository untuk operasi laporan hasil."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, laporan_hasil_data: LaporanHasilCreate) -> LaporanHasil:
        """Create laporan hasil baru (auto-generated)."""
        laporan_hasil = LaporanHasil(
            surat_tugas_id=laporan_hasil_data.surat_tugas_id
        )
        
        self.session.add(laporan_hasil)
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil
    
    async def get_by_id(self, laporan_hasil_id: str) -> Optional[LaporanHasil]:
        """Get laporan hasil by ID."""
        query = select(LaporanHasil).where(
            and_(LaporanHasil.id == laporan_hasil_id, LaporanHasil.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[LaporanHasil]:
        """Get laporan hasil by surat tugas ID."""
        query = select(LaporanHasil).where(
            and_(
                LaporanHasil.surat_tugas_id == surat_tugas_id,
                LaporanHasil.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, laporan_hasil_id: str, update_data: LaporanHasilUpdate) -> Optional[LaporanHasil]:
        """Update laporan hasil."""
        laporan_hasil = await self.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(laporan_hasil, key, value)
        
        laporan_hasil.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil
    
    async def update_file_path(self, laporan_hasil_id: str, file_path: str) -> Optional[LaporanHasil]:
        """Update file path."""
        laporan_hasil = await self.get_by_id(laporan_hasil_id)
        if not laporan_hasil:
            return None
        
        laporan_hasil.file_laporan_hasil = file_path
        laporan_hasil.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(laporan_hasil)
        return laporan_hasil
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(LaporanHasil)
            .where(
                and_(
                    LaporanHasil.surat_tugas_id == surat_tugas_id,
                    LaporanHasil.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount

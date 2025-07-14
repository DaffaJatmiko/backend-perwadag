# ===== src/repositories/surat_pemberitahuan.py =====
"""Repository untuk surat pemberitahuan."""

from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.surat_pemberitahuan import SuratPemberitahuan
from src.schemas.surat_pemberitahuan import SuratPemberitahuanCreate, SuratPemberitahuanUpdate
from src.schemas.filters import SuratPemberitahuanFilterParams


class SuratPemberitahuanRepository:
    """Repository untuk operasi surat pemberitahuan."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, surat_pemberitahuan_data: SuratPemberitahuanCreate) -> SuratPemberitahuan:
        """Create surat pemberitahuan baru (auto-generated)."""
        surat_pemberitahuan = SuratPemberitahuan(
            surat_tugas_id=surat_pemberitahuan_data.surat_tugas_id
        )
        
        self.session.add(surat_pemberitahuan)
        await self.session.commit()
        await self.session.refresh(surat_pemberitahuan)
        return surat_pemberitahuan
    
    async def get_by_id(self, surat_pemberitahuan_id: str) -> Optional[SuratPemberitahuan]:
        """Get surat pemberitahuan by ID."""
        query = select(SuratPemberitahuan).where(
            and_(SuratPemberitahuan.id == surat_pemberitahuan_id, SuratPemberitahuan.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[SuratPemberitahuan]:
        """Get surat pemberitahuan by surat tugas ID."""
        query = select(SuratPemberitahuan).where(
            and_(
                SuratPemberitahuan.surat_tugas_id == surat_tugas_id,
                SuratPemberitahuan.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, surat_pemberitahuan_id: str, update_data: SuratPemberitahuanUpdate) -> Optional[SuratPemberitahuan]:
        """Update surat pemberitahuan."""
        surat_pemberitahuan = await self.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(surat_pemberitahuan, key, value)
        
        surat_pemberitahuan.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(surat_pemberitahuan)
        return surat_pemberitahuan
    
    async def update_file_path(self, surat_pemberitahuan_id: str, file_path: str) -> Optional[SuratPemberitahuan]:
        """Update file path."""
        surat_pemberitahuan = await self.get_by_id(surat_pemberitahuan_id)
        if not surat_pemberitahuan:
            return None
        
        surat_pemberitahuan.file_dokumen = file_path
        surat_pemberitahuan.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(surat_pemberitahuan)
        return surat_pemberitahuan
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(SuratPemberitahuan)
            .where(
                and_(
                    SuratPemberitahuan.surat_tugas_id == surat_tugas_id,
                    SuratPemberitahuan.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount
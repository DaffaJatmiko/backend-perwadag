# ===== src/repositories/kuisioner.py =====
"""Repository untuk kuisioner."""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.kuisioner import Kuisioner
from src.schemas.kuisioner import KuisionerCreate, KuisionerUpdate


class KuisionerRepository:
    """Repository untuk operasi kuisioner."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, kuisioner_data: KuisionerCreate) -> Kuisioner:
        """Create kuisioner baru (auto-generated)."""
        kuisioner = Kuisioner(
            surat_tugas_id=kuisioner_data.surat_tugas_id
        )
        
        self.session.add(kuisioner)
        await self.session.commit()
        await self.session.refresh(kuisioner)
        return kuisioner
    
    async def get_by_id(self, kuisioner_id: str) -> Optional[Kuisioner]:
        """Get kuisioner by ID."""
        query = select(Kuisioner).where(
            and_(Kuisioner.id == kuisioner_id, Kuisioner.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[Kuisioner]:
        """Get kuisioner by surat tugas ID."""
        query = select(Kuisioner).where(
            and_(
                Kuisioner.surat_tugas_id == surat_tugas_id,
                Kuisioner.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_file_path(self, kuisioner_id: str, file_path: str) -> Optional[Kuisioner]:
        """Update file path."""
        kuisioner = await self.get_by_id(kuisioner_id)
        if not kuisioner:
            return None
        
        kuisioner.file_kuisioner = file_path
        kuisioner.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(kuisioner)
        return kuisioner
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(Kuisioner)
            .where(
                and_(
                    Kuisioner.surat_tugas_id == surat_tugas_id,
                    Kuisioner.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount

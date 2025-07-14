# ===== src/repositories/matriks.py =====
"""Repository untuk matriks."""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.matriks import Matriks
from src.schemas.matriks import MatriksCreate, MatriksUpdate


class MatriksRepository:
    """Repository untuk operasi matriks."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, matriks_data: MatriksCreate) -> Matriks:
        """Create matriks baru (auto-generated)."""
        matriks = Matriks(
            surat_tugas_id=matriks_data.surat_tugas_id
        )
        
        self.session.add(matriks)
        await self.session.commit()
        await self.session.refresh(matriks)
        return matriks
    
    async def get_by_id(self, matriks_id: str) -> Optional[Matriks]:
        """Get matriks by ID."""
        query = select(Matriks).where(
            and_(Matriks.id == matriks_id, Matriks.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_surat_tugas_id(self, surat_tugas_id: str) -> Optional[Matriks]:
        """Get matriks by surat tugas ID."""
        query = select(Matriks).where(
            and_(
                Matriks.surat_tugas_id == surat_tugas_id,
                Matriks.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_file_path(self, matriks_id: str, file_path: str) -> Optional[Matriks]:
        """Update file path."""
        matriks = await self.get_by_id(matriks_id)
        if not matriks:
            return None
        
        matriks.file_dokumen_matriks = file_path
        matriks.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(matriks)
        return matriks
    
    async def soft_delete_by_surat_tugas(self, surat_tugas_id: str) -> int:
        """Soft delete by surat tugas ID."""
        query = (
            update(Matriks)
            .where(
                and_(
                    Matriks.surat_tugas_id == surat_tugas_id,
                    Matriks.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount
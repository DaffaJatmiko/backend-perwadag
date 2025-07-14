# ===== src/repositories/format_kuisioner.py =====
"""Repository untuk format kuisioner."""

from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.format_kuisioner import FormatKuisioner
from src.schemas.format_kuisioner import FormatKuisionerCreate, FormatKuisionerUpdate
from src.schemas.filters import FormatKuisionerFilterParams


class FormatKuisionerRepository:
    """Repository untuk operasi format kuisioner."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, format_kuisioner_data: FormatKuisionerCreate, file_path: str) -> FormatKuisioner:
        """Create format kuisioner baru."""
        format_kuisioner = FormatKuisioner(
            nama_template=format_kuisioner_data.nama_template,
            deskripsi=format_kuisioner_data.deskripsi,
            tahun=format_kuisioner_data.tahun,
            link_template=file_path
        )
        
        self.session.add(format_kuisioner)
        await self.session.commit()
        await self.session.refresh(format_kuisioner)
        return format_kuisioner
    
    async def get_by_id(self, format_kuisioner_id: str) -> Optional[FormatKuisioner]:
        """Get format kuisioner by ID."""
        query = select(FormatKuisioner).where(
            and_(FormatKuisioner.id == format_kuisioner_id, FormatKuisioner.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(self, filters: FormatKuisionerFilterParams) -> Tuple[List[FormatKuisioner], int]:
        """Get all format kuisioner dengan filtering."""
        query = select(FormatKuisioner).where(FormatKuisioner.deleted_at.is_(None))
        
        # Apply filters
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    FormatKuisioner.nama_template.ilike(search_term),
                    FormatKuisioner.deskripsi.ilike(search_term)
                )
            )
        
        if filters.tahun:
            query = query.where(FormatKuisioner.tahun == filters.tahun)
        
        if filters.has_file is not None:
            if filters.has_file:
                query = query.where(
                    and_(
                        FormatKuisioner.link_template.is_not(None),
                        FormatKuisioner.link_template != ""
                    )
                )
            else:
                query = query.where(
                    or_(
                        FormatKuisioner.link_template.is_(None),
                        FormatKuisioner.link_template == ""
                    )
                )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        offset = (filters.page - 1) * filters.size
        query = (
            query
            .offset(offset)
            .limit(filters.size)
            .order_by(FormatKuisioner.tahun.desc(), FormatKuisioner.nama_template)
        )
        
        # Execute query
        result = await self.session.execute(query)
        format_kuisioner_list = result.scalars().all()
        
        return list(format_kuisioner_list), total
    
    async def get_by_tahun(self, tahun: int) -> List[FormatKuisioner]:
        """Get format kuisioner by tahun."""
        query = select(FormatKuisioner).where(
            and_(
                FormatKuisioner.tahun == tahun,
                FormatKuisioner.deleted_at.is_(None)
            )
        ).order_by(FormatKuisioner.nama_template)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update(self, format_kuisioner_id: str, update_data: FormatKuisionerUpdate) -> Optional[FormatKuisioner]:
        """Update format kuisioner."""
        format_kuisioner = await self.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            return None
        
        update_fields = update_data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(format_kuisioner, key, value)
        
        format_kuisioner.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(format_kuisioner)
        return format_kuisioner
    
    async def update_file_path(self, format_kuisioner_id: str, file_path: str) -> Optional[FormatKuisioner]:
        """Update file path."""
        format_kuisioner = await self.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            return None
        
        format_kuisioner.link_template = file_path
        format_kuisioner.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(format_kuisioner)
        return format_kuisioner
    
    async def soft_delete(self, format_kuisioner_id: str) -> Optional[FormatKuisioner]:
        """Soft delete format kuisioner."""
        format_kuisioner = await self.get_by_id(format_kuisioner_id)
        if not format_kuisioner:
            return None
        
        format_kuisioner.deleted_at = datetime.utcnow()
        format_kuisioner.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return format_kuisioner
    
    async def hard_delete(self, format_kuisioner_id: str) -> bool:
        """Hard delete format kuisioner."""
        query = delete(FormatKuisioner).where(FormatKuisioner.id == format_kuisioner_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def template_exists_for_year(self, nama_template: str, tahun: int, exclude_id: Optional[str] = None) -> bool:
        """Check if template dengan nama yang sama exists untuk tahun tertentu."""
        query = select(FormatKuisioner.id).where(
            and_(
                FormatKuisioner.nama_template == nama_template,
                FormatKuisioner.tahun == tahun,
                FormatKuisioner.deleted_at.is_(None)
            )
        )
        
        if exclude_id:
            query = query.where(FormatKuisioner.id != exclude_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
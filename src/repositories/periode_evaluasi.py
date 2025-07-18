# ===== src/repositories/periode_evaluasi.py (FIXED) =====
"""Repository untuk periode evaluasi - FIXED SQLAlchemy syntax."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func, update, delete, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.periode_evaluasi import PeriodeEvaluasi
from src.models.penilaian_risiko import PenilaianRisiko
from src.schemas.periode_evaluasi import PeriodeEvaluasiCreate, PeriodeEvaluasiUpdate
from src.schemas.filters import PeriodeEvaluasiFilterParams


class PeriodeEvaluasiRepository:
    """Repository untuk operasi periode evaluasi."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ===== CREATE OPERATIONS =====
    
    async def create(self, periode_data: PeriodeEvaluasiCreate) -> PeriodeEvaluasi:
        """Create periode evaluasi baru."""
        periode = PeriodeEvaluasi(
            tahun=periode_data.tahun,
            is_locked=False  # Default tidak terkunci
        )
        
        self.session.add(periode)
        await self.session.commit()
        await self.session.refresh(periode)
        return periode
    
    # ===== READ OPERATIONS =====
    
    async def get_by_id(self, periode_id: str) -> Optional[PeriodeEvaluasi]:
        """Get periode evaluasi by ID."""
        query = select(PeriodeEvaluasi).where(
            and_(PeriodeEvaluasi.id == periode_id, PeriodeEvaluasi.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_tahun(self, tahun: int) -> Optional[PeriodeEvaluasi]:
        """Get periode evaluasi by tahun."""
        query = select(PeriodeEvaluasi).where(
            and_(PeriodeEvaluasi.tahun == tahun, PeriodeEvaluasi.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(
        self, 
        filters: PeriodeEvaluasiFilterParams
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all periode evaluasi dengan filtering dan enriched data - FIXED."""
        
        # ✅ FIXED: Proper SQLAlchemy case() syntax
        penilaian_completed_case = case(
            (PenilaianRisiko.profil_risiko_auditan.is_not(None), 1),
            else_=0
        )
        
        # Build base query dengan join untuk statistics
        query = (
            select(
                PeriodeEvaluasi,
                func.count(PenilaianRisiko.id).label('total_penilaian'),
                func.sum(penilaian_completed_case).label('penilaian_completed')
            )
            .outerjoin(
                PenilaianRisiko, 
                and_(
                    PeriodeEvaluasi.id == PenilaianRisiko.periode_id,
                    PenilaianRisiko.deleted_at.is_(None)
                )
            )
            .where(PeriodeEvaluasi.deleted_at.is_(None))
            .group_by(PeriodeEvaluasi.id)
        )
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                func.cast(PeriodeEvaluasi.tahun, func.TEXT()).ilike(search_term)
            )
        
        # Apply specific filters
        
        if filters.is_locked is not None:
            query = query.where(PeriodeEvaluasi.is_locked == filters.is_locked)
        
        # ✅ FIXED: Simplified count query
        count_query_base = select(PeriodeEvaluasi).where(PeriodeEvaluasi.deleted_at.is_(None))
        
        # Apply same filters to count query
        if filters.search:
            search_term = f"%{filters.search}%"
            count_query_base = count_query_base.where(
                func.cast(PeriodeEvaluasi.tahun, func.TEXT()).ilike(search_term)
            )

        
        if filters.is_locked is not None:
            count_query_base = count_query_base.where(PeriodeEvaluasi.is_locked == filters.is_locked)
        
        # Get total count
        count_query = select(func.count()).select_from(count_query_base.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        offset = (filters.page - 1) * filters.size
        query = (
            query
            .offset(offset)
            .limit(filters.size)
            .order_by(PeriodeEvaluasi.tahun.desc())
        )
        
        # Execute query
        result = await self.session.execute(query)
        rows = result.all()
        
        # Build enriched data
        enriched_data = []
        for row in rows:
            periode = row[0]
            total_penilaian = row[1] or 0
            penilaian_completed = row[2] or 0
            
            completion_rate = 0.0
            if total_penilaian > 0:
                completion_rate = (penilaian_completed / total_penilaian) * 100
            
            enriched_data.append({
                'periode': periode,
                'total_penilaian': total_penilaian,
                'penilaian_completed': penilaian_completed,
                'completion_rate': round(completion_rate, 2)
            })
        
        return enriched_data, total
    
    # ===== UPDATE OPERATIONS =====
    
    async def update(self, periode_id: str, periode_data: PeriodeEvaluasiUpdate) -> Optional[PeriodeEvaluasi]:
        """Update periode evaluasi."""
        periode = await self.get_by_id(periode_id)
        if not periode:
            return None
        
        # Update fields
        update_data = periode_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(periode, key, value)
        
        periode.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(periode)
        return periode
    
    # ===== DELETE OPERATIONS =====
    
    async def hard_delete(self, periode_id: str) -> bool:
        """Hard delete periode evaluasi dengan cascade ke penilaian risiko."""
        # Delete all related penilaian risiko first
        delete_penilaian_query = delete(PenilaianRisiko).where(
            PenilaianRisiko.periode_id == periode_id
        )
        await self.session.execute(delete_penilaian_query)
        
        # Delete periode evaluasi
        delete_periode_query = delete(PeriodeEvaluasi).where(
            PeriodeEvaluasi.id == periode_id
        )
        result = await self.session.execute(delete_periode_query)
        await self.session.commit()
        
        return result.rowcount > 0
    
    # ===== VALIDATION OPERATIONS =====
    
    async def tahun_exists(self, tahun: int, exclude_id: Optional[str] = None) -> bool:
        """Check if tahun already exists."""
        query = select(PeriodeEvaluasi.id).where(
            and_(
                PeriodeEvaluasi.tahun == tahun,
                PeriodeEvaluasi.deleted_at.is_(None)
            )
        )
        
        if exclude_id:
            query = query.where(PeriodeEvaluasi.id != exclude_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    # ===== STATISTICS =====
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistik periode evaluasi."""
        
        # Total periode
        total_query = select(func.count(PeriodeEvaluasi.id)).where(
            PeriodeEvaluasi.deleted_at.is_(None)
        )
        total_result = await self.session.execute(total_query)
        total_periode = total_result.scalar() or 0
        
        
        # Locked vs unlocked
        locked_query = (
            select(PeriodeEvaluasi.is_locked, func.count(PeriodeEvaluasi.id))
            .where(PeriodeEvaluasi.deleted_at.is_(None))
            .group_by(PeriodeEvaluasi.is_locked)
        )
        locked_result = await self.session.execute(locked_query)
        locked_breakdown = {row[0]: row[1] for row in locked_result.all()}
        
        return {
            "total_periode": total_periode,
            "locked_breakdown": locked_breakdown,
            "periode_locked": locked_breakdown.get(True, 0),
            "periode_unlocked": locked_breakdown.get(False, 0)
        }
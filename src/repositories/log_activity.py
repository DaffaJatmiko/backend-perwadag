# ===== src/repositories/log_activity.py =====
"""Repository untuk operasi log activity."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.log_activity import LogActivity
from src.schemas.log_activity import LogActivityCreate, LogActivityFilterParams


class LogActivityRepository:
    """Repository untuk operasi log activity."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, log_data: LogActivityCreate) -> LogActivity:
        """Create log activity baru."""
        log_activity = LogActivity(**log_data.model_dump())
        
        self.session.add(log_activity)
        await self.session.commit()
        await self.session.refresh(log_activity)
        return log_activity
    
    async def get_by_id(self, log_id: str) -> Optional[LogActivity]:
        """Get log activity by ID."""
        query = select(LogActivity).where(
            and_(LogActivity.id == log_id, LogActivity.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(
        self, 
        filters: LogActivityFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[LogActivity], int]:
        """Get filtered log activities dengan role-based access."""
        
        # Base query
        query = select(LogActivity).where(LogActivity.deleted_at.is_(None))
        
        # Role-based filtering - ADMIN ONLY ACCESS
        # Hanya admin yang bisa akses log activity
        if user_role != "ADMIN":
            # Non-admin tidak bisa akses log activity sama sekali
            query = query.where(LogActivity.id == "impossible-id-to-match")  # Force empty result
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    LogActivity.activity.ilike(search_term),
                    LogActivity.user_name.ilike(search_term),
                    LogActivity.url.ilike(search_term)
                )
            )
        
        # Apply date filters
        if filters.date_from:
            query = query.where(LogActivity.date >= filters.date_from)
        if filters.date_to:
            query = query.where(LogActivity.date <= filters.date_to)
        
        # Apply other filters
        if filters.method:
            query = query.where(LogActivity.method == filters.method)
        if filters.user_id:
            query = query.where(LogActivity.user_id == filters.user_id)
        if filters.success_only:
            query = query.where(
                and_(
                    LogActivity.response_status.is_not(None),
                    LogActivity.response_status >= 200,
                    LogActivity.response_status < 400
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = (
            query
            .order_by(desc(LogActivity.date))  # Latest first
            .offset((filters.page - 1) * filters.size)
            .limit(filters.size)
        )
        
        # Execute query
        result = await self.session.execute(query)
        log_activities = result.scalars().all()
        
        return list(log_activities), total
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive statistics untuk log activities."""
        
        # Base query dengan role filtering - ADMIN ONLY
        base_query = select(LogActivity).where(LogActivity.deleted_at.is_(None))
        
        # Hanya admin yang bisa akses statistics
        if user_role != "ADMIN":
            base_query = base_query.where(LogActivity.id == "impossible-id-to-match")  # Force empty result
        
        # Total activities
        total_result = await self.session.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_result.scalar() or 0
        
        # Success rate
        success_result = await self.session.execute(
            select(func.count()).select_from(
                base_query.where(
                    and_(
                        LogActivity.response_status >= 200,
                        LogActivity.response_status < 400
                    )
                ).subquery()
            )
        )
        success_count = success_result.scalar() or 0
        
        # Activities by method
        method_query = (
            select(LogActivity.method, func.count().label('count'))
            .select_from(base_query.subquery())
            .group_by(LogActivity.method)
        )
        method_result = await self.session.execute(method_query)
        activities_by_method = {row.method: row.count for row in method_result.all()}
        
        # Activities by day (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        day_query = (
            select(
                func.date(LogActivity.date).label('activity_date'),
                func.count().label('count')
            )
            .select_from(base_query.subquery())
            .where(LogActivity.date >= seven_days_ago)
            .group_by(func.date(LogActivity.date))
            .order_by(func.date(LogActivity.date))
        )
        day_result = await self.session.execute(day_query)
        activities_by_day = {
            str(row.activity_date): row.count 
            for row in day_result.all()
        }
        
        return {
            "total_activities": total,
            "success_count": success_count,
            "success_rate": round((success_count / max(total, 1)) * 100, 2),
            "activities_by_method": activities_by_method,
            "activities_by_day": activities_by_day
        }
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Cleanup log activities older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Soft delete old logs
        from sqlalchemy import update
        query = (
            update(LogActivity)
            .where(
                and_(
                    LogActivity.date < cutoff_date,
                    LogActivity.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow())
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount
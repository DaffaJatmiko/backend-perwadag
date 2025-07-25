# ===== src/services/log_activity.py =====
"""Service untuk log activity operations."""

from typing import Optional
from fastapi import HTTPException, status

from src.repositories.log_activity import LogActivityRepository
from src.schemas.log_activity import (
    LogActivityResponse, LogActivityListResponse, LogActivityFilterParams,
    LogActivityStatistics
)
from src.schemas.common import SuccessResponse


class LogActivityService:
    """Service untuk log activity operations."""
    
    def __init__(self, log_activity_repo: LogActivityRepository):
        self.log_activity_repo = log_activity_repo
    
    async def get_log_activity_or_404(self, log_id: str) -> LogActivityResponse:
        """Get log activity by ID or raise 404."""
        log_activity = await self.log_activity_repo.get_by_id(log_id)
        if not log_activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Log activity tidak ditemukan"
            )
        
        return LogActivityResponse.model_validate(log_activity)
    
    async def get_all_log_activities(
        self,
        filters: LogActivityFilterParams,
        user_role: str = "ADMIN",  # Force admin
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> LogActivityListResponse:
        """Get all log activities - ADMIN ONLY ACCESS."""
        
        # Get filtered data
        log_activities, total = await self.log_activity_repo.get_all_filtered(
            filters, "ADMIN", None, None  # Force admin access
        )
        
        # Convert to response objects
        log_responses = [
            LogActivityResponse.model_validate(log) 
            for log in log_activities
        ]
        
        # Calculate pagination
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0
        
        return LogActivityListResponse(
            items=log_responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
    
    async def get_statistics(self) -> LogActivityStatistics:
        """Get log activity statistics - ADMIN ONLY ACCESS."""
        stats_data = await self.log_activity_repo.get_statistics("ADMIN", None, None)
        return LogActivityStatistics(**stats_data)
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> LogActivityStatistics:
        """Get log activity statistics."""
        stats_data = await self.log_activity_repo.get_statistics(
            user_role, user_inspektorat, user_id
        )
        
        return LogActivityStatistics(**stats_data)
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> SuccessResponse:
        """Cleanup old log activities (Admin only)."""
        deleted_count = await self.log_activity_repo.cleanup_old_logs(days_to_keep)
        
        return SuccessResponse(
            success=True,
            message=f"Cleaned up {deleted_count} old log activities older than {days_to_keep} days",
            data={"deleted_count": deleted_count, "days_to_keep": days_to_keep}
        )
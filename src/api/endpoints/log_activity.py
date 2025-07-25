# ===== src/api/endpoints/log_activity.py =====
"""API endpoints untuk log activity."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.log_activity import LogActivityRepository
from src.services.log_activity import LogActivityService
from src.schemas.log_activity import (
    LogActivityResponse, LogActivityListResponse, LogActivityFilterParams,
    LogActivityStatistics
)
from src.schemas.common import SuccessResponse
from src.auth.permissions import get_current_active_user, require_roles

router = APIRouter()

# Permission dependencies - ADMIN ONLY ACCESS
admin_required = require_roles(["ADMIN"])


async def get_log_activity_service(session: AsyncSession = Depends(get_db)) -> LogActivityService:
    """Dependency untuk LogActivityService."""
    log_activity_repo = LogActivityRepository(session)
    return LogActivityService(log_activity_repo)


# ===== READ OPERATIONS =====

@router.get("/", response_model=LogActivityListResponse)
async def get_all_log_activities(
    filters: LogActivityFilterParams = Depends(),
    current_user: dict = Depends(admin_required),  # ADMIN ONLY
    service: LogActivityService = Depends(get_log_activity_service)
):
    """
    Get all log activities dengan comprehensive filtering.
    
    **⚠️ ADMIN ONLY ACCESS** - Hanya admin yang bisa melihat log activities
    
    **Query Parameters:**
    - **Pagination**: page, size
    - **Search**: search (by activity, user_name, url)
    - **Date Range**: date_from, date_to
    - **Filters**: method, user_id, success_only
    
    **Sorting**: Latest activities first (by date DESC)
    
    **Use Cases:**
    - System audit trail untuk compliance
    - Security monitoring dan investigation
    - User activity tracking untuk admin purposes
    - System usage analytics
    
    **Examples:**
    - `GET /log-activity?page=1&size=20` - Recent activities
    - `GET /log-activity?search=surat tugas` - Search activities
    - `GET /log-activity?method=DELETE&success_only=true` - Successful deletions
    - `GET /log-activity?user_id=uuid&date_from=2025-01-01` - User activities from date
    """
    
    return await service.get_all_log_activities(
        filters,
        user_role="ADMIN",  # Force admin role
        user_inspektorat=None,
        user_id=None
    )


@router.get("/{log_id}", response_model=LogActivityResponse)
async def get_log_activity(
    log_id: str,
    current_user: dict = Depends(admin_required),  # ADMIN ONLY
    service: LogActivityService = Depends(get_log_activity_service)
):
    """
    Get log activity by ID.
    
    **⚠️ ADMIN ONLY ACCESS**
    
    **Returns**: Detailed log activity information
    """
    return await service.get_log_activity_or_404(log_id)


# ===== STATISTICS =====

@router.get("/statistics/overview", response_model=LogActivityStatistics)
async def get_log_activity_statistics(
    current_user: dict = Depends(admin_required),  # ADMIN ONLY
    service: LogActivityService = Depends(get_log_activity_service)
):
    """
    Get comprehensive log activity statistics.
    
    **⚠️ ADMIN ONLY ACCESS**
    
    **Returns:**
    - Total activities dan success rate
    - Breakdown by HTTP method (POST, PUT, DELETE, etc.)
    - Activities by day (last 7 days)
    
    **Use Cases:**
    - Admin dashboard analytics
    - System usage monitoring
    - Performance metrics untuk admin
    - Security analysis
    """
    
    return await service.get_statistics(
        user_role="ADMIN",  # Force admin role
        user_inspektorat=None,
        user_id=None
    )


# ===== ADMIN OPERATIONS =====

@router.post("/cleanup", response_model=SuccessResponse)
async def cleanup_old_log_activities(
    days_to_keep: int = 90,
    current_user: dict = Depends(admin_required),
    service: LogActivityService = Depends(get_log_activity_service)
):
    """
    Cleanup old log activities (Admin only).
    
    **Accessible by**: Admin only
    
    **Parameters:**
    - days_to_keep: Number of days to keep (default: 90)
    
    **Process:**
    - Soft delete log activities older than specified days
    - Returns count of cleaned up records
    
    **Use Cases:**
    - Database maintenance
    - Storage optimization
    - Compliance with data retention policies
    
    **Examples:**
    - `POST /log-activity/cleanup?days_to_keep=30` - Keep only 30 days
    - `POST /log-activity/cleanup` - Keep 90 days (default)
    """
    return await service.cleanup_old_logs(days_to_keep)


# ===== UTILITY ENDPOINTS =====

# @router.get("/dashboard/summary")
# async def get_log_activity_dashboard_summary(
#     current_user: dict = Depends(admin_required),  # ADMIN ONLY
#     service: LogActivityService = Depends(get_log_activity_service)
# ):
#     """
#     Get dashboard summary untuk log activities.
    
#     **⚠️ ADMIN ONLY ACCESS**
    
#     **Returns**: 
#     - Quick statistics
#     - Recent activities (last 10)
#     - Activity trends
    
#     **Use Case**: Admin dashboard widgets dan overview
#     """
    
#     # Get basic statistics
#     stats = await service.get_statistics(
#         user_role="ADMIN",
#         user_inspektorat=None,
#         user_id=None
#     )
    
#     # Get recent activities
#     from src.schemas.log_activity import LogActivityFilterParams
#     recent_filters = LogActivityFilterParams(page=1, size=10)
    
#     recent_activities = await service.get_all_log_activities(
#         recent_filters,
#         user_role="ADMIN",
#         user_inspektorat=None,
#         user_id=None
#     )
    
#     return {
#         "user_info": {
#             "nama": current_user["nama"],
#             "role": current_user["role"]
#         },
#         "statistics": stats,
#         "recent_activities": recent_activities.items,
#         "quick_insights": {
#             "total_activities_today": 0,  # TODO: Calculate today's activities
#             "most_active_module": "surat tugas",  # TODO: Calculate from stats
#             "success_rate_trend": "stable"  # TODO: Calculate trend
#         }
#     }


# @router.get("/export/csv")
# async def export_log_activities_csv(
#     filters: LogActivityFilterParams = Depends(),
#     current_user: dict = Depends(admin_required),  # ADMIN ONLY
#     service: LogActivityService = Depends(get_log_activity_service)
# ):
#     """
#     Export log activities to CSV (Admin only).
    
#     **⚠️ ADMIN ONLY ACCESS**
    
#     **Parameters**: Same as GET / endpoint filters
    
#     **Returns**: CSV file download
    
#     **Use Cases:**
#     - Audit reporting
#     - Compliance documentation
#     - External analysis
    
#     **Note**: Large exports may take time, consider pagination
#     """
#     # TODO: Implement CSV export functionality
#     # This would require additional CSV generation logic
    
#     # For now, return structured data
#     # In production, this should generate and return actual CSV file
#     log_activities = await service.get_all_log_activities(
#         filters,
#         user_role="ADMIN",
#         user_inspektorat=None,
#         user_id=None
#     )
    
#     return {
#         "message": "CSV export functionality - implement with pandas/csv writer",
#         "total_records": log_activities.total,
#         "note": "This endpoint should return actual CSV file in production"
#     }
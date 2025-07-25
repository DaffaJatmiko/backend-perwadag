# ===== src/schemas/log_activity.py =====
"""Schemas untuk log activity."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

from src.models.enums import UserRole
from src.schemas.shared import (
    PaginationInfo, ModuleStatistics, BaseListResponse
)

# ===== REQUEST SCHEMAS =====

class LogActivityCreate(BaseModel):
    """Schema untuk create log activity."""
    
    user_id: str
    method: str = Field(..., pattern="^(POST|PUT|PATCH|DELETE)$")
    url: str = Field(..., max_length=1000)
    activity: str
    date: datetime
    user_name: Optional[str] = None
    ip_address: Optional[str] = None
    response_status: Optional[int] = Field(None, ge=100, le=599)


# ===== RESPONSE SCHEMAS =====

class LogActivityResponse(BaseModel):
    """Schema untuk response log activity."""
    
    id: str
    user_id: str
    method: str
    url: str
    activity: str
    date: datetime
    user_name: Optional[str] = None
    ip_address: Optional[str] = None
    response_status: Optional[int] = None
    is_success: bool
    activity_type: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LogActivityListResponse(BaseListResponse[LogActivityResponse]):
    """Standardized log activity list response dengan pagination."""
    
    statistics: Optional[ModuleStatistics] = None

# ===== FILTER SCHEMAS =====

class LogActivityFilterParams(BaseModel):
    """Filter parameters untuk log activity."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    # Search
    search: Optional[str] = Field(
        None, 
        description="Search by activity, user_name, url"
    )
    
    # Date filters
    date_from: Optional[datetime] = Field(
        None, 
        description="Filter from date"
    )
    date_to: Optional[datetime] = Field(
        None, 
        description="Filter to date"
    )
    
    # Activity filters
    method: Optional[str] = Field(
        None, 
        pattern="^(POST|PUT|PATCH|DELETE)$",
        description="Filter by HTTP method"
    )
    user_id: Optional[str] = Field(
        None,
        description="Filter by specific user"
    )
    
    # Status filters
    success_only: Optional[bool] = Field(
        None, 
        description="Filter successful operations only"
    )
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long")
        return search


# ===== STATISTICS SCHEMAS =====

class LogActivityStatistics(BaseModel):
    """Schema untuk statistics log activity."""
    
    total_activities: int
    success_count: int
    success_rate: float = Field(ge=0, le=100)
    activities_by_method: dict[str, int]
    activities_by_day: dict[str, int]  # Last 7 days
    
    model_config = ConfigDict(from_attributes=True)
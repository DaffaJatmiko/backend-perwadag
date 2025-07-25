# ===== src/models/log_activity.py =====
"""Model untuk log activity sistem."""

from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class LogActivity(BaseModel, SQLModel, table=True):
    """Model untuk log semua activity di sistem."""
    
    __tablename__ = "log_activities"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    # ===== CORE FIELDS (REQUIRED) =====
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        max_length=36,
        description="ID user yang melakukan activity"
    )
    method: str = Field(
        max_length=10,
        index=True,
        description="HTTP method: POST, PUT, DELETE, PATCH"
    )
    url: str = Field(
        max_length=500,
        description="Endpoint URL yang diakses"
    )
    activity: str = Field(
        description="Deskripsi activity yang dilakukan"
    )
    date: datetime = Field(
        index=True,
        description="Waktu activity dilakukan"
    )
    
    # ===== OPTIONAL ENRICHMENT FIELDS =====
    user_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Nama user (denormalized untuk performance)"
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,  # IPv6 support
        description="IP address client"
    )
    response_status: Optional[int] = Field(
        default=None,
        description="HTTP response status code"
    )
    
    @property
    def is_success(self) -> bool:
        """Check apakah activity berhasil."""
        if self.response_status is None:
            return False
        return 200 <= self.response_status < 400
    
    @property
    def activity_type(self) -> str:
        """Get activity type berdasarkan method."""
        return {
            "POST": "CREATE",
            "PUT": "UPDATE", 
            "PATCH": "UPDATE",
            "DELETE": "DELETE"
        }.get(self.method, "UNKNOWN")
    
    def __repr__(self) -> str:
        return f"<LogActivity(user={self.user_name}, method={self.method}, activity={self.activity[:50]}...)>"
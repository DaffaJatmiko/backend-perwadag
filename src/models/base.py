"""Base model with common fields."""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    """Mixin for timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class AuditMixin(SQLModel):
    """Mixin for audit fields."""
    created_by: Optional[str] = Field(default=None, max_length=36)  # ✅ UUID string
    updated_by: Optional[str] = Field(default=None, max_length=36)  # ✅ UUID string

class SoftDeleteMixin(SQLModel):
    """Mixin for soft delete functionality."""
    deleted_at: Optional[datetime] = Field(default=None)
    deleted_by: Optional[str] = Field(default=None, max_length=36)  # ✅ UUID string juga


class BaseModel(TimestampMixin, SoftDeleteMixin, AuditMixin):
    """Base model with all common fields."""
    pass

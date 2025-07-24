"""Email template model."""

from typing import Optional
from sqlmodel import Field, SQLModel
from .base import BaseModel


class EmailTemplate(BaseModel, table=True):
    """Email template model."""
    
    __tablename__ = "email_templates"
    
    id: Optional[str] = Field(default=None, primary_key=True, max_length=36)
    name: str = Field(max_length=100, description="Template name")
    subject_template: str = Field(max_length=200, description="Email subject with variables")
    body_template: str = Field(description="Email body with variables")
    is_active: bool = Field(default=False, description="Only one template can be active")
    
    class Config:
        """Pydantic config."""
        from_attributes = True



"""Email template schemas for request/response validation."""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from .shared import BaseListResponse


class EmailTemplateCreateRequest(BaseModel):
    """Schema for creating email template."""
    
    name: str = Field(..., max_length=100, description="Template name")
    subject_template: str = Field(..., max_length=200, description="Email subject with variables")
    body_template: str = Field(..., description="Email body with variables")


class EmailTemplateUpdateRequest(BaseModel):
    """Schema for updating email template."""
    
    name: Optional[str] = Field(None, max_length=100, description="Template name")
    subject_template: Optional[str] = Field(None, max_length=200, description="Email subject with variables")
    body_template: Optional[str] = Field(None, description="Email body with variables")


class EmailTemplateResponse(BaseModel):
    """Schema for email template response."""
    
    id: str
    name: str
    subject_template: str
    body_template: str
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class EmailTemplateListResponse(BaseListResponse[EmailTemplateResponse]):
    """Schema for email template list response."""
    pass


class EmailComposedResponse(BaseModel):
    """Schema for composed email response."""
    
    subject: str = Field(description="Composed email subject")
    body: str = Field(description="Composed email body")
    gmail_url: str = Field(description="Gmail compose URL")


class EmailVariablesResponse(BaseModel):
    """Schema for available email variables response."""
    
    variables: Dict[str, str] = Field(description="Available variables with descriptions")


class MessageResponse(BaseModel):
    """Schema for simple message response."""
    
    message: str
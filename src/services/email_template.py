"""Email template service."""

from typing import List, Optional
from fastapi import HTTPException, status

from src.repositories.email_template import EmailTemplateRepository
from src.schemas.email_template import (
    EmailTemplateCreateRequest, EmailTemplateUpdateRequest, EmailTemplateResponse, EmailTemplateListResponse
)


class EmailTemplateService:
    """Email template service."""
    
    def __init__(self, email_template_repo: EmailTemplateRepository):
        self.email_template_repo = email_template_repo
    
    async def create_template(self, template_data: EmailTemplateCreateRequest, created_by: str) -> EmailTemplateResponse:
        """Create new email template."""
        # Validate template name uniqueness
        existing_templates = await self.email_template_repo.get_all()
        if any(t.name.lower() == template_data.name.lower() for t in existing_templates):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template dengan nama tersebut sudah ada"
            )
        
        # Create template
        template = await self.email_template_repo.create(template_data, created_by)
        
        return EmailTemplateResponse(
            id=template.id,
            name=template.name,
            subject_template=template.subject_template,
            body_template=template.body_template,
            is_active=template.is_active,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            created_by=template.created_by
        )
    
    async def get_all_templates(self, page: int = 1, size: int = 20) -> EmailTemplateListResponse:
        """Get all email templates with pagination."""
        templates = await self.email_template_repo.get_all()
        
        # Simple pagination
        total = len(templates)
        start_index = (page - 1) * size
        end_index = start_index + size
        paginated_templates = templates[start_index:end_index]
        
        template_responses = [
            EmailTemplateResponse(
                id=template.id,
                name=template.name,
                subject_template=template.subject_template,
                body_template=template.body_template,
                is_active=template.is_active,
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat() if template.updated_at else None,
                created_by=template.created_by
            )
            for template in paginated_templates
        ]
        
        return EmailTemplateListResponse.create(
            items=template_responses,
            total=total,
            page=page,
            size=size
        )
    
    async def get_template_by_id(self, template_id: str) -> EmailTemplateResponse:
        """Get email template by ID."""
        template = await self.email_template_repo.get_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template tidak ditemukan"
            )
        
        return EmailTemplateResponse(
            id=template.id,
            name=template.name,
            subject_template=template.subject_template,
            body_template=template.body_template,
            is_active=template.is_active,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            created_by=template.created_by
        )
    
    async def get_active_template(self) -> Optional[EmailTemplateResponse]:
        """Get active email template."""
        template = await self.email_template_repo.get_active_template()
        if not template:
            return None
        
        return EmailTemplateResponse(
            id=template.id,
            name=template.name,
            subject_template=template.subject_template,
            body_template=template.body_template,
            is_active=template.is_active,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
            created_by=template.created_by
        )
    
    async def update_template(self, template_id: str, template_data: EmailTemplateUpdateRequest, updated_by: str) -> EmailTemplateResponse:
        """Update email template."""
        # Check if template exists
        existing_template = await self.email_template_repo.get_by_id(template_id)
        if not existing_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template tidak ditemukan"
            )
        
        # Validate name uniqueness if name is being updated
        if template_data.name:
            existing_templates = await self.email_template_repo.get_all()
            if any(t.name.lower() == template_data.name.lower() and t.id != template_id for t in existing_templates):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Template dengan nama tersebut sudah ada"
                )
        
        # Update template
        updated_template = await self.email_template_repo.update(template_id, template_data, updated_by)
        
        return EmailTemplateResponse(
            id=updated_template.id,
            name=updated_template.name,
            subject_template=updated_template.subject_template,
            body_template=updated_template.body_template,
            is_active=updated_template.is_active,
            created_at=updated_template.created_at.isoformat(),
            updated_at=updated_template.updated_at.isoformat() if updated_template.updated_at else None,
            created_by=updated_template.created_by
        )
    
    async def activate_template(self, template_id: str, updated_by: str) -> EmailTemplateResponse:
        """Activate email template."""
        # Check if template exists
        existing_template = await self.email_template_repo.get_by_id(template_id)
        if not existing_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template tidak ditemukan"
            )
        
        # Activate template (this will deactivate others)
        activated_template = await self.email_template_repo.activate_template(template_id, updated_by)
        
        return EmailTemplateResponse(
            id=activated_template.id,
            name=activated_template.name,
            subject_template=activated_template.subject_template,
            body_template=activated_template.body_template,
            is_active=activated_template.is_active,
            created_at=activated_template.created_at.isoformat(),
            updated_at=activated_template.updated_at.isoformat() if activated_template.updated_at else None,
            created_by=activated_template.created_by
        )
    
    async def delete_template(self, template_id: str, deleted_by: str) -> dict:
        """Delete email template."""
        # Check if template exists
        existing_template = await self.email_template_repo.get_by_id(template_id)
        if not existing_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template tidak ditemukan"
            )
        
        # Cannot delete active template
        if existing_template.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak dapat menghapus template yang sedang aktif"
            )
        
        # Delete template
        success = await self.email_template_repo.delete(template_id, deleted_by)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gagal menghapus template"
            )
        
        return {"message": "Template berhasil dihapus"}
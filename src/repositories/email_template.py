"""Email template repository."""

from typing import List, Optional
from uuid import uuid4
from sqlalchemy import select, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.email_template import EmailTemplate
from src.schemas.email_template import EmailTemplateCreateRequest, EmailTemplateUpdateRequest


class EmailTemplateRepository:
    """Email template repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, template_data: EmailTemplateCreateRequest, created_by: str) -> EmailTemplate:
        """Create new email template."""
        template = EmailTemplate(
            id=str(uuid4()),
            name=template_data.name,
            subject_template=template_data.subject_template,
            body_template=template_data.body_template,
            is_active=False,  # New templates are inactive by default
            created_by=created_by
        )
        
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template
    
    async def get_by_id(self, template_id: str) -> Optional[EmailTemplate]:
        """Get email template by ID."""
        query = select(EmailTemplate).where(
            and_(
                EmailTemplate.id == template_id,
                EmailTemplate.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_template(self) -> Optional[EmailTemplate]:
        """Get the currently active email template."""
        query = select(EmailTemplate).where(
            and_(
                EmailTemplate.is_active == True,
                EmailTemplate.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[EmailTemplate]:
        """Get all email templates (not deleted)."""
        query = select(EmailTemplate).where(
            EmailTemplate.deleted_at.is_(None)
        ).order_by(EmailTemplate.created_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(self, template_id: str, template_data: EmailTemplateUpdateRequest, updated_by: str) -> Optional[EmailTemplate]:
        """Update email template."""
        # First get the template
        template = await self.get_by_id(template_id)
        if not template:
            return None
        
        # Update fields that are provided
        update_data = {}
        if template_data.name is not None:
            update_data["name"] = template_data.name
        if template_data.subject_template is not None:
            update_data["subject_template"] = template_data.subject_template
        if template_data.body_template is not None:
            update_data["body_template"] = template_data.body_template
        
        if update_data:
            update_data["updated_by"] = updated_by
            update_data["updated_at"] = func.now()
            
            query = update(EmailTemplate).where(
                EmailTemplate.id == template_id
            ).values(**update_data)
            
            await self.session.execute(query)
            await self.session.commit()
            
            # Return updated template
            return await self.get_by_id(template_id)
        
        return template
    
    async def activate_template(self, template_id: str, updated_by: str) -> Optional[EmailTemplate]:
        """Activate a template and deactivate all others."""
        # First deactivate all templates
        await self.session.execute(
            update(EmailTemplate).where(
                and_(
                    EmailTemplate.is_active == True,
                    EmailTemplate.deleted_at.is_(None)
                )
            ).values(is_active=False, updated_by=updated_by, updated_at=func.now())
        )
        
        # Then activate the specified template
        await self.session.execute(
            update(EmailTemplate).where(
                EmailTemplate.id == template_id
            ).values(is_active=True, updated_by=updated_by, updated_at=func.now())
        )
        
        await self.session.commit()
        return await self.get_by_id(template_id)
    
    async def delete(self, template_id: str, deleted_by: str) -> bool:
        """Soft delete email template."""
        query = update(EmailTemplate).where(
            EmailTemplate.id == template_id
        ).values(
            deleted_at=func.now(),
            deleted_by=deleted_by
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
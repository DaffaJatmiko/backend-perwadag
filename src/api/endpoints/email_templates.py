"""Email template management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.email_template import EmailTemplateRepository
from src.services.email_template import EmailTemplateService
from src.services.email_composition import EmailCompositionService
from src.services.laporan_hasil import LaporanHasilService
from src.repositories.laporan_hasil import LaporanHasilRepository
from src.schemas.email_template import (
    EmailTemplateCreateRequest,
    EmailTemplateUpdateRequest, 
    EmailTemplateResponse,
    EmailTemplateListResponse,
    EmailComposedResponse,
    EmailVariablesResponse,
    MessageResponse
)
from src.auth.permissions import get_current_active_user, require_roles

router = APIRouter()

# Admin-only access for template management
admin_required = require_roles(["ADMIN"])


async def get_email_template_service(session: AsyncSession = Depends(get_db)) -> EmailTemplateService:
    """Get email template service dependency."""
    email_template_repo = EmailTemplateRepository(session)
    return EmailTemplateService(email_template_repo)


async def get_email_composition_service(session: AsyncSession = Depends(get_db)) -> EmailCompositionService:
    """Get email composition service dependency."""
    email_template_repo = EmailTemplateRepository(session)
    laporan_hasil_repo = LaporanHasilRepository(session)
    laporan_hasil_service = LaporanHasilService(laporan_hasil_repo)
    return EmailCompositionService(email_template_repo, laporan_hasil_service)


@router.get("/", response_model=EmailTemplateListResponse, summary="Get all email templates")
async def get_all_templates(
    page: int = 1,
    size: int = 20,
    current_user: dict = Depends(admin_required),
    service: EmailTemplateService = Depends(get_email_template_service)
):
    """
    Get all email templates (admin only).
    
    Returns paginated list of email templates with their status.
    """
    return await service.get_all_templates(page=page, size=size)


@router.get("/active", response_model=EmailTemplateResponse, summary="Get active email template")
async def get_active_template(
    current_user: dict = Depends(get_current_active_user),
    service: EmailTemplateService = Depends(get_email_template_service)
):
    """
    Get currently active email template.
    
    Returns the template that will be used for email composition.
    """
    template = await service.get_active_template()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tidak ada template email yang aktif"
        )
    return template


@router.get("/variables", response_model=EmailVariablesResponse, summary="Get available variables")
async def get_available_variables(
    current_user: dict = Depends(admin_required),
    service: EmailCompositionService = Depends(get_email_composition_service)
):
    """
    Get list of available variables for email templates (admin only).
    
    Returns dictionary of variable names and their descriptions.
    """
    variables = service.get_available_variables()
    return EmailVariablesResponse(variables=variables)


@router.get("/{template_id}", response_model=EmailTemplateResponse, summary="Get email template by ID")
async def get_template_by_id(
    template_id: str,
    current_user: dict = Depends(admin_required),
    service: EmailTemplateService = Depends(get_email_template_service)
):
    """
    Get email template by ID (admin only).
    
    Returns detailed template information including content.
    """
    return await service.get_template_by_id(template_id)


@router.post("/", response_model=EmailTemplateResponse, summary="Create email template")
async def create_template(
    template_data: EmailTemplateCreateRequest,
    current_user: dict = Depends(admin_required),
    service: EmailTemplateService = Depends(get_email_template_service)
):
    """
    Create new email template (admin only).
    
    Creates a new template with the provided content. Template will be inactive by default.
    """
    return await service.create_template(template_data, current_user["id"])


@router.put("/{template_id}", response_model=EmailTemplateResponse, summary="Update email template")
async def update_template(
    template_id: str,
    template_data: EmailTemplateUpdateRequest,
    current_user: dict = Depends(admin_required),
    service: EmailTemplateService = Depends(get_email_template_service)
):
    """
    Update email template (admin only).
    
    Updates template content. Only provided fields will be updated.
    """
    return await service.update_template(template_id, template_data, current_user["id"])


@router.post("/{template_id}/activate", response_model=EmailTemplateResponse, summary="Activate email template")
async def activate_template(
    template_id: str,
    current_user: dict = Depends(admin_required),
    service: EmailTemplateService = Depends(get_email_template_service)
):
    """
    Activate email template (admin only).
    
    Activates the specified template and deactivates all others.
    Only one template can be active at a time.
    """
    return await service.activate_template(template_id, current_user["id"])


@router.delete("/{template_id}", response_model=MessageResponse, summary="Delete email template")
async def delete_template(
    template_id: str,
    current_user: dict = Depends(admin_required),
    service: EmailTemplateService = Depends(get_email_template_service)
):
    """
    Delete email template (admin only).
    
    Soft deletes the template. Cannot delete active templates.
    """
    return await service.delete_template(template_id, current_user["id"])


@router.post("/compose-email/{laporan_hasil_id}", response_model=EmailComposedResponse, summary="Compose email for laporan hasil")
async def compose_email(
    laporan_hasil_id: str,
    current_user: dict = Depends(get_current_active_user),
    service: EmailCompositionService = Depends(get_email_composition_service)
):
    """
    Compose email for laporan hasil evaluation.
    
    Uses the active email template and replaces variables with data from the specified laporan hasil.
    Returns composed subject, body, and Gmail URL.
    """
    user_name = current_user.get("nama", "Sistem Audit")
    return await service.compose_laporan_hasil_email(laporan_hasil_id, user_name)
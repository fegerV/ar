"""
Email template management endpoints for admin panel.
"""
import re
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.auth import require_admin
from app.database import Database
from app.main import get_current_app
from app.models import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    EmailTemplateResponse,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse
)
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_database() -> Database:
    """Get database instance from app state."""
    app = get_current_app()
    return app.state.database


def render_template(template_content: str, variables: dict) -> str:
    """Render template by replacing {{variable}} placeholders."""
    result = template_content
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    return result


@router.get("/api/admin/email-templates", response_model=List[EmailTemplateResponse], dependencies=[Depends(require_admin)])
def list_email_templates(
    template_type: str = None,
    is_active: bool = None,
    database: Database = Depends(get_database)
):
    """List all email templates with optional filtering."""
    try:
        templates = database.get_email_templates(template_type=template_type, is_active=is_active)
        
        return [
            EmailTemplateResponse(
                id=t['id'],
                template_type=t['template_type'],
                subject=t['subject'],
                html_content=t['html_content'],
                variables_used=t.get('variables_used'),
                is_active=bool(t['is_active']),
                created_at=str(t['created_at']),
                updated_at=str(t['updated_at'])
            )
            for t in templates
        ]
    except Exception as e:
        logger.error(f"Error listing email templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list email templates: {str(e)}"
        )


@router.get("/api/admin/email-templates/{template_id}", response_model=EmailTemplateResponse, dependencies=[Depends(require_admin)])
def get_email_template(template_id: str, database: Database = Depends(get_database)):
    """Get a single email template by ID."""
    try:
        template = database.get_email_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found"
            )
        
        return EmailTemplateResponse(
            id=template['id'],
            template_type=template['template_type'],
            subject=template['subject'],
            html_content=template['html_content'],
            variables_used=template.get('variables_used'),
            is_active=bool(template['is_active']),
            created_at=str(template['created_at']),
            updated_at=str(template['updated_at'])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email template: {str(e)}"
        )


@router.post("/api/admin/email-templates", response_model=EmailTemplateResponse, dependencies=[Depends(require_admin)])
def create_email_template(template_data: EmailTemplateCreate, database: Database = Depends(get_database)):
    """Create a new email template."""
    try:
        template_id = str(uuid.uuid4())
        
        success = database.create_email_template(
            template_id=template_id,
            template_type=template_data.template_type,
            subject=template_data.subject,
            html_content=template_data.html_content,
            variables_used=template_data.variables_used,
            is_active=template_data.is_active
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create email template"
            )
        
        template = database.get_email_template(template_id)
        
        logger.info(f"Created email template: {template_id} ({template_data.template_type})")
        
        return EmailTemplateResponse(
            id=template['id'],
            template_type=template['template_type'],
            subject=template['subject'],
            html_content=template['html_content'],
            variables_used=template.get('variables_used'),
            is_active=bool(template['is_active']),
            created_at=str(template['created_at']),
            updated_at=str(template['updated_at'])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating email template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create email template: {str(e)}"
        )


@router.put("/api/admin/email-templates/{template_id}", response_model=EmailTemplateResponse, dependencies=[Depends(require_admin)])
def update_email_template(
    template_id: str,
    template_data: EmailTemplateUpdate,
    database: Database = Depends(get_database)
):
    """Update an existing email template."""
    try:
        existing = database.get_email_template(template_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found"
            )
        
        success = database.update_email_template(
            template_id=template_id,
            subject=template_data.subject,
            html_content=template_data.html_content,
            variables_used=template_data.variables_used,
            is_active=template_data.is_active
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update email template"
            )
        
        template = database.get_email_template(template_id)
        
        logger.info(f"Updated email template: {template_id}")
        
        return EmailTemplateResponse(
            id=template['id'],
            template_type=template['template_type'],
            subject=template['subject'],
            html_content=template['html_content'],
            variables_used=template.get('variables_used'),
            is_active=bool(template['is_active']),
            created_at=str(template['created_at']),
            updated_at=str(template['updated_at'])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating email template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update email template: {str(e)}"
        )


@router.delete("/api/admin/email-templates/{template_id}", dependencies=[Depends(require_admin)])
def delete_email_template(template_id: str, database: Database = Depends(get_database)):
    """Delete an email template."""
    try:
        existing = database.get_email_template(template_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found"
            )
        
        success = database.delete_email_template(template_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete email template"
            )
        
        logger.info(f"Deleted email template: {template_id}")
        
        return {"success": True, "message": "Email template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete email template: {str(e)}"
        )


@router.post("/api/admin/email-templates/{template_id}/toggle", dependencies=[Depends(require_admin)])
def toggle_email_template(template_id: str, database: Database = Depends(get_database)):
    """Toggle email template active status."""
    try:
        existing = database.get_email_template(template_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found"
            )
        
        success = database.toggle_email_template(template_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to toggle email template status"
            )
        
        template = database.get_email_template(template_id)
        new_status = "active" if template['is_active'] else "inactive"
        
        logger.info(f"Toggled email template {template_id} to {new_status}")
        
        return {
            "success": True,
            "message": f"Email template is now {new_status}",
            "is_active": bool(template['is_active'])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling email template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle email template: {str(e)}"
        )


@router.post("/api/admin/email-templates/{template_id}/preview", response_model=EmailTemplatePreviewResponse, dependencies=[Depends(require_admin)])
def preview_email_template(
    template_id: str,
    preview_data: EmailTemplatePreviewRequest,
    database: Database = Depends(get_database)
):
    """Preview email template with sample variable values."""
    try:
        template = database.get_email_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email template not found"
            )
        
        rendered_subject = render_template(template['subject'], preview_data.variables)
        rendered_html = render_template(template['html_content'], preview_data.variables)
        
        return EmailTemplatePreviewResponse(
            subject=rendered_subject,
            html_content=rendered_html
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing email template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview email template: {str(e)}"
        )

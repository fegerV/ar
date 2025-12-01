"""
Services package for Vertex AR.
Contains service-layer components like email queue and async email service.
"""
from app.services.email_service import EmailService, init_email_service, get_email_service
from app.services.storage_folders import StorageFoldersService, get_storage_folders_service

__all__ = [
    'EmailService',
    'init_email_service',
    'get_email_service',
    'StorageFoldersService',
    'get_storage_folders_service',
]

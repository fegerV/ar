"""
Storage utility functions for Vertex AR.
Provides helpers for storage type checking and validation.
"""


def is_local_storage(storage_type: str) -> bool:
    """
    Check if storage type is local storage (treats both 'local' and 'local_disk' as local).
    
    Args:
        storage_type: Storage type string
        
    Returns:
        True if storage type is local or local_disk
    """
    return storage_type in ("local", "local_disk")


def normalize_storage_type(storage_type: str) -> str:
    """
    Normalize storage type to canonical form.
    Converts legacy 'local' to 'local_disk'.
    
    Args:
        storage_type: Storage type string
        
    Returns:
        Normalized storage type
    """
    if storage_type == "local":
        return "local_disk"
    return storage_type

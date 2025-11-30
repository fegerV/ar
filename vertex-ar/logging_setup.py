from __future__ import annotations

import logging
import os
import re
import sys
from typing import Any, Dict, Optional

import structlog

_LOGGER_CONFIGURED = False


def _redact_sensitive_data(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processor to redact sensitive information from log entries.
    
    Masks values for keys containing: password, secret, token, key, credentials, auth
    
    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary to process
        
    Returns:
        Sanitized event dictionary
    """
    sensitive_patterns = [
        'password',
        'passwd',
        'pwd',
        'secret',
        'token',
        'key',
        'credential',
        'auth',
        'api_key',
        'apikey',
    ]
    
    def should_redact(key: str) -> bool:
        """Check if a key should be redacted."""
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)
    
    def redact_value(value: Any) -> Any:
        """Redact a value, handling different types."""
        if value is None:
            return None
        if isinstance(value, dict):
            return {k: redact_value(v) if should_redact(k) else v for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(redact_value(item) for item in value)
        if isinstance(value, str) and len(value) > 0:
            return "***REDACTED***"
        return "***REDACTED***"
    
    # Redact sensitive keys in event_dict
    for key in list(event_dict.keys()):
        if should_redact(key):
            event_dict[key] = redact_value(event_dict[key])
        elif isinstance(event_dict[key], dict):
            # Recursively redact nested dicts
            event_dict[key] = redact_value(event_dict[key])
    
    # Also scrub the main message if it contains patterns
    if 'event' in event_dict:
        message = str(event_dict['event'])
        # Redact common credential patterns in messages
        patterns = [
            (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'password=***REDACTED***'),
            (r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'token=***REDACTED***'),
            (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'secret=***REDACTED***'),
            (r'key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'key=***REDACTED***'),
        ]
        for pattern, replacement in patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        event_dict['event'] = message
    
    return event_dict


def _configure_logging() -> None:
    global _LOGGER_CONFIGURED

    if _LOGGER_CONFIGURED:
        return

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_sensitive_data,  # Add sensitive data redaction
    ]

    if json_logs:
        processors.extend(
            [
                structlog.processors.EventRenamer("message"),
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ]
        )
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).setLevel(log_level)

    _LOGGER_CONFIGURED = True


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    _configure_logging()
    logger_name = name or "vertex_ar"
    return structlog.get_logger(logger_name)

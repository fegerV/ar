from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import structlog

_LOGGER_CONFIGURED = False


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

"""
Function Broker Logging
Structured logging for observability
"""

import logging
import sys
from typing import Any, Dict
import json
from datetime import datetime


class StructuredLogger(logging.Logger):
    """Logger that outputs structured JSON logs"""
    
    def _log_structured(
        self,
        level: int,
        msg: str,
        extra: Dict[str, Any] = None,
        **kwargs
    ):
        """Log with structured JSON format"""
        extra = extra or {}
        extra.update(kwargs)
        
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": logging.getLevelName(level),
            "message": msg,
            "service": "function-broker",
            **extra
        }
        
        super()._log(level, json.dumps(record), ())


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    In production, this outputs structured JSON logs for centralized logging.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def configure_logging(log_level: str = "INFO"):
    """Configure global logging settings"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

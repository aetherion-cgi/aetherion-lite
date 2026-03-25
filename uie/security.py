"""
Security Layer - Absorbed from Cortex Gateway
Authentication and rate limiting for public UIE endpoint
"""
import time
from typing import Optional
from fastapi import Header, HTTPException, Request
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib

from config import config


# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================

class APIKeyAuth:
    """
    API key authentication.
    For CustomGPT/Claude: they'll provide API key in headers.
    """
    
    def __init__(self):
        # In production, load from secure store (Vault, etc.)
        self.valid_keys = set(config.allowed_api_keys)
        
        # For development, accept demo keys
        if not self.valid_keys:
            self.valid_keys = {
                "demo-key-12345",  # Remove in production
                "customgpt-integration-key",
                "claude-integration-key"
            }
    
    def verify(self, api_key: Optional[str]) -> str:
        """
        Verify API key and return user_id.
        Raises HTTPException if invalid.
        """
        if not config.require_api_key:
            return "anonymous"
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing API key. Include X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        if api_key not in self.valid_keys:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # Hash API key to get user_id (don't expose raw keys)
        user_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return user_id


# Global auth instance
api_key_auth = APIKeyAuth()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    FastAPI dependency for API key verification.
    Returns user_id for authenticated requests.
    """
    return api_key_auth.verify(x_api_key)


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    In-memory rate limiter.
    In production, use Redis for distributed rate limiting.
    """
    
    def __init__(self):
        # user_id -> list of (timestamp, count)
        self.requests_per_minute: defaultdict[str, list] = defaultdict(list)
        self.requests_per_hour: defaultdict[str, list] = defaultdict(list)
    
    def check_rate_limit(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if user is within rate limits.
        Returns (allowed, error_message).
        """
        if not config.rate_limit_enabled:
            return True, None
        
        now = datetime.utcnow()
        
        # Clean old entries
        self._cleanup_old_entries(user_id, now)
        
        # Check per-minute limit
        minute_count = len(self.requests_per_minute[user_id])
        if minute_count >= config.rate_limit_per_minute:
            return False, f"Rate limit exceeded: {config.rate_limit_per_minute} requests per minute"
        
        # Check per-hour limit
        hour_count = len(self.requests_per_hour[user_id])
        if hour_count >= config.rate_limit_per_hour:
            return False, f"Rate limit exceeded: {config.rate_limit_per_hour} requests per hour"
        
        # Record this request
        self.requests_per_minute[user_id].append(now)
        self.requests_per_hour[user_id].append(now)
        
        return True, None
    
    def _cleanup_old_entries(self, user_id: str, now: datetime):
        """Remove entries outside the time window"""
        # Remove minute entries older than 1 minute
        minute_cutoff = now - timedelta(minutes=1)
        self.requests_per_minute[user_id] = [
            ts for ts in self.requests_per_minute[user_id]
            if ts > minute_cutoff
        ]
        
        # Remove hour entries older than 1 hour
        hour_cutoff = now - timedelta(hours=1)
        self.requests_per_hour[user_id] = [
            ts for ts in self.requests_per_hour[user_id]
            if ts > hour_cutoff
        ]


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(request: Request, user_id: str) -> None:
    """
    FastAPI dependency for rate limiting.
    Raises HTTPException if rate limit exceeded.
    """
    allowed, error_message = rate_limiter.check_rate_limit(user_id)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=error_message,
            headers={"Retry-After": "60"}
        )


# ============================================================================
# INPUT VALIDATION & SANITIZATION
# ============================================================================

class InputValidator:
    """
    Validate and sanitize user inputs before processing.
    Prevents injection attacks, prompt injections, etc.
    """
    
    MAX_MESSAGE_LENGTH = 10000
    MAX_SESSION_ID_LENGTH = 128
    
    BLOCKED_PATTERNS = [
        # Prompt injection attempts
        "ignore previous instructions",
        "ignore all previous",
        "you are now",
        "disregard all",
        "forget everything",
        
        # System prompts
        "<system>",
        "</system>",
        "[SYSTEM]",
        
        # Attempted code injection
        "'; DROP TABLE",
        "'; DELETE FROM",
        "<script>",
        "javascript:",
    ]
    
    def validate_message(self, message: str) -> tuple[bool, Optional[str]]:
        """
        Validate natural language message.
        Returns (valid, error_message).
        """
        if not message:
            return False, "Message cannot be empty"
        
        if len(message) > self.MAX_MESSAGE_LENGTH:
            return False, f"Message too long (max {self.MAX_MESSAGE_LENGTH} characters)"
        
        # Check for blocked patterns (case-insensitive)
        message_lower = message.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in message_lower:
                return False, f"Message contains blocked content"
        
        return True, None
    
    def sanitize_session_id(self, session_id: Optional[str]) -> Optional[str]:
        """Sanitize session ID"""
        if not session_id:
            return None
        
        # Remove non-alphanumeric except hyphens
        sanitized = ''.join(c for c in session_id if c.isalnum() or c == '-')
        
        # Truncate if too long
        if len(sanitized) > self.MAX_SESSION_ID_LENGTH:
            sanitized = sanitized[:self.MAX_SESSION_ID_LENGTH]
        
        return sanitized if sanitized else None


# Global validator instance
input_validator = InputValidator()

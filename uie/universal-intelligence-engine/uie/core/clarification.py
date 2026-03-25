"""
Clarification Manager

Manages clarification loop state:
- Stores envelope + partial results in Redis with TTL
- Retrieves state for continuation
- Cleans up expired threads
"""

import json
import redis.asyncio as redis
from typing import Optional, Dict, Any
from datetime import timedelta

from uie.core.schemas import Envelope


class ClarificationManager:
    """
    Manages clarification thread state.
    
    Uses Redis for short-term state storage with TTL.
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.key_prefix = "uie:clarification:"
    
    async def store_thread_state(
        self,
        thread_id: str,
        envelope: Envelope,
        step_results: Dict[str, Any],
        ttl_seconds: int = 300
    ):
        """
        Store thread state for later continuation.
        
        Args:
            thread_id: Unique thread identifier
            envelope: Original request envelope
            step_results: Partial execution results
            ttl_seconds: How long to keep state (default 5 minutes)
        """
        key = f"{self.key_prefix}{thread_id}"
        
        state = {
            "envelope": envelope.dict(),
            "step_results": {
                k: {
                    "step_id": v.step_id,
                    "status": v.status.value,
                    "output": v.output,
                    "error": v.error,
                    "duration_ms": v.duration_ms
                }
                for k, v in step_results.items()
            }
        }
        
        # Store with TTL
        await self.redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(state, default=str)
        )
    
    async def get_thread_state(
        self,
        thread_id: str
    ) -> Optional[Envelope]:
        """
        Retrieve thread state for continuation.
        
        Returns:
            Envelope if found, None if expired/not found
        """
        key = f"{self.key_prefix}{thread_id}"
        
        data = await self.redis_client.get(key)
        if not data:
            return None
        
        state = json.loads(data)
        envelope_data = state["envelope"]
        
        # Reconstruct envelope
        return Envelope(**envelope_data)
    
    async def delete_thread_state(self, thread_id: str):
        """Delete thread state (cleanup after completion)."""
        key = f"{self.key_prefix}{thread_id}"
        await self.redis_client.delete(key)
    
    async def close(self):
        """Close Redis connection."""
        await self.redis_client.close()

"""
Aetherion Agent Registry
Manages parent/child agent lifecycle with synapse-like behavior.
Parent agents are permanent modules; child agents are ephemeral synapses.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Type
from threading import Lock


class AgentRegistry:
    """
    Central registry for agent lifecycle management.
    Treats parent agents as permanent modules and child agents as ephemeral synapses.
    """
    
    def __init__(self):
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def spawn_child(
        self,
        parent_name: str,
        agent_cls: Type,
        ttl_seconds: int = 600,
        **kwargs
    ) -> tuple[str, Any]:
        """
        Spawn a child agent with automatic TTL.
        
        Args:
            parent_name: Name of the parent agent spawning this child
            agent_cls: Class of the child agent to instantiate
            ttl_seconds: Time-to-live in seconds (default 600 = 10 minutes)
            **kwargs: Arguments to pass to agent_cls constructor
        
        Returns:
            tuple: (agent_id, agent_instance)
        """
        agent_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        try:
            agent = agent_cls(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to spawn child agent: {e}")
        
        with self._lock:
            self._agents[agent_id] = {
                "agent": agent,
                "parent": parent_name,
                "expires_at": expires_at,
                "spawned_at": datetime.utcnow(),
                "agent_cls": agent_cls.__name__,
            }
        
        return agent_id, agent
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Retrieve an agent by ID. Returns None if expired or not found.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Agent instance or None
        """
        with self._lock:
            data = self._agents.get(agent_id)
            if not data:
                return None
            
            if datetime.utcnow() > data["expires_at"]:
                del self._agents[agent_id]
                return None
            
            return data["agent"]
    
    def extend_ttl(self, agent_id: str, additional_seconds: int) -> bool:
        """
        Extend the TTL of an existing agent.
        
        Args:
            agent_id: UUID of the agent
            additional_seconds: Seconds to add to current expiration
        
        Returns:
            bool: True if successful, False if agent not found/expired
        """
        with self._lock:
            data = self._agents.get(agent_id)
            if not data:
                return False
            
            if datetime.utcnow() > data["expires_at"]:
                del self._agents[agent_id]
                return False
            
            data["expires_at"] += timedelta(seconds=additional_seconds)
            return True
    
    def prune_expired(self) -> int:
        """
        Remove all expired agents from the registry.
        
        Returns:
            int: Number of agents pruned
        """
        now = datetime.utcnow()
        with self._lock:
            expired_ids = [
                aid for aid, data in self._agents.items()
                if data["expires_at"] < now
            ]
            for aid in expired_ids:
                del self._agents[aid]
        
        return len(expired_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            dict: Statistics about active agents
        """
        with self._lock:
            now = datetime.utcnow()
            active = [data for data in self._agents.values() if data["expires_at"] >= now]
            
            return {
                "total_active": len(active),
                "by_parent": self._count_by_parent(active),
                "by_class": self._count_by_class(active),
                "oldest_age_seconds": self._get_oldest_age(active),
            }
    
    def _count_by_parent(self, agents: list) -> Dict[str, int]:
        """Count agents grouped by parent."""
        counts = {}
        for agent_data in agents:
            parent = agent_data["parent"]
            counts[parent] = counts.get(parent, 0) + 1
        return counts
    
    def _count_by_class(self, agents: list) -> Dict[str, int]:
        """Count agents grouped by class."""
        counts = {}
        for agent_data in agents:
            cls = agent_data["agent_cls"]
            counts[cls] = counts.get(cls, 0) + 1
        return counts
    
    def _get_oldest_age(self, agents: list) -> Optional[int]:
        """Get age of oldest agent in seconds."""
        if not agents:
            return None
        
        now = datetime.utcnow()
        oldest = min(agent_data["spawned_at"] for agent_data in agents)
        return int((now - oldest).total_seconds())


# Global registry instance
_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    return _registry

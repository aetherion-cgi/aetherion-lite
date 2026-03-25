"""
ILE Model Registry

Central registry for all dynamic model configurations across Aetherion APIs.
Manages configs, snapshots, rollbacks, and versioning.

Author: Aetherion Development Team
Date: November 15, 2025
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# MODEL REGISTRY
# ============================================================================

class ModelRegistry:
    """
    Central registry for dynamic model configurations.
    
    Manages configurations for:
    - BUE: Scoring models, risk thresholds, feature weights
    - URPE: Risk assessment params, simulation configs
    - UIE: Routing policies, prompt templates, LLM weights
    - UDOA: Data source priorities, transformation rules
    - CEOA: Resource allocation policies, optimization params
    - Function Broker: Security thresholds, rate limits
    """
    
    def __init__(self, db_manager=None, redis_client=None):
        """
        Initialize model registry.
        
        Args:
            db_manager: Database manager for persistent storage
            redis_client: Redis client for fast access
        """
        self.db_manager = db_manager
        self.redis_client = redis_client
        
        # In-memory cache of current configs
        self.configs: Dict[str, Dict[str, Any]] = {}
        
        # Snapshot history
        self.snapshots: Dict[str, Dict] = {}
        
        logger.info("Model Registry initialized")
    
    async def get_config(
        self,
        api: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get configuration value.
        
        Args:
            api: API identifier (bue, urpe, uie, udoa, ceoa, function_broker)
            key: Configuration key (e.g., 'risk_threshold', 'model_weights')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        config_key = f"{api}:{key}"
        
        # Check memory cache
        if config_key in self.configs:
            return self.configs[config_key]
        
        # Try Redis
        if self.redis_client:
            try:
                value = await self.redis_client.get(f"config:{config_key}")
                if value:
                    parsed = json.loads(value)
                    self.configs[config_key] = parsed
                    return parsed
            except Exception as e:
                logger.error(f"Error reading from Redis: {e}")
        
        # Try database
        if self.db_manager:
            try:
                async with self.db_manager.postgres_session() as session:
                    from sqlalchemy import text
                    
                    result = await session.execute(
                        text(
                            "SELECT config_value FROM model_configs "
                            "WHERE api = :api AND config_key = :key"
                        ),
                        {"api": api, "key": key}
                    )
                    row = result.fetchone()
                    
                    if row:
                        value = json.loads(row[0])
                        self.configs[config_key] = value
                        
                        # Update Redis cache
                        if self.redis_client:
                            await self.redis_client.setex(
                                f"config:{config_key}",
                                3600,  # 1 hour TTL
                                json.dumps(value)
                            )
                        
                        return value
            except Exception as e:
                logger.error(f"Error reading from database: {e}")
        
        # Return default
        return default
    
    async def update_config(
        self,
        api: str,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Update configuration value.
        
        Args:
            api: API identifier
            key: Configuration key
            value: New configuration value
            metadata: Optional metadata (updater, reason, etc.)
        """
        config_key = f"{api}:{key}"
        
        # Get old value for audit
        old_value = await self.get_config(api, key)
        
        # Update memory cache
        self.configs[config_key] = value
        
        # Update Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"config:{config_key}",
                    3600,  # 1 hour TTL
                    json.dumps(value)
                )
            except Exception as e:
                logger.error(f"Error updating Redis: {e}")
        
        # Update database
        if self.db_manager:
            try:
                async with self.db_manager.postgres_session() as session:
                    from sqlalchemy import text
                    
                    # Upsert config
                    await session.execute(
                        text(
                            "INSERT INTO model_configs (api, config_key, config_value, "
                            "updated_at, metadata) "
                            "VALUES (:api, :key, :value, :updated_at, :metadata) "
                            "ON CONFLICT (api, config_key) DO UPDATE SET "
                            "config_value = EXCLUDED.config_value, "
                            "updated_at = EXCLUDED.updated_at, "
                            "metadata = EXCLUDED.metadata"
                        ),
                        {
                            "api": api,
                            "key": key,
                            "value": json.dumps(value),
                            "updated_at": datetime.utcnow(),
                            "metadata": json.dumps(metadata or {})
                        }
                    )
                    
                    # Log change in audit table
                    await session.execute(
                        text(
                            "INSERT INTO config_audit_log (api, config_key, "
                            "old_value, new_value, changed_at, metadata) "
                            "VALUES (:api, :key, :old_value, :new_value, :changed_at, :metadata)"
                        ),
                        {
                            "api": api,
                            "key": key,
                            "old_value": json.dumps(old_value) if old_value else None,
                            "new_value": json.dumps(value),
                            "changed_at": datetime.utcnow(),
                            "metadata": json.dumps(metadata or {})
                        }
                    )
                    
                    await session.commit()
            except Exception as e:
                logger.error(f"Error updating database: {e}")
        
        logger.info(
            f"Updated config: {api}:{key} = {value} "
            f"(metadata: {metadata})"
        )
    
    async def snapshot_config(
        self,
        api: str,
        description: Optional[str] = None
    ) -> str:
        """
        Create snapshot of all configs for an API.
        
        Args:
            api: API identifier
            description: Optional snapshot description
        
        Returns:
            Snapshot ID
        """
        snapshot_id = str(uuid4())
        
        # Get all configs for this API
        configs = {}
        
        if self.db_manager:
            try:
                async with self.db_manager.postgres_session() as session:
                    from sqlalchemy import text
                    
                    result = await session.execute(
                        text(
                            "SELECT config_key, config_value FROM model_configs "
                            "WHERE api = :api"
                        ),
                        {"api": api}
                    )
                    
                    for row in result:
                        key, value = row
                        configs[key] = json.loads(value)
            except Exception as e:
                logger.error(f"Error creating snapshot: {e}")
                return ""
        
        # Store snapshot
        snapshot = {
            "snapshot_id": snapshot_id,
            "api": api,
            "configs": configs,
            "created_at": datetime.utcnow().isoformat(),
            "description": description
        }
        
        self.snapshots[snapshot_id] = snapshot
        
        # Persist to database
        if self.db_manager:
            try:
                async with self.db_manager.postgres_session() as session:
                    from sqlalchemy import text
                    
                    await session.execute(
                        text(
                            "INSERT INTO config_snapshots (snapshot_id, api, configs, "
                            "created_at, description) "
                            "VALUES (:snapshot_id, :api, :configs, :created_at, :description)"
                        ),
                        {
                            "snapshot_id": snapshot_id,
                            "api": api,
                            "configs": json.dumps(configs),
                            "created_at": datetime.utcnow(),
                            "description": description
                        }
                    )
                    await session.commit()
            except Exception as e:
                logger.error(f"Error persisting snapshot: {e}")
        
        logger.info(f"Created snapshot {snapshot_id} for {api}")
        return snapshot_id
    
    async def rollback_config(
        self,
        api: str,
        snapshot_id: str
    ) -> bool:
        """
        Rollback all configs to a previous snapshot.
        
        Args:
            api: API identifier
            snapshot_id: Snapshot to rollback to
        
        Returns:
            Success boolean
        """
        # Load snapshot
        snapshot = self.snapshots.get(snapshot_id)
        
        if not snapshot and self.db_manager:
            try:
                async with self.db_manager.postgres_session() as session:
                    from sqlalchemy import text
                    
                    result = await session.execute(
                        text(
                            "SELECT configs FROM config_snapshots "
                            "WHERE snapshot_id = :snapshot_id AND api = :api"
                        ),
                        {"snapshot_id": snapshot_id, "api": api}
                    )
                    row = result.fetchone()
                    
                    if row:
                        snapshot = {
                            "snapshot_id": snapshot_id,
                            "api": api,
                            "configs": json.loads(row[0])
                        }
            except Exception as e:
                logger.error(f"Error loading snapshot: {e}")
                return False
        
        if not snapshot:
            logger.error(f"Snapshot {snapshot_id} not found for {api}")
            return False
        
        # Restore all configs
        for key, value in snapshot["configs"].items():
            await self.update_config(
                api,
                key,
                value,
                metadata={
                    "operation": "rollback",
                    "snapshot_id": snapshot_id
                }
            )
        
        logger.info(f"Rolled back {api} to snapshot {snapshot_id}")
        return True
    
    async def get_config_history(
        self,
        api: str,
        key: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get change history for a config.
        
        Args:
            api: API identifier
            key: Configuration key
            limit: Max number of history entries
        
        Returns:
            List of history entries
        """
        if not self.db_manager:
            return []
        
        try:
            async with self.db_manager.postgres_session() as session:
                from sqlalchemy import text
                
                result = await session.execute(
                    text(
                        "SELECT old_value, new_value, changed_at, metadata "
                        "FROM config_audit_log "
                        "WHERE api = :api AND config_key = :key "
                        "ORDER BY changed_at DESC "
                        "LIMIT :limit"
                    ),
                    {"api": api, "key": key, "limit": limit}
                )
                
                history = []
                for row in result:
                    history.append({
                        "old_value": json.loads(row[0]) if row[0] else None,
                        "new_value": json.loads(row[1]),
                        "changed_at": row[2].isoformat(),
                        "metadata": json.loads(row[3]) if row[3] else {}
                    })
                
                return history
        except Exception as e:
            logger.error(f"Error getting config history: {e}")
            return []
    
    async def list_configs(self, api: str) -> Dict[str, Any]:
        """
        List all configurations for an API.
        
        Args:
            api: API identifier
        
        Returns:
            Dictionary of all configs
        """
        configs = {}
        
        if self.db_manager:
            try:
                async with self.db_manager.postgres_session() as session:
                    from sqlalchemy import text
                    
                    result = await session.execute(
                        text(
                            "SELECT config_key, config_value, updated_at FROM model_configs "
                            "WHERE api = :api"
                        ),
                        {"api": api}
                    )
                    
                    for row in result:
                        key, value, updated_at = row
                        configs[key] = {
                            "value": json.loads(value),
                            "updated_at": updated_at.isoformat()
                        }
            except Exception as e:
                logger.error(f"Error listing configs: {e}")
        
        return configs


# ============================================================================
# GLOBAL REGISTRY INSTANCE
# ============================================================================

_registry: Optional[ModelRegistry] = None


async def get_registry(db_manager=None, redis_client=None) -> ModelRegistry:
    """Get global model registry instance"""
    global _registry
    
    if _registry is None:
        _registry = ModelRegistry(db_manager, redis_client)
    
    return _registry


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        registry = ModelRegistry()
        
        # Test config management
        await registry.update_config(
            "bue",
            "risk_threshold",
            0.25,
            metadata={"updated_by": "test", "reason": "testing"}
        )
        
        value = await registry.get_config("bue", "risk_threshold")
        print(f"Risk threshold: {value}")
        
        # Test complex config
        await registry.update_config(
            "uie",
            "llm_weights",
            {
                "claude-3-opus": 0.5,
                "gpt-4": 0.3,
                "claude-3-sonnet": 0.2
            }
        )
        
        weights = await registry.get_config("uie", "llm_weights")
        print(f"LLM weights: {weights}")
        
        # Test snapshot
        snapshot_id = await registry.snapshot_config("uie", "Before changes")
        print(f"Created snapshot: {snapshot_id}")
        
        # Modify config
        await registry.update_config("uie", "llm_weights", {"claude-3-opus": 1.0})
        
        # Rollback
        await registry.rollback_config("uie", snapshot_id)
        weights = await registry.get_config("uie", "llm_weights")
        print(f"After rollback: {weights}")
        
        # List all configs
        all_configs = await registry.list_configs("uie")
        print(f"All UIE configs: {all_configs}")
        
        print("\n✅ Model Registry test completed!")
    
    asyncio.run(test())

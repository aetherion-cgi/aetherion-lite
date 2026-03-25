"""
Internal Learning Engine - Database Configuration

Database schemas and connection management for:
- PostgreSQL + TimescaleDB (time-series learning data)
- Neo4j (knowledge graph)
- Redis (caching and task queue)

Author: Aetherion Development Team
Date: November 15, 2025
"""

import asyncio
import hashlib
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Optional

import asyncpg
from neo4j import AsyncGraphDatabase, AsyncDriver
from redis.asyncio import Redis, ConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    JSON, Text, Index, UniqueConstraint, ForeignKey
)

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


# ============================================================================
# POSTGRESQL SCHEMA DEFINITIONS
# ============================================================================

class LearningEventTable(Base):
    """Learning events table with TimescaleDB hypertable"""
    __tablename__ = "learning_events"
    
    event_id = Column(String(36), primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    domain = Column(String(50), nullable=False, index=True)
    api = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Event data (JSONB for flexibility)
    prediction_id = Column(String(100), index=True)
    inputs = Column(JSON, nullable=False)
    predicted = Column(JSON)
    actual = Column(JSON)
    learning_signal = Column(Float)
    
    # Metadata
    metadata = Column(JSON, default={})
    jurisdiction = Column(String(20), nullable=False, default="sandbox")
    
    __table_args__ = (
        Index('idx_learning_events_api_domain', 'api', 'domain'),
        Index('idx_learning_events_timestamp_desc', 'timestamp', postgresql_using='btree'),
    )


class TaskOutcomeTable(Base):
    """Task outcomes for Domain 1 learning"""
    __tablename__ = "task_outcomes"
    
    outcome_id = Column(String(36), primary_key=True)
    prediction_id = Column(String(100), nullable=False, unique=True, index=True)
    api = Column(String(20), nullable=False, index=True)
    
    # Prediction
    predicted_at = Column(DateTime, nullable=False, index=True)
    inputs = Column(JSON, nullable=False)
    predicted = Column(JSON, nullable=False)
    confidence = Column(Float)
    
    # Actual outcome
    actual = Column(JSON)
    actual_at = Column(DateTime, index=True)
    outcome_delay_days = Column(Integer)
    
    # Learning
    learning_signal = Column(Float)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_task_outcomes_pending', 'processed', 'predicted_at'),
        Index('idx_task_outcomes_api_processed', 'api', 'processed'),
    )


class ConstitutionalValidationTable(Base):
    """Constitutional governance validation results"""
    __tablename__ = "constitutional_validations"
    
    validation_id = Column(String(36), primary_key=True)
    event_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Scoring
    benefit_score = Column(Float, nullable=False)
    harm_score = Column(Float, nullable=False)
    net_benefit = Column(Float, nullable=False, index=True)
    
    # Decision
    decision = Column(String(30), nullable=False, index=True)
    decision_reason = Column(Text, nullable=False)
    
    # Checks
    human_primacy_check = Column(Boolean, nullable=False)
    privacy_check = Column(Boolean, nullable=False)
    bias_check = Column(Boolean, nullable=False)
    sovereignty_check = Column(Boolean, nullable=False)
    
    # Violations
    violations = Column(JSON, default=[])
    
    # Override
    human_override = Column(Boolean)
    override_reason = Column(Text)
    override_by = Column(String(100))
    
    __table_args__ = (
        Index('idx_constitutional_decision', 'decision', 'timestamp'),
        Index('idx_constitutional_net_benefit', 'net_benefit', 'timestamp'),
    )


class AuditLogTable(Base):
    """Immutable audit trail with blockchain-style chaining"""
    __tablename__ = "audit_log"
    
    log_id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # References
    event_id = Column(String(36), nullable=False, index=True)
    validation_id = Column(String(36), nullable=False, index=True)
    
    # Decision details
    action_type = Column(String(50), nullable=False)
    decision = Column(String(30), nullable=False, index=True)
    benefit_score = Column(Float, nullable=False)
    harm_score = Column(Float, nullable=False)
    
    # Context
    api = Column(String(20), nullable=False, index=True)
    domain = Column(String(50), nullable=False, index=True)
    jurisdiction = Column(String(20), nullable=False, index=True)
    
    # Blockchain-style chaining
    previous_hash = Column(String(64))
    current_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    __table_args__ = (
        Index('idx_audit_log_api_domain', 'api', 'domain', 'timestamp'),
        Index('idx_audit_log_jurisdiction', 'jurisdiction', 'timestamp'),
    )


class KnowledgeItemTable(Base):
    """Extracted knowledge items"""
    __tablename__ = "knowledge_items"
    
    knowledge_id = Column(String(36), primary_key=True)
    domain = Column(String(50), nullable=False, index=True)
    source = Column(Text, nullable=False, index=True)
    
    # Content
    fact = Column(Text, nullable=False)
    entities = Column(JSON, default=[])
    relationships = Column(JSON, default=[])
    context = Column(JSON, default={})
    
    # Credibility
    credibility_score = Column(Float, nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    
    # Timestamps
    extracted_at = Column(DateTime, nullable=False, index=True)
    validated_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_knowledge_domain_credibility', 'domain', 'credibility_score'),
        Index('idx_knowledge_source_type', 'source_type', 'extracted_at'),
    )


class LearningMetricsTable(Base):
    """Learning performance metrics"""
    __tablename__ = "learning_metrics"
    
    metric_id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Scope
    domain = Column(String(50), index=True)
    api = Column(String(20), index=True)
    timeframe_minutes = Column(Integer, nullable=False)
    
    # Event counts
    total_events = Column(Integer, nullable=False, default=0)
    processed_events = Column(Integer, nullable=False, default=0)
    rejected_events = Column(Integer, nullable=False, default=0)
    
    # Constitutional metrics
    approval_rate = Column(Float, nullable=False)
    avg_benefit_score = Column(Float, nullable=False)
    avg_harm_score = Column(Float, nullable=False)
    
    # Performance
    avg_processing_time_ms = Column(Float, nullable=False)
    knowledge_items_added = Column(Integer, nullable=False, default=0)
    patterns_discovered = Column(Integer, nullable=False, default=0)
    
    __table_args__ = (
        Index('idx_metrics_domain_api', 'domain', 'api', 'timestamp'),
    )


# ============================================================================
# DATABASE CONNECTION MANAGER
# ============================================================================

class DatabaseManager:
    """Manages connections to PostgreSQL, Neo4j, and Redis"""
    
    def __init__(
        self,
        postgres_url: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        redis_url: str
    ):
        self.postgres_url = postgres_url
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.redis_url = redis_url
        
        # Connections (initialized in startup)
        self.postgres_engine = None
        self.postgres_session_factory = None
        self.neo4j_driver: Optional[AsyncDriver] = None
        self.redis: Optional[Redis] = None
        
        logger.info("Database manager initialized")
    
    async def startup(self):
        """Initialize all database connections"""
        logger.info("Starting database connections...")
        
        # PostgreSQL with SQLAlchemy
        self.postgres_engine = create_async_engine(
            self.postgres_url,
            echo=False,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        self.postgres_session_factory = async_sessionmaker(
            self.postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with self.postgres_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Enable TimescaleDB hypertable for learning_events
        await self._enable_timescaledb()
        
        # Neo4j
        self.neo4j_driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password),
            max_connection_pool_size=50
        )
        
        # Verify Neo4j connection
        await self.neo4j_driver.verify_connectivity()
        
        # Create Neo4j constraints and indexes
        await self._create_neo4j_schema()
        
        # Redis
        self.redis = Redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50
        )
        
        # Test Redis connection
        await self.redis.ping()
        
        logger.info("All database connections established successfully")
    
    async def shutdown(self):
        """Close all database connections"""
        logger.info("Shutting down database connections...")
        
        if self.postgres_engine:
            await self.postgres_engine.dispose()
        
        if self.neo4j_driver:
            await self.neo4j_driver.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("All database connections closed")
    
    async def _enable_timescaledb(self):
        """Enable TimescaleDB hypertable for time-series data"""
        try:
            async with self.postgres_engine.begin() as conn:
                # Create TimescaleDB extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
                
                # Convert learning_events to hypertable
                await conn.execute("""
                    SELECT create_hypertable(
                        'learning_events',
                        'timestamp',
                        if_not_exists => TRUE,
                        chunk_time_interval => INTERVAL '1 day'
                    )
                """)
                
                logger.info("TimescaleDB hypertable enabled for learning_events")
        except Exception as e:
            logger.warning(f"Could not enable TimescaleDB (may not be installed): {e}")
    
    async def _create_neo4j_schema(self):
        """Create Neo4j constraints and indexes"""
        async with self.neo4j_driver.session() as session:
            # Node constraints
            await session.run("""
                CREATE CONSTRAINT knowledge_node_id IF NOT EXISTS
                FOR (k:Knowledge) REQUIRE k.node_id IS UNIQUE
            """)
            
            await session.run("""
                CREATE CONSTRAINT pattern_node_id IF NOT EXISTS
                FOR (p:Pattern) REQUIRE p.node_id IS UNIQUE
            """)
            
            await session.run("""
                CREATE CONSTRAINT entity_node_id IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.node_id IS UNIQUE
            """)
            
            # Indexes
            await session.run("""
                CREATE INDEX knowledge_domain IF NOT EXISTS
                FOR (k:Knowledge) ON (k.domain)
            """)
            
            await session.run("""
                CREATE INDEX pattern_domain IF NOT EXISTS
                FOR (p:Pattern) ON (p.domain)
            """)
            
            await session.run("""
                CREATE INDEX entity_type IF NOT EXISTS
                FOR (e:Entity) ON (e.entity_type)
            """)
            
            logger.info("Neo4j schema created successfully")
    
    @asynccontextmanager
    async def postgres_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for PostgreSQL sessions"""
        async with self.postgres_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    @asynccontextmanager
    async def neo4j_session(self):
        """Context manager for Neo4j sessions"""
        async with self.neo4j_driver.session() as session:
            yield session


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_audit_hash(
    event_id: str,
    validation_id: str,
    decision: str,
    timestamp: datetime,
    previous_hash: Optional[str]
) -> str:
    """
    Create blockchain-style hash for audit trail entry.
    """
    data = f"{event_id}:{validation_id}:{decision}:{timestamp.isoformat()}:{previous_hash or ''}"
    return hashlib.sha256(data.encode()).hexdigest()


async def get_last_audit_hash(session: AsyncSession) -> Optional[str]:
    """Get the hash of the most recent audit log entry."""
    from sqlalchemy import select, desc
    
    result = await session.execute(
        select(AuditLogTable.current_hash)
        .order_by(desc(AuditLogTable.timestamp))
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


# ============================================================================
# GLOBAL DATABASE INSTANCE
# ============================================================================

# Global database manager instance (initialized by orchestrator)
db_manager: Optional[DatabaseManager] = None


async def init_database(
    postgres_url: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    redis_url: str
) -> DatabaseManager:
    """
    Initialize global database manager.
    
    Args:
        postgres_url: PostgreSQL connection URL
        neo4j_uri: Neo4j bolt:// URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        redis_url: Redis connection URL
    
    Returns:
        DatabaseManager instance
    """
    global db_manager
    
    db_manager = DatabaseManager(
        postgres_url=postgres_url,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        redis_url=redis_url
    )
    
    await db_manager.startup()
    
    return db_manager


async def close_database():
    """Close global database manager."""
    global db_manager
    
    if db_manager:
        await db_manager.shutdown()
        db_manager = None

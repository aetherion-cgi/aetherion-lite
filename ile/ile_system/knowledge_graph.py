"""
Internal Learning Engine - Knowledge Graph Connector

Neo4j integration for storing and querying learned knowledge across all domains.
Manages:
- Knowledge nodes (facts, entities, concepts)
- Relationships between knowledge items
- Cross-domain patterns
- Pattern extraction and synthesis

Author: Aetherion Development Team
Date: November 15, 2025
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from neo4j import AsyncSession

from .models import (
    KnowledgeItem, GraphNode, GraphRelationship, CrossDomainPattern,
    DomainType, APIType
)
from .database import db_manager

logger = logging.getLogger(__name__)


# ============================================================================
# KNOWLEDGE GRAPH CONNECTOR
# ============================================================================

class KnowledgeGraphConnector:
    """
    Manages the Neo4j knowledge graph for the ILE system.
    
    Graph Structure:
    - Nodes: Knowledge items, entities, patterns, concepts
    - Relationships: Causal, correlational, hierarchical
    - Properties: Confidence, credibility, timestamps
    
    Capabilities:
    - Store new knowledge
    - Query related knowledge
    - Extract patterns
    - Cross-domain synthesis
    - Knowledge graph statistics
    """
    
    def __init__(self):
        if not db_manager:
            raise RuntimeError("Database manager not initialized")
        
        logger.info("Knowledge Graph Connector initialized")
    
    # ========================================================================
    # KNOWLEDGE STORAGE
    # ========================================================================
    
    async def store_knowledge(
        self,
        knowledge: KnowledgeItem,
        connect_to_existing: bool = True
    ) -> str:
        """
        Store a knowledge item in the graph.
        
        Args:
            knowledge: Knowledge item to store
            connect_to_existing: Automatically connect to related knowledge
        
        Returns:
            Node ID in the graph
        """
        try:
            async with db_manager.neo4j_session() as session:
                # Create knowledge node
                result = await session.run("""
                    CREATE (k:Knowledge {
                        node_id: $node_id,
                        knowledge_id: $knowledge_id,
                        domain: $domain,
                        source: $source,
                        fact: $fact,
                        entities: $entities,
                        credibility_score: $credibility_score,
                        source_type: $source_type,
                        extracted_at: datetime($extracted_at),
                        validated: $validated
                    })
                    RETURN k.node_id AS node_id
                """, 
                    node_id=str(knowledge.knowledge_id),
                    knowledge_id=str(knowledge.knowledge_id),
                    domain=knowledge.domain.value,
                    source=knowledge.source,
                    fact=knowledge.fact,
                    entities=knowledge.entities,
                    credibility_score=knowledge.credibility_score,
                    source_type=knowledge.source_type,
                    extracted_at=knowledge.extracted_at.isoformat(),
                    validated=knowledge.validated_at is not None
                )
                
                record = await result.single()
                node_id = record["node_id"]
                
                # Create entity nodes and relationships
                for entity in knowledge.entities:
                    await self._create_or_link_entity(
                        session, node_id, entity, knowledge.domain
                    )
                
                # Connect to existing knowledge if requested
                if connect_to_existing:
                    await self._connect_related_knowledge(
                        session, node_id, knowledge
                    )
                
                logger.info(f"Stored knowledge: {node_id} from {knowledge.domain}")
                
                return node_id
        
        except Exception as e:
            logger.error(f"Error storing knowledge: {e}", exc_info=True)
            raise
    
    async def store_pattern(
        self,
        pattern: CrossDomainPattern
    ) -> str:
        """
        Store a cross-domain pattern in the graph.
        
        Args:
            pattern: Pattern to store
        
        Returns:
            Node ID in the graph
        """
        try:
            async with db_manager.neo4j_session() as session:
                result = await session.run("""
                    CREATE (p:Pattern {
                        node_id: $node_id,
                        pattern_id: $pattern_id,
                        pattern_name: $pattern_name,
                        description: $description,
                        source_domains: $source_domains,
                        applicable_apis: $applicable_apis,
                        instances_observed: $instances_observed,
                        accuracy: $accuracy,
                        created_at: datetime()
                    })
                    RETURN p.node_id AS node_id
                """,
                    node_id=str(pattern.pattern_id),
                    pattern_id=str(pattern.pattern_id),
                    pattern_name=pattern.pattern_name,
                    description=pattern.description,
                    source_domains=[d.value for d in pattern.source_domains],
                    applicable_apis=[a.value for a in pattern.applicable_apis],
                    instances_observed=pattern.instances_observed,
                    accuracy=pattern.accuracy
                )
                
                record = await result.single()
                node_id = record["node_id"]
                
                logger.info(f"Stored pattern: {pattern.pattern_name} ({node_id})")
                
                return node_id
        
        except Exception as e:
            logger.error(f"Error storing pattern: {e}", exc_info=True)
            raise
    
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 1.0,
        confidence: float = 1.0,
        properties: Optional[Dict] = None
    ) -> str:
        """
        Create a relationship between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Type of relationship
            strength: Relationship strength (0-1)
            confidence: Confidence in relationship (0-1)
            properties: Additional properties
        
        Returns:
            Relationship ID
        """
        try:
            async with db_manager.neo4j_session() as session:
                props = properties or {}
                
                result = await session.run(f"""
                    MATCH (s {{node_id: $source_id}})
                    MATCH (t {{node_id: $target_id}})
                    CREATE (s)-[r:{relationship_type} {{
                        strength: $strength,
                        confidence: $confidence,
                        created_at: datetime(),
                        properties: $properties
                    }}]->(t)
                    RETURN id(r) AS rel_id
                """,
                    source_id=source_id,
                    target_id=target_id,
                    strength=strength,
                    confidence=confidence,
                    properties=props
                )
                
                record = await result.single()
                rel_id = str(record["rel_id"])
                
                logger.info(
                    f"Created relationship: {source_id} -{relationship_type}-> {target_id}"
                )
                
                return rel_id
        
        except Exception as e:
            logger.error(f"Error creating relationship: {e}", exc_info=True)
            raise
    
    # ========================================================================
    # KNOWLEDGE QUERYING
    # ========================================================================
    
    async def query_related_knowledge(
        self,
        node_id: str,
        max_depth: int = 2,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Query knowledge related to a given node.
        
        Args:
            node_id: Starting node ID
            max_depth: Maximum relationship depth to traverse
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of related knowledge items with relationships
        """
        try:
            async with db_manager.neo4j_session() as session:
                result = await session.run("""
                    MATCH path = (start:Knowledge {node_id: $node_id})-[r*1..$max_depth]-(related)
                    WHERE ALL(rel IN r WHERE rel.confidence >= $min_confidence)
                    RETURN 
                        related.node_id AS node_id,
                        related.fact AS fact,
                        related.domain AS domain,
                        related.credibility_score AS credibility,
                        length(path) AS distance,
                        [rel IN r | type(rel)] AS relationship_path
                    ORDER BY distance, credibility DESC
                    LIMIT 50
                """,
                    node_id=node_id,
                    max_depth=max_depth,
                    min_confidence=min_confidence
                )
                
                related = []
                async for record in result:
                    related.append({
                        "node_id": record["node_id"],
                        "fact": record["fact"],
                        "domain": record["domain"],
                        "credibility": record["credibility"],
                        "distance": record["distance"],
                        "relationship_path": record["relationship_path"]
                    })
                
                logger.info(f"Found {len(related)} related knowledge items")
                
                return related
        
        except Exception as e:
            logger.error(f"Error querying related knowledge: {e}", exc_info=True)
            return []
    
    async def find_patterns_by_domain(
        self,
        domain: DomainType,
        min_accuracy: float = 0.7
    ) -> List[Dict]:
        """
        Find patterns applicable to a specific domain.
        
        Args:
            domain: Domain type
            min_accuracy: Minimum pattern accuracy
        
        Returns:
            List of patterns with metadata
        """
        try:
            async with db_manager.neo4j_session() as session:
                result = await session.run("""
                    MATCH (p:Pattern)
                    WHERE $domain IN p.source_domains AND p.accuracy >= $min_accuracy
                    RETURN 
                        p.node_id AS node_id,
                        p.pattern_name AS name,
                        p.description AS description,
                        p.source_domains AS domains,
                        p.applicable_apis AS apis,
                        p.instances_observed AS instances,
                        p.accuracy AS accuracy
                    ORDER BY p.accuracy DESC, p.instances_observed DESC
                """,
                    domain=domain.value,
                    min_accuracy=min_accuracy
                )
                
                patterns = []
                async for record in result:
                    patterns.append({
                        "node_id": record["node_id"],
                        "name": record["name"],
                        "description": record["description"],
                        "domains": record["domains"],
                        "apis": record["apis"],
                        "instances": record["instances"],
                        "accuracy": record["accuracy"]
                    })
                
                logger.info(f"Found {len(patterns)} patterns for {domain}")
                
                return patterns
        
        except Exception as e:
            logger.error(f"Error finding patterns: {e}", exc_info=True)
            return []
    
    async def search_knowledge(
        self,
        query: str,
        domain: Optional[DomainType] = None,
        min_credibility: float = 0.5,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for knowledge by text query.
        
        Args:
            query: Search query
            domain: Optional domain filter
            min_credibility: Minimum credibility threshold
            limit: Maximum results
        
        Returns:
            List of matching knowledge items
        """
        try:
            async with db_manager.neo4j_session() as session:
                # Simple text search (can be enhanced with full-text index)
                domain_filter = "AND k.domain = $domain" if domain else ""
                
                result = await session.run(f"""
                    MATCH (k:Knowledge)
                    WHERE k.fact CONTAINS $query
                    {domain_filter}
                    AND k.credibility_score >= $min_credibility
                    RETURN 
                        k.node_id AS node_id,
                        k.fact AS fact,
                        k.domain AS domain,
                        k.source AS source,
                        k.credibility_score AS credibility,
                        k.extracted_at AS extracted_at
                    ORDER BY k.credibility_score DESC
                    LIMIT $limit
                """,
                    query=query,
                    domain=domain.value if domain else None,
                    min_credibility=min_credibility,
                    limit=limit
                )
                
                results = []
                async for record in result:
                    results.append({
                        "node_id": record["node_id"],
                        "fact": record["fact"],
                        "domain": record["domain"],
                        "source": record["source"],
                        "credibility": record["credibility"],
                        "extracted_at": record["extracted_at"]
                    })
                
                logger.info(f"Found {len(results)} knowledge items for query: {query}")
                
                return results
        
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # PATTERN EXTRACTION
    # ========================================================================
    
    async def extract_patterns(
        self,
        min_instances: int = 3,
        min_confidence: float = 0.7
    ) -> List[Dict]:
        """
        Extract common patterns from the knowledge graph.
        
        Args:
            min_instances: Minimum pattern instances required
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of discovered patterns
        """
        try:
            async with db_manager.neo4j_session() as session:
                # Find frequently occurring relationship patterns
                result = await session.run("""
                    MATCH path = (k1:Knowledge)-[r]->(k2:Knowledge)
                    WHERE r.confidence >= $min_confidence
                    WITH type(r) AS rel_type, 
                         k1.domain AS source_domain, 
                         k2.domain AS target_domain,
                         count(*) AS instances
                    WHERE instances >= $min_instances
                    RETURN 
                        rel_type,
                        source_domain,
                        target_domain,
                        instances
                    ORDER BY instances DESC
                    LIMIT 20
                """,
                    min_instances=min_instances,
                    min_confidence=min_confidence
                )
                
                patterns = []
                async for record in result:
                    patterns.append({
                        "relationship_type": record["rel_type"],
                        "source_domain": record["source_domain"],
                        "target_domain": record["target_domain"],
                        "instances": record["instances"]
                    })
                
                logger.info(f"Extracted {len(patterns)} patterns")
                
                return patterns
        
        except Exception as e:
            logger.error(f"Error extracting patterns: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # CROSS-DOMAIN SYNTHESIS
    # ========================================================================
    
    async def find_cross_domain_connections(
        self,
        source_domain: DomainType,
        target_domain: DomainType,
        min_strength: float = 0.5
    ) -> List[Dict]:
        """
        Find connections between different learning domains.
        
        Args:
            source_domain: Source domain
            target_domain: Target domain
            min_strength: Minimum connection strength
        
        Returns:
            List of cross-domain connections
        """
        try:
            async with db_manager.neo4j_session() as session:
                result = await session.run("""
                    MATCH (k1:Knowledge {domain: $source_domain})-[r*1..3]-(k2:Knowledge {domain: $target_domain})
                    WHERE ALL(rel IN r WHERE rel.strength >= $min_strength)
                    RETURN 
                        k1.node_id AS source_id,
                        k1.fact AS source_fact,
                        k2.node_id AS target_id,
                        k2.fact AS target_fact,
                        length(r) AS distance,
                        [rel IN r | type(rel)] AS path
                    ORDER BY distance
                    LIMIT 30
                """,
                    source_domain=source_domain.value,
                    target_domain=target_domain.value,
                    min_strength=min_strength
                )
                
                connections = []
                async for record in result:
                    connections.append({
                        "source_id": record["source_id"],
                        "source_fact": record["source_fact"],
                        "target_id": record["target_id"],
                        "target_fact": record["target_fact"],
                        "distance": record["distance"],
                        "path": record["path"]
                    })
                
                logger.info(
                    f"Found {len(connections)} connections between "
                    f"{source_domain} and {target_domain}"
                )
                
                return connections
        
        except Exception as e:
            logger.error(f"Error finding cross-domain connections: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # STATISTICS AND ANALYTICS
    # ========================================================================
    
    async def get_statistics(self) -> Dict:
        """
        Get knowledge graph statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            async with db_manager.neo4j_session() as session:
                # Count nodes by type
                result = await session.run("""
                    MATCH (n)
                    RETURN labels(n) AS labels, count(n) AS count
                """)
                
                node_counts = {}
                async for record in result:
                    label = record["labels"][0] if record["labels"] else "Unknown"
                    node_counts[label] = record["count"]
                
                # Count relationships by type
                result = await session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) AS type, count(r) AS count
                """)
                
                rel_counts = {}
                async for record in result:
                    rel_counts[record["type"]] = record["count"]
                
                # Domain distribution
                result = await session.run("""
                    MATCH (k:Knowledge)
                    RETURN k.domain AS domain, count(k) AS count
                    ORDER BY count DESC
                """)
                
                domain_dist = {}
                async for record in result:
                    domain_dist[record["domain"]] = record["count"]
                
                stats = {
                    "node_counts": node_counts,
                    "relationship_counts": rel_counts,
                    "domain_distribution": domain_dist,
                    "total_nodes": sum(node_counts.values()),
                    "total_relationships": sum(rel_counts.values())
                }
                
                logger.info(f"Knowledge graph stats: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")
                
                return stats
        
        except Exception as e:
            logger.error(f"Error getting statistics: {e}", exc_info=True)
            return {}
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _create_or_link_entity(
        self,
        session: AsyncSession,
        knowledge_id: str,
        entity: str,
        domain: DomainType
    ):
        """Create or link to an entity node"""
        await session.run("""
            MERGE (e:Entity {name: $entity})
            ON CREATE SET 
                e.node_id = randomUUID(),
                e.entity_type = 'general',
                e.first_seen = datetime(),
                e.domains = [$domain]
            ON MATCH SET
                e.domains = CASE 
                    WHEN NOT $domain IN e.domains 
                    THEN e.domains + $domain 
                    ELSE e.domains 
                END
            WITH e
            MATCH (k:Knowledge {node_id: $knowledge_id})
            MERGE (k)-[:MENTIONS]->(e)
        """,
            entity=entity,
            domain=domain.value,
            knowledge_id=knowledge_id
        )
    
    async def _connect_related_knowledge(
        self,
        session: AsyncSession,
        new_node_id: str,
        knowledge: KnowledgeItem
    ):
        """Automatically connect to related existing knowledge"""
        # Find knowledge with common entities
        if not knowledge.entities:
            return
        
        await session.run("""
            MATCH (new:Knowledge {node_id: $node_id})
            MATCH (existing:Knowledge)-[:MENTIONS]->(e:Entity)
            WHERE e.name IN $entities 
                AND existing.node_id <> $node_id
                AND existing.credibility_score >= 0.5
            WITH new, existing, count(e) AS common_entities
            WHERE common_entities >= 1
            MERGE (new)-[r:RELATED_TO]->(existing)
            SET r.strength = toFloat(common_entities) / size($entities),
                r.confidence = (new.credibility_score + existing.credibility_score) / 2,
                r.reason = 'common_entities'
        """,
            node_id=new_node_id,
            entities=knowledge.entities
        )


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_knowledge_graph: Optional[KnowledgeGraphConnector] = None


def get_knowledge_graph() -> KnowledgeGraphConnector:
    """Get global knowledge graph connector (singleton)"""
    global _knowledge_graph
    
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraphConnector()
    
    return _knowledge_graph


# ============================================================================
# MAIN - For standalone testing
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from .database import init_database
    import os
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test():
        """Test knowledge graph functionality"""
        # Initialize database
        await init_database(
            postgres_url=os.getenv("POSTGRES_URL", "postgresql+asyncpg://ile_user:ile_password@localhost/ile_database"),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "ile_password"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
        
        kg = get_knowledge_graph()
        
        # Test 1: Store knowledge
        knowledge1 = KnowledgeItem(
            domain=DomainType.INTERNET,
            source="https://example.com/ai-research",
            fact="Large language models demonstrate emergent abilities at scale",
            entities=["LLM", "emergent_abilities", "scale"],
            credibility_score=0.9,
            source_type="academic"
        )
        
        node_id1 = await kg.store_knowledge(knowledge1)
        print(f"\n✅ Stored knowledge: {node_id1}")
        
        # Test 2: Store related knowledge
        knowledge2 = KnowledgeItem(
            domain=DomainType.TASK_BASED,
            source="BUE learning outcome",
            fact="LLM accuracy improves with domain-specific fine-tuning",
            entities=["LLM", "fine-tuning", "accuracy"],
            credibility_score=0.85,
            source_type="experimental"
        )
        
        node_id2 = await kg.store_knowledge(knowledge2)
        print(f"✅ Stored related knowledge: {node_id2}")
        
        # Test 3: Query related knowledge
        related = await kg.query_related_knowledge(node_id1)
        print(f"\n✅ Found {len(related)} related knowledge items")
        
        # Test 4: Search knowledge
        results = await kg.search_knowledge("LLM")
        print(f"✅ Search found {len(results)} results")
        
        # Test 5: Get statistics
        stats = await kg.get_statistics()
        print(f"\n✅ Graph statistics:")
        print(f"   Total nodes: {stats.get('total_nodes', 0)}")
        print(f"   Total relationships: {stats.get('total_relationships', 0)}")
        
        print("\n✅ Knowledge graph tests completed!")
    
    asyncio.run(test())

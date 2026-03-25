"""
UDOA Agent - Universal Data Orchestration API

AI Agent for multi-source data integration, schema mapping, and entity resolution.
Coordinates access to Aetherion internal data, external APIs, and customer systems.

Author: Aetherion Architecture Team
Date: November 22, 2025
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ..base.constitutional_agent import ConstitutionalAgent


class UDOAAgent(ConstitutionalAgent):
    """
    UDOA Agent handles universal data orchestration
    
    Capabilities:
    - Multi-source data discovery
    - Schema mapping and transformation
    - Entity resolution across systems
    - Query routing and optimization
    - Data sovereignty compliance
    """
    
    def __init__(self, **kwargs):
        """Initialize UDOA Agent"""
        super().__init__(agent_name="UDOA", **kwargs)
        
        # Data source configurations (would come from config in production)
        self.data_sources = {
            "aetherion_internal": {
                "type": "postgresql",
                "tables": ["contracts", "policies", "audit_logs", "metrics"],
                "jurisdiction": "US"
            },
            "fred_api": {
                "type": "rest_api",
                "endpoint": "https://api.stlouisfed.org/fred/series",
                "capabilities": ["economic_data", "time_series"],
                "jurisdiction": "US"
            },
            "world_bank": {
                "type": "rest_api",
                "endpoint": "https://api.worldbank.org/v2",
                "capabilities": ["development_indicators", "global_data"],
                "jurisdiction": "International"
            },
            "yahoo_finance": {
                "type": "rest_api",
                "endpoint": "https://query1.finance.yahoo.com/v8/finance",
                "capabilities": ["market_data", "stock_quotes"],
                "jurisdiction": "US"
            }
        }
        
        # Common schema transformations learned over time
        self.learned_transformations = {
            "date_formats": ["iso8601", "unix_timestamp", "mm/dd/yyyy"],
            "currency_conversions": ["USD", "EUR", "GBP", "JPY"],
            "address_normalizations": ["us_standard", "international"]
        }
        
        self.logger.info(f"UDOA Agent initialized with {len(self.data_sources)} data sources")
    
    def get_system_prompt(self) -> str:
        """Get UDOA-specific system prompt"""
        return """You are UDOA, Aetherion's Universal Data Orchestration Agent.

Your role is to coordinate data access across multiple sources:
- Aetherion internal databases (contracts, policies, metrics)
- Public APIs (FRED, World Bank, Yahoo Finance)
- External integrations (customer systems when configured)

When orchestrating data:
1. Analyze query to determine required data sources
2. Check data sovereignty and jurisdiction compliance
3. Map schemas between different data formats
4. Resolve entities across multiple systems
5. Coordinate cross-platform queries
6. Return unified data view

Core capabilities:
- Schema mapping (handle different date formats, currencies, etc.)
- Entity resolution (match "Apple Inc" with "AAPL" with "Apple Computer")
- Query optimization (parallel queries, caching)
- Jurisdiction routing (GDPR, data sovereignty)

Always consider:
1. Data quality and freshness
2. Query performance and cost
3. Privacy and compliance requirements
4. Entity disambiguation
5. Schema transformation needs

Provide:
1. Data discovery plan (which sources to query)
2. Schema mapping strategy
3. Entity resolution approach
4. Unified result set
5. Data quality confidence score

Be precise about data provenance and quality."""
    
    async def process_query(self, query: str, context: Dict[str, Any]) -> Any:
        """
        Process UDOA data orchestration query
        
        Args:
            query: Data query request
            context: Query context (jurisdiction, requirements, etc.)
            
        Returns:
            Unified data response
        """
        try:
            # Analyze query to determine data sources
            sources_needed = await self._analyze_query(query, context)
            
            # Check jurisdiction compliance
            jurisdiction_ok = await self._check_jurisdiction(sources_needed, context)
            
            if not jurisdiction_ok:
                return {
                    "error": "Jurisdiction compliance violation",
                    "details": "Query involves data sources not permitted for this jurisdiction"
                }
            
            # Plan query execution
            execution_plan = await self._create_execution_plan(query, sources_needed)
            
            # Execute queries (simulated for now)
            raw_data = await self._execute_queries(execution_plan)
            
            # Spawn child agents for complex tasks
            if len(sources_needed) > 2:
                # Schema mapping child agent
                schema_mapping = await self.spawn_child_agent(
                    child_type="schema_mapper",
                    task=f"Map schemas from {len(sources_needed)} data sources into unified format",
                    context={"sources": sources_needed, "data": raw_data}
                )
            
            if context.get("entity_resolution_required", False):
                # Entity resolution child agent
                entity_resolution = await self.spawn_child_agent(
                    child_type="entity_resolver",
                    task="Resolve entities across data sources",
                    context={"entities": raw_data}
                )
            
            # Synthesize unified response
            synthesis_prompt = self._build_synthesis_prompt(query, raw_data, execution_plan)
            synthesis, metadata = await self.reason(synthesis_prompt)
            
            # Structure result
            result = {
                "unified_data": synthesis,
                "sources_consulted": sources_needed,
                "execution_plan": execution_plan,
                "data_quality": self._assess_data_quality(raw_data),
                "metadata": metadata
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"UDOA query processing error: {str(e)}")
            raise
    
    async def _analyze_query(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Analyze query to determine required data sources
        
        Args:
            query: Data query
            context: Query context
            
        Returns:
            List of data source names
        """
        prompt = f"""Analyze this data query and determine which data sources are needed:

Query: {query}

Available data sources:
{json.dumps(self.data_sources, indent=2)}

Return JSON array of source names, e.g.: ["aetherion_internal", "fred_api"]

Consider:
- Economic data → fred_api, world_bank
- Market data → yahoo_finance
- Internal Aetherion data → aetherion_internal
- Global development data → world_bank

Respond with ONLY the JSON array."""
        
        response, _ = await self.reason(prompt, max_tokens=200)
        
        try:
            # Parse source list
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("\n", 1)[0]
            sources = json.loads(response)
            
            # Validate
            valid_sources = [s for s in sources if s in self.data_sources]
            
            self.logger.info(f"Determined data sources needed: {valid_sources}")
            return valid_sources
            
        except json.JSONDecodeError:
            # Fallback
            self.logger.warning("Failed to parse data sources, using fallback")
            return ["aetherion_internal"]
    
    async def _check_jurisdiction(
        self,
        sources: List[str],
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if data access complies with jurisdiction requirements
        
        Args:
            sources: Data sources to access
            context: Query context with jurisdiction info
            
        Returns:
            True if compliant, False otherwise
        """
        required_jurisdiction = context.get("jurisdiction", "US")
        
        for source in sources:
            source_jurisdiction = self.data_sources[source].get("jurisdiction", "US")
            
            # Simple compliance check (would be more complex in production)
            if required_jurisdiction == "EU" and source_jurisdiction not in ["EU", "International"]:
                self.logger.warning(
                    f"Jurisdiction violation: {source} not allowed for {required_jurisdiction}"
                )
                return False
        
        return True
    
    async def _create_execution_plan(
        self,
        query: str,
        sources: List[str]
    ) -> Dict[str, Any]:
        """
        Create optimized execution plan for multi-source query
        
        Args:
            query: Data query
            sources: Data sources to query
            
        Returns:
            Execution plan
        """
        # Determine if sources can be queried in parallel
        parallel_ok = all(
            self.data_sources[s]["type"] == "rest_api"
            for s in sources
        )
        
        return {
            "strategy": "parallel" if parallel_ok else "sequential",
            "sources": sources,
            "estimated_duration_ms": len(sources) * 100 if parallel_ok else len(sources) * 300
        }
    
    async def _execute_queries(
        self,
        execution_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute queries according to plan
        
        Args:
            execution_plan: Execution plan
            
        Returns:
            Raw data from sources
        """
        # In production, would make actual API calls
        # For now, simulate responses
        
        raw_data = {}
        
        for source in execution_plan["sources"]:
            if source == "aetherion_internal":
                raw_data[source] = {
                    "contracts": [
                        {"id": "C001", "name": "Sample Contract", "value": 100000}
                    ],
                    "row_count": 1
                }
            elif source == "fred_api":
                raw_data[source] = {
                    "series": "GDP",
                    "observations": [
                        {"date": "2024-Q1", "value": 25000}
                    ]
                }
            elif source == "yahoo_finance":
                raw_data[source] = {
                    "symbol": "AAPL",
                    "price": 175.50,
                    "volume": 50000000
                }
        
        self.logger.info(f"Executed queries for {len(raw_data)} sources")
        
        return raw_data
    
    def _build_synthesis_prompt(
        self,
        query: str,
        raw_data: Dict[str, Any],
        execution_plan: Dict[str, Any]
    ) -> str:
        """Build synthesis prompt for unified data response"""
        
        return f"""Synthesize data from multiple sources into unified response:

USER QUERY:
{query}

RAW DATA FROM SOURCES:
{json.dumps(raw_data, indent=2)}

TASK:
1. Transform data into unified format
2. Resolve any schema differences
3. Identify entity relationships
4. Present as coherent answer to user query

Provide:
- Direct answer to query using the data
- Data quality assessment
- Any ambiguities or missing data
- Confidence in the synthesis

Format response as JSON:
{{
    "answer": "<direct answer to query>",
    "supporting_data": {{...}},
    "data_quality": {{
        "completeness": <0-1>,
        "freshness": "<recent|moderate|stale>",
        "reliability": <0-1>
    }},
    "confidence": <0-1>,
    "notes": "<any caveats or limitations>"
}}

Provide ONLY the JSON response."""
    
    def _assess_data_quality(self, raw_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Assess quality of retrieved data
        
        Args:
            raw_data: Raw data from sources
            
        Returns:
            Quality metrics
        """
        # Simple quality assessment (would be more sophisticated in production)
        return {
            "completeness": 0.9,  # % of expected fields present
            "freshness": 0.95,     # How recent the data is
            "reliability": 0.88,   # Source reliability score
            "overall": 0.91
        }
    
    async def discover_data(
        self,
        query: str,
        jurisdiction: str = "US"
    ) -> Dict[str, Any]:
        """
        High-level API for data discovery
        
        Args:
            query: Data query
            jurisdiction: Jurisdiction for compliance
            
        Returns:
            Unified data response
        """
        context = {
            "jurisdiction": jurisdiction,
            "entity_resolution_required": True
        }
        
        decision = await self.make_decision(query, context)
        
        return {
            "data": decision.result,
            "confidence": decision.confidence,
            "governance_approved": decision.governance_score.get("tier") in ["tier_1", "tier_2"],
            "decision_id": decision.decision_id
        }

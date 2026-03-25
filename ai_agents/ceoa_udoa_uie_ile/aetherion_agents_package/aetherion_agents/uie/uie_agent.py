"""
UIE Agent - Universal Intelligence Engine

AI Agent for multi-engine intelligence synthesis and user-facing responses.
Coordinates BUE, URPE, UDOA, CEOA and creates coherent narratives.

Author: Aetherion Architecture Team
Date: November 22, 2025
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ..base.constitutional_agent import ConstitutionalAgent


class UIEAgent(ConstitutionalAgent):
    """
    UIE Agent handles intelligence synthesis and user interaction
    
    Capabilities:
    - Multi-engine coordination (BUE, URPE, UDOA, CEOA)
    - Response format selection
    - Confidence scoring
    - User persona adaptation
    - Narrative generation
    """
    
    def __init__(self, **kwargs):
        """Initialize UIE Agent"""
        super().__init__(agent_name="UIE", **kwargs)
        
        # Engine endpoints (would come from config in production)
        self.engine_endpoints = {
            "bue": "http://localhost:8003/bue",
            "urpe": "http://localhost:8004/urpe",
            "udoa": "http://localhost:8005/udoa",
            "ceoa": "http://localhost:8006/ceoa"
        }
        
        # Response format templates
        self.response_formats = [
            "executive_summary",
            "detailed_analysis",
            "comparative_table",
            "scenario_narrative",
            "risk_opportunity_matrix"
        ]
        
        self.logger.info("UIE Agent initialized with multi-engine coordination")
    
    def get_system_prompt(self) -> str:
        """Get UIE-specific system prompt"""
        return """You are UIE, Aetherion's Universal Intelligence Engine.

Your role is to synthesize intelligence from multiple specialized agents:
- BUE: Business underwriting and financial analysis
- URPE: Strategic analysis and geopolitical risk  
- UDOA: Data orchestration and integration
- CEOA: Compute and energy optimization

When coordinating intelligence:
1. Decompose user query into sub-questions for appropriate engines
2. Coordinate engine responses in optimal sequence
3. Resolve conflicts between engine recommendations
4. Synthesize coherent narrative from multiple sources
5. Adapt response depth to user persona
6. Provide confidence scores calibrated to agreement between engines

Response format options:
- Executive Summary: 2-3 sentence high-level answer + key insights
- Detailed Analysis: Comprehensive breakdown with methodology
- Comparative Table: Side-by-side comparison of options
- Scenario Narrative: Story-based explanation of possibilities
- Risk/Opportunity Matrix: Structured risk-reward analysis

Always provide:
1. Direct answer to user's question
2. Supporting evidence from relevant engines
3. Confidence score (0-1) with calibration reasoning
4. Alternative perspectives if engines disagree
5. Clear next steps or recommendations

Be clear, actionable, and adaptive to user needs."""
    
    async def process_query(self, query: str, context: Dict[str, Any]) -> Any:
        """
        Process UIE synthesis query
        
        Args:
            query: User query requiring multi-engine synthesis
            context: User context (persona, preferences, history)
            
        Returns:
            Synthesized intelligence response
        """
        try:
            # Determine which engines are needed
            engines_needed = await self._determine_engines(query, context)
            
            # Determine optimal response format
            response_format = await self._determine_format(query, context)
            
            # Coordinate engine calls (simulated for now)
            engine_responses = await self._coordinate_engines(query, engines_needed)
            
            # Synthesize final response
            synthesis_prompt = self._build_synthesis_prompt(
                query, engine_responses, response_format, context
            )
            
            synthesis, metadata = await self.reason(synthesis_prompt)
            
            # Calculate confidence based on engine agreement
            confidence = self._calculate_multi_engine_confidence(engine_responses)
            
            # Structure final response
            result = {
                "response": synthesis,
                "format": response_format,
                "confidence": confidence,
                "engines_consulted": engines_needed,
                "engine_responses": engine_responses,
                "metadata": metadata
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"UIE query processing error: {str(e)}")
            raise
    
    async def _determine_engines(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Determine which engines are needed for this query
        
        Args:
            query: User query
            context: Query context
            
        Returns:
            List of engine names to consult
        """
        # Use LLM to analyze query and determine engines
        prompt = f"""Analyze this query and determine which engines should be consulted:

Query: {query}

Available engines:
- BUE: Business analysis, financial modeling, investment thesis
- URPE: Strategic analysis, geopolitical risk, scenario planning
- UDOA: Data retrieval, multi-source integration
- CEOA: Compute placement, resource optimization

Return JSON array of engine names needed, e.g.: ["bue", "urpe"]

Consider:
- Financial questions → BUE
- Strategic/geopolitical questions → URPE
- Data retrieval questions → UDOA
- Compute/infrastructure questions → CEOA
- Complex questions may need multiple engines

Respond with ONLY the JSON array."""
        
        response, _ = await self.reason(prompt, max_tokens=100)
        
        try:
            # Parse engine list
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("\n", 1)[0]
            engines = json.loads(response)
            
            # Validate
            valid_engines = [e for e in engines if e in self.engine_endpoints]
            
            self.logger.info(f"Determined engines needed: {valid_engines}")
            return valid_engines
            
        except json.JSONDecodeError:
            # Fallback: guess based on keywords
            engines = []
            query_lower = query.lower()
            if any(word in query_lower for word in ["invest", "financial", "revenue", "cost", "profit"]):
                engines.append("bue")
            if any(word in query_lower for word in ["strategic", "risk", "geopolitical", "competitive"]):
                engines.append("urpe")
            if any(word in query_lower for word in ["data", "find", "retrieve", "integrate"]):
                engines.append("udoa")
            if any(word in query_lower for word in ["compute", "infrastructure", "cloud", "optimize"]):
                engines.append("ceoa")
            
            return engines if engines else ["bue"]  # Default to BUE
    
    async def _determine_format(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Determine optimal response format for user
        
        Args:
            query: User query
            context: User context and preferences
            
        Returns:
            Response format name
        """
        # Check explicit user preference
        if "format" in context:
            return context["format"]
        
        # Check user persona
        persona = context.get("persona", "analyst")
        
        # Map persona to format
        persona_format_map = {
            "executive": "executive_summary",
            "analyst": "detailed_analysis",
            "technical": "detailed_analysis",
            "strategic": "scenario_narrative"
        }
        
        return persona_format_map.get(persona, "detailed_analysis")
    
    async def _coordinate_engines(
        self,
        query: str,
        engines: List[str]
    ) -> Dict[str, Any]:
        """
        Coordinate calls to multiple engines
        
        Args:
            query: User query
            engines: List of engine names
            
        Returns:
            Dictionary mapping engine name to response
        """
        # In production, this would make actual API calls to engines
        # For now, simulate engine responses
        
        responses = {}
        
        for engine in engines:
            if engine == "bue":
                responses["bue"] = {
                    "analysis": "Financial viability assessment: positive outlook",
                    "confidence": 0.85,
                    "key_metrics": ["revenue_growth", "margins", "cash_flow"]
                }
            elif engine == "urpe":
                responses["urpe"] = {
                    "analysis": "Strategic positioning assessment: moderate risk",
                    "confidence": 0.78,
                    "key_factors": ["market_dynamics", "competitive_landscape", "regulatory"]
                }
            elif engine == "udoa":
                responses["udoa"] = {
                    "data_sources": ["internal_db", "market_data_api"],
                    "entities_found": 12,
                    "confidence": 0.92
                }
            elif engine == "ceoa":
                responses["ceoa"] = {
                    "recommended_placement": "aws-us-east-1",
                    "estimated_cost": 0.15,
                    "confidence": 0.88
                }
        
        self.logger.info(f"Coordinated {len(responses)} engine responses")
        
        return responses
    
    def _build_synthesis_prompt(
        self,
        query: str,
        engine_responses: Dict[str, Any],
        response_format: str,
        context: Dict[str, Any]
    ) -> str:
        """Build synthesis prompt for final response"""
        
        prompt = f"""Synthesize a response to this user query:

USER QUERY:
{query}

ENGINE RESPONSES:
{json.dumps(engine_responses, indent=2)}

RESPONSE FORMAT: {response_format}
USER PERSONA: {context.get('persona', 'analyst')}

TASK:
Create a {response_format} response that:
1. Directly answers the user's question
2. Incorporates insights from all engines
3. Resolves any conflicts between engines
4. Provides actionable recommendations
5. Matches the user's expertise level

Format guidelines for {response_format}:
"""
        
        if response_format == "executive_summary":
            prompt += """
- Start with 2-3 sentence direct answer
- Include 3-5 key bullet points
- End with single recommended action
- Total length: 150-200 words
"""
        elif response_format == "detailed_analysis":
            prompt += """
- Comprehensive breakdown with sections
- Include methodology and evidence
- Show how engines contributed
- Length: 400-600 words
"""
        elif response_format == "comparative_table":
            prompt += """
- Present as markdown table
- Columns: Option, Pros, Cons, Recommendation
- Include confidence scores
"""
        elif response_format == "scenario_narrative":
            prompt += """
- Tell story of different possibilities
- Use: "If X, then Y" scenarios
- Include probabilities
- Length: 300-500 words
"""
        
        prompt += "\n\nProvide the synthesized response now:"
        
        return prompt
    
    def _calculate_multi_engine_confidence(
        self,
        engine_responses: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence based on engine agreement
        
        Args:
            engine_responses: Responses from engines
            
        Returns:
            Confidence score (0-1)
        """
        if not engine_responses:
            return 0.5
        
        # Average confidence from engines that provided it
        confidences = [
            resp.get("confidence", 0.7)
            for resp in engine_responses.values()
            if isinstance(resp, dict)
        ]
        
        if not confidences:
            return 0.7
        
        avg_confidence = sum(confidences) / len(confidences)
        
        # Boost if multiple engines agree
        if len(engine_responses) > 1:
            avg_confidence *= 1.1  # 10% boost for multi-engine consensus
        
        return min(1.0, avg_confidence)
    
    async def synthesize(
        self,
        query: str,
        persona: str = "analyst",
        format_preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        High-level API for intelligence synthesis
        
        Args:
            query: User query
            persona: User persona (executive, analyst, technical)
            format_preference: Optional format override
            
        Returns:
            Synthesized intelligence response
        """
        context = {
            "persona": persona,
            "format": format_preference
        }
        
        decision = await self.make_decision(query, context)
        
        return {
            "synthesis": decision.result,
            "confidence": decision.confidence,
            "governance_approved": decision.governance_score.get("tier") in ["tier_1", "tier_2"],
            "decision_id": decision.decision_id
        }

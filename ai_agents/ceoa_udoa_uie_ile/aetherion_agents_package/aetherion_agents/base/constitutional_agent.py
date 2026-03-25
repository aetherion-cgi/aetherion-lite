"""
Constitutional Agent Base Class

All Aetherion agents inherit from this base class, which provides:
- Constitutional Governance integration
- Child agent spawning capability
- ILE observation integration
- LLM reasoning interface
- Error handling and logging

Author: Aetherion Architecture Team
Date: November 22, 2025
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import anthropic
from anthropic import Anthropic


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AgentDecision:
    """Represents a decision made by an agent"""
    decision_id: str
    agent_name: str
    query: str
    reasoning: str
    result: Any
    confidence: float
    governance_score: Dict[str, float]
    timestamp: datetime
    child_agents_spawned: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "agent_name": self.agent_name,
            "query": self.query,
            "reasoning": self.reasoning,
            "result": self.result,
            "confidence": self.confidence,
            "governance_score": self.governance_score,
            "timestamp": self.timestamp.isoformat(),
            "child_agents_spawned": self.child_agents_spawned,
            "duration_ms": self.duration_ms
        }


@dataclass
class GovernanceResult:
    """Result from Constitutional Governance evaluation"""
    approved: bool
    benefit_score: float
    harm_score: float
    authorization_tier: str
    reasoning: str
    blind_spots: List[str] = field(default_factory=list)
    marginal_benefit: float = 0.0


class AgentStatus(Enum):
    """Agent operational status"""
    INITIALIZING = "initializing"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"


# ============================================================================
# Base Constitutional Agent
# ============================================================================

class ConstitutionalAgent(ABC):
    """
    Base class for all Aetherion AI agents
    
    Provides:
    - LLM integration (Anthropic Claude)
    - Constitutional Governance validation
    - Child agent spawning
    - ILE observation hooks
    - Standard error handling
    """
    
    def __init__(
        self,
        agent_name: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        governance_endpoint: Optional[str] = None,
        ile_endpoint: Optional[str] = None
    ):
        """
        Initialize Constitutional Agent
        
        Args:
            agent_name: Unique name for this agent
            model: Claude model to use
            max_tokens: Maximum tokens for LLM responses
            temperature: LLM temperature (0-1)
            governance_endpoint: URL for Constitutional Governance API
            ile_endpoint: URL for ILE observation API
        """
        self.agent_name = agent_name
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.governance_endpoint = governance_endpoint or "http://localhost:8002/governance"
        self.ile_endpoint = ile_endpoint or "http://localhost:8007/ile"
        
        # Initialize Anthropic client
        self.client = Anthropic()
        
        # Agent state
        self.status = AgentStatus.INITIALIZING
        self.decision_history: List[AgentDecision] = []
        self.child_agents: Dict[str, Any] = {}
        
        # Logging
        self.logger = logging.getLogger(f"aetherion.{agent_name}")
        self.logger.setLevel(logging.INFO)
        
        # Performance metrics
        self.total_decisions = 0
        self.total_duration_ms = 0.0
        self.governance_approvals = 0
        self.governance_rejections = 0
        
        self.logger.info(f"Initialized {agent_name} agent")
        self.status = AgentStatus.OPERATIONAL
    
    # ========================================================================
    # Abstract Methods (Must be implemented by subclasses)
    # ========================================================================
    
    @abstractmethod
    async def process_query(self, query: str, context: Dict[str, Any]) -> Any:
        """
        Process a query and return result
        
        Subclasses must implement this with their specific logic
        
        Args:
            query: The query to process
            context: Additional context for processing
            
        Returns:
            Result of query processing
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent
        
        Returns:
            System prompt string
        """
        pass
    
    # ========================================================================
    # LLM Reasoning
    # ========================================================================
    
    async def reason(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Use LLM to reason about a problem
        
        Args:
            prompt: The prompt to send to LLM
            system_prompt: Optional system prompt override
            max_tokens: Optional max tokens override
            
        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            start_time = time.time()
            
            # Use provided system prompt or default
            sys_prompt = system_prompt or self.get_system_prompt()
            tokens = max_tokens or self.max_tokens
            
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=tokens,
                temperature=self.temperature,
                system=sys_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract response
            response_text = message.content[0].text
            
            metadata = {
                "model": self.model,
                "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "duration_ms": duration_ms,
                "stop_reason": message.stop_reason
            }
            
            self.logger.debug(f"LLM reasoning completed in {duration_ms:.2f}ms")
            
            return response_text, metadata
            
        except Exception as e:
            self.logger.error(f"LLM reasoning error: {str(e)}")
            raise
    
    # ========================================================================
    # Constitutional Governance Integration
    # ========================================================================
    
    async def validate_with_governance(
        self,
        action: str,
        context: Dict[str, Any],
        proposed_result: Any
    ) -> GovernanceResult:
        """
        Validate action with Constitutional Governance
        
        Args:
            action: Description of action being taken
            context: Context for governance evaluation
            proposed_result: The result being proposed
            
        Returns:
            GovernanceResult with approval decision
        """
        try:
            # In production, this would call actual governance API
            # For now, simulate governance evaluation
            
            # Calculate benefit/harm scores (placeholder logic)
            benefit_score = 75.0  # Would come from actual OPA policy
            harm_score = 15.0
            
            # Determine authorization tier
            if benefit_score >= 70 and harm_score <= 30:
                tier = "tier_1"
                approved = True
            elif benefit_score >= 50 and harm_score <= 50:
                tier = "tier_2"
                approved = True
            else:
                tier = "tier_3"
                approved = False  # Would require human review
            
            # Identify blind spots (placeholder)
            blind_spots = []
            if "risk" not in str(context).lower():
                blind_spots.append("Risk assessment not explicitly considered")
            
            result = GovernanceResult(
                approved=approved,
                benefit_score=benefit_score,
                harm_score=harm_score,
                authorization_tier=tier,
                reasoning=f"Action evaluated at {tier}: benefit={benefit_score}, harm={harm_score}",
                blind_spots=blind_spots,
                marginal_benefit=benefit_score - harm_score
            )
            
            # Track metrics
            if approved:
                self.governance_approvals += 1
            else:
                self.governance_rejections += 1
            
            self.logger.info(
                f"Governance evaluation: approved={approved}, "
                f"benefit={benefit_score}, harm={harm_score}, tier={tier}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Governance validation error: {str(e)}")
            # Fail safe: reject on error
            return GovernanceResult(
                approved=False,
                benefit_score=0.0,
                harm_score=100.0,
                authorization_tier="tier_3",
                reasoning=f"Governance validation failed: {str(e)}"
            )
    
    # ========================================================================
    # Child Agent Management
    # ========================================================================
    
    async def spawn_child_agent(
        self,
        child_type: str,
        task: str,
        context: Dict[str, Any]
    ) -> Any:
        """
        Spawn a child agent to handle a specific task
        
        Args:
            child_type: Type of child agent to spawn
            task: Task for child agent
            context: Context for child agent
            
        Returns:
            Result from child agent
        """
        child_id = str(uuid.uuid4())[:8]
        child_name = f"{self.agent_name}_child_{child_type}_{child_id}"
        
        self.logger.info(f"Spawning child agent: {child_name}")
        
        try:
            # Child agents use simpler prompts focused on their specific task
            child_prompt = f"""
You are a specialized sub-agent tasked with: {task}

Context: {context}

Provide a focused analysis for this specific task. Be concise and actionable.
"""
            
            response, metadata = await self.reason(
                prompt=child_prompt,
                max_tokens=1000  # Child agents use fewer tokens
            )
            
            # Track child agent
            self.child_agents[child_id] = {
                "name": child_name,
                "type": child_type,
                "task": task,
                "result": response,
                "metadata": metadata
            }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Child agent spawn error: {str(e)}")
            return None
    
    # ========================================================================
    # ILE Observation Integration
    # ========================================================================
    
    async def report_to_ile(self, decision: AgentDecision) -> None:
        """
        Report decision to ILE for meta-learning
        
        Args:
            decision: The decision to report
        """
        try:
            # In production, this would call ILE API
            # For now, log the decision
            
            self.logger.info(
                f"ILE observation: {self.agent_name} decision {decision.decision_id} "
                f"(confidence={decision.confidence:.2f}, "
                f"duration={decision.duration_ms:.2f}ms)"
            )
            
            # Store in decision history
            self.decision_history.append(decision)
            
            # In production, would POST to ILE endpoint:
            # await self.ile_client.post(
            #     f"{self.ile_endpoint}/observe",
            #     json=decision.to_dict()
            # )
            
        except Exception as e:
            self.logger.error(f"ILE reporting error: {str(e)}")
            # Don't fail on ILE errors - observation is not critical path
    
    # ========================================================================
    # Main Decision Pipeline
    # ========================================================================
    
    async def make_decision(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> AgentDecision:
        """
        Main decision pipeline with governance and ILE integration
        
        Args:
            query: Query to process
            context: Context for processing
            
        Returns:
            AgentDecision with result and metadata
        """
        decision_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing query: {query[:100]}...")
            
            # 1. Process query (implemented by subclass)
            result = await self.process_query(query, context)
            
            # 2. Validate with Constitutional Governance
            governance_result = await self.validate_with_governance(
                action=f"Query processing: {query[:50]}",
                context=context,
                proposed_result=result
            )
            
            if not governance_result.approved:
                self.logger.warning(
                    f"Governance rejected decision: {governance_result.reasoning}"
                )
                # In production, would refine or reject
                # For now, continue with warning
            
            # 3. Calculate confidence
            confidence = self._calculate_confidence(result, governance_result)
            
            # 4. Create decision object
            duration_ms = (time.time() - start_time) * 1000
            
            decision = AgentDecision(
                decision_id=decision_id,
                agent_name=self.agent_name,
                query=query,
                reasoning=governance_result.reasoning,
                result=result,
                confidence=confidence,
                governance_score={
                    "benefit": governance_result.benefit_score,
                    "harm": governance_result.harm_score,
                    "tier": governance_result.authorization_tier
                },
                timestamp=datetime.now(),
                child_agents_spawned=list(self.child_agents.keys()),
                duration_ms=duration_ms
            )
            
            # 5. Report to ILE
            await self.report_to_ile(decision)
            
            # 6. Update metrics
            self.total_decisions += 1
            self.total_duration_ms += duration_ms
            
            self.logger.info(
                f"Decision complete: confidence={confidence:.2f}, "
                f"duration={duration_ms:.2f}ms"
            )
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Decision pipeline error: {str(e)}")
            self.status = AgentStatus.DEGRADED
            raise
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _calculate_confidence(
        self,
        result: Any,
        governance_result: GovernanceResult
    ) -> float:
        """
        Calculate confidence score for decision
        
        Args:
            result: The decision result
            governance_result: Governance evaluation
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence on governance scores
        confidence = (governance_result.benefit_score / 100.0)
        
        # Adjust for harm
        confidence *= (1.0 - governance_result.harm_score / 100.0)
        
        # Ensure in range [0, 1]
        return max(0.0, min(1.0, confidence))
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent performance metrics
        
        Returns:
            Dictionary of metrics
        """
        avg_duration = (
            self.total_duration_ms / self.total_decisions
            if self.total_decisions > 0 else 0
        )
        
        approval_rate = (
            self.governance_approvals / (self.governance_approvals + self.governance_rejections)
            if (self.governance_approvals + self.governance_rejections) > 0 else 0
        )
        
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "total_decisions": self.total_decisions,
            "avg_duration_ms": avg_duration,
            "governance_approval_rate": approval_rate,
            "child_agents_spawned": len(self.child_agents),
            "decision_history_size": len(self.decision_history)
        }

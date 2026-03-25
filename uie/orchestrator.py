"""
UIE Orchestrator - Main Intelligence Coordination
Absorbs Cortex Gateway's Planner, Executor, and Synthesizer
"""
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from api_models import (
    AetherionRequest,
    AetherionResponse,
    IntentClassification,
    ExecutionPlan,
    ExecutionStep,
    GovernanceDecision,
    CapabilityResult
)
from function_broker_client import get_broker_client
from config import config


logger = logging.getLogger(__name__)

# Broker-safe public capability IDs for the current local Aetherion stack.
BROKER_CAPABILITY_MAP = {
    "underwrite": "bue.underwrite",
    "simulate": "urpe.scenario",
    "analyze": "uie.query",
    "query": "uie.query",
    "compute": "ceoa.schedule",
}


class UIEOrchestrator:
    """
    Main orchestrator for Aetherion.
    
    Responsibilities (absorbed from Cortex Gateway):
    1. Parse intent from natural language (Planner)
    2. Create execution plans (Planner)
    3. Execute capabilities via Function Broker (Executor)
    4. Synthesize results into conversational responses (Synthesizer)
    5. Manage governance checks
    """
    
    def __init__(self):
        self.broker = get_broker_client()
        self.conversation_memory: Dict[str, List[Dict[str, Any]]] = {}

    def _resolve_capability(self, purpose: str) -> str:
        """Resolve a high-level purpose into the current broker-safe capability ID."""
        return BROKER_CAPABILITY_MAP.get(purpose, "uie.query")
    
    async def process_request(
        self,
        request: AetherionRequest,
        user_id: str
    ) -> AetherionResponse:
        """
        Main entry point for processing requests.
        Handles both natural language and structured requests.
        """
        start_time = datetime.utcnow()
        session_id = request.session_id or f"session-{uuid.uuid4()}"
        
        try:
            # Step 1: Parse intent
            logger.info(f"Processing request for user {user_id}, session {session_id}")
            intent = await self._parse_intent(request, user_id, session_id)
            
            # Check if clarification needed
            if intent.requires_clarification:
                return self._create_clarification_response(intent, session_id)
            
            # Step 2: Build governance context
            governance_context = self._build_governance_context(
                intent, user_id, request
            )
            
            # Step 3: Create execution plan
            plan = await self._create_execution_plan(intent, governance_context)
            
            # Step 4: Check governance authorization
            governance_decision = await self._check_governance(
                plan, governance_context
            )
            
            if not governance_decision.allowed:
                return self._create_governance_denial_response(
                    governance_decision, intent, session_id
                )
            
            # Step 5: Execute plan
            results = await self._execute_plan(plan, governance_context)
            
            # Step 6: Synthesize response
            response = await self._synthesize_response(
                request, intent, plan, results, session_id, user_id
            )
            
            # Add metadata
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            response.execution_time_ms = execution_time
            response.session_id = session_id
            response.intent = intent
            response.execution_plan = plan
            response.governance = governance_decision
            response.capabilities_used = [step.capability for step in plan.steps]
            
            # Store in conversation memory
            if config.enable_conversation_memory:
                self._update_conversation_memory(
                    session_id, request, response
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return AetherionResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                status="error",
                execution_time_ms=execution_time,
                session_id=session_id
            )
    
    async def _parse_intent(
        self,
        request: AetherionRequest,
        user_id: str,
        session_id: str
    ) -> IntentClassification:
        """
        Parse user request into structured intent.
        Handles both natural language and structured formats.
        """
        # If structured format (legacy), create intent directly
        if request.capability:
            purpose = request.capability.split('.')[0]
            normalized_capability = request.capability

            # If a legacy/high-level capability is passed in, normalize it to the broker-safe namespace.
            if request.capability in BROKER_CAPABILITY_MAP:
                normalized_capability = BROKER_CAPABILITY_MAP[request.capability]
            elif purpose in BROKER_CAPABILITY_MAP and request.capability.count('.') == 0:
                normalized_capability = self._resolve_capability(purpose)

            return IntentClassification(
                purpose=purpose,
                primary_capability=normalized_capability,
                parameters=request.params or {},
                confidence=1.0,
                requires_clarification=False
            )
        
        # Natural language - parse with LLM
        message = request.message
        conversation_history = self._get_conversation_history(session_id)
        
        # For now, simple rule-based intent classification
        # In production, use LLM for sophisticated intent parsing
        intent = self._simple_intent_classification(message, conversation_history)
        
        return intent
    
    def _simple_intent_classification(
        self,
        message: str,
        history: List[Dict[str, Any]]
    ) -> IntentClassification:
        """
        Simple rule-based intent classification.
        In production, replace with LLM-based parsing.
        """
        message_lower = message.lower()
        
        # Financial/underwriting keywords
        if any(word in message_lower for word in ["underwrite", "deal", "investment", "project finance"]):
            return IntentClassification(
                purpose="underwrite",
                primary_capability=self._resolve_capability("underwrite"),
                parameters={"message": message},
                confidence=0.85
            )
        
        # Scenario/simulation keywords
        elif any(word in message_lower for word in ["simulate", "scenario", "what if", "forecast", "predict"]):
            return IntentClassification(
                purpose="simulate",
                primary_capability=self._resolve_capability("simulate"),
                parameters={"scenario": message},
                confidence=0.80
            )
        
        # Analysis/query keywords
        elif any(word in message_lower for word in ["analyze", "impact", "effect", "consequence"]):
            return IntentClassification(
                purpose="analyze",
                primary_capability=self._resolve_capability("analyze"),
                parameters={"prompt": message},
                confidence=0.80
            )
        
        # Compute/scheduling
        elif any(word in message_lower for word in ["compute", "process", "schedule", "run"]):
            return IntentClassification(
                purpose="compute",
                primary_capability=self._resolve_capability("compute"),
                parameters={"job": message},
                confidence=0.75
            )
        
        # Default: general intelligence query
        else:
            return IntentClassification(
                purpose="query",
                primary_capability=self._resolve_capability("query"),
                parameters={"prompt": message},
                confidence=0.60
            )
    
    def _build_governance_context(
        self,
        intent: IntentClassification,
        user_id: str,
        request: AetherionRequest
    ) -> Dict[str, Any]:
        """Build governance context for authorization"""
        return {
            "actor": user_id,
            "purpose": intent.purpose,
            "intent_confidence": intent.confidence,
            "jurisdiction": request.jurisdiction or config.default_jurisdiction,
            "requested_capabilities": [intent.primary_capability],
            "complexity_score": 0.5,  # Calculate based on plan complexity
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _create_execution_plan(
        self,
        intent: IntentClassification,
        governance_context: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        Create execution plan from intent.
        For complex queries, may involve multiple steps.
        """
        # Simple case: single capability
        steps = [
            ExecutionStep(
                step_number=1,
                capability=intent.primary_capability,
                params=intent.parameters,
                is_critical=True,
                description=f"Execute {intent.purpose}"
            )
        ]
        
        return ExecutionPlan(
            steps=steps,
            estimated_duration_seconds=30.0,  # Estimate based on capability
            complexity_score=0.5
        )
    
    async def _check_governance(
        self,
        plan: ExecutionPlan,
        governance_context: Dict[str, Any]
    ) -> GovernanceDecision:
        """
        Check governance authorization via Function Broker.
        Function Broker consults OPA for the decision.
        """
        if not config.governance_enabled:
            return GovernanceDecision(
                allowed=True,
                tier="T1",
                explanation="Governance disabled"
            )
        
        # Check authorization for primary capability
        primary_step = plan.steps[0]
        
        decision = await self.broker.check_authorization(
            capability=primary_step.capability,
            params=primary_step.params,
            governance_context=governance_context
        )
        
        return decision
    
    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        governance_context: Dict[str, Any]
    ) -> List[CapabilityResult]:
        """Execute all steps in the plan"""
        results = []
        
        for step in plan.steps:
            logger.info(f"Executing step {step.step_number}: {step.capability}")
            
            result = await self.broker.invoke_capability(
                capability_id=step.capability,
                params=step.params,
                governance_context=governance_context
            )
            
            results.append(result)
            
            # If critical step failed, stop execution
            if step.is_critical and result.status == "error":
                logger.error(f"Critical step {step.step_number} failed, stopping execution")
                break
        
        return results
    
    async def _synthesize_response(
        self,
        request: AetherionRequest,
        intent: IntentClassification,
        plan: ExecutionPlan,
        results: List[CapabilityResult],
        session_id: str,
        user_id: str
    ) -> AetherionResponse:
        """
        Synthesize results into conversational response.
        This is where UIE's intelligence shines.
        """
        # Check if any results failed
        failed_results = [r for r in results if r.status == "error"]
        if failed_results:
            return AetherionResponse(
                message=f"I encountered an error: {failed_results[0].error}",
                status="error",
                execution_time_ms=0
            )
        
        # Get primary result
        primary_result = results[0]
        
        # Format response based on request format preference
        if request.response_format == "structured":
            return AetherionResponse(
                message="Request completed successfully.",
                data=primary_result.data,
                status="success",
                execution_time_ms=0
            )
        
        # Conversational format (default for CustomGPT/Claude)
        conversational_message = self._create_conversational_response(
            intent, primary_result, request.detail_level
        )
        
        # Generate follow-up suggestions
        follow_ups = self._generate_follow_up_suggestions(intent, primary_result)
        
        return AetherionResponse(
            message=conversational_message,
            data=primary_result.data if request.response_format == "both" else None,
            status="success",
            execution_time_ms=0,
            follow_up_suggestions=follow_ups
        )
    
    def _create_conversational_response(
        self,
        intent: IntentClassification,
        result: CapabilityResult,
        detail_level: str
    ) -> str:
        """Create human-friendly conversational response"""
        # In production, use LLM to synthesize
        # For now, simple formatting
        
        if not result.data:
            return "I've processed your request, but received no data from the backend systems."
        
        # Basic formatting based on capability type
        if intent.primary_capability in {"uie.query", "uie.plan"}:
            return f"Based on my analysis: {result.data.get('summary', result.data.get('synthesis', 'Analysis complete.'))}"
        
        elif intent.primary_capability == "bue.underwrite":
            return f"Underwriting analysis complete. {result.data.get('recommendation', 'See detailed results.')}"
        
        elif intent.primary_capability == "ceoa.schedule":
            return f"Compute orchestration request completed successfully. {result.data}"
        
        else:
            return f"Request completed successfully. {result.data}"
    
    def _generate_follow_up_suggestions(
        self,
        intent: IntentClassification,
        result: CapabilityResult
    ) -> List[str]:
        """Generate contextual follow-up suggestions"""
        # In production, use LLM to generate smart suggestions
        suggestions = [
            "Would you like more details on any specific aspect?",
            "Should I run additional scenarios?"
        ]
        return suggestions
    
    def _create_clarification_response(
        self,
        intent: IntentClassification,
        session_id: str
    ) -> AetherionResponse:
        """Create response asking for clarification"""
        questions = intent.clarification_questions or [
            "Could you provide more details about what you'd like me to do?"
        ]
        
        return AetherionResponse(
            message="I need some clarification:\n" + "\n".join(f"- {q}" for q in questions),
            status="success",
            execution_time_ms=0,
            session_id=session_id
        )
    
    def _create_governance_denial_response(
        self,
        decision: GovernanceDecision,
        intent: IntentClassification,
        session_id: str
    ) -> AetherionResponse:
        """Create response for governance denial"""
        if decision.tier == "T3":
            message = (
                f"I can't proceed with this request autonomously. "
                f"Reason: {decision.explanation}. "
                f"I've submitted it for human review. "
                f"Reference: {decision.review_id or 'N/A'}"
            )
        else:
            message = (
                f"I can't proceed with that request. "
                f"Reason: {decision.explanation}. "
                "If you believe this is an error, please contact support."
            )
        
        return AetherionResponse(
            message=message,
            status="requires_review" if decision.tier == "T3" else "error",
            governance=decision,
            execution_time_ms=0,
            session_id=session_id
        )
    
    def _get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        return self.conversation_memory.get(session_id, [])
    
    def _update_conversation_memory(
        self,
        session_id: str,
        request: AetherionRequest,
        response: AetherionResponse
    ):
        """Update conversation memory"""
        if session_id not in self.conversation_memory:
            self.conversation_memory[session_id] = []
        
        self.conversation_memory[session_id].append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": request.message or str(request.dict()),
            "assistant_message": response.message,
            "intent": request.dict() if request.message else None
        })
        
        # Trim to max history length
        if len(self.conversation_memory[session_id]) > config.max_conversation_history:
            self.conversation_memory[session_id] = self.conversation_memory[session_id][-config.max_conversation_history:]

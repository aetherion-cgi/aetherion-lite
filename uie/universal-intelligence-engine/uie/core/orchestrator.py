"""
Query Orchestration Engine

Executes capability plans as a DAG (Directed Acyclic Graph):
- Fan-out/fan-in for parallel execution
- Timeouts and retries with exponential backoff
- Calls Function Broker only (never engines directly)
- Handles clarification responses from broker-returned results
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import asyncio 
from datetime import datetime, timedelta
import uuid

from uie.core.schemas import (
    Envelope, NormalizedResult, ToolPlanStep, ToolCall,
    ClarificationRequest, Usage, create_normalized_result
)


class StepStatus(str, Enum):
    """Status of a tool plan step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of executing a tool plan step."""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retries: int = 0


@dataclass
class DAGNode:
    """A node in the execution DAG."""
    step: ToolPlanStep
    status: StepStatus = StepStatus.PENDING
    result: Optional[StepResult] = None
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)



class FunctionBrokerClient:
    """
    Client for communicating with the Function Broker.

    Lite UIE talks to the Function Broker only.
    """

    def __init__(self, broker_url: str = "http://127.0.0.1:8081"):
        self.broker_url = broker_url.rstrip("/")
        import httpx
        self.client = httpx.AsyncClient(timeout=30.0)

    async def invoke_capability(
        self,
        capability_id: str,
        payload: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.broker_url}/v1/invoke?capability_id={capability_id}"
        request_body = {
            "tenant_id": context.get("tenant_id", "public-dev"),
            "actor": context.get("actor", "uie"),
            "intent": {"task": capability_id.split(".")[-1]},
            "payload": payload,
        }
        response = await self.client.post(
            url,
            json=request_body,
            headers={"X-Service-ID": "uie"},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


class QueryOrchestrator:
    """
    Orchestrates query execution using a DAG approach.
    
    Takes an envelope, builds execution plan, runs tools via Cortex Gateway,
    and synthesizes results into NormalizedResult.
    """
    
    def __init__(
        self,
        broker_client: Optional[FunctionBrokerClient] = None,
        max_retries: int = 3,
        timeout_seconds: float = 30.0
    ):
        self.broker = broker_client or FunctionBrokerClient()
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
    
    async def execute(self, envelope: Envelope) -> NormalizedResult:
        """
        Execute a query from start to finish.
        
        Returns:
            NormalizedResult with status "completed", "clarify", or "error"
        """
        start_time = datetime.utcnow()

        # Normalize Lite payload shape so gateway input works consistently.
        if not getattr(envelope.payload, "text", None):
            if hasattr(envelope.payload, "input") and getattr(envelope.payload, "input", None):
                envelope.payload.text = envelope.payload.input
            elif getattr(envelope.payload, "json_data", None):
                envelope.payload.text = envelope.payload.json_data.get("input")

        # 1. Build execution plan if not provided
        if not envelope.tool_plan:
            envelope.tool_plan = await self._build_tool_plan(envelope)
        
        # 2. Build DAG from tool plan
        dag = self._build_dag(envelope.tool_plan)
        
        # 3. Execute DAG
        try:
            step_results = await self._execute_dag(
                dag,
                envelope,
                timeout_seconds=envelope.limits.timeout_seconds
            )
        except asyncio.TimeoutError:
            # Return partial results on timeout
            return self._create_partial_result(envelope, step_results, start_time)
        except Exception as e:
            # Return error result
            return self._create_error_result(envelope, str(e), start_time)
        
        # 4. Check if broker-returned results requested clarification
        clarification = self._check_for_clarification(step_results)
        if clarification:
            return self._create_clarification_result(
                envelope,
                clarification,
                step_results,
                start_time
            )
        
        # 5. Synthesize results
        final_result = self._synthesize_lite_result(envelope, step_results)

        # 6. Package as NormalizedResult
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return create_normalized_result(
            request_id=envelope.request_id,
            trace_id=envelope.trace.trace_id,
            status="completed",
            policy_digest="placeholder_digest",  # Will be filled by policy enforcer
            usage=Usage(
                input_tokens=self._count_input_tokens(envelope),
                output_tokens=self._count_output_tokens(final_result),
                total_tokens=0,  # Will be calculated
                tool_calls=len(step_results),
                duration_ms=duration_ms
            ),
            final_text=final_result.get("text"),
            structured=final_result.get("structured"),
            citations=final_result.get("citations", []),
            tool_calls=self._create_tool_call_records(step_results)
        )
    
    async def resume(self, envelope: Envelope) -> NormalizedResult:
        """
        Resume execution after clarification.
        
        Finds where execution left off and continues from there.
        """
        # Implementation would:
        # 1. Load execution state from where it left off
        # 2. Merge continuation_data into context
        # 3. Resume DAG execution from earliest unmet step
        # 4. Synthesize and return results
        
        # For now, just re-execute
        return await self.execute(envelope)
    
    async def _build_tool_plan(self, envelope: Envelope) -> List[ToolPlanStep]:
        """
        Build a tool execution plan using the 'plan' tool.

        This asks the Function Broker to plan the execution.
        """
        query_text = (
            getattr(envelope.payload, "text", None)
            or getattr(envelope.payload, "input", None)
            or (envelope.payload.json_data.get("input") if getattr(envelope.payload, "json_data", None) else None)
            or str(getattr(envelope.payload, "json_data", {}) or "")
        )

        lowered = query_text.lower()
        steps: List[ToolPlanStep] = []

        # Aetherion Lite uses deterministic capability planning instead of broker planning.
        if any(keyword in lowered for keyword in ["compute", "schedule", "optimize", "optimization", "workload", "resource"]):
            steps.append(ToolPlanStep(
                tool_name="ceoa.optimize",
                parameters={
                    "description": query_text,
                    "docker_image": "analysis:latest",
                    "requirements": {
                        "cpu_cores": 2,
                        "memory_gb": 4,
                        "gpu_required": False,
                        "estimated_duration_minutes": 30,
                    },
                },
                depends_on=[],
                step_id=str(uuid.uuid4())
            ))
        else:
            steps.append(ToolPlanStep(
                tool_name="bue.underwrite",
                parameters={
                    "project": query_text,
                    "capex": 0,
                    "expected_revenue": 0,
                    "asset_type": "cre",
                },
                depends_on=[],
                step_id=str(uuid.uuid4())
            ))

        return steps
    
    def _build_dag(self, tool_plan: List[ToolPlanStep]) -> Dict[str, DAGNode]:
        """
        Build DAG from tool plan.
        
        Returns:
            Dict of step_id -> DAGNode
        """
        dag = {}
        
        # Create nodes
        for step in tool_plan:
            node = DAGNode(
                step=step,
                dependencies=set(step.depends_on)
            )
            dag[step.step_id] = node
        
        # Build dependency relationships
        for step_id, node in dag.items():
            for dep_id in node.dependencies:
                if dep_id in dag:
                    dag[dep_id].dependents.add(step_id)
        
        return dag
    
    async def _execute_dag(
        self,
        dag: Dict[str, DAGNode],
        envelope: Envelope,
        timeout_seconds: float
    ) -> Dict[str, StepResult]:
        """
        Execute DAG with parallel execution where possible.
        
        Returns:
            Dict of step_id -> StepResult
        """
        results = {}
        
        async def execute_step(step_id: str) -> StepResult:
            """Execute a single step with retries."""
            node = dag[step_id]
            
            # Wait for dependencies
            for dep_id in node.dependencies:
                if dep_id in results and results[dep_id].status == StepStatus.FAILED:
                    # Dependency failed, skip this step
                    return StepResult(
                        step_id=step_id,
                        status=StepStatus.SKIPPED,
                        error=f"Dependency {dep_id} failed"
                    )
            
            # Execute with retries
            for attempt in range(self.max_retries):
                try:
                    start = datetime.utcnow()
                    
                    # Call Function Broker using the capability ID stored in the step.
                    result = await self.broker.invoke_capability(
                        capability_id=node.step.tool_name,
                        payload=node.step.parameters,
                        context={
                            "tenant_id": envelope.tenant_id,
                            "trace_id": envelope.trace.trace_id,
                            "request_id": envelope.request_id,
                            "actor": "uie",
                        }
                    )
                    
                    duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
                    
                    return StepResult(
                        step_id=step_id,
                        status=StepStatus.COMPLETED,
                        output=result,
                        duration_ms=duration_ms,
                        retries=attempt
                    )
                
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        # Final attempt failed
                        return StepResult(
                            step_id=step_id,
                            status=StepStatus.FAILED,
                            error=f"{type(e).__name__}: {str(e)}",
                            retries=attempt + 1
                        )

                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        # Execute DAG in topological order with parallelism
        pending = set(dag.keys())
        
        while pending:
            # Find steps ready to execute (all dependencies met)
            ready = [
                step_id for step_id in pending
                if all(dep_id in results for dep_id in dag[step_id].dependencies)
            ]
            
            if not ready:
                # Circular dependency or all remaining steps failed
                break
            
            # Execute ready steps in parallel
            tasks = [execute_step(step_id) for step_id in ready]
            step_results = await asyncio.gather(*tasks)
            
            # Store results
            for step_result in step_results:
                results[step_result.step_id] = step_result
                pending.remove(step_result.step_id)
        
        return results

    def _check_for_clarification(
        self,
        step_results: Dict[str, StepResult]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if any step returned a clarification request.

        Returns:
            Clarification data if found, None otherwise
        """
        for result in step_results.values():
            if result.output and isinstance(result.output, dict):
                if result.output.get("type") == "clarify":
                    return result.output
                if result.output.get("status") == "clarify":
                    return result.output
                if result.output.get("clarification"):
                    return result.output
        return None

    def _synthesize_lite_result(
        self,
        envelope: Envelope,
        step_results: Dict[str, StepResult]
    ) -> Dict[str, Any]:
        """Lite-friendly synthesis that does not depend on Domain Cortex or advanced synthesis modules."""
        completed = [result for result in step_results.values() if result.status == StepStatus.COMPLETED]
        failed = [result for result in step_results.values() if result.status == StepStatus.FAILED]

        text_parts: List[str] = []
        structured_data: Dict[str, Any] = {
            "completed_steps": [],
            "failed_steps": [],
            "raw_outputs": {},
        }

        for result in completed:
            output = result.output if isinstance(result.output, dict) else {"raw": str(result.output)}
            data = output.get("data") if isinstance(output, dict) else None
            details = output.get("details") if isinstance(output, dict) else None

            structured_data["completed_steps"].append(result.step_id)
            structured_data["raw_outputs"][result.step_id] = output

            summary = None
            if isinstance(data, dict):
                summary = data.get("summary") or data.get("message") or data.get("recommendation")
            if not summary and isinstance(details, dict):
                summary = details.get("summary")
            if not summary:
                summary = str(output)[:400]

            text_parts.append(f"[{result.step_id}] {summary}")

        for result in failed:
            structured_data["failed_steps"].append({
                "step_id": result.step_id,
                "error": result.error,
            })
            text_parts.append(f"[{result.step_id}] failed: {result.error}")

        if not text_parts:
            text_parts.append("Aetherion Lite completed the request, but no engine output was returned.")

        return {
            "text": "\n".join(text_parts),
            "structured": {
                "schema_name": "aetherion_lite_result",
                "data": structured_data,
                "validation_passed": True,
            },
            "citations": [],
        }

    def _count_input_tokens(self, envelope: Envelope) -> int:
        """Estimate input token count."""
        text = (
            getattr(envelope.payload, "text", None)
            or getattr(envelope.payload, "input", None)
            or ""
        )
        json_text = str(envelope.payload.json_data) if getattr(envelope.payload, "json_data", None) else ""
        return len(text + json_text) // 4

    def _count_output_tokens(self, result: Dict[str, Any]) -> int:
        """Estimate output token count."""
        text = result.get("text", "")
        return len(text) // 4

    def _create_tool_call_records(
        self,
        step_results: Dict[str, StepResult]
    ) -> List[ToolCall]:
        """Create tool call records for audit trail."""
        records = []

        for step_id, result in step_results.items():
            if result.status == StepStatus.COMPLETED:
                capability_id = step_id
                if isinstance(result.output, dict):
                    capability_id = (
                        result.output.get("traces", {}).get("capability_id")
                        or result.output.get("capability_id")
                        or step_id
                    )

                records.append(ToolCall(
                    tool_name=capability_id,
                    parameters={},
                    result_summary=str(result.output)[:200],
                    duration_ms=result.duration_ms,
                    success=True
                ))

        return records

    def _create_partial_result(
        self,
        envelope: Envelope,
        step_results: Dict[str, StepResult],
        start_time: datetime
    ) -> NormalizedResult:
        """Create partial result when timeout occurs."""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return create_normalized_result(
            request_id=envelope.request_id,
            trace_id=envelope.trace.trace_id,
            status="partial",
            policy_digest="placeholder_digest",
            usage=Usage(
                input_tokens=self._count_input_tokens(envelope),
                output_tokens=0,
                total_tokens=0,
                tool_calls=len(step_results),
                duration_ms=duration_ms
            ),
            final_text="Request timed out. Partial results available.",
            tool_calls=self._create_tool_call_records(step_results)
        )

    def _create_error_result(
        self,
        envelope: Envelope,
        error: str,
        start_time: datetime
    ) -> NormalizedResult:
        """Create error result."""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return create_normalized_result(
            request_id=envelope.request_id,
            trace_id=envelope.trace.trace_id,
            status="error",
            policy_digest="placeholder_digest",
            usage=Usage(
                input_tokens=self._count_input_tokens(envelope),
                output_tokens=0,
                total_tokens=0,
                tool_calls=0,
                duration_ms=duration_ms
            ),
            error_message=error,
            error_code="ORCHESTRATION_ERROR",
            final_text=f"Aetherion Lite orchestration error: {error}"
        )

    def _create_clarification_result(
        self,
        envelope: Envelope,
        clarification_data: Dict[str, Any],
        step_results: Dict[str, StepResult],
        start_time: datetime
    ) -> NormalizedResult:
        """Create clarification result."""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        clarification = ClarificationRequest(
            question=clarification_data["question"],
            fields_needed=clarification_data.get("fields_needed", []),
            thread_id=str(uuid.uuid4()),
            ttl_seconds=300
        )

        from uie.core.clarification import ClarificationManager
        clarification_mgr = ClarificationManager()
        asyncio.create_task(
            clarification_mgr.store_thread_state(
                clarification.thread_id,
                envelope,
                step_results
            )
        )

        return create_normalized_result(
            request_id=envelope.request_id,
            trace_id=envelope.trace.trace_id,
            status="clarify",
            policy_digest="placeholder_digest",
            usage=Usage(
                input_tokens=self._count_input_tokens(envelope),
                output_tokens=len(clarification.question) // 4,
                total_tokens=0,
                tool_calls=len(step_results),
                duration_ms=duration_ms
            ),
            clarification=clarification
        )

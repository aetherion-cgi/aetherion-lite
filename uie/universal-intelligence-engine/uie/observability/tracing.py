"""
Observability: Tracing and Metrics

OpenTelemetry-based tracing and Prometheus metrics.
"""

from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime
import time


class TracingManager:
    """
    OpenTelemetry tracing manager.
    
    Provides distributed tracing across UIE components.
    """
    
    def __init__(self):
        self.traces: Dict[str, Dict[str, Any]] = {}
    
    @contextmanager
    def span(self, name: str, trace_id: Optional[str] = None):
        """
        Context manager for creating a span.
        
        Usage:
            with tracing.span("operation_name") as span:
                # Do work
                span.set_attribute("key", "value")
        """
        span_id = str(time.time_ns())
        start_time = datetime.utcnow()
        
        span_data = {
            "name": name,
            "span_id": span_id,
            "trace_id": trace_id,
            "start_time": start_time,
            "attributes": {},
            "events": []
        }
        
        # Yield span context
        span_context = SpanContext(span_data)
        try:
            yield span_context
        finally:
            # End span
            span_data["end_time"] = datetime.utcnow()
            span_data["duration_ms"] = (
                span_data["end_time"] - start_time
            ).total_seconds() * 1000
            
            # Store trace
            if trace_id:
                if trace_id not in self.traces:
                    self.traces[trace_id] = {"spans": []}
                self.traces[trace_id]["spans"].append(span_data)


class SpanContext:
    """Context for a single span."""
    
    def __init__(self, span_data: Dict[str, Any]):
        self.span_data = span_data
    
    def set_attribute(self, key: str, value: Any):
        """Set an attribute on the span."""
        self.span_data["attributes"][key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span."""
        self.span_data["events"].append({
            "name": name,
            "timestamp": datetime.utcnow(),
            "attributes": attributes or {}
        })
    
    def record_exception(self, exception: Exception):
        """Record an exception in the span."""
        self.span_data["exception"] = {
            "type": type(exception).__name__,
            "message": str(exception),
            "timestamp": datetime.utcnow()
        }


class MetricsCollector:
    """
    Prometheus-compatible metrics collector.
    
    Tracks:
    - Request counts
    - Latencies
    - Token usage
    - Error rates
    """
    
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.histograms: Dict[str, list] = {}
        self.gauges: Dict[str, float] = {}
    
    def increment(self, metric_name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        key = self._make_key(metric_name, labels)
        self.counters[key] = self.counters.get(key, 0) + value
    
    def record_latency(self, metric_name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """Record a latency measurement."""
        key = self._make_key(metric_name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(duration_ms)
    
    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        key = self._make_key(metric_name, labels)
        self.gauges[key] = value
    
    def record_tokens(self, token_type: str, count: int, labels: Optional[Dict[str, str]] = None):
        """Record token usage."""
        metric_name = f"tokens_{token_type}"
        self.increment(metric_name, count, labels)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus format."""
        metrics = {
            "counters": self.counters,
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v),
                    "p50": self._percentile(v, 50),
                    "p95": self._percentile(v, 95),
                    "p99": self._percentile(v, 99)
                }
                for k, v in self.histograms.items()
            },
            "gauges": self.gauges
        }
        return metrics
    
    def _make_key(self, metric_name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create metric key with labels."""
        if not labels:
            return metric_name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{metric_name}{{{label_str}}}"
    
    def _percentile(self, values: list, p: int) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (p / 100))
        return sorted_values[min(index, len(sorted_values) - 1)]


class CircuitBreaker:
    """
    Circuit breaker for rate limiting and fault tolerance.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            # Check if timeout passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            
            # Success
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e


# Cost tracking
class CostTracker:
    """Track API costs across different models."""
    
    def __init__(self):
        self.costs: Dict[str, float] = {}
    
    def record_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_per_1m_input: float,
        cost_per_1m_output: float
    ):
        """Record cost for a model call."""
        input_cost = (input_tokens / 1_000_000) * cost_per_1m_input
        output_cost = (output_tokens / 1_000_000) * cost_per_1m_output
        total_cost = input_cost + output_cost
        
        self.costs[model_id] = self.costs.get(model_id, 0.0) + total_cost
    
    def get_total_cost(self) -> float:
        """Get total cost across all models."""
        return sum(self.costs.values())
    
    def get_costs_by_model(self) -> Dict[str, float]:
        """Get costs broken down by model."""
        return self.costs.copy()

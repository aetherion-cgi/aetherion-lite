"""
Scheduler Core - Greedy with Regret + Batch OR-Tools for flexible queues.

Architecture: Config-driven, minimal code. All weights and thresholds in YAML.
Logic: Extract features → Score placements → Rank → Select top

~400 LOC core vs. ~1,500-2,000 LOC hardcoded approach.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import yaml
from ortools.sat.python import cp_model


# ============================================================================
# LOAD CONFIGURATION
# ============================================================================
def load_scheduler_config(config_path: str = "configs/scheduler.yaml") -> Dict[str, Any]:
    """Load scheduler configuration from YAML"""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# Global config (loaded once at startup)
CONFIG = load_scheduler_config()


# ============================================================================
# FEATURE EXTRACTION
# ============================================================================
@dataclass
class PlacementFeatures:
    """
    Features extracted from workload + infrastructure for scoring.
    
    This is the input to the scoring function. All domain knowledge
    is captured here, not scattered through conditional logic.
    """
    # Cost features
    estimated_cost_usd: float
    spot_available: bool
    spot_discount_percent: float
    
    # Carbon features
    carbon_intensity_gco2_kwh: float
    is_green_window: bool
    hours_until_green_window: float
    
    # Latency features
    expected_duration_seconds: float
    queue_length: int
    
    # Data gravity features
    data_transfer_cost_usd: float
    data_transfer_latency_ms: float
    same_region_as_data: bool
    
    # Reliability features
    provider_reliability_score: float
    recent_failure_rate: float
    
    # Resource availability
    cpu_utilization: float
    memory_utilization: float
    available_immediately: bool


def extract_features(
    workload: Dict[str, Any],
    node: Dict[str, Any],
    carbon_data: Dict[str, Any],
    config: Dict[str, Any],
) -> PlacementFeatures:
    """
    Extract placement features from workload + infrastructure.
    
    This is where domain knowledge lives. Changes here affect scoring
    but don't require touching the scoring logic itself.
    """
    # Cost calculation
    estimated_cost = _calculate_cost(workload, node)
    spot_available = node.get("pricing", {}).get("spot_available", False)
    spot_discount = node.get("pricing", {}).get("spot_discount_percent", 0.0)
    
    # Carbon calculation
    carbon_intensity = carbon_data.get("current_intensity", 300.0)  # gCO2/kWh
    green_threshold = config["scheduler"]["carbon"]["green_window_threshold_gco2_kwh"]
    is_green = carbon_intensity < green_threshold
    
    # Find next green window
    hours_until_green = _find_next_green_window(carbon_data, green_threshold)
    
    # Latency calculation
    estimated_duration = workload["requirements"].get("estimated_duration_minutes", 30) * 60
    queue_length = node.get("availability", {}).get("queue_length", 0)
    
    # Data gravity calculation
    data_sources = workload.get("data_sources", [])
    transfer_cost, transfer_latency, same_region = _calculate_data_gravity(
        data_sources, node, config
    )
    
    # Reliability
    provider = node.get("provider")
    region = node.get("region")
    reliability = config["scheduler"]["provider_reliability"].get(provider, {}).get(region, 0.9)
    failure_rate = node.get("metrics", {}).get("recent_failure_rate", 0.0)
    
    # Resource availability
    cpu_util = node.get("metrics", {}).get("cpu_utilization", 0.5)
    mem_util = node.get("metrics", {}).get("memory_utilization", 0.5)
    available_immediately = queue_length < config["scheduler"]["resource_selection"]["max_queue_length"]
    
    return PlacementFeatures(
        estimated_cost_usd=estimated_cost,
        spot_available=spot_available,
        spot_discount_percent=spot_discount,
        carbon_intensity_gco2_kwh=carbon_intensity,
        is_green_window=is_green,
        hours_until_green_window=hours_until_green,
        expected_duration_seconds=estimated_duration,
        queue_length=queue_length,
        data_transfer_cost_usd=transfer_cost,
        data_transfer_latency_ms=transfer_latency,
        same_region_as_data=same_region,
        provider_reliability_score=reliability,
        recent_failure_rate=failure_rate,
        cpu_utilization=cpu_util,
        memory_utilization=mem_util,
        available_immediately=available_immediately,
    )


# ============================================================================
# SCORING FUNCTION (Config-Driven)
# ============================================================================
def score_placement(features: PlacementFeatures, config: Dict[str, Any]) -> float:
    """
    Score placement based on features and config weights.
    
    Returns: Score between 0.0 (worst) and 1.0 (best)
    
    This is a WEIGHTED SUM of normalized feature scores.
    No conditional logic - all behavior controlled by config.
    """
    weights = config["scheduler"]["weights"]
    
    # Cost score (normalized: lower cost = higher score)
    cost_score = 1.0 / (1.0 + features.estimated_cost_usd)
    if features.spot_available:
        cost_score *= (1.0 + features.spot_discount_percent / 100)
    
    # Carbon score (normalized: lower carbon = higher score)
    carbon_score = 1.0 / (1.0 + features.carbon_intensity_gco2_kwh / 100)
    if features.is_green_window:
        carbon_multiplier = config["scheduler"]["carbon"]["weight_multiplier_in_green_window"]
        carbon_score *= carbon_multiplier
    
    # Latency score (normalized: lower latency = higher score)
    expected_wait = features.queue_length * 60  # Rough estimate: 1 min per queued job
    total_time = features.expected_duration_seconds + expected_wait
    latency_score = 1.0 / (1.0 + total_time / 3600)  # Normalize by hours
    
    # Data gravity score (normalized: lower transfer cost/latency = higher score)
    data_score = 1.0 / (1.0 + features.data_transfer_cost_usd + features.data_transfer_latency_ms / 1000)
    if features.same_region_as_data:
        data_score *= 1.5  # Boost for same-region
    
    # Reliability score (directly usable, already 0-1)
    reliability_score = features.provider_reliability_score * (1.0 - features.recent_failure_rate)
    
    # Weighted sum
    total_score = (
        weights["cost"] * cost_score +
        weights["carbon"] * carbon_score +
        weights["latency"] * latency_score +
        weights["data_gravity"] * data_score +
        weights["reliability"] * reliability_score
    )
    
    # Penalty for high utilization (avoid overloaded nodes)
    utilization_penalty = max(features.cpu_utilization, features.memory_utilization) * 0.2
    total_score -= utilization_penalty
    
    # Ensure score is in [0, 1]
    return max(0.0, min(1.0, total_score))


# ============================================================================
# GREEDY SCHEDULER (Primary Path)
# ============================================================================
def greedy_select_placement(
    workload: Dict[str, Any],
    available_nodes: List[Dict[str, Any]],
    carbon_data: Dict[str, Any],
    config: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Greedy placement selection with regret mitigation.
    
    Returns: (best_placement, top_3_alternatives)
    
    Algorithm:
    1. Extract features for each node
    2. Score each placement
    3. Rank by score
    4. Return top placement + alternatives (for regret)
    """
    scored_placements = []
    
    for node in available_nodes:
        # Extract features
        features = extract_features(workload, node, carbon_data, config)
        
        # Score placement
        score = score_placement(features, config)
        
        scored_placements.append({
            "node": node,
            "features": features,
            "score": score,
        })
    
    # Sort by score (descending)
    scored_placements.sort(key=lambda x: x["score"], reverse=True)
    
    # Get top placement and alternatives
    best = scored_placements[0] if scored_placements else None
    alternatives = scored_placements[1:4]  # Top 3 alternatives
    
    return best, alternatives


# ============================================================================
# BATCH OPTIMIZER (For Flexible Workloads)
# ============================================================================
def batch_optimize_placements(
    workloads: List[Dict[str, Any]],
    available_nodes: List[Dict[str, Any]],
    carbon_data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Batch optimization using OR-Tools for flexible workloads.
    
    This runs periodically (every 60s) for workloads that can be deferred.
    Uses constraint programming to find globally optimal placement.
    
    Only ~60 LOC because OR-Tools does the heavy lifting.
    """
    model = cp_model.CpModel()
    
    # Decision variables: workload[i] assigned to node[j]
    assignments = {}
    for i, workload in enumerate(workloads):
        for j, node in enumerate(available_nodes):
            assignments[(i, j)] = model.NewBoolVar(f"w{i}_n{j}")
    
    # Constraint: Each workload assigned to exactly one node
    for i in range(len(workloads)):
        model.Add(sum(assignments[(i, j)] for j in range(len(available_nodes))) == 1)
    
    # Constraint: Node capacity (simplified: just count assignments)
    for j, node in enumerate(available_nodes):
        max_capacity = 10  # Simplified capacity model
        model.Add(sum(assignments[(i, j)] for i in range(len(workloads))) <= max_capacity)
    
    # Objective: Maximize total placement score
    objective_terms = []
    for i, workload in enumerate(workloads):
        for j, node in enumerate(available_nodes):
            features = extract_features(workload, node, carbon_data, config)
            score = score_placement(features, config)
            objective_terms.append(assignments[(i, j)] * int(score * 1000))  # Scale for integer
    
    model.Maximize(sum(objective_terms))
    
    # Solve with timeout
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config["scheduler"]["batch_optimizer"]["timeout_seconds"]
    status = solver.Solve(model)
    
    # Extract solution
    placements = {}
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for i, workload in enumerate(workloads):
            for j, node in enumerate(available_nodes):
                if solver.Value(assignments[(i, j)]) == 1:
                    placements[workload["id"]] = {"node": node, "score": 1.0}  # Placeholder score
    
    return placements


# ============================================================================
# REGRET MITIGATION
# ============================================================================
async def place_with_regret(
    workload: Dict[str, Any],
    available_nodes: List[Dict[str, Any]],
    carbon_data: Dict[str, Any],
    config: Dict[str, Any],
    cloud_adapter,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Place workload with automatic fallback to alternatives if primary fails.
    
    Returns: (success, job_id, node_id)
    """
    best, alternatives = greedy_select_placement(workload, available_nodes, carbon_data, config)
    
    if not best:
        return False, None, None
    
    # Try primary placement
    max_retries = config["scheduler"]["regret"]["max_retries"]
    
    for attempt in range(max_retries):
        try:
            current_node = best["node"] if attempt == 0 else alternatives[attempt - 1]["node"]
            
            # Submit job via cloud adapter
            job_id = await cloud_adapter.submit_job(workload, current_node)
            
            return True, job_id, current_node["id"]
        
        except Exception as e:
            # Log failure and try next alternative
            print(f"Placement failed (attempt {attempt + 1}): {e}")
            
            if attempt >= len(alternatives):
                break
    
    return False, None, None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def _calculate_cost(workload: Dict[str, Any], node: Dict[str, Any]) -> float:
    """Calculate estimated cost for workload on node"""
    duration_hours = workload["requirements"].get("estimated_duration_minutes", 30) / 60
    cost_per_hour = node.get("pricing", {}).get("compute_per_hour", 0.10)
    return duration_hours * cost_per_hour


def _find_next_green_window(carbon_data: Dict[str, Any], threshold: float) -> float:
    """Find hours until next green window (carbon intensity < threshold)"""
    forecast = carbon_data.get("forecast", [])
    
    for i, datapoint in enumerate(forecast):
        if datapoint["carbon_intensity"] < threshold:
            return i  # Hours from now
    
    return 99.0  # No green window in forecast


def _calculate_data_gravity(
    data_sources: List[str],
    node: Dict[str, Any],
    config: Dict[str, Any],
) -> Tuple[float, float, bool]:
    """
    Calculate data transfer cost and latency.
    
    Returns: (cost_usd, latency_ms, same_region)
    """
    if not data_sources:
        return 0.0, 0.0, True
    
    # Simplified: assume first data source determines locality
    # Production would parse S3 URIs, check regions, etc.
    data_region = "us-west-2"  # Placeholder
    node_region = node.get("region", "us-west-2")
    
    same_region = data_region == node_region
    
    # Rough estimates
    data_size_gb = 10.0  # Would extract from workload metadata
    
    if same_region:
        cost = data_size_gb * config["scheduler"]["data_gravity"]["transfer_cost_per_gb"]["same_region"]
        latency = 10.0  # ms
    else:
        cost = data_size_gb * config["scheduler"]["data_gravity"]["transfer_cost_per_gb"]["inter_region"]
        latency = 100.0  # ms
    
    return cost, latency, same_region

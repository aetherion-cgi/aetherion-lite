# OPA Policy Bundle for CEOA Governance
# Version: production_v1
#
# Strategy: All governance rules as declarative policies, not Python code.
# Changes to compliance rules = policy update, not code deployment.
# Hot-reload via OPA bundle server (S3/GCS).

package ceoa.governance

import future.keywords.if
import future.keywords.in

# ============================================================================
# SOVEREIGNTY & DATA RESIDENCY
# ============================================================================

# Data residency compliance - workloads must respect jurisdiction requirements
data_residency_compliant if {
    # Get workload's sovereignty requirements
    sovereignty_reqs := input.workload.preferences.sovereignty_requirements
    
    # Get proposed placement region
    placement_region := input.placement.region
    
    # Get placement country from region mapping
    placement_country := region_to_country[placement_region]
    
    # Check if placement country is in allowed list
    placement_country in sovereignty_reqs
}

# Default: if no sovereignty requirements, allow any region
data_residency_compliant if {
    not input.workload.preferences.sovereignty_requirements
}

# Region to country mapping
region_to_country := {
    "us-west-2": "US",
    "us-east-1": "US",
    "eu-west-1": "IE",
    "eu-central-1": "DE",
    "ap-northeast-1": "JP",
    "ap-southeast-1": "SG",
}

# Export control compliance - certain jurisdictions are restricted
export_controlled_regions := {
    "cn-north-1",      # China
    "cn-northwest-1",
    "me-south-1",      # Middle East (Bahrain)
    "ap-east-1",       # Hong Kong
}

export_control_compliant if {
    placement_region := input.placement.region
    not placement_region in export_controlled_regions
}

# ============================================================================
# BENEFIT / HARM SCORING
# ============================================================================

# Calculate benefit score (0-1) based on workload characteristics
benefit_score := score if {
    workload := input.workload
    
    # Factors that increase benefit
    carbon_benefit := carbon_reduction_benefit
    cost_benefit := cost_reduction_benefit
    social_benefit := social_impact_benefit
    
    # Weighted sum
    score := (carbon_benefit * 0.4) + (cost_benefit * 0.3) + (social_benefit * 0.3)
}

carbon_reduction_benefit := benefit if {
    # Higher benefit if workload uses carbon-aware scheduling
    carbon_aware := input.workload.preferences.carbon_aware
    carbon_weight := input.workload.preferences.carbon_weight
    
    benefit := 0.8 if carbon_aware else 0.3
}

cost_reduction_benefit := benefit if {
    # Benefit based on cost optimization
    cost_optimize := input.workload.preferences.cost_optimize
    spot_instance := input.placement.spot_instance
    
    # Higher benefit if using cost optimization features
    base := 0.7 if cost_optimize else 0.3
    spot_bonus := 0.2 if spot_instance else 0.0
    
    benefit := min([base + spot_bonus, 1.0])
}

social_impact_benefit := benefit if {
    # Benefit based on workload purpose (would be more sophisticated in production)
    # For now, default to moderate benefit
    benefit := 0.5
}

# Calculate harm score (0-1) based on workload characteristics
harm_score := score if {
    workload := input.workload
    
    # Factors that increase harm
    carbon_harm := carbon_emission_harm
    cost_harm := economic_harm
    security_harm := security_risk_harm
    
    # Max of harms (worst-case)
    score := max([carbon_harm, cost_harm, security_harm])
}

carbon_emission_harm := harm if {
    # Harm based on estimated carbon footprint
    estimated_carbon_kg := input.estimates.carbon_kg
    
    # Scoring: 0-10kg = low harm, 10-100kg = medium, 100+ = high
    harm := min([estimated_carbon_kg / 100, 1.0])
}

economic_harm := harm if {
    # Harm based on cost (excessive cost is harmful waste)
    estimated_cost_usd := input.estimates.cost_usd
    
    # Scoring: $0-10 = low, $10-100 = medium, $100+ = high
    harm := min([estimated_cost_usd / 100, 1.0])
}

security_risk_harm := harm if {
    # Harm based on security risks (simplified)
    # Would integrate with security scanning in production
    harm := 0.1  # Default low security risk
}

# ============================================================================
# AUTHORIZATION TIERS
# ============================================================================

# Determine authorization tier based on benefit/harm scores
authorization_tier := tier if {
    benefit := benefit_score
    harm := harm_score
    
    # Tier determination based on config thresholds
    tier := "routine" if {
        harm <= 0.2
        benefit >= 0.5
    }
}

authorization_tier := "elevated" if {
    benefit := benefit_score
    harm := harm_score
    
    harm <= 0.4
    harm > 0.2
    benefit >= 0.6
}

authorization_tier := "restricted" if {
    benefit := benefit_score
    harm := harm_score
    
    harm <= 0.6
    harm > 0.4
    benefit >= 0.7
}

authorization_tier := "prohibited" if {
    harm := harm_score
    harm > 0.6
}

# ============================================================================
# AUTHORIZATION DECISION
# ============================================================================

# Main authorization decision
authorized if {
    # Must pass all compliance checks
    data_residency_compliant
    export_control_compliant
    
    # Must meet tier requirements
    tier := authorization_tier
    tier != "prohibited"
    
    # Restricted tier requires human approval
    tier != "restricted"
}

# Allow restricted tier with human approval
authorized if {
    authorization_tier == "restricted"
    input.human_approval == true
}

# ============================================================================
# VIOLATIONS
# ============================================================================

# Collect all violations for audit trail
violations[violation] {
    not data_residency_compliant
    violation := {
        "policy": "data_residency",
        "severity": "critical",
        "message": "Placement violates data residency requirements",
    }
}

violations[violation] {
    not export_control_compliant
    violation := {
        "policy": "export_control",
        "severity": "critical",
        "message": "Placement violates export control regulations",
    }
}

violations[violation] {
    harm := harm_score
    harm > 0.6
    violation := {
        "policy": "harm_threshold",
        "severity": "critical",
        "message": sprintf("Harm score %.2f exceeds threshold 0.6", [harm]),
    }
}

violations[violation] {
    benefit := benefit_score
    benefit < 0.5
    authorization_tier == "routine"
    violation := {
        "policy": "benefit_threshold",
        "severity": "warning",
        "message": sprintf("Benefit score %.2f below routine threshold 0.5", [benefit]),
    }
}

# ============================================================================
# COMPLETE EVALUATION
# ============================================================================

# Complete governance evaluation result
evaluation := result if {
    result := {
        "authorized": authorized,
        "tier": authorization_tier,
        "benefit_score": benefit_score,
        "harm_score": harm_score,
        "sovereignty_compliant": data_residency_compliant,
        "violations": violations,
        "timestamp": time.now_ns(),
    }
}

# ============================================================================
# DEVICE MESH SPECIFIC POLICIES
# ============================================================================

# Device mesh workload eligibility
device_mesh_eligible if {
    workload := input.workload
    
    # Only certain workload types eligible for device mesh
    eligible_types := {
        "batch_processing",
        "data_transformation",
        "ml_inference",
    }
    
    workload.type in eligible_types
    
    # Must not require high security
    not workload.requires_high_security
    
    # Must not process sensitive data
    not workload.contains_pii
}

# ============================================================================
# COST CONTROLS
# ============================================================================

# Cost limits per tier
cost_limit_exceeded if {
    tier := authorization_tier
    estimated_cost := input.estimates.cost_usd
    
    limits := {
        "routine": 100,
        "elevated": 1000,
        "restricted": 10000,
    }
    
    limit := limits[tier]
    estimated_cost > limit
}

# Alert if cost limit exceeded
violations[violation] {
    cost_limit_exceeded
    violation := {
        "policy": "cost_limit",
        "severity": "warning",
        "message": sprintf("Estimated cost %.2f exceeds tier limit", [input.estimates.cost_usd]),
    }
}

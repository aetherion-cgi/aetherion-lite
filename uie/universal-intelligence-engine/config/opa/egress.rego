# OPA Egress Policy for UIE
# Enforces security rules before returning responses

package aetherion.uie.egress

import future.keywords.if
import future.keywords.in

# Default deny
default allow = false
default allow_with_masking = false

# Allow responses that meet requirements
allow if {
    meets_quality_requirements
    meets_safety_requirements
    meets_regional_requirements
    not has_violations
}

# Allow with additional masking if needed
allow_with_masking if {
    meets_quality_requirements
    meets_safety_requirements
    meets_regional_requirements
    input.policy.pii_masking == true
}

# Quality requirements
meets_quality_requirements if {
    input.result.status in ["completed", "clarify", "partial"]
}

meets_quality_requirements if {
    input.result.status == "completed"
    input.result.has_final_text == true
}

meets_quality_requirements if {
    input.result.status == "clarify"
}

# Safety requirements
meets_safety_requirements if {
    not has_critical_safety_flags
}

has_critical_safety_flags if {
    input.result.safety_flag_count > 0
    input.result.safety_severity == "critical"
}

# Regional requirements
meets_regional_requirements if {
    input.policy.region in ["US", "EU", "ROW"]
}

# Violations
has_violations if {
    violations[_]
}

violations[violation] if {
    input.result.status == "completed"
    input.result.has_final_text == false
    violation := {
        "type": "missing_content",
        "severity": "high",
        "message": "Completed responses must include final_text"
    }
}

violations[violation] if {
    input.policy.region == "EU"
    input.result.citation_count == 0
    input.result.has_final_text == true
    violation := {
        "type": "missing_citations",
        "severity": "medium",
        "message": "EU regulation requires citation of sources"
    }
}

violations[violation] if {
    input.result.safety_severity == "critical"
    violation := {
        "type": "safety_violation",
        "severity": "critical",
        "message": "Response contains critical safety issues"
    }
}

# Fields to mask on egress
mask_fields[field] if {
    input.policy.pii_masking == true
    field := "final_text"
}

mask_fields[field] if {
    input.policy.pii_masking == true
    input.result.has_structured == true
    field := "structured"
}

# Reasoning for decision
reasoning := msg if {
    allow
    msg := "Response authorized"
}

reasoning := msg if {
    allow_with_masking
    msg := "Response authorized with final redaction"
}

reasoning := msg if {
    not allow
    not allow_with_masking
    msg := sprintf("Response blocked: %v", [violations])
}

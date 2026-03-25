# OPA Ingress Policy for UIE
# Enforces security rules before processing requests

package aetherion.uie.ingress

import future.keywords.if
import future.keywords.in

# Default deny
default allow = false
default allow_with_masking = false

# Allow requests from authorized tenants
allow if {
    input.tenant_id
    is_authorized_tenant(input.tenant_id)
    meets_regional_requirements
    not has_policy_violations
}

# Allow with PII masking if required
allow_with_masking if {
    input.tenant_id
    is_authorized_tenant(input.tenant_id)
    meets_regional_requirements
    input.policy.pii_masking == true
    not has_critical_violations
}

# Check if tenant is authorized
is_authorized_tenant(tenant_id) if {
    # In production, check against tenant database
    tenant_id != ""
    tenant_id != "blocked_tenant"
}

# Regional requirements
meets_regional_requirements if {
    input.policy.region in ["US", "EU", "ROW"]
}

# Policy violations
has_policy_violations if {
    violations[_]
}

has_critical_violations if {
    count(violations) > 0
    some violation in violations
    violation.severity == "critical"
}

# Collect violations
violations[violation] if {
    input.intent.sensitivity == "restricted"
    not input.actor
    violation := {
        "type": "missing_actor",
        "severity": "critical",
        "message": "Restricted requests require actor identification"
    }
}

violations[violation] if {
    input.policy.region == "EU"
    input.policy.data_retention_days > 90
    violation := {
        "type": "gdpr_violation",
        "severity": "critical",
        "message": "GDPR requires data retention <= 90 days"
    }
}

violations[violation] if {
    input.policy.region == "US"
    input.intent.domains[_] == "healthcare"
    input.policy.pii_masking == false
    violation := {
        "type": "hipaa_violation",
        "severity": "critical",
        "message": "HIPAA requires PII masking for healthcare data"
    }
}

# Fields to mask if PII masking enabled
mask_fields[field] if {
    input.policy.pii_masking == true
    field := "payload.text"
}

mask_fields[field] if {
    input.policy.pii_masking == true
    input.payload.has_json == true
    field := "payload.json_data"
}

# Reasoning for decision
reasoning := msg if {
    allow
    msg := "Request authorized"
}

reasoning := msg if {
    allow_with_masking
    msg := "Request authorized with PII masking"
}

reasoning := msg if {
    not allow
    not allow_with_masking
    msg := sprintf("Request denied: %v", [violations])
}

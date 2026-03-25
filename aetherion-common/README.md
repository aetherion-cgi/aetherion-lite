# Aetherion Common

Shared data models and schemas for the Aetherion Collective General Intelligence platform.

## Overview

This package provides canonical request/response contracts used across the Aetherion integration fabric:
- **Function Broker**: Uses these schemas to communicate with internal engines
- **Cortex Gateway**: Uses these schemas for orchestration
- **Clair Interface**: Uses these schemas for user interactions
- **All Engines**: Adapt to these schemas via adapters

## Key Components

### Envelope
Universal request format carrying:
- Tenant and actor identification
- Intent (what the user wants to accomplish)
- Payload (specific data)
- Policy context
- Constitutional governance metadata
- Execution context (traces, session info)

### NormalizedResult
Universal response format providing:
- Primary result data
- Additional details and metadata
- Governance outcomes
- Execution traces
- Success/error status

### GovernanceMetadata
Constitutional governance information:
- Authorization tier (T1/T2/T3/halt)
- Jurisdiction (US/EU/ROW)
- PII masking preferences
- Escalation targets
- Benefit/harm scoring
- Audit tags

## Installation

```bash
pip install -e .
```

## Usage

```python
from aetherion_common import Envelope, NormalizedResult, GovernanceMetadata
from aetherion_common.enums import GovernanceTier, Region

# Create an envelope
envelope = Envelope(
    tenant_id="acme-corp",
    actor="user@example.com",
    intent={"task": "underwriting", "domains": ["finance"]},
    payload={"scenario": "commercial_loan"},
    governance=GovernanceMetadata(
        requested_tier=GovernanceTier.T2,
        region=Region.US
    )
)

# Create a result
result = NormalizedResult(
    data={"recommendation": "approve"},
    details={"confidence": 0.95},
    governance=envelope.governance
)
```

## Design Principles

1. **Constitutional Governance**: Every operation carries governance metadata ensuring human primacy
2. **No Internal Exposure**: Error messages never expose stack traces, source code, or policy details
3. **Immutable Audit Trail**: All operations generate audit records for transparency
4. **Multi-Tenancy**: Built-in tenant isolation at the schema level
5. **Observability**: Comprehensive tracing support for debugging and monitoring

## Security

This package enforces critical security boundaries:
- Sanitized error messages that never leak implementation details
- Governance metadata to prevent unauthorized operations
- Audit records for constitutional compliance
- No exposure of internal engine specifics

## Version

Current version: 1.0.0

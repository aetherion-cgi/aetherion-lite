## What Aetherion Lite is

Aetherion Lite is a local-first orchestration runtime built around:

- **UIE** — Universal Intelligence Engine (public entrypoint)
- **Function Broker** — internal routing layer
- **BUE** — underwriting / business analysis
- **CEOA** — compute and workload optimization
- **ILE** — internal learning layer

In Lite, users talk to the **UIE only**.

Users do **not** call the internal engines directly.

---

## Core architecture

```text
User / Terminal
   ↓
UIE
   ↓
Function Broker
   ↓
BUE / CEOA / ILE

Important rule

For normal usage:
	•	send requests to UIE
	•	do not send internal broker envelopes unless you are explicitly testing broker internals

⸻

Starting Aetherion Lite

From the repo root:

chmod +x ./install_lite.sh ./start_aetherion_lite.sh
./install_lite.sh
./start_aetherion_lite.sh

When startup succeeds, you should see the main services online, including:
	•	UIE on http://127.0.0.1:8000
	•	Function Broker on http://127.0.0.1:8081

⸻

Health checks

UIE

curl -s http://127.0.0.1:8000/health

Function Broker

curl -s http://127.0.0.1:8081/health


⸻

The main UIE endpoints

Aetherion Lite currently exposes two main public-friendly UIE endpoints for terminal usage:
	•	POST /v1/simple-submit
	•	POST /orchestrate

Both accept the same user-friendly request shape.

⸻

Public request structure

Minimum request body

{
  "input": "Analyze copper market conditions and provide a risk summary"
}

Request with session id

{
  "input": "Analyze copper market conditions and provide a risk summary",
  "session_id": "demo-session-1"
}

Field definitions

Field	Required	Type	Description
input	Yes	string	The user’s natural-language request
session_id	No	string	Optional session identifier for continuity


⸻

Recommended endpoint: /v1/simple-submit

This is the simplest public entrypoint for users.

Example

curl -X POST "http://127.0.0.1:8000/v1/simple-submit" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Analyze copper market conditions and provide a risk summary"
  }'

Example with session id

curl -X POST "http://127.0.0.1:8000/v1/simple-submit" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Run underwriting on a CRE deal with 15M capex and 2.2M revenue",
    "session_id": "cre-demo-1"
  }'


⸻

Alternate endpoint: /orchestrate

This is a thin wrapper endpoint that accepts the same request shape.

Example

curl -X POST "http://127.0.0.1:8000/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Provide a risk summary for copper market conditions",
    "session_id": "risk-demo-1"
  }'


⸻

What the UIE does internally

Users do not need to send the full internal envelope.

The UIE takes the public request:

{
  "input": "Analyze copper market conditions",
  "session_id": "demo-session-1"
}

and wraps it into a fuller internal request structure for orchestration.

Internal UIE-wrapped envelope example

{
  "tenant_id": "public-dev",
  "actor": "aetherion-lite-user",
  "intent": {
    "type": "freeform_request",
    "task": "general_query",
    "topic": "general",
    "urgency": "normal",
    "target_engine": "uie",
    "domains": []
  },
  "payload": {
    "input": "Analyze copper market conditions",
    "text": "Analyze copper market conditions",
    "json_data": {},
    "context": {
      "session_id": "demo-session-1",
      "source": "aetherion_lite_terminal"
    }
  },
  "context_refs": [],
  "trace_id": "generated-uuid"
}

This is handled by the UIE internally. End users normally do not need to send this manually.

⸻

How Lite decides what engine to use

Aetherion Lite currently uses a deterministic orchestration path.

If the input suggests compute / optimization work

It routes toward:
	•	ceoa.optimize

Keywords include terms like:
	•	compute
	•	schedule
	•	optimize
	•	optimization
	•	workload
	•	resource

Otherwise

It routes toward:
	•	bue.underwrite

That means most general business / finance / risk-style prompts in Lite currently flow through BUE.

⸻

Example prompts that work well

BUE-style prompts

Run underwriting on a CRE deal with 15M capex and 2.2M revenue

Analyze copper market conditions and provide a risk summary

Evaluate a business opportunity for a property acquisition

CEOA-style prompts

Optimize compute resources for a 30-minute analysis workload

Schedule a lightweight workload and choose an efficient resource plan

Provide compute optimization guidance for a small analytics task


⸻

Expected response style

Aetherion Lite returns a normalized response that may include:
	•	final_text
	•	structured
	•	tool_calls
	•	usage
	•	status

Typical behavior
	•	successful completed response
	•	structured Lite result payload
	•	summary text generated from the engine output

⸻

Internal broker usage

Most users should not call the Function Broker directly.

But if you are testing internal routing, the broker endpoint pattern is:

POST http://127.0.0.1:8081/v1/invoke?capability_id=<capability>

Example direct broker call

curl -X POST "http://127.0.0.1:8081/v1/invoke?capability_id=bue.underwrite" \
  -H "Content-Type: application/json" \
  -H "X-Service-ID: uie" \
  -d '{
    "tenant_id": "public-dev",
    "actor": "uie",
    "intent": { "task": "underwrite" },
    "payload": {
      "project": "Run underwriting on a CRE deal with 15M capex and 2.2M revenue",
      "capex": 0,
      "expected_revenue": 0,
      "asset_type": "cre"
    }
  }'

Important

This is an internal-style call, not the preferred public UIE usage pattern.

⸻

Public UIE vs internal broker envelopes

Public UIE request

Send this to port 8000:

{
  "input": "Analyze copper market conditions",
  "session_id": "demo-session-1"
}

Internal broker request

Send this to port 8081 only if you are intentionally testing broker internals:

{
  "tenant_id": "public-dev",
  "actor": "uie",
  "intent": {
    "task": "underwrite"
  },
  "payload": {
    "project": "Analyze copper market conditions",
    "capex": 0,
    "expected_revenue": 0,
    "asset_type": "cre"
  }
}

Do not confuse the two

If you send broker-style envelopes to the UIE public port, you may get validation or internal errors.

⸻

Common terminal examples

Example 1 — market / risk style request

curl -X POST "http://127.0.0.1:8000/v1/simple-submit" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Analyze copper market conditions and provide a risk summary"
  }'

Example 2 — underwriting request

curl -X POST "http://127.0.0.1:8000/v1/simple-submit" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Run underwriting on a CRE deal with 15M capex and 2.2M revenue"
  }'

Example 3 — compute optimization request

curl -X POST "http://127.0.0.1:8000/v1/simple-submit" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Optimize compute resources for a short analysis workload"
  }'

Example 4 — alternate /orchestrate path

curl -X POST "http://127.0.0.1:8000/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Provide a risk summary for copper market conditions",
    "session_id": "risk-demo-1"
  }'


⸻

Failure handling and debugging

If you get Internal UIE error

Check the UIE logs:

tail -n 120 ./.logs/uie.log

If the stack is not fully online

Restart Lite:

./start_aetherion_lite.sh

Recheck health

curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8081/health


⸻

Current capabilities of Aetherion Lite

Aetherion Lite currently supports:
	•	local UIE entrypoint
	•	broker-mediated orchestration
	•	BUE-based business / underwriting responses
	•	CEOA-based compute optimization requests
	•	ILE internal learning integration
	•	structured terminal usage

⸻

Current limits of Aetherion Lite

Aetherion Lite does not include the full private Aetherion stack.

Not included in Lite
	•	full Domain Cortex workflows
	•	Cortex Gateway dependencies
	•	UDOA full data layer
	•	URPE advanced strategic/existential modules
    •   Constitutional Governance protocols
    •   9-Lane Data Architecture
	•	global compute / mesh orchestration
	•	enterprise connectors and production deployment layers
    •   Full platform agnosticism software/hardware/platform (potential operations for cloud, on-prem, edge)
    •   
    
Full Aetherion capabilities are set to release over time! Currently raising capital! Make sure to share our GitHub @aetherion-cgi and stay tuned for updates as we pursue the path of what we call Collective General Intelligence!

⸻

Aetherion Lite vs Full Aetherion

Aetherion Lite
	•	local-first
	•	simplified deterministic routing
	•	public terminal-friendly UIE layer
	•	selected internal engines only
	•	designed for demos, evaluation, and early adoption

Full Aetherion
	•	broader orchestration graph
	•	richer routing intelligence
	•	larger capability surface
	•	deeper governance and enterprise controls
	•	full private intelligence infrastructure

⸻

Best practice for users

Use the UIE public endpoints first:
	•	/v1/simple-submit
	•	/orchestrate

Only use direct broker calls if you are intentionally testing internals.

The simplest reliable starting point is:

curl -X POST "http://127.0.0.1:8000/v1/simple-submit" \
  -H "Content-Type: application/json" \
  -d '{"input":"Analyze copper market conditions and provide a risk summary"}'


⸻

Summary

If you remember only one thing, remember this:

Public UIE request

{
  "input": "your request here",
  "session_id": "optional"
}

Best endpoint

POST /v1/simple-submit

That is the cleanest way for users to interact with Aetherion Lite from the terminal.

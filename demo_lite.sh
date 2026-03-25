#!/bin/bash

echo "🚀 Running Aetherion Lite Demo"
echo ""

# === STEP 1: BUE ===
echo "[BUE] Running underwriting..."
curl -s -X POST "http://127.0.0.1:8081/v1/invoke?capability_id=bue.underwrite" \
  -H "Content-Type: application/json" \
  -H "X-Service-ID: uie" \
  -d '{
    "tenant_id": "demo",
    "actor": "user",
    "intent": { "task": "underwrite" },
    "payload": {
      "project": "Multifamily Acquisition",
      "capex": 10000000,
      "expected_revenue": 1800000
    }
  }' | jq '.data.summary'

echo "✅ BUE Complete"
echo ""

# === STEP 2: CEOA ===
echo "[CEOA] Optimizing compute..."
curl -s -X POST "http://127.0.0.1:8081/v1/invoke?capability_id=ceoa.optimize" \
  -H "Content-Type: application/json" \
  -H "X-Service-ID: uie" \
  -d '{
    "tenant_id": "demo",
    "actor": "user",
    "intent": { "task": "optimize" },
    "payload": {
      "description": "Run analysis workload",
      "requirements": {
        "cpu_cores": 2,
        "memory_gb": 4
      }
    }
  }' | jq '.data.primary'

echo "✅ CEOA Complete"
echo ""

# === STEP 3: ILE ===
echo "[ILE] Capturing learning..."
curl -s -X POST "http://127.0.0.1:8081/v1/invoke?capability_id=ile.learn" \
  -H "Content-Type: application/json" \
  -H "X-Service-ID: system" \
  -d '{
    "tenant_id": "demo",
    "actor": "system",
    "intent": { "task": "learn" },
    "payload": {
      "observation": {
        "event": "Lite demo completed",
        "confidence": 0.9
      }
    }
  }' | jq '.data.status'

echo "✅ ILE Complete"
echo ""
echo "🎯 Aetherion Lite Demo Finished"
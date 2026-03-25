# AETHERION UIE INTEGRATION - STEP-BY-STEP MIGRATION GUIDE
# Absorbing Cortex Gateway into UIE

===============================================================================
OVERVIEW
===============================================================================

This guide will help you:
1. Integrate the new UIE service structure
2. Deprecate Cortex Gateway
3. Update docker-compose to expose only UIE on port 8000
4. Test the integration end-to-end
5. Integrate with CustomGPT/Claude

Architecture Change:
  BEFORE: Gateway (port 8080) → Broker → Engines
  AFTER:  UIE (port 8000) → Broker → Engines

===============================================================================
PREREQUISITES
===============================================================================

1. Existing Aetherion Master repository with:
   - constitutional-governance/
   - aetherion-common/
   - function-broker/
   - All engines (BUE, CEOA, UDOA, UIE, ILE, Domain Cortex)

2. Docker and Docker Compose installed

3. mTLS certificates generated (or will generate in Step 2)

===============================================================================
STEP 1: BACKUP EXISTING CONFIGURATION
===============================================================================

# Backup current setup
cd /path/to/Aetherion-Master
git checkout -b backup-before-uie-integration
git add .
git commit -m "Backup before UIE integration"

# Backup docker-compose
cp docker-compose.yml docker-compose.yml.backup

===============================================================================
STEP 2: INTEGRATE NEW UIE SERVICE
===============================================================================

2.1. Update universal-intelligence-engine directory:

cd universal-intelligence-engine/

# Create new structure
mkdir -p uie/api uie/orchestration uie/intelligence uie/clients uie/security

# Copy files from the integration package:
cp /path/to/integration/config.py uie/
cp /path/to/integration/api_models.py uie/
cp /path/to/integration/security.py uie/security/
cp /path/to/integration/function_broker_client.py uie/clients/
cp /path/to/integration/orchestrator.py uie/orchestration/
cp /path/to/integration/main.py uie/

# Add __init__.py files
touch uie/__init__.py
touch uie/api/__init__.py
touch uie/orchestration/__init__.py
touch uie/intelligence/__init__.py
touch uie/clients/__init__.py
touch uie/security/__init__.py

# Update Dockerfile
cp /path/to/integration/Dockerfile ./Dockerfile

# Update requirements
cp /path/to/integration/requirements.txt ./requirements.txt

2.2. Update pyproject.toml:

cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "aetherion-uie"
version = "2.0.0"
description = "Universal Intelligence Engine with absorbed Gateway functionality"
requires-python = ">=3.11"
dependencies = [
  "aetherion-common>=1.0.0",
  "fastapi>=0.110,<1.0",
  "uvicorn[standard]>=0.27,<0.28",
  "pydantic>=2.6,<3.0",
  "httpx>=0.27,<0.28",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["uie*"]
EOF

===============================================================================
STEP 3: UPDATE DOCKER-COMPOSE
===============================================================================

3.1. Replace docker-compose.yml with new architecture:

cd /path/to/Aetherion-Master
cp /path/to/integration/docker-compose.yml ./docker-compose.yml

3.2. Create .env file for secrets:

cat > .env << 'EOF'
# Aetherion Environment Variables

# API Keys (comma-separated for multiple keys)
AETHERION_API_KEYS=demo-key-12345,customgpt-key-xyz,claude-key-abc

# Database passwords
POSTGRES_PASSWORD=your-secure-postgres-password
NEO4J_PASSWORD=your-secure-neo4j-password

# Add other secrets as needed
EOF

# Secure the .env file
chmod 600 .env

===============================================================================
STEP 4: GENERATE mTLS CERTIFICATES
===============================================================================

# Create certificates directory
mkdir -p certs

# Generate certificates script
cat > scripts/generate-certs.sh << 'EOF'
#!/bin/bash
set -e

CERTS_DIR="certs"
mkdir -p $CERTS_DIR

# Generate CA
openssl req -new -x509 -days 3650 -keyout $CERTS_DIR/ca.key \
  -out $CERTS_DIR/ca.crt -nodes -subj "/CN=Aetherion-CA"

# Generate UIE certificate
openssl req -new -keyout $CERTS_DIR/uie.key -out $CERTS_DIR/uie.csr \
  -nodes -subj "/CN=uie"
openssl x509 -req -in $CERTS_DIR/uie.csr -CA $CERTS_DIR/ca.crt \
  -CAkey $CERTS_DIR/ca.key -CAcreateserial -out $CERTS_DIR/uie.crt -days 3650

# Generate Function Broker certificate
openssl req -new -keyout $CERTS_DIR/broker.key -out $CERTS_DIR/broker.csr \
  -nodes -subj "/CN=function-broker"
openssl x509 -req -in $CERTS_DIR/broker.csr -CA $CERTS_DIR/ca.crt \
  -CAkey $CERTS_DIR/ca.key -CAcreateserial -out $CERTS_DIR/broker.crt -days 3650

# Clean up CSRs
rm $CERTS_DIR/*.csr

echo "Certificates generated in $CERTS_DIR/"
EOF

chmod +x scripts/generate-certs.sh
./scripts/generate-certs.sh

===============================================================================
STEP 5: BUILD AND START SERVICES
===============================================================================

5.1. Build all images:

docker-compose build

5.2. Start infrastructure first:

docker-compose up -d postgres neo4j redis redpanda opa

# Wait for infrastructure to be healthy
sleep 30

5.3. Start engines:

docker-compose up -d bue ceoa udoa uie-engine ile domain-cortex urpe

# Wait for engines to be ready
sleep 20

5.4. Start Function Broker:

docker-compose up -d function-broker

# Wait for broker
sleep 10

5.5. Start UIE (public service):

docker-compose up -d uie

5.6. Verify all services are running:

docker-compose ps

# Expected: All services should show "Up" or "Up (healthy)"

===============================================================================
STEP 6: VERIFY INTEGRATION
===============================================================================

6.1. Check UIE health:

curl http://localhost:8000/health

# Expected: {"status": "healthy", ...}

6.2. Check root endpoint:

curl http://localhost:8000/

# Expected: Service info with version 2.0.0

6.3. Test natural language request:

curl -X POST http://localhost:8000/aetherion \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-12345" \
  -d '{
    "message": "What happens if fusion energy becomes commercial by 2030?",
    "session_id": "test-session-1"
  }'

# Expected: Conversational response with analysis

6.4. Test structured request (legacy format):

curl -X POST http://localhost:8000/aetherion \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-12345" \
  -d '{
    "capability": "intelligence.query",
    "params": {
      "prompt": "Analyze copper demand through 2030"
    },
    "response_format": "structured"
  }'

# Expected: Structured data response

===============================================================================
STEP 7: VERIFY SECURITY
===============================================================================

7.1. Test without API key (should fail):

curl -X POST http://localhost:8000/aetherion \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# Expected: 401 Unauthorized

7.2. Test with invalid API key (should fail):

curl -X POST http://localhost:8000/aetherion \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid-key" \
  -d '{"message": "test"}'

# Expected: 401 Invalid API key

7.3. Test rate limiting:

for i in {1..65}; do
  curl -X POST http://localhost:8000/aetherion \
    -H "X-API-Key: demo-key-12345" \
    -H "Content-Type: application/json" \
    -d '{"message": "test '$i'"}' &
done
wait

# Expected: Some requests will return 429 Too Many Requests

7.4. Verify engines are not accessible externally:

curl http://localhost:7500/health  # Domain Cortex
# Expected: Connection refused (no route to host)

curl http://localhost:9000/health  # BUE
# Expected: Connection refused (no route to host)

===============================================================================
STEP 8: FULL SMOKE TEST
===============================================================================

# Run comprehensive smoke test
python scripts/aetherion_smoke_test.py

# This will test:
# - UIE endpoint
# - All capability routes through Function Broker
# - Governance enforcement
# - Multi-step workflows

===============================================================================
STEP 9: CUSTOMGPT INTEGRATION
===============================================================================

9.1. Get your public endpoint:

# If deploying to cloud:
YOUR_DOMAIN=https://aetherion.yourdomain.com

# If testing locally with ngrok:
ngrok http 8000
# Copy the ngrok URL

9.2. In CustomGPT:

1. Go to CustomGPT settings
2. Add Action:
   - Name: "Aetherion"
   - Description: "Universal AI platform for analysis and intelligence"
   - Authentication: API Key
   - API Key Header: X-API-Key
   - API Key Value: <your-api-key>
   - OpenAPI Schema URL: YOUR_DOMAIN/openapi.json

3. Test the action:
   - Message: "What happens if fusion energy becomes commercial?"
   - Should receive conversational response

===============================================================================
STEP 10: CLAUDE INTEGRATION (MCP)
===============================================================================

10.1. Create MCP configuration:

cat > ~/.config/claude/mcp_servers.json << 'EOF'
{
  "aetherion": {
    "url": "http://localhost:8000/aetherion",
    "headers": {
      "X-API-Key": "claude-key-abc"
    },
    "description": "Aetherion AI platform for analysis"
  }
}
EOF

10.2. Test in Claude:

User: "Connect to Aetherion and analyze fusion energy impact"
Claude will: Call your endpoint via MCP

===============================================================================
STEP 11: DEPRECATE CORTEX GATEWAY
===============================================================================

11.1. Remove Gateway from docker-compose:

# Gateway is no longer needed - it's been absorbed into UIE

# If you want to keep it temporarily as backup:
docker-compose stop cortex-gateway
# Then remove from docker-compose.yml when confident

11.2. Update documentation:

# Update all docs to point to:
# - Endpoint: http://localhost:8000/aetherion
# - No longer: http://localhost:8080/...

===============================================================================
MONITORING AND MAINTENANCE
===============================================================================

# View UIE logs
docker-compose logs -f uie

# View all logs
docker-compose logs -f

# Restart UIE
docker-compose restart uie

# Update UIE
docker-compose build uie
docker-compose up -d uie

===============================================================================
ROLLBACK PLAN (If Needed)
===============================================================================

# If something goes wrong:

1. Stop services:
   docker-compose down

2. Restore backup:
   git checkout backup-before-uie-integration
   cp docker-compose.yml.backup docker-compose.yml

3. Restart old configuration:
   docker-compose up -d

===============================================================================
SUCCESS CRITERIA
===============================================================================

✓ UIE is accessible on port 8000
✓ All engines are internal-only (not accessible externally)
✓ Natural language requests work
✓ Structured requests work (backward compatible)
✓ Authentication works (API key required)
✓ Rate limiting works
✓ Governance checks work
✓ Domain Cortex is protected (no external access)
✓ Function Broker orchestrates correctly
✓ Health checks pass
✓ CustomGPT/Claude integration works

===============================================================================
NEXT STEPS
===============================================================================

1. Configure production API keys
2. Setup SSL/TLS for production
3. Configure cloud deployment
4. Setup monitoring and alerting
5. Add LLM-based intent parsing (replace simple rules)
6. Enhance conversation memory with persistent storage
7. Add streaming responses
8. Performance optimization

===============================================================================

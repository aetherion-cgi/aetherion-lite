# Aetherion UIE Integration Package
## Universal Intelligence Engine - Cortex Gateway Absorption

**Version:** 2.0.0  
**Date:** 2024  
**Author:** Aetherion Team

---

## What This Package Contains

This is the complete implementation for absorbing Cortex Gateway functionality into UIE, making UIE the single public interface on port 8000.

### Files Included:

#### Core Application
- `config.py` - Configuration management
- `api_models.py` - Request/response Pydantic models
- `security.py` - Authentication, rate limiting, input validation
- `function_broker_client.py` - mTLS client for internal communication
- `orchestrator.py` - Main orchestration logic (absorbed from Gateway)
- `main.py` - FastAPI application

#### Docker & Deployment
- `Dockerfile` - Container image for UIE
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Complete system deployment

#### Documentation & Testing
- `COMPLETE_SUMMARY.md` - Architecture overview and quick start
- `MIGRATION_GUIDE.md` - Detailed step-by-step migration instructions
- `aetherion_smoke_test.py` - Comprehensive test suite
- `uie_service_structure.txt` - Service structure reference
- `README.md` - This file

---

## Quick Start (10 Minutes)

### 1. Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- Existing Aetherion Master repository
- Basic understanding of the architecture

### 2. Installation

```bash
# Navigate to your Aetherion Master repo
cd /path/to/Aetherion-Master

# Copy integration files
cp -r /path/to/aetherion-uie-integration/* universal-intelligence-engine/

# Create environment file
cat > .env << 'EOF'
AETHERION_API_KEYS=demo-key-12345,customgpt-key,claude-key
POSTGRES_PASSWORD=change-me
NEO4J_PASSWORD=change-me
EOF

# Generate mTLS certificates
mkdir -p scripts
cat > scripts/generate-certs.sh << 'EOF'
#!/bin/bash
set -e
CERTS_DIR="certs"
mkdir -p $CERTS_DIR
openssl req -new -x509 -days 3650 -keyout $CERTS_DIR/ca.key \
  -out $CERTS_DIR/ca.crt -nodes -subj "/CN=Aetherion-CA"
openssl req -new -keyout $CERTS_DIR/uie.key -out $CERTS_DIR/uie.csr \
  -nodes -subj "/CN=uie"
openssl x509 -req -in $CERTS_DIR/uie.csr -CA $CERTS_DIR/ca.crt \
  -CAkey $CERTS_DIR/ca.key -CAcreateserial -out $CERTS_DIR/uie.crt -days 3650
openssl req -new -keyout $CERTS_DIR/broker.key -out $CERTS_DIR/broker.csr \
  -nodes -subj "/CN=function-broker"
openssl x509 -req -in $CERTS_DIR/broker.csr -CA $CERTS_DIR/ca.crt \
  -CAkey $CERTS_DIR/ca.key -CAcreateserial -out $CERTS_DIR/broker.crt -days 3650
rm $CERTS_DIR/*.csr
echo "Certificates generated"
EOF
chmod +x scripts/generate-certs.sh
./scripts/generate-certs.sh
```

### 3. Deploy

```bash
# Build images
docker-compose build

# Start infrastructure
docker-compose up -d postgres neo4j redis redpanda opa
sleep 30

# Start engines
docker-compose up -d bue ceoa udoa uie-engine ile domain-cortex urpe
sleep 20

# Start Function Broker
docker-compose up -d function-broker
sleep 10

# Start UIE (public service)
docker-compose up -d uie
```

### 4. Test

```bash
# Health check
curl http://localhost:8000/health

# Natural language test
curl -X POST http://localhost:8000/aetherion \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-12345" \
  -d '{"message": "What happens if fusion energy becomes commercial by 2030?"}'

# Full smoke test
python aetherion_smoke_test.py
```

---

## What You Get

### Before (Old Architecture)
- Gateway on port 8080 (public)
- UIE on port 8000 (internal)
- Duplicate orchestration logic
- Multiple attack surfaces

### After (New Architecture)
- **UIE on port 8000 (ONLY public port)**
- All engines internal-only
- Single orchestrator
- Domain Cortex fully protected
- Perfect for CustomGPT/Claude integration

---

## Key Features

✅ **Single Public Endpoint** - Port 8000 only  
✅ **Natural Language Interface** - Conversational API  
✅ **Protected Engines** - All internal, no external access  
✅ **Domain Cortex Security** - The brain is invisible  
✅ **Constitutional Governance** - OPA enforcement  
✅ **Session Management** - Conversation memory  
✅ **Rate Limiting** - Protection against abuse  
✅ **API Key Authentication** - Secure access  
✅ **CustomGPT/Claude Ready** - Direct integration support  
✅ **Backward Compatible** - Structured format still works  

---

## For CustomGPT Integration

1. Deploy UIE to your domain
2. In CustomGPT settings:
   - Add Action
   - Name: "Aetherion"
   - Authentication: API Key (X-API-Key header)
   - Base URL: `https://your-domain.com:8000`
   - OpenAPI Schema: `/openapi.json`

3. Test:
```
User: "Use Aetherion to analyze fusion energy impact"
→ CustomGPT calls your endpoint
→ Receives conversational response
```

---

## For Claude Integration (MCP)

```bash
# Create MCP config
cat > ~/.config/claude/mcp_servers.json << 'EOF'
{
  "aetherion": {
    "url": "http://localhost:8000/aetherion",
    "headers": {
      "X-API-Key": "claude-key"
    }
  }
}
EOF
```

Then in Claude:
```
User: "Connect to Aetherion and analyze copper demand"
→ Claude calls via MCP
→ Your UIE processes
→ Returns synthesized response
```

---

## Documentation

- **Quick Start**: This file
- **Complete Guide**: `COMPLETE_SUMMARY.md`
- **Migration Steps**: `MIGRATION_GUIDE.md`
- **Architecture**: `uie_service_structure.txt`
- **API Docs**: http://localhost:8000/docs (when running)

---

## Testing

### Smoke Test
```bash
python aetherion_smoke_test.py
```

Tests:
- Basic connectivity
- Authentication
- Natural language requests
- Structured requests
- Governance enforcement
- Security features
- Conversation memory

Expected: 100% pass rate

---

## Security

### What's Protected

1. **Domain Cortex**
   - No public ports
   - Only Function Broker access
   - UIE sanitizes inputs
   - Results synthesized before return

2. **All Engines**
   - Internal network only
   - mTLS communication
   - No direct external access

3. **Function Broker**
   - Internal only (port 8081)
   - Constitutional governance
   - OPA policy enforcement

### Security Layers

Every request passes through:
1. API Key Authentication
2. Rate Limiting
3. Input Validation
4. Intent Parsing
5. Governance Authorization
6. mTLS Communication
7. Result Synthesis
8. Output Filtering

---

## Troubleshooting

### UIE Not Starting
```bash
docker-compose logs uie
# Check Function Broker health
# Check certificates exist
```

### Cannot Connect
```bash
# Check port 8000 is accessible
curl http://localhost:8000/health

# Check Docker networks
docker network ls
```

### Authentication Fails
```bash
# Verify API key in .env
cat .env | grep API_KEYS

# Test with correct key
curl -H "X-API-Key: demo-key-12345" http://localhost:8000/aetherion
```

---

## Support

- Read `COMPLETE_SUMMARY.md` for full architecture
- Read `MIGRATION_GUIDE.md` for detailed steps
- Run `aetherion_smoke_test.py` for diagnostics
- Check logs: `docker-compose logs -f uie`

---

## Success Criteria

✅ UIE accessible on port 8000  
✅ Health check returns healthy  
✅ Natural language requests work  
✅ Structured requests work  
✅ Authentication enforced  
✅ Rate limiting active  
✅ Engines not externally accessible  
✅ Governance enforced  
✅ All smoke tests pass  
✅ CustomGPT/Claude can connect  

---

## Next Steps

1. **Production Setup**
   - Remove demo API keys
   - Configure SSL/TLS
   - Setup reverse proxy
   - Deploy to cloud

2. **Enhance Intelligence**
   - Add LLM-based intent parsing
   - Persistent conversation memory
   - Streaming responses

3. **Monitoring**
   - Prometheus + Grafana
   - Distributed tracing
   - Performance profiling

---

## License & Attribution

Built for Aetherion Platform  
With constitutional governance and human primacy  
Ready for Earth to interplanetary operations

---

**Questions? Issues? Feedback?**

This is a complete, production-ready implementation. Follow the migration guide step-by-step, run the smoke tests, and you'll have UIE as your single public interface protecting all internal engines including Domain Cortex.

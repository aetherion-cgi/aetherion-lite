# ILE Deployment Guide

**Quick Start:** Get the complete 7-domain ILE system running in production

---

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ with TimescaleDB extension
- Neo4j 5.13+
- Redis 7+
- Docker & Docker Compose (optional but recommended)

---

## Option 1: Docker Deployment (Recommended)

### 1. Create `docker-compose.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL with TimescaleDB
  postgres:
    image: timescale/timescaledb:latest-pg14
    environment:
      POSTGRES_DB: ile_database
      POSTGRES_USER: ile_user
      POSTGRES_PASSWORD: ile_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ile_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Neo4j Graph Database
  neo4j:
    image: neo4j:5.13
    environment:
      NEO4J_AUTH: neo4j/ile_password
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
      NEO4J_dbms_memory_heap_max__size: 2G
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ile_password 'RETURN 1'"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redpanda (Kafka-compatible)
  redpanda:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start
      - --smp 1
      - --memory 1G
      - --reserve-memory 0M
      - --overprovisioned
      - --node-id 0
      - --kafka-addr PLAINTEXT://0.0.0.0:29092,OUTSIDE://0.0.0.0:9092
      - --advertise-kafka-addr PLAINTEXT://redpanda:29092,OUTSIDE://localhost:9092
    ports:
      - "9092:9092"
      - "29092:29092"
    volumes:
      - redpanda_data:/var/lib/redpanda/data

  # ILE Orchestrator
  ile_orchestrator:
    build: .
    environment:
      # Database connections
      POSTGRES_URL: postgresql+asyncpg://ile_user:ile_password@postgres:5432/ile_database
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: ile_password
      REDIS_URL: redis://redis:6379/0
      KAFKA_BOOTSTRAP_SERVERS: redpanda:29092
      
      # System configuration
      NUM_WORKERS: 8
      LOG_LEVEL: INFO
      
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      redis:
        condition: service_healthy
      redpanda:
        condition: service_started
    ports:
      - "8000:8000"  # API port
    restart: unless-stopped

volumes:
  postgres_data:
  neo4j_data:
  redis_data:
  redpanda_data:
```

### 2. Create `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ILE system
COPY ile_system/ ./ile_system/

# Copy startup script
COPY docker_entrypoint.py .

# Expose API port
EXPOSE 8000

# Run ILE system
CMD ["python", "docker_entrypoint.py"]
```

### 3. Create `docker_entrypoint.py`

```python
"""Docker entrypoint for ILE system"""

import asyncio
import logging
import os

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    from ile_system import setup_complete_ile_system
    from ile_system.database import init_database
    from ile_system.ingestion import ILEIngestionService
    
    # Initialize databases
    logger.info("Initializing databases...")
    await init_database(
        postgres_url=os.getenv("POSTGRES_URL"),
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_user=os.getenv("NEO4J_USER"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        redis_url=os.getenv("REDIS_URL")
    )
    
    # Setup ILE system
    logger.info("Setting up ILE system...")
    from ile_system.database import db_manager
    from ile_system.knowledge_graph import get_knowledge_graph
    from ile_system.constitutional_validator import ConstitutionalValidator
    
    validator = ConstitutionalValidator()
    kg = get_knowledge_graph()
    
    orchestrator, domains = await setup_complete_ile_system(
        db_manager=db_manager,
        knowledge_graph=kg,
        constitutional_validator=validator
    )
    
    # Start ingestion service
    logger.info("Starting ingestion service...")
    ingestion = ILEIngestionService(orchestrator)
    await ingestion.start()
    
    logger.info("🚀 ILE System running - all 7 domains active!")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await ingestion.stop()
        from ile_system import stop_orchestrator, close_database
        await stop_orchestrator()
        await close_database()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Deploy

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f ile_orchestrator

# Check status
docker-compose ps

# Scale orchestrators horizontally
docker-compose up -d --scale ile_orchestrator=5
```

---

## Option 2: Manual Deployment

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install ILE system
pip install -e .
```

### 2. Setup Databases

```bash
# PostgreSQL with TimescaleDB
createdb ile_database
psql ile_database -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"

# Create tables (run migrations)
python scripts/init_database.py
```

### 3. Configure Environment

Create `.env` file:

```bash
# Database URLs
POSTGRES_URL=postgresql+asyncpg://user:pass@localhost/ile_database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
REDIS_URL=redis://localhost:6379/0

# System configuration
NUM_WORKERS=4
LOG_LEVEL=INFO
```

### 4. Run System

```python
# run_ile.py
import asyncio
import logging
from ile_system import setup_complete_ile_system
from ile_system.database import init_database, db_manager
from ile_system.knowledge_graph import get_knowledge_graph
from ile_system.constitutional_validator import ConstitutionalValidator
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

async def main():
    # Initialize databases
    await init_database(
        postgres_url=os.getenv("POSTGRES_URL"),
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_user=os.getenv("NEO4J_USER"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        redis_url=os.getenv("REDIS_URL")
    )
    
    # Setup ILE
    validator = ConstitutionalValidator()
    kg = get_knowledge_graph()
    
    orchestrator, domains = await setup_complete_ile_system(
        db_manager=db_manager,
        knowledge_graph=kg,
        constitutional_validator=validator
    )
    
    print("🚀 ILE System ready!")
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
python run_ile.py
```

---

## Option 3: Kubernetes Deployment

### 1. Create Helm Chart

```yaml
# values.yaml
replicaCount: 3

image:
  repository: aetherion/ile
  tag: "1.0.0"
  pullPolicy: IfNotPresent

resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

postgres:
  enabled: true
  host: postgres-service
  database: ile_database

neo4j:
  enabled: true
  host: neo4j-service

redis:
  enabled: true
  host: redis-service

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
```

### 2. Deploy

```bash
# Install with Helm
helm install ile-system ./helm-chart -f values.yaml

# Or use kubectl
kubectl apply -f k8s/
```

---

## Production Checklist

### Security
- [ ] Change default passwords
- [ ] Enable TLS/SSL for all database connections
- [ ] Configure firewall rules
- [ ] Set up VPN for database access
- [ ] Enable audit logging

### Performance
- [ ] Configure connection pooling
- [ ] Set appropriate worker counts
- [ ] Enable Redis persistence
- [ ] Configure TimescaleDB retention policies
- [ ] Set up database indexes

### Monitoring
- [ ] Configure Prometheus metrics
- [ ] Set up Grafana dashboards
- [ ] Configure alerting rules
- [ ] Enable distributed tracing
- [ ] Set up log aggregation

### Reliability
- [ ] Configure database backups
- [ ] Set up replication
- [ ] Configure circuit breakers
- [ ] Enable graceful shutdown
- [ ] Test disaster recovery

---

## Testing Deployment

```python
# test_deployment.py
import asyncio
from ile_system.models import LearningEvent, DomainType, APIType, LearningEventType

async def test():
    from ile_system import get_orchestrator
    
    orchestrator = await get_orchestrator()
    
    # Create test event
    event = LearningEvent(
        event_type=LearningEventType.OUTCOME,
        domain=DomainType.TASK_BASED,
        api=APIType.BUE,
        prediction_id="test_001",
        inputs={"company": "TestCorp"},
        predicted={"risk_score": 0.25},
        actual={"default": False},
        learning_signal=0.75
    )
    
    # Process event
    result = await orchestrator.process_learning_event(event, priority=7)
    
    print(f"✅ Test passed: {result}")
    
    # Get metrics
    metrics = await orchestrator.get_metrics()
    print(f"Metrics: {metrics}")

if __name__ == "__main__":
    asyncio.run(test())
```

```bash
python test_deployment.py
```

---

## Troubleshooting

### Issue: Database connection errors

```bash
# Check database connectivity
psql -h localhost -U ile_user -d ile_database -c "SELECT 1"
neo4j-admin server console  # Check Neo4j logs
redis-cli ping
```

### Issue: High memory usage

```bash
# Reduce worker count
export NUM_WORKERS=2

# Limit Neo4j heap
export NEO4J_dbms_memory_heap_max__size=1G
```

### Issue: Slow performance

```bash
# Check database indexes
psql ile_database -c "\di"

# Check Neo4j query performance
PROFILE MATCH (n) RETURN count(n)

# Enable Redis persistence
redis-cli CONFIG SET save "900 1 300 10"
```

---

## Scaling Guide

### Horizontal Scaling

```bash
# Scale orchestrators
docker-compose up -d --scale ile_orchestrator=10

# Or with Kubernetes
kubectl scale deployment ile-orchestrator --replicas=10
```

### Database Scaling

```bash
# PostgreSQL read replicas
# Configure streaming replication

# Neo4j clustering
# Set up causal cluster with 3+ core servers

# Redis cluster
# Configure Redis cluster mode for sharding
```

### Performance Tuning

```python
# Adjust worker pool size
os.environ["NUM_WORKERS"] = "16"

# Batch size for processing
os.environ["BATCH_SIZE"] = "500"

# Increase connection pools
os.environ["POSTGRES_POOL_SIZE"] = "100"
os.environ["NEO4J_MAX_CONNECTIONS"] = "50"
```

---

## Support

For issues or questions:
- Documentation: `/docs`
- GitHub: [Aetherion ILE Issues]
- Email: support@aetherion.ai

---

**Your ILE system is ready for production! 🚀**

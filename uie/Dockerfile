# Aetherion UIE Dockerfile
# Absorbs Cortex Gateway functionality into UIE
# Public-facing service on port 8000

FROM python:3.11-slim

LABEL maintainer="Aetherion Team"
LABEL description="Universal Intelligence Engine - Public interface with absorbed Gateway functionality"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install aetherion-common (from parent repo)
COPY aetherion-common /tmp/aetherion-common
RUN pip install --no-cache-dir -e /tmp/aetherion-common

# Install wrappers (UIE has direct access to wrappers for optimization)
COPY wrappers /tmp/wrappers
RUN pip install --no-cache-dir -e /tmp/wrappers

# Copy UIE application code
COPY uie/ /app/uie/
COPY config.py api_models.py security.py function_broker_client.py orchestrator.py main.py /app/

# Create directory for mTLS certificates
RUN mkdir -p /certs

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port 8000 (PUBLIC)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run UIE
CMD ["python", "main.py"]

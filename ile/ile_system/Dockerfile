FROM python:3.11-slim

WORKDIR /app

# --- System deps (for configs, HTTP, optional data work) ---
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Install shared aetherion-common from the monorepo ---
# Assumes aetherion-common/ lives at the repo root (context: .)
COPY aetherion-common /tmp/aetherion-common
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /tmp/aetherion-common

# --- Copy ILE project (ile_system) into the image ---
# This folder contains pyproject.toml and the ile_system package.
COPY ILE_Complete_Implementation/ile_system /app/ile_system

# --- Install ILE itself as a package ---
RUN pip install --no-cache-dir -e /app/ile_system

ENV PYTHONPATH=/app

# Match the port referenced in docker-compose for the 'ile' service
EXPOSE 7400

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7400/health || exit 1

# Adjust module path if your FastAPI entrypoint differs
# Make sure ile_system/api/main.py defines `app = FastAPI(...)`
CMD ["uvicorn", "ile_system.api.main:app", "--host", "0.0.0.0", "--port", "7400"]
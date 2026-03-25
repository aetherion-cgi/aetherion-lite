FROM python:3.11-slim

WORKDIR /app

# --- System deps (HTTP, JSON, etc.) ---
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Install shared aetherion-common from the monorepo ---
# Assumes aetherion-common/ lives at the repo root (context: .)
COPY aetherion-common /tmp/aetherion-common
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /tmp/aetherion-common

# --- Copy Function Broker project metadata + code ---
# Assumes function-broker/pyproject.toml and function-broker/function_broker/ exist.
COPY function-broker/pyproject.toml ./pyproject.toml
COPY function-broker/ ./function-broker

# --- Install Function Broker itself as a package ---
RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app

# Example: if function-broker hosts an API
EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

# Adjust module path to your actual FastAPI app
# e.g., if your entrypoint is function_broker.api.main:app
CMD ["uvicorn", "function_broker.api.main:app", "--host", "0.0.0.0", "--port", "8100"]

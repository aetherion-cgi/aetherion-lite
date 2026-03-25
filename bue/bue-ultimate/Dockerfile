FROM python:3.11-slim

WORKDIR /app

# --- System deps for scientific stack (numpy/pandas/scipy, etc.) ---
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    gfortran \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Install shared aetherion-common from the monorepo ---
# aetherion-common lives at ./aetherion-common relative to the repo root (context: .)
COPY aetherion-common /tmp/aetherion-common
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /tmp/aetherion-common

# --- Copy BUE application code & metadata into the image ---
# these paths are relative to the build context (the repo root)
COPY bue-ultimate/bue-ultimate/pyproject.toml ./pyproject.toml
COPY bue-ultimate/bue-ultimate/bue ./bue
COPY bue-ultimate/bue-ultimate/config ./config

# --- Install BUE itself as an editable package ---
RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app

# BUE unified-service port (matches top-level docker-compose.yml)
EXPOSE 9000

# Optional: HTTP healthcheck (adjust path once your API exposes it)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# --- Start the BUE API ---
# Make sure bue/api/rest.py exists and exposes `app = FastAPI(...)`
CMD ["uvicorn", "bue.api.rest:app", "--host", "0.0.0.0", "--port", "9000"]
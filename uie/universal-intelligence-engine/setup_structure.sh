#!/bin/bash

# Universal Intelligence Engine - Project Structure Setup

# Core application
mkdir -p uie/api
mkdir -p uie/core
mkdir -p uie/adapters
mkdir -p uie/catalogs
mkdir -p uie/security
mkdir -p uie/observability

# Configuration and artifacts
mkdir -p config/opa
mkdir -p config/models
mkdir -p config/prompts
mkdir -p config/tools

# Tests
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/e2e
mkdir -p tests/fixtures

# Deployment
mkdir -p deployment/docker
mkdir -p deployment/k8s

# Documentation
mkdir -p docs/api
mkdir -p docs/architecture
mkdir -p docs/guides

# Create __init__.py files
touch uie/__init__.py
touch uie/api/__init__.py
touch uie/core/__init__.py
touch uie/adapters/__init__.py
touch uie/catalogs/__init__.py
touch uie/security/__init__.py
touch uie/observability/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/e2e/__init__.py

echo "UIE project structure created successfully"

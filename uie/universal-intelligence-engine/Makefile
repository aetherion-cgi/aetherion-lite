.PHONY: help install test lint format clean docker-build docker-up docker-down logs

help:
	@echo "Universal Intelligence Engine - Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make test         - Run all tests"
	@echo "  make lint         - Run linters (flake8, mypy)"
	@echo "  make format       - Format code with black"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start all services"
	@echo "  make docker-down  - Stop all services"
	@echo "  make logs         - View UIE logs"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=uie --cov-report=html

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v

lint:
	flake8 uie/ --max-line-length=100
	mypy uie/

format:
	black uie/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/ .coverage

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-restart:
	docker-compose restart uie

logs:
	docker-compose logs -f uie

logs-all:
	docker-compose logs -f

health:
	curl -s http://localhost:8000/health | python -m json.tool

# Development
dev:
	uvicorn uie.api.gateway:app --reload --host 0.0.0.0 --port 8000

# Database/Cache
redis-cli:
	docker-compose exec redis redis-cli

# Monitoring
prometheus:
	@echo "Opening Prometheus at http://localhost:9090"
	open http://localhost:9090 || xdg-open http://localhost:9090

grafana:
	@echo "Opening Grafana at http://localhost:3000"
	@echo "Default credentials: admin/admin"
	open http://localhost:3000 || xdg-open http://localhost:3000

# Documentation
docs:
	@echo "Opening documentation..."
	open README.md || xdg-open README.md

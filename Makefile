# ═══════════════════════════════════════════════════════════════════════
# Makefile — common development commands
# ═══════════════════════════════════════════════════════════════════════

.DEFAULT_GOAL := help

# ── Docker ───────────────────────────────────────────────────────────

.PHONY: up down build logs ps restart

up: ## Start all services (detached)
	docker compose up -d

build: ## Build and start all services
	docker compose up --build -d

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose down && docker compose up -d

logs: ## Tail all service logs
	docker compose logs -f --tail=50

ps: ## Show running services
	docker compose ps

# ── Individual Services ──────────────────────────────────────────────

.PHONY: rebuild-% logs-%

rebuild-%: ## Rebuild a single service (e.g. make rebuild-content)
	docker compose up -d --build $*

logs-%: ## Tail logs for a single service (e.g. make logs-auth)
	docker compose logs -f --tail=100 $*

# ── Virtual Environments ─────────────────────────────────────────────

SHARED   := server/services/shared
SERVICES := server/services/auth_service \
            server/services/content_service \
            server/services/notification_service \
            server/services/search_service \
            server/services/dashboard_service \
            server/services/realtime_service \
            server/api_gateway

.PHONY: setup venv-clean

setup: ## Create per-service virtual environments and install dependencies
	@echo "Creating venv for shared..."
	@python -m uv venv $(SHARED)/.venv --quiet
	@python -m uv pip install -e $(SHARED) --python $(SHARED)/.venv/Scripts/python.exe --quiet
	@for svc in $(SERVICES); do \
		echo "Creating venv for $$(basename $$svc)..."; \
		python -m uv venv $$svc/.venv --quiet; \
		python -m uv pip install -e $(SHARED) -e "$$svc[test]" --python $$svc/.venv/Scripts/python.exe --quiet; \
	done
	@echo "All virtual environments ready."

venv-clean: ## Remove all per-service virtual environments
	@for svc in $(SHARED) $(SERVICES); do \
		rm -rf $$svc/.venv; \
	done
	@echo "All .venv directories removed."

# ── Development ──────────────────────────────────────────────────────

.PHONY: frontend seed lint test clean

frontend: ## Start frontend dev server
	cd frontend && npm run dev

seed: ## Seed the database with test data
	python scripts/seed.py

lint: ## Run ruff linter across all services
	ruff check server/

test: ## Run all unit tests
	@echo "Running auth tests..."
	cd server/services/auth_service && python -m pytest tests/ -v
	@echo "Running content tests..."
	cd server/services/content_service && python -m pytest tests/ -v
	@echo "Running notification tests..."
	cd server/services/notification_service && python -m pytest tests/ -v
	@echo "Running gateway tests..."
	cd server/api_gateway && python -m pytest tests/ -v

smoke: ## Run smoke tests against running stack
	python tests/smoke_microservices.py

# ── Database ─────────────────────────────────────────────────────────

.PHONY: db-reset

db-reset: ## ⚠️  Destroy all database volumes and restart
	docker compose down -v
	docker compose up --build -d

# ── Cleanup ──────────────────────────────────────────────────────────

.PHONY: clean prune

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

prune: ## Remove unused Docker resources
	docker system prune -f

# ── Help ─────────────────────────────────────────────────────────────

.PHONY: help

help: ## Show this help message
	@grep -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

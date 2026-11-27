CONTAINER_CLI ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
COMPOSE       ?= $(shell command -v podman-compose >/dev/null 2>&1 && echo podman-compose || ($(CONTAINER_CLI) compose version >/dev/null 2>&1 && echo "$(CONTAINER_CLI) compose" || echo docker-compose))

COMPOSE_DEV  = $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_PROD = $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml

.PHONY: help dev-up dev-down dev-logs prod-up prod-down prod-logs init-db seed-dev \
        test test-backend k8s-validate k8s-dev k8s-prod docker-build docker-up docker-down \
        lab-up lab-down lab-status bird-routes bird-unicast test-integration

help:
	@echo "Gabu — Operational & Lifecycle Commands (Container CLI: $(CONTAINER_CLI) | Compose: $(COMPOSE))"
	@echo ""
	@echo "  Developer & Multi-Peer Lab Environment:"
	@echo "    make dev-up            - Build & start full Dev + 3x BIRD Lab (auto-migrates & seeds lab)"
	@echo "    make dev-down          - Stop Dev + Lab containers"
	@echo "    make dev-logs          - Tail logs from Dev stack"
	@echo "    make seed-dev          - Re-run demo user & lab BGP peer seeding inside backend container"
	@echo ""
	@echo "  Production Environment:"
	@echo "    make prod-up           - Build & start hardened Production stack (Nginx + Gunicorn + GoBGP + DB + Syncer)"
	@echo "    make prod-down         - Stop Production containers"
	@echo "    make prod-logs         - Tail logs from Production stack"
	@echo "    make init-db           - Manually run migrations, RBAC bootstrap, and starter profile seed"
	@echo ""
	@echo "  Testing & Lab Diagnostics:"
	@echo "    make test-backend      - Run full Django unit test suite inside backend container"
	@echo "    make test-integration  - Run end-to-end Flowspec & RTBH propagation test across 3 BIRD routers"
	@echo "    make lab-status        - Display BGP session state across GoBGP and all 3 BIRD routers"
	@echo "    make bird-routes       - Query received Flowspec routes across all BIRD routers"
	@echo "    make bird-unicast      - Query received Unicast RTBH routes across all BIRD routers"
	@echo ""
	@echo "  Kubernetes:"
	@echo "    make k8s-validate      - Validate all Kubernetes manifests using kustomize"
	@echo "    make k8s-dev           - Deploy dev overlay to active Kubernetes cluster"
	@echo "    make k8s-prod          - Deploy prod overlay to active Kubernetes cluster"

# --- Developer & Lab Workflows ---
dev-up:
	$(COMPOSE_DEV) up -d --build

dev-down:
	$(COMPOSE_DEV) down

dev-logs:
	$(COMPOSE_DEV) logs -f

# Backward-compatible aliases
lab-up: dev-up
lab-down: dev-down
docker-up: dev-up
docker-down: dev-down

# --- Production Workflows ---
prod-up:
	$(COMPOSE_PROD) up -d --build

prod-down:
	$(COMPOSE_PROD) down

prod-logs:
	$(COMPOSE_PROD) logs -f

# --- Database & Seeding Helpers ---
init-db:
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py migrate --noinput
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py bootstrap_roles --ensure-superuser
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py seed_default_routing --only-if-empty
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py bootstrap_bgp_config

seed-dev:
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py bootstrap_roles --create-demo-users
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py seed_default_routing --only-if-empty
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py seed_dev_lab --force

# --- Testing & Validation ---
test:
	@echo "Running BGP backend contract test suite..."
	cd backend && python3 -m unittest discover apps/bgp_engine/tests

test-backend:
	$(CONTAINER_CLI) exec bgpweb-backend python manage.py test

test-integration:
	python3 tests/integration/test_ebgp_flowspec_propagation.py

docker-build:
	$(CONTAINER_CLI) build -t bgpweb-backend:latest -f deploy/docker/backend.Dockerfile .
	$(CONTAINER_CLI) build -t bgpweb-frontend:latest -f deploy/docker/frontend.Dockerfile .
	$(CONTAINER_CLI) build -t bgpweb-bird:latest -f deploy/docker/bird.Dockerfile .

k8s-validate:
	@echo "Validating Kubernetes manifests..."
	kubectl kustomize deploy/k8s/ > /dev/null
	kubectl kustomize deploy/overlays/dev/ > /dev/null
	kubectl kustomize deploy/overlays/prod/ > /dev/null
	@echo "All Kubernetes manifests and overlays validated successfully!"

k8s-dev:
	kubectl apply -k deploy/overlays/dev/

k8s-prod:
	kubectl apply -k deploy/overlays/prod/

lab-status:
	@echo "=== GoBGP Neighbors ==="
	@$(CONTAINER_CLI) exec bgpweb-gobgp gobgp neighbor || true
	@echo ""
	@echo "=== BIRD eBGP (10.100.0.20, AS 65001) ==="
	@$(CONTAINER_CLI) exec bgpweb-bird birdc show protocols all gobgp_peer || true
	@echo ""
	@echo "=== BIRD iBGP 1 (10.100.0.30, AS 65000) ==="
	@$(CONTAINER_CLI) exec bgpweb-bird-ibgp1 birdc show protocols all gobgp_peer || true
	@echo ""
	@echo "=== BIRD iBGP 2 (10.100.0.40, AS 65000) ==="
	@$(CONTAINER_CLI) exec bgpweb-bird-ibgp2 birdc show protocols all gobgp_peer || true

bird-routes:
	@echo "=== BIRD eBGP Flowspec Routes ==="
	@$(CONTAINER_CLI) exec bgpweb-bird birdc show route table t_flow4 all || true
	@echo ""
	@echo "=== BIRD iBGP 1 Flowspec Routes ==="
	@$(CONTAINER_CLI) exec bgpweb-bird-ibgp1 birdc show route table t_flow4 all || true
	@echo ""
	@echo "=== BIRD iBGP 2 Flowspec Routes ==="
	@$(CONTAINER_CLI) exec bgpweb-bird-ibgp2 birdc show route table t_flow4 all || true

bird-unicast:
	@echo "=== BIRD eBGP Unicast Routes ==="
	@$(CONTAINER_CLI) exec bgpweb-bird birdc show route table t_unicast4 all || true
	@echo ""
	@echo "=== BIRD iBGP 1 Unicast Routes ==="
	@$(CONTAINER_CLI) exec bgpweb-bird-ibgp1 birdc show route table t_unicast4 all || true
	@echo ""
	@echo "=== BIRD iBGP 2 Unicast Routes ==="
	@$(CONTAINER_CLI) exec bgpweb-bird-ibgp2 birdc show route table t_unicast4 all || true

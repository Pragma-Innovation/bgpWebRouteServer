.PHONY: help test k8s-validate k8s-dev k8s-prod docker-build docker-up docker-down lab-up lab-down lab-status bird-routes bird-unicast test-integration

help:
	@echo "bgpWebRouteServer - Automation Commands:"
	@echo "  make test              - Run BGP backend contract test suite"
	@echo "  make k8s-validate      - Validate all Kubernetes manifests using kustomize"
	@echo "  make k8s-dev           - Deploy dev overlay to active Kubernetes cluster"
	@echo "  make k8s-prod          - Deploy prod overlay to active Kubernetes cluster"
	@echo "  make docker-build      - Build backend, frontend, and bird Docker images"
	@echo "  make docker-up         - Start local stack via Docker Compose"
	@echo "  make docker-down       - Stop local Docker Compose stack"
	@echo "  make lab-up            - Build & start full multi-peer lab (GoBGP + 3x BIRD + Django + UI)"
	@echo "  make lab-down          - Stop full lab"
	@echo "  make lab-status        - Display BGP session state across GoBGP and all 3 BIRD routers"
	@echo "  make bird-routes       - Query received Flowspec routes across all BIRD routers"
	@echo "  make bird-unicast      - Query received Unicast RTBH routes across all BIRD routers"
	@echo "  make test-integration  - Run automated end-to-end Flowspec & RTBH propagation test"

test:
	@echo "Running backend test suite..."
	cd backend && python3 -m unittest discover apps/bgp_engine/tests

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

docker-build:
	docker build -t bgpweb-backend:latest -f deploy/docker/backend.Dockerfile .
	docker build -t bgpweb-frontend:latest -f deploy/docker/frontend.Dockerfile .
	docker build -t bgpweb-bird:latest -f deploy/docker/bird.Dockerfile .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

lab-up:
	docker-compose up -d --build

lab-down:
	docker-compose down

lab-status:
	@echo "=== GoBGP Neighbors ==="
	@podman exec bgpweb-gobgp gobgp neighbor || docker-compose exec -T gobgp gobgp neighbor || true
	@echo ""
	@echo "=== BIRD eBGP (10.100.0.20, AS 65001) ==="
	@podman exec bgpweb-bird birdc show protocols all gobgp_peer || true
	@echo ""
	@echo "=== BIRD iBGP 1 (10.100.0.30, AS 65000) ==="
	@podman exec bgpweb-bird-ibgp1 birdc show protocols all gobgp_peer || true
	@echo ""
	@echo "=== BIRD iBGP 2 (10.100.0.40, AS 65000) ==="
	@podman exec bgpweb-bird-ibgp2 birdc show protocols all gobgp_peer || true

bird-routes:
	@echo "=== BIRD eBGP Flowspec Routes ==="
	@podman exec bgpweb-bird birdc show route table t_flow4 all || true
	@echo ""
	@echo "=== BIRD iBGP 1 Flowspec Routes ==="
	@podman exec bgpweb-bird-ibgp1 birdc show route table t_flow4 all || true
	@echo ""
	@echo "=== BIRD iBGP 2 Flowspec Routes ==="
	@podman exec bgpweb-bird-ibgp2 birdc show route table t_flow4 all || true

bird-unicast:
	@echo "=== BIRD eBGP Unicast Routes ==="
	@podman exec bgpweb-bird birdc show route table t_unicast4 all || true
	@echo ""
	@echo "=== BIRD iBGP 1 Unicast Routes ==="
	@podman exec bgpweb-bird-ibgp1 birdc show route table t_unicast4 all || true
	@echo ""
	@echo "=== BIRD iBGP 2 Unicast Routes ==="
	@podman exec bgpweb-bird-ibgp2 birdc show route table t_unicast4 all || true

test-integration:
	python3 tests/integration/test_ebgp_flowspec_propagation.py

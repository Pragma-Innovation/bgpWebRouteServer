.PHONY: help test k8s-validate k8s-dev k8s-prod docker-build docker-up docker-down lab-up lab-down lab-status bird-routes bird-unicast test-integration

help:
	@echo "bgpWebRouteServer - Automation Commands:"
	@echo "  make test              - Run BGP backend contract test suite"
	@echo "  make k8s-validate      - Validate all Kubernetes manifests using kustomize"
	@echo "  make k8s-dev           - Deploy dev overlay to active Kubernetes cluster"
	@echo "  make k8s-prod          - Deploy prod overlay to active Kubernetes cluster"
	@echo "  make docker-build      - Build backend, frontend, and gobgp Docker images"
	@echo "  make docker-up         - Start local stack via Docker Compose"
	@echo "  make docker-down       - Stop local Docker Compose stack"
	@echo "  make lab-up            - Build & start full eBGP lab (GoBGP + BIRD 3 + Django + UI)"
	@echo "  make lab-down          - Stop full eBGP lab"
	@echo "  make lab-status        - Display BGP session state across GoBGP and BIRD"
	@echo "  make bird-routes       - Query BIRD 3 received Flowspec routes (table t_flow4)"
	@echo "  make bird-unicast      - Query BIRD 3 received Unicast routes (table t_unicast4)"
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
	@docker-compose exec -T gobgp gobgp neighbor || true
	@echo ""
	@echo "=== BIRD 3 Protocols ==="
	@docker-compose exec -T bird birdc show protocols all gobgp_peer || true

bird-routes:
	@docker-compose exec -T bird birdc show route table t_flow4 all

test-integration:
	python3 tests/integration/test_ebgp_flowspec_propagation.py

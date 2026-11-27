# AGENTS.md — Development & Operational Guidelines for bgpWebRouteServer

Welcome to the **bgpWebRouteServer** project ("Gabu"). This file defines the core architectural principles, modularity requirements, coding standards, containerization rules, and operational workflows for AI agents and human developers collaborating on this repository.

---

## 1. Project Mission & Context

* **Project Objective:** Modernize and re-architect the legacy Go + Qt application [bgpflowspectool](https://github.com/Pragma-Innovation/bgpflowspectool) into an enterprise-grade multi-AFI/SAFI BGP Route Server and traffic mitigation platform.
* **Target Architecture:**
  * **Frontend:** Vue 3 SPA using Composition API (`<script setup lang="ts">`), Vite, Pinia, TypeScript, and responsive styling.
  * **Backend:** Python 3 + Django 5.2 LTS + Django REST Framework (DRF) with JWT auth and Role-Based Access Control (`Admin`, `Operator`, `Viewer`).
  * **Database:** PostgreSQL 16 utilizing native network types (`CIDR`, `INET`) and `JSONB` for flexible BGP attributes.
  * **BGP Engine:** Multi-vendor, pluggable BGP abstraction layer with a unified backend interface (`BaseBgpBackend`), providing a concrete GoBGP v3 gRPC driver and BIRD 3 peer integration.
  * **Multi-AFI Scope:** IPv4 Unicast, IPv6 Unicast, IPv4 Flowspec, and IPv6 Flowspec.
  * **Cloud-Native & Kubernetes:** 12-factor containerized architecture running in Docker Compose and Kubernetes with multi-stage Dockerfiles and non-root security contexts.

---

## 2. Directory Layout & App Architecture

```text
bgpWebRouteServer/
├── README.md                       # Project overview, dedication, and quickstart guide
├── SPECS.md                        # Authoritative functional & technical specifications
├── AGENTS.md                       # Agent operational rules & workflows (this file)
├── docker-compose.yml              # Shared core services (db, backend, peer-syncer, gobgp, frontend)
├── docker-compose.dev.yml          # Dev & Lab overlay (HMR, bind-mounts, demo seeds, 3x BIRD routers)
├── docker-compose.prod.yml         # Hardened Production overlay (Nginx, Gunicorn, TCP/179, no demo data)
├── .env.example                    # Developer environment template
├── .env.prod.example               # Production environment template
├── Makefile                        # Canonical operational commands (auto-detects podman vs docker)
├── deploy/                         # Multi-stage Dockerfiles & Kubernetes manifests
│   ├── docker/                     # Dockerfiles (backend, frontend, bird, gobgp)
│   └── k8s/                        # Base manifests & Kustomize overlays (dev/prod)
├── backend/                        # Django REST Framework backend service
│   ├── entrypoint.sh               # Automated DB wait, migrate, RBAC/superuser & starter profile bootstrap
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                     # Settings (base.py, development.py, production.py), urls, asgi
│   └── apps/                       # Modular Django domain apps
│       ├── prefixes/               # Unified IPv4 & IPv6 Prefix Inventory & RIPEstat discovery
│       │   ├── models.py           # IpPrefix (PostgreSQL CIDRField)
│       │   ├── services/           # AsnDiscoveryService (fast bulk_create RIPEstat import)
│       │   ├── views.py            # IpPrefixViewSet with server pagination & filtering
│       │   └── management/         # import_asn_prefixes CLI command
│       ├── routing/                # Hierarchical Routing Engine
│       │   ├── models.py           # PseudoRib (Policy), Rib (Master), Announcement (Loc-RIB)
│       │   └── views.py            # PseudoRibViewSet, RibViewSet (push action), Announcements
│       ├── flowspec/               # BGP Flowspec rules management (RFC 5575 / RFC 8955)
│       │   ├── models.py           # FlowspecRule (15 match criteria + action types)
│       │   └── views.py            # FlowspecRuleViewSet
│       ├── peers/                  # BGP Neighbors, Peering Sessions & Global Router Identity
│       │   ├── models.py           # BgpGlobalConfig (singleton), BgpPeerConfig
│       │   ├── serializers.py      # BgpGlobalConfigSerializer, BgpPeerConfigSerializer
│       │   ├── services.py         # PeerReconciliationService (unified session consolidation & active reconcile)
│       │   ├── management/         # run_peer_syncer daemon CLI command
│       │   └── views.py            # BgpGlobalConfigView, BgpPeerConfigViewSet (sessions, reconcile, adopt, reset)
│       └── bgp_engine/             # Pluggable BGP Abstraction & Drivers
│           ├── base.py             # BaseBgpBackend (Abstract Base Class with peer methods)
│           ├── manager.py          # BgpManager factory
│           ├── permissions.py      # IsOperatorOrReadOnly, IsAdminOrReadOnly RBAC permissions
│           └── backends/           # Drivers: gobgp/ (gRPC & config writer), bird/, mock/
├── web/                            # Frontend Vue 3 Single Page Application
│   ├── index.html
│   ├── vite.config.ts
│   └── src/
│       ├── api/client.ts           # Axios client configured with JWT interceptor
│       ├── stores/                 # Pinia stores (prefixStore, routingStore, flowspecStore, bgpStore)
│       ├── views/                  # PrefixInventoryView, FlowspecView, RoutingWorkflowView, AnnouncementsView, PeersView
│       └── components/             # GlobalConfigModal, PeerModal, RuleBuilderModal, StatusBadge
├── configs/                        # GoBGP and BIRD 3 (eBGP & 2x iBGP) configuration files
└── tests/                          # Integration test suites
    └── integration/                # test_ebgp_flowspec_propagation.py
```

---

## 3. Core Development Invariants for AI Agents

### Invariant 1: Maintain the 3-Tier Routing Hierarchy
Never inject routes or Flowspec rules directly into the BGP stack without associating them with a policy container:
$$\text{Route Asset (Prefix / Flowspec Rule)} \longrightarrow \text{Pseudo-RIB (Route Profile)} \longrightarrow \text{Master RIB} \longrightarrow \text{Router Loc-RIB}$$
* A **Pseudo-RIB** contains the routing attributes (Communities, Next-Hop, Local-Pref, MED).
* The **Master RIB** aggregates Pseudo-RIBs and reconciles state with GoBGP.
* The **Announcement** model reflects what is confirmed active in the router's Loc-RIB.

### Invariant 2: Type Safety Across Address Families
* An IPv4 Unicast Pseudo-RIB can only attach IPv4 prefixes (`ip_version=4`).
* An IPv6 Unicast Pseudo-RIB can only attach IPv6 prefixes (`ip_version=6`).
* Flowspec Pseudo-RIBs can only attach Flowspec rules.
* Unicast Pseudo-RIBs must reject Flowspec rules, and vice versa.

### Invariant 3: Zero Protocol Leaks in Upper Layers
* Serializers, ViewSets, and models must **never** import `grpcio`, GoBGP protobufs, or stack-specific sockets.
* All BGP communications must pass exclusively through `BgpManager.get_active_backend()`.

### Invariant 4: PostgreSQL Native Network Types
* Network subnets must be stored using PostgreSQL `CIDR` columns (via `django.contrib.postgres.fields.CIDRField`).
* All user-supplied subnets must be normalized through `ipaddress.ip_network(prefix, strict=False)` in model `clean()` and `save()` methods.

### Invariant 5: Bulk Ingestion Performance
* When importing prefixes from external registries (e.g. RIPEstat), **never** execute sequential `get_or_create` loops for thousands of items.
* Always use `bulk_create(batch, batch_size=1000, ignore_conflicts=True)` after deduplicating in memory.

### Invariant 6: Server-Side Filtering & Pagination
* The prefix inventory and announcement tables contain thousands of routes.
* Filtering (`ip_version=4/6`, `search=`, `asn=`) and pagination (`page=`, `page_size=`) MUST occur server-side in Django. Never filter large datasets exclusively in Vue memory.

### Invariant 7: Documentation in Lockstep (Mandatory for All AI Agents)
Every code change (new feature, bug fix, model change, API parameter, CLI option, or architectural adjustment) **MUST be reflected in the documentation in the exact same turn/commit**:
1. **[`SPECS.md`](file:///home/mtexier/projects/bgpWebRouteServer/SPECS.md)**: Update schemas, field types, model relationships, RFC references, algorithmic details, and API endpoint contracts whenever backend, data-model, or routing behaviors are added or altered.
2. **[`README.md`](file:///home/mtexier/projects/bgpWebRouteServer/README.md)**: Update architecture diagrams, capabilities, quickstart instructions, or operational commands whenever user-facing or deployment behaviors change.
3. **[`AGENTS.md`](file:///home/mtexier/projects/bgpWebRouteServer/AGENTS.md)**: Update agent operational rules, container execution commands, or invariants whenever development patterns evolve.
*Rule of thumb for AI agents:* **A coding task is NEVER complete until the code, the unit/integration tests, AND the corresponding documentation files are updated and verified in lockstep.** Never defer documentation updates to a future task.

---

## 4. Operational & Execution Guidelines

### Running Tests in Local Environment
The local development environment uses rootless Podman / Docker. AI agents must execute commands inside running containers:

```bash
# 1. Start Developer + Multi-Peer Lab stack (auto-migrates & seeds lab):
make dev-up

# 2. Run all Django backend unit tests:
make test-backend

# 3. Run the automated eBGP + 2x iBGP integration test:
make test-integration

# 4. Verify TypeScript and compile frontend bundle:
podman exec bgpweb-frontend npm run build

# 5. Start hardened Production stack (after configuring .env from .env.prod.example):
make prod-up
```

### Checking BGP Peering and Route Tables
```bash
# Check BGP session state:
make lab-status

# Check routes received in BIRD 3:
make bird-unicast   # Table t_unicast4 (RTBH routes)
make bird-routes    # Table t_flow4 (Flowspec rules)
```

### Sandboxing & Command Execution Rules
* Commands invoking `podman` or `docker` require `BypassSandbox: true` because rootless container sockets reside outside the standard agent sandbox.
* Preparation, file edits, and git status checks must run inside the standard sandbox (`BypassSandbox: false`).

---

## 5. References

* **[`README.md`](file:///home/mtexier/projects/bgpWebRouteServer/README.md)**: System overview, history, tribute to Frédéric Gabut-Deloraine, and quickstart.
* **[`SPECS.md`](file:///home/mtexier/projects/bgpWebRouteServer/SPECS.md)**: Exhaustive functional and technical specifications, data models, RFC compliance, and API reference.

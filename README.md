# bgpWebRouteServer — "Gabu"

> **Enterprise-Grade Multi-AFI/SAFI BGP Route Server & Traffic Mitigation Platform**  
> Supporting BGP Flowspec (RFC 5575 / RFC 8955), Remotely Triggered Blackhole (RTBH RFC 7999), IPv4 & IPv6 Unicast Routing, RIPEstat ASN Discovery, and Pluggable BGP Stacks.

---

## Tool Name and Special Dédicace

This tool is named **"Gabu"** in memory of **Frédéric Gabut-Deloraine**.

"Gabu" is the nickname of a brilliant young French network engineer who passed away way too early and is deeply missed by anyone who ever crossed his path. Frédéric was a pioneer in advocating for open, programmable routing protocols and community-driven network security in France.

To enjoy a classic and inspiring presentation given by Frédéric Gabut-Deloraine on leveraging BGP Flowspec for large-scale DDoS mitigation, please watch his FRnOG conference talk:
* **[Frédéric Gabut-Deloraine — FRnOG 18: BGP Flowspec for DDoS Mitigation](http://www.dailymotion.com/video/xtngjg_frnog-18-flowspec-frederic-gabut-deloraine-neo-telecoms_tech)**

This modern implementation carries forward his vision into a production-ready, cloud-native architecture.

---

## Introduction

**bgpWebRouteServer** is developed to help network engineers, internet service providers (ISPs), and data center operators effectively manage undesirable traffic passing through their backbone, transit, and peering links.

The platform provides a modern, intuitive Single Page Application (SPA) backed by a robust REST API to control advanced routing features:
* **Traffic Filtering with BGP Flowspec** (RFC 5575 & RFC 8955 for IPv4 and IPv6).
* **Malicious Traffic Mitigation with BGP Blackholing** (Remotely Triggered Blackhole — RTBH RFC 7999).
* **Unified IP Prefix Asset Inventory** backed by native PostgreSQL `CIDR` indexing.
* **Automated Prefix Discovery** via public RIPEstat and RPKI routing registries.
* **Hierarchical Policy Management** through **Pseudo-RIBs** (Route Profiles) and **Master RIB** reconciliation.
* **Real-Time Loc-RIB Synchronization** and multi-AFI route monitoring across peering partners.

---

## Evolution: From Desktop Prototype to Cloud-Native Platform

This project represents the complete architectural modernization of the original Go + Qt prototype [bgpflowspectool](https://github.com/Pragma-Innovation/bgpflowspectool):

| Feature | Legacy Prototype (`bgpflowspectool`) | Modern Platform (`bgpWebRouteServer`) |
|---|---|---|
| **User Interface** | Go + Qt5 desktop UI (`therecipe/qt`) requiring X11 display | Modern responsive Vue 3 SPA (Vite, Pinia, TypeScript, Tailwind) accessible from any browser |
| **Data Storage** | Local flat JSON `.fslib` files on disk | Relational PostgreSQL 16 with native network data types (`CIDR`, `INET`, `JSONB`) |
| **API Layer** | None (direct in-process gRPC calls) | Comprehensive Django 5.2 LTS REST Framework API with JWT auth and RBAC |
| **AFI/SAFI Scope** | IPv4 Flowspec only | **Multi-AFI/SAFI**: IPv4 Unicast, IPv6 Unicast, IPv4 Flowspec, IPv6 Flowspec |
| **Routing Concept** | Flat, direct rule injection to GoBGP | **Hierarchical Workflow**: Route Assets $\rightarrow$ Pseudo-RIB (Policy) $\rightarrow$ Master RIB $\rightarrow$ Router Loc-RIB |
| **Asset Discovery** | Manual entry only | Automated ASN prefix discovery from RIPEstat / RPKI (IPv4 & IPv6 selective) |
| **BGP Stack Support** | Hardcoded GoBGP local daemon | Pluggable multi-vendor engine (`BaseBgpBackend`) supporting **GoBGP**, **BIRD 3**, **FRR**, and **ExaBGP** |
| **Deployment** | Bare-metal manual build with 8 GB Qt toolchain | Containerized 12-factor architecture with Docker Compose and Kubernetes manifests |

---

## Architecture Overview

`bgpWebRouteServer` is architected as a centralized BGP controller and Route Server:

```mermaid
flowchart TD
    subgraph Client["Presentation Tier"]
        UI["Vue 3 SPA<br/>(TypeScript / Pinia / Vite)"]
    end

    subgraph Backend["Application Tier (Django 5.2 LTS / DRF)"]
        API["REST API & RBAC<br/>(Admin / Operator / Viewer)"]
        PrefixSvc["ASN Discovery Service<br/>(RIPEstat / RPKI API)"]
        RoutingSvc["Routing Engine<br/>(Pseudo-RIB & Master RIB Sync)"]
        BgpManager["BgpManager Abstraction<br/>(Pluggable Stack Drivers)"]
    end

    subgraph Storage["Data Tier"]
        DB[("PostgreSQL 16<br/>(Native CIDR / JSONB)")]
    end

    subgraph Controller["BGP Route Server Engine"]
        GoBGP["GoBGP v3 Daemon<br/>(Primary Route Server / Controller)"]
    end

    subgraph Network["Network Routers (iBGP / eBGP Peering)"]
        subgraph Production["Production Network"]
            R1["Edge / Border Routers"]
            R2["Core / Transit Routers"]
            R3["Data Center Gateways"]
        end
        subgraph TestLab["Local Development & Testing Lab"]
            BIRD_E["BIRD 3 eBGP Router<br/>(10.100.0.20, AS 65001)"]
            BIRD_I1["BIRD 3 iBGP Core 1<br/>(10.100.0.30, AS 65000)"]
            BIRD_I2["BIRD 3 iBGP Core 2<br/>(10.100.0.40, AS 65000)"]
        end
    end

    UI <-->|HTTPS / REST API| API
    API <--> RoutingSvc
    API <--> PrefixSvc
    API <--> DB
    RoutingSvc <--> DB
    RoutingSvc --> BgpManager
    BgpManager <-->|gRPC :50051| GoBGP
    GoBGP -.->|Production: iBGP / eBGP TCP 179| Production
    GoBGP <-->|Test Lab: eBGP TCP 179| BIRD_E
    GoBGP <-->|Test Lab: iBGP TCP 179| BIRD_I1
    GoBGP <-->|Test Lab: iBGP TCP 179| BIRD_I2
```

### Production Deployment vs. Local Test Lab

* **In Production**: GoBGP functions as the centralized BGP Route Server. It establishes BGP sessions using either **eBGP or iBGP** directly with the operator's actual network routers (Cisco, Juniper, Nokia, Arista, etc.) across the backbone, transit edges, and data center perimeters. When an operator triggers a Flowspec filter or an RTBH blackhole, GoBGP advertises the update across these BGP sessions, directing the physical routers to drop or rate-limit traffic at line rate.
* **In the Local Test Lab**: To allow continuous automated testing without requiring physical network hardware, **3 containerized BIRD 3 routers** emulate a realistic multi-peer network:
  * **1x eBGP Edge Peer (`bgpweb-bird`)**: AS 65001 @ `10.100.0.20`
  * **2x iBGP Core Peers (`bgpweb-bird-ibgp1`, `bgpweb-bird-ibgp2`)**: AS 65000 @ `10.100.0.30` and `10.100.0.40`
  * **Resource Efficiency**: BIRD 3 is exceptionally lightweight (written in C), with each container consuming only ~3–4 MB of RAM (total ~11 MB across all 3 routers), having zero impact on developer machines while validating multi-peer eBGP and iBGP distribution simultaneously. The automated integration test suite (`make test-integration`) verifies that Flowspec rules (`t_flow4`) and RTBH routes (`t_unicast4`) propagate and withdraw synchronously across all three peer routers.

### The Hierarchical Routing Model

To prevent accidental route injection and maintain strict operational control over backbone routing tables, `bgpWebRouteServer` implements a three-tier routing hierarchy:

1. **Route Assets (Inventory)**:
   * **IP Prefixes** (`apps.prefixes`): Network subnets discovered via ASN queries or added manually.
   * **Flowspec Rules** (`apps.flowspec`): Granular L3/L4 match criteria (protocol, ports, TCP flags, ICMP) and mitigation actions (`discard`, `rate-limit`, `redirect`, `mark`).
2. **Pseudo-RIBs / Route Profiles** (`apps.routing.PseudoRib`):
   * Reusable policy containers grouping routes that share identical BGP attributes (AFI/SAFI, Next-Hop, standard communities like `65535:666`, extended communities, large communities, local-preference, and MED).
3. **Master RIB** (`apps.routing.Rib`):
   * Groups one or more Pseudo-RIBs representing the cohesive routing table to program into the BGP stack.
   * Pushing the Master RIB evaluates diffs, programs new routes, and automatically withdraws obsolete routes.
4. **Loc-RIB Announcements** (`apps.routing.Announcement`):
   * Live synchronized table showing every route programmed into the router across all AFI/SAFIs with full filtering capabilities.

---

## Key Capabilities

### 1. Unified IPv4 & IPv6 Prefix Inventory
* Native PostgreSQL `CIDR` column type enforcing network subnet boundaries and host-bit zeroing.
* Search by CIDR prefix, label, owner tag, or Autonomous System Number.
* 1-Click RTBH Blackhole action directly from the inventory table.

### 2. Automated ASN Prefix Discovery
* Queries public RIPEstat and RPKI tables to discover all active BGP announced prefixes for any ASN.
* Selective import flags (`import_v4` and `import_v6`).
* High-performance `bulk_create` batching: importing 1,500+ prefixes takes under 1 second.
* Granular CLI command: `python manage.py import_asn_prefixes <ASN> [--no-v4] [--no-v6] [--tag <TAG>]`.

### 3. Comprehensive BGP Flowspec Support (RFC 5575 / RFC 8955)
* Full support for 15 match criteria: destination prefix, source prefix, IP protocol, source/destination ports, ICMP type/code, TCP flags (SYN, ACK, FIN, RST), packet length, and DSCP.
* Actions: Discard (Drop), Rate-Limit (traffic-rate), Policy-Based Routing (Redirect VRF / Next-Hop), and DSCP Remarking.
* Backwards compatible `.fslib` JSON import/export commands (`import_fslib` and `export_fslib`).

### 4. Primary BGP Stack & Multi-Vendor Peering
* **GoBGP (Primary Production BGP Stack)**: GoBGP v3 is the first and primary BGP stack supported to interface with the operator's routers. It provides high-performance gRPC control, robust multi-AFI/SAFI routing tables, and acts as the Route Server establishing iBGP or eBGP peering sessions with the network devices.
* **BIRD 3 (Testing & Lab Emulation)**: BIRD 3 is included in the local environment specifically for testing and CI/CD validation. It simulates a peer router, verifying that advertised Flowspec rules and RTBH blackholes are received and applied as `RTD_BLACKHOLE` in external routing tables.
* **Extensible Driver Architecture**: The application interfaces with the routing daemon through the `BaseBgpBackend` abstraction layer, allowing future direct integration with alternative BGP engines (such as native BIRD, FRRouting, or ExaBGP) without touching frontend or API layers.

### 5. Backbone BGP Session Management & Continuous Reconciliation
* **Unified Single-View Dashboard**: A consolidated, single-table view displaying both database-configured BGP neighbors and live runtime-discovered sessions without disjoint UI tables.
* **Continuous Synchronization**: Automated background reconciliation loop (5-second reactive UI polling and background daemon task `run_peer_syncer`) keeping PostgreSQL intent and GoBGP memory continuously aligned.
* **Explicit Approval Workflow (Option 1)**: Discovered unmanaged peering sessions appear seamlessly alongside managed peers with a distinct `Discovered (Unmanaged)` badge, allowing operators to adopt them into persistent database configuration with 1-click.
* **Filter Tabs & Real-Time Search**: Quick filter tabs (`All Sessions`, `Managed`, `Discovered`, `Established`) with dynamic count badges and search filtering across IP addresses, ASNs, and names.
* **Dual Transport (IPv4 & IPv6)**: Supports IPv4 and IPv6 transport protocols for all peering sessions.
* **Automatic Session Type Inference**: Dynamically identifies internal (`iBGP`) vs. external (`eBGP`) sessions based on the speaker's Local ASN and remote peer ASN.
* **eBGP Multi-Hop Support**: Configurable IP TTL (1–255) for sessions spanning multiple IP hops, firewalls, or loopback interfaces.
* **TCP MD5 Authentication (RFC 2385)**: Optional cryptographic MD5 signature protection on TCP peering sockets.
* **Per-Peer Address Families**: Granular AFI/SAFI negotiation (`ipv4-unicast`, `ipv6-unicast`, `ipv4-flowspec`, `ipv6-flowspec`).
* **Session Lifecycle & Soft Reset (RFC 2918)**: Trigger on-demand soft route refreshes without session drop, alongside real-time FSM state tracking (`ESTABLISHED`, `ACTIVE`, `IDLE`) and prefix exchange telemetry.
* **Interactive Session Inspector**: Clicking any row reveals detailed session metrics: uptime, message counters (Rx/Tx), prefix exchange counters (Recv/Acc/Adv), and transport timers.
* **Persistent Configuration Synchronization**: Automatically writes runtime changes to GoBGP's static configuration (`configs/gobgp.yaml`) to ensure seamless restarts without configuration loss.

---

## Installation & Quickstart (Developer vs. Production)

Gabu uses layered Compose configurations (`docker-compose.yml` + `docker-compose.dev.yml` or `docker-compose.prod.yml`) and an automated container entrypoint (`backend/entrypoint.sh`) that initializes the database schema, RBAC roles, and starter profiles automatically on first boot. Both **Docker Compose** and **Podman (`podman-compose`)** are auto-detected by the `Makefile`.

### Prerequisites
* [Docker](https://docs.docker.com/get-docker/) & Docker Compose **or** [Podman](https://podman.io/) (with `podman-compose`).
* Python 3.10+ (optional, for running the host-side integration test script).

---

### Option A: Developer & Multi-Peer Lab Installation (1 Command)
Starts all **8 containers** (`db`, `backend` with live reload, `peer-syncer`, `frontend` Vite HMR, `gobgp`, and **3 simulated BIRD 3 routers**: 1x eBGP + 2x iBGP) and automatically migrates PostgreSQL, seeds demo accounts, starter Pseudo-RIB profiles, and the 3 lab BGP sessions:

```bash
git clone https://github.com/Pragma-Innovation/bgpWebRouteServer.git
cd bgpWebRouteServer

# Build, initialize DB & seeds, and start the full multi-peer lab
make dev-up
```

#### Developer Lab Endpoints & Demo Accounts
| Service | URL / Endpoint | Default Credentials | Description |
|---|---|---|---|
| **Web UI (Vite HMR)** | `http://localhost:5173` | `operator` / `bgppassword123` | Single Page Application (Dev mode) |
| **Django REST API** | `http://localhost:8000/api/v1/` | JWT or Session auth | REST API root |
| **Django Admin** | `http://localhost:8000/admin/` | `admin` / `bgppassword123` | System & user administration |
| **GoBGP gRPC** | `localhost:50051` | Internal / Lab | GoBGP management API |
| **eBGP Peering** | `10.100.0.10` ↔ `10.100.0.20` | TCP 179 | GoBGP (AS 65000) ↔ BIRD eBGP (AS 65001) |
| **iBGP Peering 1** | `10.100.0.10` ↔ `10.100.0.30` | TCP 179 | GoBGP (AS 65000) ↔ BIRD iBGP Core 1 (AS 65000) |
| **iBGP Peering 2** | `10.100.0.10` ↔ `10.100.0.40` | TCP 179 | GoBGP (AS 65000) ↔ BIRD iBGP Core 2 (AS 65000) |

#### Pre-Seeded Dev Lab RBAC Accounts
* **Admin** (`admin` / `bgppassword123`): Full administrative rights, user management, and BGP peer/router settings.
* **Operator** (`operator` / `bgppassword123`): Create/edit prefixes, manage Flowspec rules, configure Pseudo-RIBs, push Master RIB to GoBGP.
* **Viewer** (`viewer` / `bgppassword123`): Read-only monitoring of inventory, announcements, and peer states.

---

### Option B: Production Installation
Starts only the **5 hardened production services**:
1. **`frontend` (Unprivileged Nginx):** Serves the compiled Vue 3 static bundle and reverse-proxies `/api/` and `/admin/` to Gunicorn on a single port (`8080` by default, configurable via `GABU_HTTP_PORT`). Demo quick-login chips are stripped from the production build.
2. **`backend` (Gunicorn, non-root `appuser`):** Runs with `DEBUG=False`, migrates PostgreSQL automatically, bootstraps RBAC roles (`Admin`, `Operator`, `Viewer`), creates your initial `Admin` superuser from `.env`, initializes your Local ASN & Router ID, and seeds only the starter RTBH/Flowspec Pseudo-RIB templates on an empty database (no demo accounts, no lab BIRD peers).
3. **`peer-syncer`:** Background reconciliation daemon keeping PostgreSQL peer configurations and GoBGP synchronized.
4. **`gobgp`:** Production BGP speaker exposing TCP port `179` (`GABU_BGP_PORT`) to peer with your physical or virtual backbone routers.
5. **`db` (PostgreSQL 16):** Persistent relational database isolated on the internal container network.

```bash
git clone https://github.com/Pragma-Innovation/bgpWebRouteServer.git
cd bgpWebRouteServer

# 1. Prepare your production environment configuration
cp .env.prod.example .env
# Edit .env: set DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_SUPERUSER_PASSWORD,
# DJANGO_ALLOWED_HOSTS, BGP_LOCAL_AS, and BGP_ROUTER_ID.

# 2. Build and start the hardened production stack
make prod-up
```
Access Gabu at `http://<server-ip>:8080` (or port `80` if `GABU_HTTP_PORT=80` / behind TLS Ingress) and sign in with your configured `DJANGO_SUPERUSER_USERNAME`.

---

## Operational Commands (`Makefile`)

```bash
# Developer & Lab lifecycle
make dev-up            # Start Dev + 3x BIRD Lab stack (auto-migrates & seeds lab)
make dev-down          # Stop Dev + Lab stack
make seed-dev          # Manually re-seed demo accounts & 3 BIRD lab peers

# Production lifecycle
make prod-up           # Start hardened 5-service Production stack
make prod-down         # Stop Production stack
make init-db           # Manually run migrations, RBAC bootstrap, and starter profile seed

# Testing & BGP Lab Diagnostics
make test-backend      # Run full Django unit test suite inside backend container
make test-integration  # Run end-to-end Flowspec & RTBH propagation test across 3 BIRD routers
make lab-status        # Check BGP session status across GoBGP and all 3 BIRD routers
make bird-unicast      # Inspect BIRD 3 Unicast RTBH tables
make bird-routes       # Inspect BIRD 3 Flowspec tables

# Kubernetes
make k8s-validate      # Validate Kubernetes manifests & overlays via Kustomize
```

---

## Documentation Index

* **[`SPECS.md`](file:///home/mtexier/projects/bgpWebRouteServer/SPECS.md)**: Exhaustive functional and technical specifications, data models, RFC compliance contracts, and API reference.
* **[`AGENTS.md`](file:///home/mtexier/projects/bgpWebRouteServer/AGENTS.md)**: Development guidelines, coding conventions, architectural invariants, and workflow instructions for AI agents.
* **[`docker-compose.yml`](file:///home/mtexier/projects/bgpWebRouteServer/docker-compose.yml)** / **[`docker-compose.dev.yml`](file:///home/mtexier/projects/bgpWebRouteServer/docker-compose.dev.yml)** / **[`docker-compose.prod.yml`](file:///home/mtexier/projects/bgpWebRouteServer/docker-compose.prod.yml)**: Layered container orchestration topologies.
* **[`deploy/k8s/`](file:///home/mtexier/projects/bgpWebRouteServer/deploy/k8s/)**: Production-ready Kubernetes manifests with Kustomize overlays (`dev` / `prod`).

---

## Licensing

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](file:///home/mtexier/projects/bgpWebRouteServer/LICENSE) file for details.

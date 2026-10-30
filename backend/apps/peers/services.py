import logging
from typing import Dict, Any, List
from apps.bgp_engine.manager import BgpManager
from apps.bgp_engine.backends.gobgp.config_writer import GoBgpConfigWriter
from .models import BgpPeerConfig, BgpGlobalConfig
from .serializers import BgpPeerConfigSerializer

logger = logging.getLogger(__name__)


class PeerReconciliationService:
    """
    Continuous synchronization and reconciliation engine between
    Gabu's desired configuration (PostgreSQL) and observed runtime (GoBGP).
    """

    @classmethod
    def get_unified_sessions(cls) -> List[Dict[str, Any]]:
        """
        Consolidates configured peers in DB with live daemon neighbors into a single unified list.
        """
        global_cfg = BgpGlobalConfig.get_solo()
        local_as = global_cfg.local_as

        backend = BgpManager.get_active_backend()
        live_neighbors = backend.get_neighbors() or []

        # Map live neighbors by lowercase IP
        live_map = {}
        for nbr in live_neighbors:
            addr = (nbr.get("neighbor_address") or "").strip().lower()
            if addr:
                live_map[addr] = nbr

        configured_peers = BgpPeerConfig.objects.all()
        configured_addrs = set()
        sessions = []

        # 1. Process all configured peers (Desired State)
        for peer in configured_peers:
            addr_key = (peer.neighbor_address or "").strip().lower()
            configured_addrs.add(addr_key)
            live = live_map.get(addr_key)

            # Determine sync status
            if not peer.is_enabled:
                sync_status = "disabled"
                fsm_state = "DISABLED"
            elif live:
                fsm_state = live.get("state", "ACTIVE")
                if live.get("peer_as") and live.get("peer_as") != peer.peer_as:
                    sync_status = "drift"
                elif fsm_state == "ESTABLISHED":
                    sync_status = "in_sync"
                else:
                    sync_status = "connecting"
            else:
                fsm_state = "IDLE"
                sync_status = "offline"

            serialized_config = BgpPeerConfigSerializer(peer).data
            sessions.append({
                "neighbor_address": peer.neighbor_address,
                "ip_version": peer.ip_version,
                "peer_as": peer.peer_as,
                "session_type": peer.session_type,
                "description": peer.description,
                "origin": "managed",
                "is_managed": True,
                "sync_status": sync_status,
                "state": fsm_state,
                "config": serialized_config,
                "live": live,
                "uptime": live.get("uptime", 0) if live else 0,
                "prefixes_received": live.get("prefixes_received", 0) if live else 0,
                "prefixes_accepted": live.get("prefixes_accepted", 0) if live else 0,
                "prefixes_advertised": live.get("prefixes_advertised", 0) if live else 0,
                "messages_received": live.get("messages_received", 0) if live else 0,
                "messages_sent": live.get("messages_sent", 0) if live else 0,
            })

        # 2. Process discovered unmanaged neighbors (Observed Runtime only)
        for addr_key, live in live_map.items():
            if addr_key not in configured_addrs:
                peer_as = live.get("peer_as", 0)
                session_type = "iBGP" if peer_as == local_as else "eBGP"
                raw_addr = live.get("neighbor_address", addr_key)
                ip_version = 6 if ":" in raw_addr else 4

                sessions.append({
                    "neighbor_address": raw_addr,
                    "ip_version": ip_version,
                    "peer_as": peer_as,
                    "session_type": session_type,
                    "description": live.get("description", "Discovered BGP neighbor"),
                    "origin": "discovered",
                    "is_managed": False,
                    "sync_status": "discovered",
                    "state": live.get("state", "ACTIVE"),
                    "config": None,
                    "live": live,
                    "uptime": live.get("uptime", 0),
                    "prefixes_received": live.get("prefixes_received", 0),
                    "prefixes_accepted": live.get("prefixes_accepted", 0),
                    "prefixes_advertised": live.get("prefixes_advertised", 0),
                    "messages_received": live.get("messages_received", 0),
                    "messages_sent": live.get("messages_sent", 0),
                })

        # Sort by neighbor_address
        sessions.sort(key=lambda s: s.get("neighbor_address", ""))
        return sessions

    @classmethod
    def reconcile(cls) -> Dict[str, Any]:
        """
        Executes an active reconciliation cycle:
        Pushes any enabled DB peers missing from GoBGP runtime.
        Returns summary of reconciliation.
        """
        backend = BgpManager.get_active_backend()
        live_neighbors = backend.get_neighbors() or []
        live_addrs = {(n.get("neighbor_address") or "").strip().lower() for n in live_neighbors}

        configured_peers = BgpPeerConfig.objects.filter(is_enabled=True)
        pushed = []
        errors = []

        for peer in configured_peers:
            addr = (peer.neighbor_address or "").strip().lower()
            if addr not in live_addrs:
                try:
                    success = backend.add_peer(peer)
                    if success:
                        pushed.append(peer.neighbor_address)
                    else:
                        errors.append(f"Failed to add {peer.neighbor_address} to GoBGP")
                except Exception as e:
                    errors.append(f"Error adding {peer.neighbor_address}: {e}")

        # Update persistent gobgp.yaml
        GoBgpConfigWriter.sync_to_file()

        unified = cls.get_unified_sessions()
        managed_count = sum(1 for s in unified if s["is_managed"])
        discovered_count = sum(1 for s in unified if not s["is_managed"])

        return {
            "status": "success" if not errors else "partial",
            "pushed_to_gobgp": pushed,
            "errors": errors,
            "total_sessions": len(unified),
            "managed_count": managed_count,
            "discovered_count": discovered_count,
        }

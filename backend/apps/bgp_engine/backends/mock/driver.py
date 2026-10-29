import logging
import time
from typing import Any, Dict, List, Optional
from ...base import BaseBgpBackend

logger = logging.getLogger(__name__)


class MockBgpBackend(BaseBgpBackend):
    """
    In-memory simulated BGP stack driver for local development and offline CI testing.
    Requires no running daemons, root privileges, or network connectivity.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._connected = False
        self._start_time = time.time()
        self._mock_rules: Dict[str, Dict[str, Any]] = {}
        self._mock_unicast_routes: Dict[str, Dict[str, Any]] = {}
        self._mock_neighbors = [
            {
                "neighbor_address": "10.0.0.2",
                "peer_as": 65001,
                "state": "ESTABLISHED",
                "uptime": "03:45:12",
                "prefixes_received": 142,
                "prefixes_accepted": 142,
                "prefixes_advertised": 8,
                "description": "Upstream Transit A"
            },
            {
                "neighbor_address": "10.0.0.3",
                "peer_as": 65002,
                "state": "ESTABLISHED",
                "uptime": "01:12:08",
                "prefixes_received": 58,
                "prefixes_accepted": 58,
                "prefixes_advertised": 8,
                "description": "IXP Peering Router"
            },
            {
                "neighbor_address": "192.168.100.1",
                "peer_as": 65100,
                "state": "ACTIVE",
                "uptime": "never",
                "prefixes_received": 0,
                "prefixes_accepted": 0,
                "prefixes_advertised": 0,
                "description": "Backup Lab Edge"
            }
        ]

    def connect(self) -> bool:
        self._connected = True
        logger.info("[MockBgpBackend] Mock BGP engine initialized and ready.")
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info("[MockBgpBackend] Mock BGP engine disconnected.")

    def get_server_status(self) -> Dict[str, Any]:
        uptime_seconds = int(time.time() - self._start_time)
        return {
            "backend": "MockBgpBackend (Simulation Mode)",
            "ready": self._connected,
            "router_id": "10.0.0.1",
            "as_number": 65000,
            "uptime_seconds": uptime_seconds,
            "peers_count": len(self._mock_neighbors),
            "flowspec_rules_active": len(self._mock_rules),
            "version": "1.0.0-mock",
        }

    def get_neighbors(self) -> List[Dict[str, Any]]:
        return self._mock_neighbors

    def get_rib(self, family: str = "ipv4-flowspec") -> List[Dict[str, Any]]:
        if family in ("ipv4-unicast", "ipv6-unicast"):
            return [r for r in self._mock_unicast_routes.values() if r.get("afi_safi") == family]
        return list(self._mock_rules.values())

    def add_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        rule_id = rule.get("id") or str(len(self._mock_rules) + 1)
        self._mock_rules[rule_id] = rule
        logger.info(f"[MockBgpBackend] Injected Flowspec rule {rule_id}: {rule}")
        return True

    def delete_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        rule_id = rule.get("id")
        if rule_id and rule_id in self._mock_rules:
            del self._mock_rules[rule_id]
            logger.info(f"[MockBgpBackend] Withdrew Flowspec rule {rule_id}")
            return True
        return False

    def add_unicast_route(
        self,
        prefix: str,
        next_hop: Optional[str] = None,
        communities: Optional[List[str]] = None,
        large_communities: Optional[List[str]] = None,
        med: Optional[int] = None,
        local_pref: Optional[int] = None,
        as_path_prepend: Optional[str] = None,
        origin: str = "igp",
        afi_safi: str = "ipv4-unicast",
    ) -> bool:
        key = f"{afi_safi}:{prefix}"
        self._mock_unicast_routes[key] = {
            "prefix": prefix,
            "next_hop": next_hop,
            "communities": communities or [],
            "large_communities": large_communities or [],
            "med": med,
            "local_pref": local_pref,
            "as_path_prepend": as_path_prepend,
            "origin": origin,
            "afi_safi": afi_safi,
        }
        logger.info(f"[MockBgpBackend] Injected Unicast route {key} (Next-Hop: {next_hop}, Communities: {communities})")
        return True

    def delete_unicast_route(self, prefix: str, afi_safi: str = "ipv4-unicast") -> bool:
        key = f"{afi_safi}:{prefix}"
        if key in self._mock_unicast_routes:
            del self._mock_unicast_routes[key]
            logger.info(f"[MockBgpBackend] Withdrew Unicast route {key}")
            return True
        return False

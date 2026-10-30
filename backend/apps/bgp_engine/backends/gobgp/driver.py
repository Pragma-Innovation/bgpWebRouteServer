import logging
from typing import Any, Dict, List
try:
    from django.conf import settings
except ImportError:
    settings = None
from ...base import BaseBgpBackend
from .client import GoBgpClient

logger = logging.getLogger(__name__)


class GoBgpBackend(BaseBgpBackend):
    """
    GoBGP stack driver communicating over gRPC & gobgp CLI (https://github.com/osrg/gobgp).
    Handles channel lifecycle, connection retries, and Flowspec announcements.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = GoBgpClient(
            host=getattr(settings, "GOBGP_GRPC_HOST", "localhost"),
            port=getattr(settings, "GOBGP_GRPC_PORT", 50051),
            timeout=getattr(settings, "GOBGP_TIMEOUT_SECONDS", 10),
        )

    def connect(self) -> bool:
        """Attempt to establish gRPC connection to GoBGP."""
        return self.client.connect()

    def disconnect(self) -> None:
        self.client.close()

    def get_server_status(self) -> Dict[str, Any]:
        info = self.client.get_bgp_info()
        connected = info.get("connected", False)
        return {
            "backend": "GoBGP (https://github.com/osrg/gobgp)",
            "ready": connected,
            "target": self.client.target,
            "router_id": info.get("router_id", "10.100.0.10" if connected else "unknown"),
            "as_number": info.get("as_number", 65000 if connected else 0),
            "connected": connected,
            "message": "Connected to GoBGP daemon" if connected else "GoBGP daemon offline / connecting...",
        }

    def get_neighbors(self) -> List[Dict[str, Any]]:
        return self.client.list_peers()

    def get_rib(self, family: str = "ipv4-flowspec") -> List[Dict[str, Any]]:
        return self.client.get_rib(family)

    def add_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Constructs and injects a Flowspec NLRI into GoBGP's global table via AddPath.
        """
        if not self.client.is_connected() and not self.client.connect():
            logger.warning(
                f"[GoBgpBackend] Cannot inject Flowspec rule #{rule.get('id')}: "
                f"GoBGP daemon at {self.client.target} is offline."
            )
            return False

        success = self.client.add_flowspec_rule(rule)
        if success:
            logger.info(
                f"[GoBgpBackend] Injected Flowspec rule #{rule.get('id')} "
                f"({rule.get('action')} {rule.get('dst_prefix')}) into GoBGP global table."
            )
        return success

    def delete_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Withdraws a Flowspec NLRI from GoBGP's global table via DeletePath.
        """
        if not self.client.is_connected() and not self.client.connect():
            logger.warning(
                f"[GoBgpBackend] Cannot withdraw Flowspec rule #{rule.get('id')}: "
                f"GoBGP daemon at {self.client.target} is offline."
            )
            return False

        success = self.client.delete_flowspec_rule(rule)
        if success:
            logger.info(
                f"[GoBgpBackend] Withdrew Flowspec rule #{rule.get('id')} from GoBGP global table."
            )
        return success

    def add_unicast_route(
        self,
        prefix: str,
        next_hop: str = None,
        communities: List[str] = None,
        large_communities: List[str] = None,
        med: int = None,
        local_pref: int = None,
        as_path_prepend: str = None,
        origin: str = "igp",
        afi_safi: str = "ipv4-unicast",
    ) -> bool:
        if not self.client.is_connected() and not self.client.connect():
            logger.warning(f"[GoBgpBackend] Cannot add unicast route {prefix}: GoBGP daemon is offline.")
            return False

        return self.client.add_unicast_route(
            prefix=prefix,
            next_hop=next_hop,
            communities=communities,
            large_communities=large_communities,
            med=med,
            local_pref=local_pref,
            as_path_prepend=as_path_prepend,
            origin=origin,
            afi_safi=afi_safi,
        )

    def delete_unicast_route(self, prefix: str, afi_safi: str = "ipv4-unicast") -> bool:
        if not self.client.is_connected() and not self.client.connect():
            logger.warning(f"[GoBgpBackend] Cannot delete unicast route {prefix}: GoBGP daemon is offline.")
            return False

        return self.client.delete_unicast_route(prefix=prefix, afi_safi=afi_safi)

    def add_peer(self, peer: Any) -> bool:
        return self.client.add_peer(peer)

    def delete_peer(self, neighbor_address: str) -> bool:
        return self.client.delete_peer(neighbor_address)

    def update_peer(self, peer: Any) -> bool:
        return self.client.update_peer(peer)

    def reset_peer(self, neighbor_address: str, soft: bool = True) -> bool:
        return self.client.reset_peer(neighbor_address, soft=soft)

    def sync_all_peers(self) -> Dict[str, Any]:
        return self.client.sync_all_peers()

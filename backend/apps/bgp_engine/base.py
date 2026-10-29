from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseBgpBackend(ABC):
    """
    Abstract Base Class for pluggable BGP stack drivers (GoBGP, BIRD, FRR, ExaBGP).
    Higher-level application layers (views, serializers, models) must interact ONLY
    with this interface, ensuring zero leakage of vendor/protocol specifics.
    """

    def __init__(self, **kwargs):
        self.options = kwargs

    @abstractmethod
    def connect(self) -> bool:
        """Initialize connection or verify socket/API availability to the BGP daemon."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully close sessions, sockets, or gRPC channels."""
        pass

    @abstractmethod
    def get_server_status(self) -> Dict[str, Any]:
        """
        Return the global status of the BGP router daemon.
        Example return:
            {
                "backend": "GoBGP",
                "ready": True,
                "router_id": "10.0.0.1",
                "as_number": 65000,
                "uptime_seconds": 3600,
                "peers_count": 2,
                "flowspec_rules_active": 5
            }
        """
        pass

    @abstractmethod
    def get_neighbors(self) -> List[Dict[str, Any]]:
        """
        Return list of configured BGP neighbors and their current session state.
        Example item:
            {
                "neighbor_address": "10.0.0.2",
                "peer_as": 65001,
                "state": "ESTABLISHED",
                "uptime": "01:23:45",
                "prefixes_received": 12,
                "prefixes_accepted": 12,
                "prefixes_advertised": 4
            }
        """
        pass

    @abstractmethod
    def get_rib(self, family: str = "ipv4-flowspec") -> List[Dict[str, Any]]:
        """
        Return the Routing Information Base (RIB) entries for the specified AFI/SAFI family.
        """
        pass

    @abstractmethod
    def add_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Announce a BGP Flowspec rule into the BGP daemon's RIB.
        """
        pass

    @abstractmethod
    def delete_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Withdraw an active BGP Flowspec rule from the BGP daemon's RIB.
        """
        pass

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
        """
        Announce an IPv4 or IPv6 unicast route (e.g. RTBH Blackhole) into the BGP RIB.
        """
        return True

    def delete_unicast_route(self, prefix: str, afi_safi: str = "ipv4-unicast") -> bool:
        """
        Withdraw an IPv4 or IPv6 unicast route from the BGP RIB.
        """
        return True

import json
import logging
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional
try:
    from django.conf import settings
except ImportError:
    settings = None

logger = logging.getLogger(__name__)


class GoBgpClient:
    """
    Manages communication with the GoBGP v3 daemon via gRPC probe and gobgp CLI.
    Reference: https://github.com/osrg/gobgp
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        self.host = host or getattr(settings, "GOBGP_GRPC_HOST", "localhost")
        self.port = port or getattr(settings, "GOBGP_GRPC_PORT", 50051)
        self.timeout = timeout or getattr(settings, "GOBGP_TIMEOUT_SECONDS", 10)
        self.target = f"{self.host}:{self.port}"

        self._channel = None
        self._connected = False
        self._last_connect_attempt = 0
        self._gobgp_bin = shutil.which("gobgp") or "/usr/local/bin/gobgp"

    def connect(self) -> bool:
        """Establish insecure gRPC channel to GoBGP daemon."""
        now = time.time()
        if not self._connected and (now - self._last_connect_attempt) < 3.0:
            return False

        self._last_connect_attempt = now
        try:
            import grpc
            self._channel = grpc.insecure_channel(
                self.target,
                options=[
                    ("grpc.keepalive_time_ms", 30000),
                    ("grpc.keepalive_timeout_ms", 10000),
                ]
            )
            # Connectivity probe with short timeout
            grpc.channel_ready_future(self._channel).result(timeout=2)
            self._connected = True
            logger.info(f"[GoBgpClient] Connected to GoBGP gRPC endpoint at {self.target}")
            return True
        except ImportError:
            # If grpc module is absent, fallback to testing via CLI
            res = self._run_gobgp(["global"], timeout=2)
            if res is not None:
                self._connected = True
                return True
            logger.warning("[GoBgpClient] 'grpc' module not installed & CLI unreachable.")
            self._connected = False
            return False
        except Exception as e:
            logger.debug(f"[GoBgpClient] Could not reach GoBGP at {self.target}: {e}")
            self._connected = False
            return False

    def close(self) -> None:
        """Close gRPC channel."""
        if self._channel:
            try:
                self._channel.close()
            except Exception:
                pass
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _run_gobgp(self, args: List[str], timeout: Optional[int] = None) -> Optional[str]:
        """Execute a gobgp CLI command against the configured host/port."""
        cmd = [self._gobgp_bin, "-u", str(self.host), "-p", str(self.port), *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
            else:
                logger.debug(f"[GoBgpClient] Command {cmd} failed (rc={proc.returncode}): {proc.stderr}")
                return None
        except Exception as e:
            logger.debug(f"[GoBgpClient] Executing {cmd} raised: {e}")
            return None

    def get_bgp_info(self) -> Dict[str, Any]:
        """Query GoBGP global configuration and health status."""
        if not self._connected and not self.connect():
            return {
                "connected": False,
                "target": self.target,
                "error": "GoBGP daemon unreachable",
            }

        # Try query via gobgp -j global
        raw_json = self._run_gobgp(["-j", "global"])
        if raw_json:
            try:
                data = json.loads(raw_json)
                return {
                    "connected": True,
                    "target": self.target,
                    "router_id": data.get("router_id", "10.100.0.10"),
                    "as_number": data.get("asn", 65000),
                    "ready": True,
                }
            except Exception as e:
                logger.warning(f"[GoBgpClient] Failed to parse global JSON: {e}")

        # Fallback default info when channel is confirmed ready
        return {
            "connected": True,
            "target": self.target,
            "router_id": "10.100.0.10",
            "as_number": 65000,
            "ready": True,
        }

    def list_peers(self) -> List[Dict[str, Any]]:
        """Query list of peers and session states (ListPeer)."""
        if not self._connected and not self.connect():
            return []

        raw_json = self._run_gobgp(["-j", "neighbor"])
        if not raw_json:
            return []

        state_map = {
            0: "UNKNOWN",
            1: "IDLE",
            2: "CONNECT",
            3: "ACTIVE",
            4: "OPENSENT",
            5: "OPENCONFIRM",
            6: "ESTABLISHED",
        }

        peers = []
        try:
            data = json.loads(raw_json)
            if not isinstance(data, list):
                data = [data]

            for p in data:
                conf = p.get("conf", {})
                state = p.get("state", {})
                timers = p.get("timers", {})
                session_state_num = state.get("session_state", 0)
                state_str = state_map.get(session_state_num, "ACTIVE")

                prefixes_recv = 0
                prefixes_accepted = 0
                prefixes_adv = 0
                for af in p.get("afi_safis", []):
                    af_state = af.get("state", {})
                    prefixes_recv += af_state.get("prefixes", {}).get("received", 0)
                    prefixes_accepted += af_state.get("prefixes", {}).get("accepted", 0)
                    prefixes_adv += af_state.get("prefixes", {}).get("advertised", 0)

                peers.append({
                    "neighbor_address": conf.get("neighbor_address", ""),
                    "peer_as": conf.get("peer_as", 0),
                    "local_as": conf.get("local_as", 65000),
                    "state": state_str,
                    "router_id": state.get("router_id", conf.get("neighbor_address", "")),
                    "uptime": timers.get("state", {}).get("uptime", {}).get("seconds", 0),
                    "messages_received": state.get("messages", {}).get("received", {}).get("total", 0),
                    "messages_sent": state.get("messages", {}).get("sent", {}).get("total", 0),
                    "prefixes_received": prefixes_recv,
                    "prefixes_accepted": prefixes_accepted,
                    "prefixes_advertised": prefixes_adv,
                    "description": conf.get("description", "BGP Peer"),
                })
        except Exception as e:
            logger.error(f"[GoBgpClient] Failed to parse neighbor JSON: {e}")

        return peers

    def build_flowspec_args(self, rule: Dict[str, Any], action_type: str = "add") -> List[str]:
        """Translate Django Flowspec rule dict into gobgp global rib [add|del] match arguments."""
        addr_fam = rule.get("addr_fam", "IPv4")
        family_str = "ipv6-flowspec" if addr_fam == "IPv6" else "ipv4-flowspec"

        args = ["global", "rib", action_type, "match"]

        dst_prefix = rule.get("dst_prefix", "").strip()
        if dst_prefix:
            args.extend(["destination", dst_prefix])

        src_prefix = rule.get("src_prefix", "").strip()
        if src_prefix:
            args.extend(["source", src_prefix])

        proto_number = rule.get("proto_number", "").strip()
        if proto_number:
            proto_val = proto_number.replace("==", "").replace("=", "").strip()
            proto_map = {"6": "tcp", "17": "udp", "1": "icmp", "58": "ipv6-icmp"}
            args.extend(["protocol", proto_map.get(proto_val, proto_val)])

        dst_port = rule.get("dst_port", "").strip()
        if dst_port:
            port_val = dst_port if dst_port.startswith("==") else f"=={dst_port}"
            args.extend(["destination-port", port_val])

        src_port = rule.get("src_port", "").strip()
        if src_port:
            port_val = src_port if src_port.startswith("==") else f"=={src_port}"
            args.extend(["source-port", port_val])

        tcp_flags = rule.get("tcp_flags", "").strip()
        if tcp_flags:
            args.extend(["tcp-flags", tcp_flags])

        icmp_type = rule.get("icmp_type", "").strip()
        if icmp_type:
            args.extend(["icmp-type", icmp_type])

        icmp_code = rule.get("icmp_code", "").strip()
        if icmp_code:
            args.extend(["icmp-code", icmp_code])

        packet_len = rule.get("packet_len", "").strip()
        if packet_len:
            args.extend(["packet-length", packet_len])

        dscp = rule.get("dscp", "").strip()
        if dscp:
            args.extend(["dscp", dscp])

        # Then actions
        args.append("then")
        action = rule.get("action", "Drop")
        action_val = str(rule.get("action_value", "")).strip()

        if action == "Drop":
            args.append("discard")
        elif action == "Shape":
            rate = action_val or "0"
            args.extend(["rate-limit", rate])
        elif action == "Redirect":
            args.extend(["redirect", action_val or "10.0.0.1"])
        elif action == "Mark":
            args.extend(["mark", action_val or "0"])
        else:
            args.append("discard")

        args.extend(["-a", family_str])
        return args

    def add_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        """Inject Flowspec rule into GoBGP global table."""
        if not self._connected and not self.connect():
            logger.warning(f"[GoBgpClient] Cannot add rule: GoBGP at {self.target} is unreachable.")
            return False

        args = self.build_flowspec_args(rule, action_type="add")
        res = self._run_gobgp(args)
        if res is not None:
            logger.info(f"[GoBgpClient] Successfully injected Flowspec rule #{rule.get('id')}")
            return True
        logger.error(f"[GoBgpClient] Failed to inject Flowspec rule #{rule.get('id')} with args: {args}")
        return False

    def delete_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        """Withdraw Flowspec rule from GoBGP global table."""
        if not self._connected and not self.connect():
            logger.warning(f"[GoBgpClient] Cannot delete rule: GoBGP at {self.target} is unreachable.")
            return False

        args = self.build_flowspec_args(rule, action_type="del")
        res = self._run_gobgp(args)
        if res is not None:
            logger.info(f"[GoBgpClient] Successfully withdrew Flowspec rule #{rule.get('id')}")
            return True
        logger.error(f"[GoBgpClient] Failed to withdraw Flowspec rule #{rule.get('id')} with args: {args}")
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
        """Inject an IPv4 or IPv6 unicast route (e.g. RTBH Blackhole) into GoBGP global table."""
        if not self._connected and not self.connect():
            logger.warning(f"[GoBgpClient] Cannot add unicast route: GoBGP at {self.target} is unreachable.")
            return False

        family_arg = "ipv6" if "ipv6" in afi_safi else "ipv4"
        cmd_args = ["global", "rib", "add", prefix, "-a", family_arg]

        if next_hop:
            cmd_args.extend(["nexthop", next_hop])
        if communities:
            cmd_args.extend(["community", ",".join(communities)])
        if large_communities:
            cmd_args.extend(["large-community", ",".join(large_communities)])
        if med is not None:
            cmd_args.extend(["med", str(med)])
        if local_pref is not None:
            cmd_args.extend(["local-pref", str(local_pref)])
        if as_path_prepend:
            cmd_args.extend(["as-path", as_path_prepend])
        if origin:
            cmd_args.extend(["origin", origin])

        res = self._run_gobgp(cmd_args)
        if res is not None:
            logger.info(f"[GoBgpClient] Successfully injected unicast route {prefix} into {family_arg}")
            return True
        logger.error(f"[GoBgpClient] Failed to inject unicast route {prefix} with args: {cmd_args}")
        return False

    def delete_unicast_route(self, prefix: str, afi_safi: str = "ipv4-unicast") -> bool:
        """Withdraw an IPv4 or IPv6 unicast route from GoBGP global table."""
        if not self._connected and not self.connect():
            logger.warning(f"[GoBgpClient] Cannot delete unicast route: GoBGP at {self.target} is unreachable.")
            return False

        family_arg = "ipv6" if "ipv6" in afi_safi else "ipv4"
        cmd_args = ["global", "rib", "del", prefix, "-a", family_arg]
        res = self._run_gobgp(cmd_args)
        if res is not None:
            logger.info(f"[GoBgpClient] Successfully withdrew unicast route {prefix} from {family_arg}")
            return True
        logger.error(f"[GoBgpClient] Failed to withdraw unicast route {prefix} with args: {cmd_args}")
        return False

    def get_rib(self, family: str = "ipv4-flowspec") -> List[Dict[str, Any]]:
        """Query routes from global RIB."""
        if not self._connected and not self.connect():
            return []

        raw_json = self._run_gobgp(["-j", "global", "rib", "-a", family])
        if not raw_json:
            return []

        try:
            data = json.loads(raw_json)
            if isinstance(data, dict):
                routes = []
                for prefix_key, paths in data.items():
                    if isinstance(paths, list):
                        for p in paths:
                            if isinstance(p, dict):
                                item = dict(p)
                                item["prefix"] = prefix_key
                                routes.append(item)
                            else:
                                routes.append({"prefix": prefix_key, "data": p})
                    else:
                        routes.append({"prefix": prefix_key, "data": paths})
                return routes
            elif isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def add_peer(self, peer: Any) -> bool:
        """Dynamically add or replace a BGP neighbor in the running GoBGP daemon."""
        from .config_writer import GoBgpConfigWriter

        if isinstance(peer, dict):
            neighbor_addr = str(peer.get("neighbor_address", ""))
            peer_as = peer.get("peer_as", 0)
            multihop = peer.get("multihop_enabled", False)
            multihop_ttl = peer.get("multihop_ttl", 255) or 255
            families = peer.get("families", [])
            session_type = peer.get("session_type", "")
        else:
            neighbor_addr = str(getattr(peer, "neighbor_address", ""))
            peer_as = getattr(peer, "peer_as", 0)
            multihop = getattr(peer, "multihop_enabled", False)
            multihop_ttl = getattr(peer, "multihop_ttl", 255) or 255
            families = getattr(peer, "families", [])
            session_type = getattr(peer, "session_type", "")

        # First remove if already present in runtime
        self._run_gobgp(["neighbor", "del", neighbor_addr])

        cmd = ["neighbor", "add", neighbor_addr, "as", str(peer_as)]
        if multihop or session_type == "eBGP":
            cmd.extend(["ebgp-multihop-ttl", str(multihop_ttl)])
        if families:
            cmd.extend(["family", ",".join(families)])

        res = self._run_gobgp(cmd)
        GoBgpConfigWriter.sync_to_file()

        if res is not None:
            logger.info(f"[GoBgpClient] Successfully added BGP peer {neighbor_addr} (AS{peer_as})")
            return True
        logger.error(f"[GoBgpClient] Failed to add BGP peer {neighbor_addr} with args: {cmd}")
        return False

    def delete_peer(self, neighbor_address: str) -> bool:
        """Remove a BGP neighbor from the running GoBGP daemon."""
        from .config_writer import GoBgpConfigWriter

        res = self._run_gobgp(["neighbor", "del", neighbor_address])
        GoBgpConfigWriter.sync_to_file()
        if res is not None:
            logger.info(f"[GoBgpClient] Successfully deleted BGP peer {neighbor_address}")
            return True
        logger.error(f"[GoBgpClient] Failed to delete BGP peer {neighbor_address}")
        return False

    def update_peer(self, peer: Any) -> bool:
        """Update an existing BGP neighbor."""
        return self.add_peer(peer)

    def reset_peer(self, neighbor_address: str, soft: bool = True) -> bool:
        """Trigger soft or hard session reset for a BGP neighbor."""
        if soft:
            res = self._run_gobgp(["neighbor", neighbor_address, "softreset"])
        else:
            self._run_gobgp(["neighbor", neighbor_address, "reset"])
            time.sleep(0.5)
            res = self._run_gobgp(["neighbor", neighbor_address, "enable"])

        return res is not None

    def sync_all_peers(self) -> Dict[str, Any]:
        """Reconcile all enabled peers from the database to GoBGP and write config file."""
        from apps.peers.models import BgpPeerConfig
        from .config_writer import GoBgpConfigWriter

        peers = BgpPeerConfig.objects.filter(is_enabled=True)
        synced = 0
        for peer in peers:
            if self.add_peer(peer):
                synced += 1

        GoBgpConfigWriter.sync_to_file()
        return {"total_peers": peers.count(), "synced": synced}

import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def format_yaml(data: Any, indent: int = 0) -> str:
    """Format python dict/list into clean human-readable YAML without external dependencies."""
    lines = []
    space = " " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{space}{k}:")
                lines.append(format_yaml(v, indent + 2))
            else:
                val_str = str(v).lower() if isinstance(v, bool) else str(v)
                if isinstance(v, str) and (":" in v or " " in v or not v):
                    val_str = f'"{v}"'
                lines.append(f"{space}{k}: {val_str}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    if first:
                        if isinstance(v, (dict, list)):
                            lines.append(f"{space}- {k}:")
                            lines.append(format_yaml(v, indent + 4))
                        else:
                            val_str = str(v).lower() if isinstance(v, bool) else str(v)
                            if isinstance(v, str) and (":" in v or " " in v or not v):
                                val_str = f'"{v}"'
                            lines.append(f"{space}- {k}: {val_str}")
                        first = False
                    else:
                        if isinstance(v, (dict, list)):
                            lines.append(f"{space}  {k}:")
                            lines.append(format_yaml(v, indent + 4))
                        else:
                            val_str = str(v).lower() if isinstance(v, bool) else str(v)
                            if isinstance(v, str) and (":" in v or " " in v or not v):
                                val_str = f'"{v}"'
                            lines.append(f"{space}  {k}: {val_str}")
            else:
                lines.append(f"{space}- {item}")
    return "\n".join(lines)


class GoBgpConfigWriter:
    """
    Exports BgpGlobalConfig and BgpPeerConfig from PostgreSQL to GoBGP YAML configuration.
    Ensures BGP sessions, parameters (multihop, MD5 password, timers),
    and local ASN/Router ID are persistent across container and host restarts.
    """

    TARGET_PATHS = [
        "/configs/gobgp.yaml",
        "/etc/gobgp/gobgp.yaml",
        "configs/gobgp.yaml",
    ]

    @classmethod
    def generate_config_dict(cls) -> Dict[str, Any]:
        from apps.peers.models import BgpGlobalConfig, BgpPeerConfig

        global_cfg = BgpGlobalConfig.get_solo()
        peers = BgpPeerConfig.objects.filter(is_enabled=True)

        config_dict: Dict[str, Any] = {
            "global": {
                "config": {
                    "as": global_cfg.local_as,
                    "router-id": global_cfg.router_id,
                    "port": global_cfg.listen_port,
                }
            },
            "neighbors": []
        }

        for peer in peers:
            neighbor_entry: Dict[str, Any] = {
                "config": {
                    "neighbor-address": peer.neighbor_address,
                    "peer-as": peer.peer_as,
                }
            }

            if peer.description:
                neighbor_entry["config"]["description"] = peer.description

            if peer.md5_password:
                neighbor_entry["config"]["auth-password"] = peer.md5_password

            # eBGP multihop
            if peer.multihop_enabled or peer.session_type == "eBGP":
                neighbor_entry["ebgp-multihop"] = {
                    "config": {
                        "enabled": True,
                        "multihop-ttl": peer.multihop_ttl or 255,
                    }
                }

            # Timers
            neighbor_entry["timers"] = {
                "config": {
                    "hold-time": peer.hold_time or 90,
                    "keepalive-interval": peer.keepalive_interval or 30,
                }
            }

            # Transport / passive mode
            if peer.passive_mode:
                neighbor_entry["transport"] = {
                    "config": {
                        "passive-mode": True
                    }
                }

            # Address families
            families = peer.families or BgpPeerConfig.DEFAULT_FAMILIES
            neighbor_entry["afi-safis"] = [
                {"config": {"afi-safi-name": fam}} for fam in families
            ]

            config_dict["neighbors"].append(neighbor_entry)

        return config_dict

    @classmethod
    def sync_to_file(cls, target_path: Optional[str] = None) -> bool:
        """Write the generated configuration to disk."""
        paths = [target_path] if target_path else cls.TARGET_PATHS
        data = cls.generate_config_dict()

        try:
            import yaml
            yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        except ImportError:
            yaml_content = format_yaml(data)

        written = False
        for path in paths:
            if not path:
                continue
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)
                logger.info(f"[GoBgpConfigWriter] Successfully wrote GoBGP config to {path}")
                written = True
            except Exception as e:
                logger.debug(f"[GoBgpConfigWriter] Could not write to {path}: {e}")

        return written

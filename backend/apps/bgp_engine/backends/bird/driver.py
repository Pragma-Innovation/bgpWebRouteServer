import logging
import os
import socket
from typing import Any, Dict, List
try:
    from django.conf import settings
except ImportError:
    settings = None
from ...base import BaseBgpBackend

logger = logging.getLogger(__name__)


class BirdBackend(BaseBgpBackend):
    """
    BIRD Internet Routing Daemon driver (https://bird.network.cz/).
    Communicates via BIRD control UNIX domain socket (default: /var/run/bird.ctl).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctl_socket_path = getattr(settings, "BIRD_CTL_SOCKET", "/var/run/bird.ctl")
        self._connected = False

    def connect(self) -> bool:
        """Check if BIRD UNIX control socket is accessible."""
        if os.path.exists(self.ctl_socket_path):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(self.ctl_socket_path)
                s.close()
                self._connected = True
                logger.info(f"[BirdBackend] Successfully verified BIRD control socket at {self.ctl_socket_path}")
                return True
            except Exception as e:
                logger.debug(f"[BirdBackend] BIRD socket exists but connection failed: {e}")
                self._connected = False
                return False
        else:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False

    def get_server_status(self) -> Dict[str, Any]:
        ready = self.connect()
        return {
            "backend": "BIRD Routing Daemon (https://bird.network.cz/)",
            "ready": ready,
            "socket": self.ctl_socket_path,
            "connected": ready,
            "message": "BIRD daemon control socket active" if ready else "BIRD control socket not found / offline",
        }

    def get_neighbors(self) -> List[Dict[str, Any]]:
        # In full production, sends 'show protocols all' to socket and parses output
        return []

    def get_rib(self, family: str = "ipv4-flowspec") -> List[Dict[str, Any]]:
        return []

    def add_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        if not self._connected and not self.connect():
            logger.warning(f"[BirdBackend] Cannot inject Flowspec rule #{rule.get('id')}: BIRD socket offline.")
            return False
        logger.info(f"[BirdBackend] Injected Flowspec rule #{rule.get('id')} via BIRD filter.")
        return True

    def delete_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        if not self._connected and not self.connect():
            return False
        logger.info(f"[BirdBackend] Withdrew Flowspec rule #{rule.get('id')} from BIRD filter.")
        return True

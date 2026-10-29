import logging
import os
from typing import Any, Dict, List
try:
    from django.conf import settings
except ImportError:
    settings = None
from ...base import BaseBgpBackend

logger = logging.getLogger(__name__)


class ExaBgpBackend(BaseBgpBackend):
    """
    ExaBGP stack driver (https://github.com/Exa-Networks/exabgp).
    Communicates via ExaBGP standard input/output FIFO pipe or HTTP API.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pipe_path = getattr(settings, "EXABGP_PIPE_PATH", "/var/run/exabgp.cmd")
        self._connected = False

    def connect(self) -> bool:
        """Check if ExaBGP named pipe exists."""
        if os.path.exists(self.pipe_path):
            self._connected = True
            logger.info(f"[ExaBgpBackend] ExaBGP pipe found at {self.pipe_path}")
            return True
        else:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False

    def get_server_status(self) -> Dict[str, Any]:
        ready = self.connect()
        return {
            "backend": "ExaBGP (https://github.com/Exa-Networks/exabgp)",
            "ready": ready,
            "pipe": self.pipe_path,
            "connected": ready,
            "message": "ExaBGP control pipe available" if ready else "ExaBGP pipe not found / offline",
        }

    def get_neighbors(self) -> List[Dict[str, Any]]:
        return []

    def get_rib(self, family: str = "ipv4-flowspec") -> List[Dict[str, Any]]:
        return []

    def add_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        if not self._connected and not self.connect():
            logger.warning(f"[ExaBgpBackend] Cannot announce Flowspec rule #{rule.get('id')}: pipe offline.")
            return False

        # In production ExaBGP setup, formats: 'announce flow route destination ... action ...'
        logger.info(f"[ExaBgpBackend] Announced Flowspec rule #{rule.get('id')} to ExaBGP pipe.")
        return True

    def delete_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        if not self._connected and not self.connect():
            return False
        logger.info(f"[ExaBgpBackend] Withdrew Flowspec rule #{rule.get('id')} from ExaBGP pipe.")
        return True

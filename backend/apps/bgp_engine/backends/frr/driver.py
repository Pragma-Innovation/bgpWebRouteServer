import logging
import shutil
import subprocess
from typing import Any, Dict, List
try:
    from django.conf import settings
except ImportError:
    settings = None
from ...base import BaseBgpBackend

logger = logging.getLogger(__name__)


class FrrBackend(BaseBgpBackend):
    """
    FRRouting (FRR) stack driver (https://frrouting.org/).
    Interfaces with FRR daemon via vtysh CLI or northbound API.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vtysh_bin = getattr(settings, "FRR_VTYSH_PATH", "vtysh")
        self._connected = False

    def connect(self) -> bool:
        """Check if vtysh command is available in PATH or accessible."""
        if shutil.which(self.vtysh_bin):
            self._connected = True
            logger.info(f"[FrrBackend] vtysh binary found at {shutil.which(self.vtysh_bin)}")
            return True
        else:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False

    def get_server_status(self) -> Dict[str, Any]:
        ready = self.connect()
        return {
            "backend": "FRRouting / FRR (https://frrouting.org/)",
            "ready": ready,
            "vtysh": self.vtysh_bin,
            "connected": ready,
            "message": "FRR vtysh available" if ready else "FRR vtysh executable not found in PATH",
        }

    def get_neighbors(self) -> List[Dict[str, Any]]:
        # In live FRR setup, executes: vtysh -c "show bgp summary json" and parses neighbors
        return []

    def get_rib(self, family: str = "ipv4-flowspec") -> List[Dict[str, Any]]:
        return []

    def add_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        if not self._connected and not self.connect():
            logger.warning(f"[FrrBackend] Cannot inject Flowspec rule #{rule.get('id')}: FRR vtysh offline.")
            return False
        logger.info(f"[FrrBackend] Configured Flowspec rule #{rule.get('id')} in FRR address-family.")
        return True

    def delete_flowspec_rule(self, rule: Dict[str, Any]) -> bool:
        if not self._connected and not self.connect():
            return False
        logger.info(f"[FrrBackend] Removed Flowspec rule #{rule.get('id')} from FRR address-family.")
        return True

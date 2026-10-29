import logging
try:
    from django.conf import settings
    from django.utils.module_loading import import_string
except ImportError:
    settings = None
    import_string = None

from .base import BaseBgpBackend

logger = logging.getLogger(__name__)


class BgpManager:
    """
    Factory and resolver for the active pluggable BGP backend provider.
    """
    _instance: BaseBgpBackend = None

    @classmethod
    def get_active_backend(cls) -> BaseBgpBackend:
        if cls._instance is None:
            backend_path = getattr(
                settings,
                'BGP_ENGINE_BACKEND',
                'apps.bgp_engine.backends.mock.MockBgpBackend'
            )
            try:
                if import_string:
                    backend_cls = import_string(backend_path)
                else:
                    mod_name, cls_name = backend_path.rsplit('.', 1)
                    mod = __import__(mod_name, fromlist=[cls_name])
                    backend_cls = getattr(mod, cls_name)
                cls._instance = backend_cls()
                cls._instance.connect()
                logger.info(f"Loaded BGP backend: {backend_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to load configured BGP backend '{backend_path}' ({e}). "
                    "Falling back to MockBgpBackend."
                )
                from .backends.mock.driver import MockBgpBackend
                cls._instance = MockBgpBackend()
                cls._instance.connect()

        return cls._instance

    @classmethod
    def inject_flowspec_rule(cls, rule_dict: dict) -> bool:
        backend = cls.get_active_backend()
        return backend.add_flowspec_rule(rule_dict)

    @classmethod
    def withdraw_flowspec_rule(cls, rule_dict: dict) -> bool:
        backend = cls.get_active_backend()
        return backend.delete_flowspec_rule(rule_dict)

    @classmethod
    def inject_unicast_route(
        cls,
        prefix: str,
        next_hop: str = None,
        communities: list = None,
        large_communities: list = None,
        med: int = None,
        local_pref: int = None,
        as_path_prepend: str = None,
        origin: str = "igp",
        afi_safi: str = "ipv4-unicast",
    ) -> bool:
        backend = cls.get_active_backend()
        return backend.add_unicast_route(
            prefix=prefix,
            next_hop=next_hop,
            communities=communities or [],
            large_communities=large_communities or [],
            med=med,
            local_pref=local_pref,
            as_path_prepend=as_path_prepend,
            origin=origin,
            afi_safi=afi_safi,
        )

    @classmethod
    def withdraw_unicast_route(cls, prefix: str, afi_safi: str = "ipv4-unicast") -> bool:
        backend = cls.get_active_backend()
        return backend.delete_unicast_route(prefix=prefix, afi_safi=afi_safi)

    @classmethod
    def reset(cls) -> None:
        """Reset the cached instance (useful for testing)."""
        if cls._instance:
            try:
                cls._instance.disconnect()
            except Exception:
                pass
        cls._instance = None

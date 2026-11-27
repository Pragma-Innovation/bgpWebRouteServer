"""
Management command to initialize Global BGP Router settings (from environment on first boot)
and synchronize GoBGP's YAML configuration file on disk.
"""
import os
from django.core.management.base import BaseCommand
from apps.peers.models import BgpGlobalConfig
from apps.bgp_engine.backends.gobgp.config_writer import GoBgpConfigWriter


class Command(BaseCommand):
    help = "Initialize Global BGP Router Config (if empty) and synchronize GoBGP YAML configuration."

    def handle(self, *args, **options):
        if not BgpGlobalConfig.objects.exists():
            local_as = int(os.environ.get("BGP_LOCAL_AS", "65000"))
            router_id = os.environ.get("BGP_ROUTER_ID", "10.100.0.10").strip()
            listen_port = int(os.environ.get("BGP_LISTEN_PORT", "179"))

            cfg = BgpGlobalConfig.objects.create(
                id=1,
                local_as=local_as,
                router_id=router_id,
                listen_port=listen_port,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Initialized Global BGP Config: AS{cfg.local_as}, Router-ID {cfg.router_id}, Port {cfg.listen_port}"
                )
            )
        else:
            cfg = BgpGlobalConfig.get_solo()
            self.stdout.write(
                f"  • Global BGP Config present: AS{cfg.local_as}, Router-ID {cfg.router_id}, Port {cfg.listen_port}"
            )

        if GoBgpConfigWriter.sync_to_file():
            self.stdout.write(self.style.SUCCESS("  ✓ Synchronized GoBGP YAML configuration file."))
        else:
            self.stdout.write(self.style.WARNING("  ! Could not write GoBGP YAML configuration file (no writable path)."))

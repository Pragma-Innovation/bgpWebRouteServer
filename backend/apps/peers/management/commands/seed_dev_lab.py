"""
Management command to seed the 3-router BIRD development lab topology (1x eBGP + 2x iBGP)
into PostgreSQL and write GoBGP's YAML configuration.
Intended strictly for development/test environments (AUTO_SEED_DEMO_LAB=True).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from apps.peers.models import BgpPeerConfig
from apps.bgp_engine.backends.gobgp.config_writer import GoBgpConfigWriter


DEV_LAB_PEERS = [
    {
        "neighbor_address": "10.100.0.20",
        "peer_as": 65001,
        "description": "BIRD eBGP Backbone Router",
        "is_enabled": True,
        "multihop_enabled": True,
        "multihop_ttl": 255,
    },
    {
        "neighbor_address": "10.100.0.30",
        "peer_as": 65000,
        "description": "BIRD iBGP Core Router 1",
        "is_enabled": True,
        "multihop_enabled": False,
        "multihop_ttl": 1,
    },
    {
        "neighbor_address": "10.100.0.40",
        "peer_as": 65000,
        "description": "BIRD iBGP Core Router 2",
        "is_enabled": True,
        "multihop_enabled": False,
        "multihop_ttl": 1,
    },
]


class Command(BaseCommand):
    help = "Seed default BIRD lab BGP neighbors (1x eBGP + 2x iBGP) for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Seed missing lab peers even if other BGP peers already exist in the database.",
        )

    def handle(self, *args, **options):
        # Ensure global router identity exists first
        call_command("bootstrap_bgp_config")

        if BgpPeerConfig.objects.exists() and not options["force"]:
            self.stdout.write(
                f"  • {BgpPeerConfig.objects.count()} BGP peer(s) already configured — skipping dev lab peer seed."
            )
            GoBgpConfigWriter.sync_to_file()
            return

        self.stdout.write(self.style.NOTICE("Seeding development lab BGP neighbors (1x eBGP + 2x iBGP)..."))
        for peer_data in DEV_LAB_PEERS:
            peer, created = BgpPeerConfig.objects.get_or_create(
                neighbor_address=peer_data["neighbor_address"],
                defaults={
                    "peer_as": peer_data["peer_as"],
                    "description": peer_data["description"],
                    "is_enabled": peer_data["is_enabled"],
                    "multihop_enabled": peer_data["multihop_enabled"],
                    "multihop_ttl": peer_data["multihop_ttl"],
                    "families": BgpPeerConfig.DEFAULT_FAMILIES.copy(),
                },
            )
            action_str = "Created" if created else "Verified"
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ {action_str} {peer.session_type} peer {peer.neighbor_address} (AS{peer.peer_as})")
            )

        GoBgpConfigWriter.sync_to_file()
        self.stdout.write(self.style.SUCCESS("Development lab BGP neighbors seeded and synced to GoBGP config."))

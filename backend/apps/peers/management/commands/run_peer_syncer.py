import time
import logging
from django.core.management.base import BaseCommand
from apps.peers.services import PeerReconciliationService

logger = logging.getLogger("peer_syncer")


class Command(BaseCommand):
    help = "Run continuous BGP peer reconciliation between PostgreSQL configuration and GoBGP daemon."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=10,
            help="Polling interval in seconds between reconciliation cycles (default: 10).",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single reconciliation cycle and exit.",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        once = options["once"]

        self.stdout.write(self.style.SUCCESS(f"Starting Gabu BGP Peer Syncer (interval={interval}s)..."))

        try:
            while True:
                start = time.time()
                stats = PeerReconciliationService.reconcile()
                elapsed = time.time() - start

                msg = (
                    f"Reconciliation cycle completed in {elapsed:.3f}s: "
                    f"{stats['managed_count']} managed, "
                    f"{stats['discovered_count']} discovered, "
                    f"{len(stats['pushed_to_gobgp'])} pushed."
                )
                if stats["errors"]:
                    self.stdout.write(self.style.WARNING(f"{msg} Errors: {stats['errors']}"))
                else:
                    self.stdout.write(self.style.SUCCESS(msg))

                if once:
                    break

                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.NOTICE("Peer Syncer stopped by operator."))

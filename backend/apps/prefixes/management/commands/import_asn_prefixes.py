from django.core.management.base import BaseCommand, CommandError
from apps.prefixes.services.asn_discovery import AsnDiscoveryService


class Command(BaseCommand):
    help = "Discover and import active BGP prefixes from RIPEstat for a given ASN"

    def add_arguments(self, parser):
        parser.add_argument("asn", type=int, help="Target Autonomous System Number (e.g. 15169)")
        parser.add_argument("--tag", type=str, default="", help="Optional tag to assign to imported prefixes")
        parser.add_argument("--no-v4", action="store_true", help="Do not import IPv4 prefixes")
        parser.add_argument("--no-v6", action="store_true", help="Do not import IPv6 prefixes")

    def handle(self, *args, **options):
        asn = options["asn"]
        tag = options.get("tag")
        import_v4 = not options.get("no_v4", False)
        import_v6 = not options.get("no_v6", False)

        self.stdout.write(f"Connecting to RIPEstat to discover announced prefixes for AS{asn} (v4={import_v4}, v6={import_v6})...")
        try:
            res = AsnDiscoveryService.import_prefixes_for_asn(
                asn,
                tag=tag,
                import_v4=import_v4,
                import_v6=import_v6
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"AS{asn} Discovery Completed:\n"
                    f"  - Total Discovered: {res['total_found']} (IPv4: {res['ipv4_found']}, IPv6: {res['ipv6_found']})\n"
                    f"  - Newly Created: {res['created']} (IPv4: {res['ipv4_created']}, IPv6: {res['ipv6_created']})\n"
                    f"  - Skipped / Existing: {res['skipped_or_existing']}"
                )
            )
        except Exception as e:
            raise CommandError(f"Failed to import prefixes for AS{asn}: {e}")

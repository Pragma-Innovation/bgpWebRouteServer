import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.flowspec.models import FlowspecRule
from apps.flowspec.serializers import FlowspecRuleSerializer
from apps.bgp_engine.manager import BgpManager


class Command(BaseCommand):
    help = "Import legacy .fslib JSON files from bgpflowspectool into the PostgreSQL database."

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to the legacy .fslib file (e.g. /path/to/mycustom-lib-new-format.fslib)"
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            default=False,
            help="Immediately inject imported rules into the active BGP RIB."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Validate and preview import without saving to database."
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            default=False,
            help="Delete existing rules in database before importing."
        )

    def handle(self, *args, **options):
        file_path = Path(options["file_path"]).expanduser().resolve()
        activate = options["activate"]
        dry_run = options["dry_run"]
        clear_existing = options["clear_existing"]

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(self.style.NOTICE(f"Reading legacy .fslib file: {file_path}"))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            raise CommandError(f"Failed to parse JSON in {file_path}: {e}")

        if not isinstance(raw_data, list):
            raise CommandError("Expected JSON array of rule objects, got " + type(raw_data).__name__)

        self.stdout.write(f"Found {len(raw_data)} rule candidate(s) in file.")

        if clear_existing and not dry_run:
            deleted_count, _ = FlowspecRule.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted_count} existing rule(s)."))

        imported_count = 0
        skipped_count = 0

        action_map = {
            "drop": FlowspecRule.ACTION_DROP,
            "shape": FlowspecRule.ACTION_SHAPE,
            "redirect": FlowspecRule.ACTION_REDIRECT,
            "mark": FlowspecRule.ACTION_MARK,
        }

        bgp_backend = BgpManager.get_active_backend() if activate and not dry_run else None

        for idx, item in enumerate(raw_data, start=1):
            raw_action = str(item.get("Action", "Drop")).strip()
            action = action_map.get(raw_action.lower(), FlowspecRule.ACTION_DROP)

            dst_prefix = item.get("DstPrefix", "").strip()
            src_prefix = item.get("SrcPrefix", "").strip()
            addr_fam = item.get("AddrFam", FlowspecRule.FAMILY_IPV4).strip()
            if addr_fam.upper() == "IPV6" or ":" in dst_prefix or ":" in src_prefix:
                addr_fam = FlowspecRule.FAMILY_IPV6
            else:
                addr_fam = FlowspecRule.FAMILY_IPV4

            port = item.get("Port", "").strip()
            src_port = item.get("SrcPort", "").strip()
            dst_port = item.get("DstPort", "").strip()
            proto_number = item.get("ProtoNumber", "").strip()
            tcp_flags = item.get("TcpFlags", "").strip()
            icmp_type = item.get("IcmpType", "").strip()
            icmp_code = item.get("IcmpCode", "").strip()
            packet_len = item.get("PacketLen", "").strip()
            dscp = item.get("Dscp", "").strip()
            ip_frag = item.get("IpFrag", "").strip()
            action_value = item.get("ActSisterValue", "").strip()

            target_desc = dst_prefix or src_prefix or "All traffic"
            name = f"Imported #{idx}: {action} {target_desc}"
            description = f"Imported from {file_path.name}"

            # Deduplication check
            exists = FlowspecRule.objects.filter(
                addr_fam=addr_fam,
                dst_prefix=dst_prefix,
                src_prefix=src_prefix,
                proto_number=proto_number,
                port=port,
                src_port=src_port,
                dst_port=dst_port,
                tcp_flags=tcp_flags,
                action=action,
                action_value=action_value
            ).exists()

            if exists and not clear_existing:
                skipped_count += 1
                self.stdout.write(f"  [SKIP] Rule #{idx} ({target_desc}) already exists in DB.")
                continue

            if dry_run:
                self.stdout.write(f"  [DRY-RUN] Would create: {name} [{addr_fam}] -> Action: {action}")
                imported_count += 1
                continue

            rule = FlowspecRule.objects.create(
                name=name,
                description=description,
                is_active=activate,
                addr_fam=addr_fam,
                dst_prefix=dst_prefix,
                src_prefix=src_prefix,
                proto_number=proto_number,
                port=port,
                src_port=src_port,
                dst_port=dst_port,
                tcp_flags=tcp_flags,
                icmp_type=icmp_type,
                icmp_code=icmp_code,
                packet_len=packet_len,
                dscp=dscp,
                ip_frag=ip_frag,
                action=action,
                action_value=action_value,
            )

            if activate and bgp_backend:
                serialized = FlowspecRuleSerializer(rule).data
                bgp_backend.add_flowspec_rule(serialized)

            self.stdout.write(f"  [CREATED] Rule #{rule.id}: {rule.name} (Active: {activate})")
            imported_count += 1

        status_msg = f"\nImport finished! Created: {imported_count}, Skipped (duplicate): {skipped_count}."
        if dry_run:
            self.stdout.write(self.style.WARNING(status_msg + " (DRY-RUN - NO CHANGES WRITTEN)"))
        else:
            self.stdout.write(self.style.SUCCESS(status_msg))

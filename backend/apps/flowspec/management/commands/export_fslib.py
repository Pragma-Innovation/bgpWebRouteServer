import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.flowspec.models import FlowspecRule


class Command(BaseCommand):
    help = "Export Flowspec rules from PostgreSQL into legacy .fslib JSON format."

    def add_arguments(self, parser):
        parser.add_argument(
            "output_path",
            type=str,
            help="Path where .fslib file will be written"
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            default=False,
            help="Only export rules currently marked as active in BGP"
        )

    def handle(self, *args, **options):
        output_path = Path(options["output_path"]).expanduser().resolve()
        active_only = options["active_only"]

        qs = FlowspecRule.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)

        exported_rules = []
        for r in qs:
            exported_rules.append({
                "DstPrefix": r.dst_prefix,
                "SrcPrefix": r.src_prefix,
                "AddrFam": r.addr_fam,
                "Port": r.port,
                "SrcPort": r.src_port,
                "DstPort": r.dst_port,
                "TcpFlags": r.tcp_flags,
                "IcmpType": r.icmp_type,
                "IcmpCode": r.icmp_code,
                "ProtoNumber": r.proto_number,
                "PacketLen": r.packet_len,
                "Dscp": r.dscp,
                "IpFrag": r.ip_frag,
                "Action": r.action,
                "ActSisterValue": r.action_value,
            })

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(exported_rules, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully exported {len(exported_rules)} rule(s) to {output_path}")
        )

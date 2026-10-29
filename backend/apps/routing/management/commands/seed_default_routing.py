from django.core.management.base import BaseCommand
from apps.routing.models import PseudoRib, BgpCommunity, Rib


class Command(BaseCommand):
    help = 'Seeds default Pseudo-RIB policy profiles and Master Loc-RIB'

    def handle(self, *args, **options):
        # 1. IPv4 RTBH Blackhole
        rib_v4, created = PseudoRib.objects.get_or_create(
            name='RTBH Backbone Blackhole (IPv4)',
            defaults={
                'description': 'RFC 7999 / RFC 5737 Remotely Triggered Blackhole via RFC 5737 Discard Next-Hop',
                'afi_safi': PseudoRib.AFI_IPV4_UNICAST,
                'next_hop': '192.0.2.1',
                'local_pref': 100,
                'is_default': True,
            }
        )
        if created:
            BgpCommunity.objects.get_or_create(
                pseudo_rib=rib_v4,
                community_type=BgpCommunity.TYPE_STANDARD,
                value='65535:666',
                defaults={'description': 'RFC 7999 BLACKHOLE Well-Known Community'}
            )
            self.stdout.write(self.style.SUCCESS(f"Created '{rib_v4.name}'"))
        else:
            self.stdout.write(f"'{rib_v4.name}' already exists.")

        # 2. IPv6 RTBH Blackhole
        rib_v6, created = PseudoRib.objects.get_or_create(
            name='RTBH Backbone Blackhole (IPv6)',
            defaults={
                'description': 'RFC 7999 Remotely Triggered Blackhole for IPv6 networks via RFC 6666 Discard Next-Hop',
                'afi_safi': PseudoRib.AFI_IPV6_UNICAST,
                'next_hop': '100::1',
                'local_pref': 100,
                'is_default': True,
            }
        )
        if created:
            BgpCommunity.objects.get_or_create(
                pseudo_rib=rib_v6,
                community_type=BgpCommunity.TYPE_STANDARD,
                value='65535:666',
                defaults={'description': 'RFC 7999 BLACKHOLE Well-Known Community'}
            )
            self.stdout.write(self.style.SUCCESS(f"Created '{rib_v6.name}'"))
        else:
            self.stdout.write(f"'{rib_v6.name}' already exists.")

        # 3. Scrubbing Center Diversion
        rib_scrub, created = PseudoRib.objects.get_or_create(
            name='Scrubbing Center Diversion (IPv4)',
            defaults={
                'description': 'Diverts incoming traffic to Anti-DDoS scrubbing GRE tunnel with Large Community',
                'afi_safi': PseudoRib.AFI_IPV4_UNICAST,
                'next_hop': '192.0.2.2',
                'local_pref': 200,
                'is_default': False,
            }
        )
        if created:
            BgpCommunity.objects.get_or_create(
                pseudo_rib=rib_scrub,
                community_type=BgpCommunity.TYPE_LARGE,
                value='65000:666:2',
                defaults={'description': 'Large Community RFC 8092 Scrubbing Trigger'}
            )
            self.stdout.write(self.style.SUCCESS(f"Created '{rib_scrub.name}'"))
        else:
            self.stdout.write(f"'{rib_scrub.name}' already exists.")

        # 4. Flowspec Mitigation Pseudo-RIB
        rib_flow, created = PseudoRib.objects.get_or_create(
            name='DDoS Edge Mitigation (IPv4 Flowspec)',
            defaults={
                'description': 'RFC 5575 / RFC 8955 Flowspec traffic filters with local priority 150',
                'afi_safi': PseudoRib.AFI_IPV4_FLOWSPEC,
                'local_pref': 150,
                'is_default': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created '{rib_flow.name}'"))
        else:
            self.stdout.write(f"'{rib_flow.name}' already exists.")

        # 5. Master Named RIB: Production Loc-RIB
        master_rib, created = Rib.objects.get_or_create(
            name='Production Loc-RIB',
            defaults={
                'description': 'Master BGP Loc-RIB aggregating IPv4/IPv6 Unicast RTBH and Flowspec mitigations',
                'is_active': True,
                'status': Rib.STATUS_DRAFT,
            }
        )
        master_rib.pseudo_ribs.add(rib_v4, rib_v6, rib_flow)
        self.stdout.write(self.style.SUCCESS(f"Master RIB '{master_rib.name}' initialized with {master_rib.pseudo_ribs.count()} Pseudo-RIBs."))

import unittest
from django.core.exceptions import ValidationError
from apps.prefixes.models import IpPrefix
from apps.routing.models import PseudoRib, BgpCommunity, BgpAnnouncement


class RoutingModelTest(unittest.TestCase):
    def test_pseudo_rib_ip_version_assignment(self):
        rib_v4 = PseudoRib(name='RTBH v4', afi_safi=PseudoRib.AFI_IPV4_UNICAST)
        rib_v4.clean()
        self.assertEqual(rib_v4.ip_version, 4)

        rib_v6 = PseudoRib(name='RTBH v6', afi_safi=PseudoRib.AFI_IPV6_UNICAST)
        rib_v6.clean()
        self.assertEqual(rib_v6.ip_version, 6)

    def test_standard_community_validation(self):
        rib = PseudoRib(name='Test Profile', afi_safi=PseudoRib.AFI_IPV4_UNICAST)
        valid_comm = BgpCommunity(pseudo_rib=rib, community_type=BgpCommunity.TYPE_STANDARD, value='65535:666')
        valid_comm.clean()
        self.assertEqual(valid_comm.value, '65535:666')

        # Well-known conversion
        named_comm = BgpCommunity(pseudo_rib=rib, community_type=BgpCommunity.TYPE_STANDARD, value='BLACKHOLE')
        named_comm.clean()
        self.assertEqual(named_comm.value, '65535:666')

        # Invalid format
        invalid_comm = BgpCommunity(pseudo_rib=rib, community_type=BgpCommunity.TYPE_STANDARD, value='invalid')
        with self.assertRaises(ValidationError):
            invalid_comm.clean()

        # > 65535 in standard community raises error
        overflow_comm = BgpCommunity(pseudo_rib=rib, community_type=BgpCommunity.TYPE_STANDARD, value='70000:100')
        with self.assertRaises(ValidationError):
            overflow_comm.clean()

    def test_large_community_validation(self):
        rib = PseudoRib(name='Test Profile Large', afi_safi=PseudoRib.AFI_IPV4_UNICAST)
        valid_comm = BgpCommunity(pseudo_rib=rib, community_type=BgpCommunity.TYPE_LARGE, value='65000:666:1')
        valid_comm.clean()
        self.assertEqual(valid_comm.value, '65000:666:1')

        # Invalid large community format
        invalid_comm = BgpCommunity(pseudo_rib=rib, community_type=BgpCommunity.TYPE_LARGE, value='65000:666')
        with self.assertRaises(ValidationError):
            invalid_comm.clean()

    def test_announcement_version_mismatch_fails(self):
        prefix_v4 = IpPrefix(prefix='198.51.100.0/24')
        prefix_v4.clean()
        rib_v6 = PseudoRib(name='V6 Profile', afi_safi=PseudoRib.AFI_IPV6_UNICAST)
        rib_v6.clean()

        ann = BgpAnnouncement(prefix=prefix_v4, pseudo_rib=rib_v6)
        with self.assertRaises(ValidationError):
            ann.clean()

    def test_rib_model_representation(self):
        rib = PseudoRib(name='Test Rib', afi_safi=PseudoRib.AFI_IPV4_UNICAST)
        master = PseudoRib(name='Master', afi_safi=PseudoRib.AFI_IPV4_UNICAST)
        self.assertEqual(str(rib), 'Test Rib (ipv4-unicast)')

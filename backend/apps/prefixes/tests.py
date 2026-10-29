import unittest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from apps.prefixes.models import IpPrefix
from apps.prefixes.services.asn_discovery import AsnDiscoveryService


class IpPrefixModelTest(unittest.TestCase):
    def test_ipv4_prefix_validation(self):
        prefix = IpPrefix(prefix='198.51.100.0/24')
        prefix.clean()
        self.assertEqual(prefix.ip_version, 4)
        self.assertEqual(prefix.prefix, '198.51.100.0/24')

    def test_ipv6_prefix_validation(self):
        prefix = IpPrefix(prefix='2001:db8::/32')
        prefix.clean()
        self.assertEqual(prefix.ip_version, 6)
        self.assertEqual(prefix.prefix, '2001:db8::/32')

    def test_host_bits_normalization(self):
        # 198.51.100.5/24 should normalize to network 198.51.100.0/24
        prefix = IpPrefix(prefix='198.51.100.5/24')
        prefix.clean()
        self.assertEqual(prefix.prefix, '198.51.100.0/24')

    def test_invalid_prefix_raises(self):
        prefix = IpPrefix(prefix='not-an-ip/999')
        with self.assertRaises(ValidationError):
            prefix.clean()


class AsnDiscoveryServiceTest(TestCase):
    @patch.object(AsnDiscoveryService, 'fetch_announced_prefixes')
    def test_import_both_v4_and_v6(self, mock_fetch):
        mock_fetch.return_value = [
            '198.51.100.0/24',
            '203.0.113.0/24',
            '2001:db8:1::/48',
            '2001:db8:2::/48',
        ]
        res = AsnDiscoveryService.import_prefixes_for_asn(65001, import_v4=True, import_v6=True)
        self.assertEqual(res['total_found'], 4)
        self.assertEqual(res['ipv4_found'], 2)
        self.assertEqual(res['ipv6_found'], 2)
        self.assertEqual(res['created'], 4)
        self.assertEqual(res['ipv4_created'], 2)
        self.assertEqual(res['ipv6_created'], 2)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65001, ip_version=4).count(), 2)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65001, ip_version=6).count(), 2)

    @patch.object(AsnDiscoveryService, 'fetch_announced_prefixes')
    def test_import_v6_only(self, mock_fetch):
        mock_fetch.return_value = [
            '198.51.100.0/24',
            '2001:db8:3::/48',
        ]
        res = AsnDiscoveryService.import_prefixes_for_asn(65002, import_v4=False, import_v6=True)
        self.assertEqual(res['total_found'], 2)
        self.assertEqual(res['ipv4_found'], 1)
        self.assertEqual(res['ipv6_found'], 1)
        self.assertEqual(res['created'], 1)
        self.assertEqual(res['ipv4_created'], 0)
        self.assertEqual(res['ipv6_created'], 1)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65002, ip_version=6).count(), 1)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65002, ip_version=4).count(), 0)

    @patch.object(AsnDiscoveryService, 'fetch_announced_prefixes')
    def test_import_v4_only(self, mock_fetch):
        mock_fetch.return_value = [
            '198.51.100.0/24',
            '2001:db8:4::/48',
        ]
        res = AsnDiscoveryService.import_prefixes_for_asn(65003, import_v4=True, import_v6=False)
        self.assertEqual(res['created'], 1)
        self.assertEqual(res['ipv4_created'], 1)
        self.assertEqual(res['ipv6_created'], 0)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65003, ip_version=4).count(), 1)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65003, ip_version=6).count(), 0)


class AsnImportApiTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin_test', password='password123', is_superuser=True)
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch.object(AsnDiscoveryService, 'fetch_announced_prefixes')
    def test_api_import_asn_v6_only(self, mock_fetch):
        mock_fetch.return_value = [
            '198.51.100.0/24',
            '2001:db8:99::/48'
        ]
        response = self.client.post('/api/v1/prefixes/import-asn/', {
            'asn': 65099,
            'import_v4': False,
            'import_v6': True
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 1)
        self.assertEqual(response.data['ipv4_created'], 0)
        self.assertEqual(response.data['ipv6_created'], 1)
        self.assertEqual(response.data['ipv6_found'], 1)
        self.assertEqual(response.data['ipv4_found'], 1)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65099, ip_version=6).count(), 1)
        self.assertEqual(IpPrefix.objects.filter(origin_asn=65099, ip_version=4).count(), 0)

    def test_api_filter_ip_version(self):
        IpPrefix.objects.create(prefix='198.51.100.0/24', ip_version=4)
        IpPrefix.objects.create(prefix='2001:db8::/32', ip_version=6)

        r_v6 = self.client.get('/api/v1/prefixes/?ip_version=6')
        self.assertEqual(r_v6.status_code, 200)
        prefixes_v6 = [item['prefix'] for item in r_v6.data['results']]
        self.assertIn('2001:db8::/32', prefixes_v6)
        self.assertNotIn('198.51.100.0/24', prefixes_v6)

        r_v4 = self.client.get('/api/v1/prefixes/?ip_version=4')
        self.assertEqual(r_v4.status_code, 200)
        prefixes_v4 = [item['prefix'] for item in r_v4.data['results']]
        self.assertIn('198.51.100.0/24', prefixes_v4)
        self.assertNotIn('2001:db8::/32', prefixes_v4)

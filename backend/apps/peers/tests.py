import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.peers.models import BgpGlobalConfig, BgpPeerConfig
from apps.bgp_engine.backends.gobgp.config_writer import GoBgpConfigWriter


class BgpPeerModelTest(TestCase):
    def setUp(self):
        self.global_cfg = BgpGlobalConfig.get_solo()
        self.global_cfg.local_as = 65000
        self.global_cfg.router_id = "10.100.0.10"
        self.global_cfg.listen_port = 179
        self.global_cfg.save()

    def test_ipv4_peer_validation_and_session_type(self):
        # iBGP peer
        ibgp_peer = BgpPeerConfig(
            neighbor_address="10.100.0.50",
            peer_as=65000,
        )
        ibgp_peer.full_clean()
        ibgp_peer.save()
        self.assertEqual(ibgp_peer.ip_version, 4)
        self.assertEqual(ibgp_peer.session_type, "iBGP")

        # eBGP peer
        ebgp_peer = BgpPeerConfig(
            neighbor_address="10.100.0.20",
            peer_as=65001,
            multihop_enabled=True,
            multihop_ttl=10,
        )
        ebgp_peer.full_clean()
        ebgp_peer.save()
        self.assertEqual(ebgp_peer.ip_version, 4)
        self.assertEqual(ebgp_peer.session_type, "eBGP")
        self.assertEqual(ebgp_peer.multihop_ttl, 10)

    def test_ipv6_peer_validation(self):
        peer = BgpPeerConfig(
            neighbor_address="2001:db8::2",
            peer_as=65002,
        )
        peer.full_clean()
        peer.save()
        self.assertEqual(peer.ip_version, 6)
        self.assertEqual(peer.session_type, "eBGP")

    def test_config_writer_yaml_generation(self):
        BgpPeerConfig.objects.create(
            neighbor_address="10.100.0.20",
            peer_as=65001,
            description="BIRD Test Peer",
            multihop_enabled=True,
            md5_password="secretpassword",
        )
        config_dict = GoBgpConfigWriter.generate_config_dict()
        self.assertEqual(config_dict["global"]["config"]["as"], 65000)
        self.assertEqual(config_dict["global"]["config"]["router-id"], "10.100.0.10")
        self.assertEqual(len(config_dict["neighbors"]), 1)
        neighbor = config_dict["neighbors"][0]
        self.assertEqual(neighbor["config"]["neighbor-address"], "10.100.0.20")
        self.assertEqual(neighbor["config"]["auth-password"], "secretpassword")


class BgpPeerApiTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin_peer', password='password123', is_superuser=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_and_patch_global_config(self):
        res = self.client.get('/api/v1/peers/global/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['local_as'], 65000)

        patch_res = self.client.patch('/api/v1/peers/global/', {
            'local_as': 64512,
            'router_id': '192.0.2.1',
        })
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.data['local_as'], 64512)
        self.assertEqual(patch_res.data['router_id'], '192.0.2.1')

    @patch('apps.bgp_engine.backends.gobgp.config_writer.GoBgpConfigWriter.sync_to_file')
    def test_create_and_delete_peer_api(self, mock_sync):
        mock_sync.return_value = True

        create_res = self.client.post('/api/v1/peers/peers/', {
            'neighbor_address': '10.100.0.88',
            'peer_as': 65088,
            'description': 'Edge Router Paris',
            'multihop_enabled': True,
            'multihop_ttl': 64,
            'md5_password': 'mypassword',
        })
        self.assertEqual(create_res.status_code, 201)
        self.assertEqual(create_res.data['neighbor_address'], '10.100.0.88')
        self.assertEqual(create_res.data['session_type'], 'eBGP')
        peer_id = create_res.data['id']

        # Reset session
        reset_res = self.client.post(f'/api/v1/peers/peers/{peer_id}/reset/', {'soft': True})
        self.assertEqual(reset_res.status_code, 200)

        # Delete session
        del_res = self.client.delete(f'/api/v1/peers/peers/{peer_id}/')
        self.assertEqual(del_res.status_code, 204)
        self.assertEqual(BgpPeerConfig.objects.filter(id=peer_id).count(), 0)

    @patch('apps.bgp_engine.manager.BgpManager.get_active_backend')
    def test_unified_sessions_api(self, mock_get_backend):
        mock_backend = MagicMock()
        mock_backend.get_neighbors.return_value = [
            {
                'neighbor_address': '10.100.0.20',
                'peer_as': 65001,
                'state': 'ESTABLISHED',
                'uptime': 3600,
                'prefixes_received': 5,
            },
            {
                'neighbor_address': '172.16.1.1',
                'peer_as': 65200,
                'state': 'ACTIVE',
                'uptime': 0,
                'prefixes_received': 0,
            }
        ]
        mock_get_backend.return_value = mock_backend

        # Create one managed peer
        BgpPeerConfig.objects.create(
            neighbor_address='10.100.0.20',
            peer_as=65001,
            description='Managed BIRD',
        )

        res = self.client.get('/api/v1/peers/peers/sessions/')
        self.assertEqual(res.status_code, 200)
        sessions = res.data
        self.assertEqual(len(sessions), 2)

        # 10.100.0.20 is managed
        s1 = next(s for s in sessions if s['neighbor_address'] == '10.100.0.20')
        self.assertTrue(s1['is_managed'])
        self.assertEqual(s1['origin'], 'managed')
        self.assertEqual(s1['sync_status'], 'in_sync')
        self.assertEqual(s1['state'], 'ESTABLISHED')

        # 172.16.1.1 is discovered
        s2 = next(s for s in sessions if s['neighbor_address'] == '172.16.1.1')
        self.assertFalse(s2['is_managed'])
        self.assertEqual(s2['origin'], 'discovered')
        self.assertEqual(s2['sync_status'], 'discovered')
        self.assertEqual(s2['state'], 'ACTIVE')

    @patch('apps.bgp_engine.backends.gobgp.config_writer.GoBgpConfigWriter.sync_to_file')
    @patch('apps.bgp_engine.manager.BgpManager.get_active_backend')
    def test_reconcile_api(self, mock_get_backend, mock_sync):
        mock_sync.return_value = True
        mock_backend = MagicMock()
        mock_backend.get_neighbors.return_value = []
        mock_backend.add_peer.return_value = True
        mock_get_backend.return_value = mock_backend

        # Create enabled peer missing from GoBGP
        BgpPeerConfig.objects.create(
            neighbor_address='10.100.0.99',
            peer_as=65099,
            is_enabled=True,
        )

        res = self.client.post('/api/v1/peers/peers/reconcile/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'success')
        self.assertIn('10.100.0.99', res.data['pushed_to_gobgp'])
        mock_backend.add_peer.assert_called_once()

    @patch('apps.bgp_engine.backends.gobgp.config_writer.GoBgpConfigWriter.sync_to_file')
    @patch('apps.bgp_engine.manager.BgpManager.get_active_backend')
    def test_adopt_discovered_peer_api(self, mock_get_backend, mock_sync):
        mock_sync.return_value = True
        mock_backend = MagicMock()
        mock_backend.add_peer.return_value = True
        mock_get_backend.return_value = mock_backend

        res = self.client.post('/api/v1/peers/peers/adopt/', {
            'neighbor_address': '172.16.1.1',
            'peer_as': 65200,
            'description': 'Adopted Test Peer',
            'multihop_enabled': True,
            'multihop_ttl': 64,
            'families': ['ipv4-unicast'],
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['neighbor_address'], '172.16.1.1')
        self.assertEqual(res.data['peer_as'], 65200)
        self.assertTrue(BgpPeerConfig.objects.filter(neighbor_address='172.16.1.1').exists())
        mock_backend.add_peer.assert_called_once()


class BootstrapAndSeedingCommandsTest(TestCase):
    @patch('apps.bgp_engine.backends.gobgp.config_writer.GoBgpConfigWriter.sync_to_file', return_value=True)
    @patch.dict('os.environ', {
        'BGP_LOCAL_AS': '64555',
        'BGP_ROUTER_ID': '192.0.2.55',
        'BGP_LISTEN_PORT': '1179',
    })
    def test_bootstrap_bgp_config_from_env_when_empty(self, mock_sync):
        from django.core.management import call_command
        BgpGlobalConfig.objects.all().delete()

        call_command('bootstrap_bgp_config')
        cfg = BgpGlobalConfig.get_solo()
        self.assertEqual(cfg.local_as, 64555)
        self.assertEqual(cfg.router_id, '192.0.2.55')
        self.assertEqual(cfg.listen_port, 1179)
        self.assertTrue(mock_sync.called)

    @patch('apps.bgp_engine.backends.gobgp.config_writer.GoBgpConfigWriter.sync_to_file', return_value=True)
    def test_seed_dev_lab_idempotent(self, mock_sync):
        from django.core.management import call_command
        BgpPeerConfig.objects.all().delete()

        call_command('seed_dev_lab')
        self.assertEqual(BgpPeerConfig.objects.count(), 3)
        self.assertTrue(BgpPeerConfig.objects.filter(neighbor_address='10.100.0.20', peer_as=65001).exists())
        self.assertTrue(BgpPeerConfig.objects.filter(neighbor_address='10.100.0.30', peer_as=65000).exists())
        self.assertTrue(BgpPeerConfig.objects.filter(neighbor_address='10.100.0.40', peer_as=65000).exists())

        # Subsequent call without --force keeps existing peer table untouched
        BgpPeerConfig.objects.filter(neighbor_address='10.100.0.40').delete()
        call_command('seed_dev_lab')
        self.assertEqual(BgpPeerConfig.objects.count(), 2)

        # With --force, missing lab peer is restored
        call_command('seed_dev_lab', force=True)
        self.assertEqual(BgpPeerConfig.objects.count(), 3)

    @patch.dict('os.environ', {
        'DJANGO_SUPERUSER_USERNAME': 'prod_admin',
        'DJANGO_SUPERUSER_EMAIL': 'noc@prod.local',
        'DJANGO_SUPERUSER_PASSWORD': 'StrongProdPassword!123',
    })
    def test_bootstrap_roles_production_superuser_without_demo_users(self):
        from django.core.management import call_command
        User = get_user_model()

        call_command('bootstrap_roles', ensure_superuser=True)
        prod_admin = User.objects.filter(username='prod_admin').first()
        self.assertIsNotNone(prod_admin)
        self.assertTrue(prod_admin.is_superuser)
        self.assertTrue(prod_admin.groups.filter(name='Admin').exists())
        # Demo users must NOT be created in production mode
        self.assertFalse(User.objects.filter(username='operator').exists())
        self.assertFalse(User.objects.filter(username='viewer').exists())

    def test_seed_default_routing_only_if_empty(self):
        from django.core.management import call_command
        from apps.routing.models import PseudoRib, Rib

        PseudoRib.objects.all().delete()
        Rib.objects.all().delete()

        call_command('seed_default_routing', only_if_empty=True)
        self.assertEqual(PseudoRib.objects.count(), 4)
        self.assertEqual(Rib.objects.count(), 1)

        # Delete one starter profile; subsequent --only-if-empty must NOT recreate it
        PseudoRib.objects.filter(name='Scrubbing Center Diversion (IPv4)').delete()
        call_command('seed_default_routing', only_if_empty=True)
        self.assertEqual(PseudoRib.objects.count(), 3)



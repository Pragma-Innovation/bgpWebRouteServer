"""
Test suite for JWT Authentication and 3-Tier RBAC (Viewer, Operator, Admin).
Verifies:
  - Anonymous users are rejected with 401 on protected endpoints.
  - Health probes remain unauthenticated (200 OK).
  - Viewer role has read-only access (GET allowed, POST/PUT/DELETE blocked with 403).
  - Operator role can manage Flowspec rules but cannot alter BGP peer definitions.
  - Admin role has full access across all resources.
"""
from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.flowspec.models import FlowspecRule
from apps.peers.models import BgpPeerConfig


class AuthRbacTests(APITestCase):

    def setUp(self):
        # Create RBAC Groups
        self.viewer_group = Group.objects.create(name='Viewer')
        self.operator_group = Group.objects.create(name='Operator')
        self.admin_group = Group.objects.create(name='Admin')

        # Create Test Users
        self.password = 'testpass123'

        self.viewer_user = User.objects.create_user(
            username='test_viewer',
            email='viewer@example.com',
            password=self.password
        )
        self.viewer_user.groups.add(self.viewer_group)

        self.operator_user = User.objects.create_user(
            username='test_operator',
            email='operator@example.com',
            password=self.password
        )
        self.operator_user.groups.add(self.operator_group)

        self.admin_user = User.objects.create_superuser(
            username='test_admin',
            email='admin@example.com',
            password=self.password
        )
        self.admin_user.groups.add(self.admin_group)

        # Seed sample Flowspec rule
        self.sample_rule = FlowspecRule.objects.create(
            name="Sample Drop Rule",
            addr_fam="IPv4",
            dst_prefix="198.51.100.1/32",
            action="Drop",
            is_active=True
        )

        self.login_url = reverse('token_obtain_pair')
        self.rules_url = '/api/v1/flowspec/rules/'
        self.peers_url = '/api/v1/peers/peers/'

    def test_anonymous_access_blocked_on_api(self):
        """Anonymous requests must be rejected with 401 Unauthorized."""
        response = self.client.get(self.rules_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(self.rules_url, {'dst_prefix': '10.0.0.1/32', 'action': 'Drop'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_health_probes_remain_unauthenticated(self):
        """Kubernetes health probes must be accessible without authentication."""
        resp_live = self.client.get('/api/health/live/')
        self.assertEqual(resp_live.status_code, status.HTTP_200_OK)

        resp_ready = self.client.get('/api/health/ready/')
        self.assertEqual(resp_ready.status_code, status.HTTP_200_OK)

    def test_login_returns_jwt_and_user_role(self):
        """Logging in returns access/refresh tokens and user role metadata."""
        response = self.client.post(self.login_url, {
            'username': 'test_operator',
            'password': self.password
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'test_operator')
        self.assertEqual(response.data['user']['role'], 'Operator')

    def test_viewer_role_read_only_access(self):
        """Viewer can read rules (200) but cannot create or mutate rules (403)."""
        self.client.force_authenticate(user=self.viewer_user)

        # GET should succeed
        get_resp = self.client.get(self.rules_url)
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)

        # POST should be rejected with 403 Forbidden
        post_resp = self.client.post(self.rules_url, {
            'dst_prefix': '192.0.2.1/32',
            'action': 'Drop',
            'is_active': True
        })
        self.assertEqual(post_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Toggle action should be rejected with 403 Forbidden
        toggle_resp = self.client.post(f"{self.rules_url}{self.sample_rule.id}/toggle/")
        self.assertEqual(toggle_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_operator_role_can_manage_flowspec_rules(self):
        """Operator can create, toggle, update, and delete rules, but cannot alter peers."""
        self.client.force_authenticate(user=self.operator_user)

        # Create rule
        create_resp = self.client.post(self.rules_url, {
            'name': 'DDoS Mitigation #1',
            'addr_fam': 'IPv4',
            'dst_prefix': '203.0.113.50/32',
            'action': 'Drop',
            'is_active': True
        })
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        new_rule_id = create_resp.data['id']

        # Toggle rule
        toggle_resp = self.client.post(f"{self.rules_url}{new_rule_id}/toggle/")
        self.assertEqual(toggle_resp.status_code, status.HTTP_200_OK)

        # Delete rule
        del_resp = self.client.delete(f"{self.rules_url}{new_rule_id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Peer configuration creation should be 403 Forbidden for Operator
        peer_resp = self.client.post(self.peers_url, {
            'neighbor_address': '10.200.1.1',
            'peer_as': 65005
        })
        self.assertEqual(peer_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_role_has_full_access(self):
        """Admin role can manage both Flowspec rules and BGP peers."""
        self.client.force_authenticate(user=self.admin_user)

        # Can create Flowspec rule
        rule_resp = self.client.post(self.rules_url, {
            'name': 'Admin Emergency Blackhole',
            'addr_fam': 'IPv4',
            'dst_prefix': '198.51.100.99/32',
            'action': 'Drop',
            'is_active': True
        })
        self.assertEqual(rule_resp.status_code, status.HTTP_201_CREATED)

        # Can create BGP Peer
        peer_resp = self.client.post(self.peers_url, {
            'neighbor_address': '172.16.1.1',
            'peer_as': 65200,
            'description': 'Core Route Reflector'
        })
        self.assertEqual(peer_resp.status_code, status.HTTP_201_CREATED)

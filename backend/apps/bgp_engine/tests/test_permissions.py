"""
Unit tests for RBAC permission classes and role resolution logic.
Runs standalone without requiring an active database or live Django server.
"""
import unittest
from unittest.mock import MagicMock
from apps.bgp_engine.permissions import (
    get_user_role,
    IsOperatorOrReadOnly,
    IsAdminOrReadOnly,
)


class TestRbacPermissionsLogic(unittest.TestCase):

    def _create_mock_user(self, username="testuser", is_authenticated=True, is_superuser=False, is_staff=False, groups=None):
        user = MagicMock()
        user.username = username
        user.is_authenticated = is_authenticated
        user.is_superuser = is_superuser
        user.is_staff = is_staff

        group_names = groups or []
        user.groups.filter.side_effect = lambda **kwargs: MagicMock(
            exists=lambda: any(
                g in group_names for g in (
                    [kwargs.get('name')] if 'name' in kwargs else kwargs.get('name__in', [])
                )
            )
        )
        return user

    def test_anonymous_role(self):
        anon = self._create_mock_user(is_authenticated=False)
        self.assertEqual(get_user_role(anon), 'Anonymous')
        self.assertEqual(get_user_role(None), 'Anonymous')

    def test_admin_role_resolution(self):
        # Superuser
        admin1 = self._create_mock_user(is_superuser=True)
        self.assertEqual(get_user_role(admin1), 'Admin')

        # User in Admin group
        admin2 = self._create_mock_user(groups=['Admin'])
        self.assertEqual(get_user_role(admin2), 'Admin')

    def test_operator_role_resolution(self):
        op = self._create_mock_user(groups=['Operator'])
        self.assertEqual(get_user_role(op), 'Operator')

    def test_viewer_role_resolution(self):
        viewer = self._create_mock_user(groups=['Viewer'])
        self.assertEqual(get_user_role(viewer), 'Viewer')

        regular = self._create_mock_user(groups=[])
        self.assertEqual(get_user_role(regular), 'Viewer')

    def test_operator_or_read_only_permission(self):
        perm = IsOperatorOrReadOnly()
        view = MagicMock()

        # Anonymous: denied all methods
        anon = self._create_mock_user(is_authenticated=False)
        req_get = MagicMock(user=anon, method="GET")
        req_post = MagicMock(user=anon, method="POST")
        self.assertFalse(perm.has_permission(req_get, view))
        self.assertFalse(perm.has_permission(req_post, view))

        # Viewer: GET allowed, POST denied
        viewer = self._create_mock_user(groups=['Viewer'])
        req_view_get = MagicMock(user=viewer, method="GET")
        req_view_post = MagicMock(user=viewer, method="POST")
        req_view_delete = MagicMock(user=viewer, method="DELETE")
        self.assertTrue(perm.has_permission(req_view_get, view))
        self.assertFalse(perm.has_permission(req_view_post, view))
        self.assertFalse(perm.has_permission(req_view_delete, view))

        # Operator: GET and POST/DELETE allowed
        op = self._create_mock_user(groups=['Operator'])
        req_op_get = MagicMock(user=op, method="GET")
        req_op_post = MagicMock(user=op, method="POST")
        req_op_delete = MagicMock(user=op, method="DELETE")
        self.assertTrue(perm.has_permission(req_op_get, view))
        self.assertTrue(perm.has_permission(req_op_post, view))
        self.assertTrue(perm.has_permission(req_op_delete, view))

        # Admin: GET and POST allowed
        admin = self._create_mock_user(is_superuser=True)
        req_admin_post = MagicMock(user=admin, method="POST")
        self.assertTrue(perm.has_permission(req_admin_post, view))

    def test_admin_or_read_only_permission(self):
        perm = IsAdminOrReadOnly()
        view = MagicMock()

        # Viewer: GET allowed, POST denied
        viewer = self._create_mock_user(groups=['Viewer'])
        self.assertTrue(perm.has_permission(MagicMock(user=viewer, method="GET"), view))
        self.assertFalse(perm.has_permission(MagicMock(user=viewer, method="POST"), view))

        # Operator: GET allowed, but POST denied for admin resources (like peers)
        op = self._create_mock_user(groups=['Operator'])
        self.assertTrue(perm.has_permission(MagicMock(user=op, method="GET"), view))
        self.assertFalse(perm.has_permission(MagicMock(user=op, method="POST"), view))

        # Admin: GET and POST allowed
        admin = self._create_mock_user(groups=['Admin'])
        self.assertTrue(perm.has_permission(MagicMock(user=admin, method="GET"), view))
        self.assertTrue(perm.has_permission(MagicMock(user=admin, method="POST"), view))


if __name__ == '__main__':
    unittest.main()

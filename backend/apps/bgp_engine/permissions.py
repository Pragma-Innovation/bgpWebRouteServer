"""
Role-Based Access Control (RBAC) permission classes for bgpWebRouteServer.
Defines 3 operational roles:
  - Viewer: Read-only monitoring of Flowspec rules, BGP peers, and telemetry.
  - Operator: Can create, toggle, update, and delete Flowspec rules.
  - Admin: Full administrative privileges (BGP peering config, user management).
"""
try:
    from rest_framework import permissions
    SAFE_METHODS = permissions.SAFE_METHODS
    BasePermission = permissions.BasePermission
except ImportError:
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    class BasePermission:
        pass


def get_user_role(user) -> str:
    """Return normalized role string for an authenticated user."""
    if not user or not user.is_authenticated:
        return 'Anonymous'
    if user.is_superuser or user.groups.filter(name='Admin').exists():
        return 'Admin'
    if user.groups.filter(name='Operator').exists():
        return 'Operator'
    return 'Viewer'


class IsOperatorOrReadOnly(BasePermission):
    """
    Custom permission allowing Viewers read-only access (GET/HEAD/OPTIONS).
    Requires Operator or Admin role for any mutations (POST/PUT/PATCH/DELETE).
    """

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        # Read-only safe methods open to all authenticated users (including Viewer)
        if request.method in SAFE_METHODS:
            return True

        # Mutation operations require Operator or Admin
        role = get_user_role(request.user)
        return role in ('Operator', 'Admin')


class IsAdminOrReadOnly(BasePermission):
    """
    Custom permission for critical administrative operations (e.g. BGP peering configuration).
    Allows read-only access to all authenticated users, but requires Admin role to modify.
    """

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        role = get_user_role(request.user)
        return role == 'Admin'

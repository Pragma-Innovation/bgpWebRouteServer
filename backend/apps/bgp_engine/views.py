from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .manager import BgpManager


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bgp_status_view(request):
    """Return live status of the active BGP backend router."""
    backend = BgpManager.get_active_backend()
    status = backend.get_server_status()
    return Response(status)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bgp_neighbors_view(request):
    """Return active BGP neighbors/peers and their session state."""
    backend = BgpManager.get_active_backend()
    neighbors = backend.get_neighbors()
    return Response(neighbors)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bgp_rib_view(request):
    """Return Routing Information Base (RIB) entries."""
    family = request.query_params.get('family', 'ipv4-flowspec')
    backend = BgpManager.get_active_backend()
    routes = backend.get_rib(family=family)
    return Response(routes)

from rest_framework import viewsets
from .models import BgpPeerConfig
from .serializers import BgpPeerConfigSerializer
from apps.bgp_engine.permissions import IsAdminOrReadOnly


class BgpPeerConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for administrative configuration of BGP peers.
    Requires Admin role for creating, updating, or deleting peers.
    """
    queryset = BgpPeerConfig.objects.all()
    serializer_class = BgpPeerConfigSerializer
    permission_classes = [IsAdminOrReadOnly]

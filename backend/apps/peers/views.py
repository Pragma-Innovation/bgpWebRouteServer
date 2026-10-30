from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.bgp_engine.permissions import IsOperatorOrReadOnly, IsAdminOrReadOnly
from apps.bgp_engine.manager import BgpManager
from apps.bgp_engine.backends.gobgp.config_writer import GoBgpConfigWriter
from .models import BgpPeerConfig, BgpGlobalConfig
from .serializers import BgpPeerConfigSerializer, BgpGlobalConfigSerializer
from .services import PeerReconciliationService


class BgpGlobalConfigView(APIView):
    """
    Endpoint for managing global BGP router parameters (Local ASN, Router ID, Route Reflector).
    GET: Retrieve current global configuration.
    PATCH/PUT: Update global parameters (Admin only).
    """
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        cfg = BgpGlobalConfig.get_solo()
        serializer = BgpGlobalConfigSerializer(cfg)
        return Response(serializer.data)

    def patch(self, request):
        cfg = BgpGlobalConfig.get_solo()
        serializer = BgpGlobalConfigSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        GoBgpConfigWriter.sync_to_file()
        return Response(serializer.data)

    def put(self, request):
        return self.patch(request)


class BgpPeerConfigViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing BGP peering sessions with backbone routers.
    Supports IPv4/IPv6 transport, eBGP multi-hop, MD5 authentication, Route Reflector client flags,
    and runtime synchronization with the active BGP backend (GoBGP).
    """
    queryset = BgpPeerConfig.objects.all()
    serializer_class = BgpPeerConfigSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        peer = serializer.save()
        backend = BgpManager.get_active_backend()
        backend.add_peer(peer)
        GoBgpConfigWriter.sync_to_file()

    def perform_update(self, serializer):
        peer = serializer.save()
        backend = BgpManager.get_active_backend()
        backend.update_peer(peer)
        GoBgpConfigWriter.sync_to_file()

    def perform_destroy(self, instance):
        addr = instance.neighbor_address
        instance.delete()
        backend = BgpManager.get_active_backend()
        backend.delete_peer(addr)
        GoBgpConfigWriter.sync_to_file()

    @action(detail=True, methods=['post'], url_path='reset')
    def reset(self, request, pk=None):
        """Trigger a soft or hard session reset for this peer."""
        peer = self.get_object()
        soft = request.data.get('soft', True)
        backend = BgpManager.get_active_backend()
        success = backend.reset_peer(peer.neighbor_address, soft=soft)
        if success:
            mode = "Soft" if soft else "Hard"
            return Response({'detail': f"{mode} reset successfully sent to {peer.neighbor_address}."})
        return Response(
            {'detail': f"Failed to reset session for {peer.neighbor_address}."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @action(detail=False, methods=['post'], url_path='sync')
    def sync_all(self, request):
        """Re-synchronize all active peers with the BGP stack and write configuration."""
        backend = BgpManager.get_active_backend()
        result = backend.sync_all_peers()
        GoBgpConfigWriter.sync_to_file()
        return Response(result)

    @action(detail=False, methods=['get'], url_path='sessions')
    def unified_sessions(self, request):
        """Return the consolidated single view of both configured and discovered BGP peering sessions."""
        sessions = PeerReconciliationService.get_unified_sessions()
        return Response(sessions)

    @action(detail=False, methods=['post'], url_path='reconcile')
    def reconcile(self, request):
        """Execute active reconciliation between DB intent and GoBGP live runtime."""
        stats = PeerReconciliationService.reconcile()
        return Response(stats)

    @action(detail=False, methods=['post'], url_path='adopt')
    def adopt_discovered(self, request):
        """Adopt an unmanaged discovered BGP neighbor into persistent database configuration."""
        serializer = BgpPeerConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        peer = serializer.save()
        backend = BgpManager.get_active_backend()
        backend.add_peer(peer)
        GoBgpConfigWriter.sync_to_file()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

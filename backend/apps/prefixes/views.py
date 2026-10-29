from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from apps.bgp_engine.permissions import IsOperatorOrReadOnly
from .models import IpPrefix
from .serializers import IpPrefixSerializer, AsnImportRequestSerializer
from .services.asn_discovery import AsnDiscoveryService


class IpPrefixPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class IpPrefixViewSet(viewsets.ModelViewSet):
    """
    CRUD API for IP Prefix Inventory.
    Supports filtering by ip_version (?ip_version=4 or 6), origin_asn, source, and search by prefix/name.
    """
    queryset = IpPrefix.objects.all()
    serializer_class = IpPrefixSerializer
    permission_classes = [IsOperatorOrReadOnly]
    pagination_class = IpPrefixPagination

    def get_queryset(self):
        qs = super().get_queryset()
        ip_version = self.request.query_params.get('ip_version')
        if ip_version and ip_version in ['4', '6']:
            qs = qs.filter(ip_version=int(ip_version))

        source = self.request.query_params.get('source')
        if source:
            qs = qs.filter(source=source)

        asn = self.request.query_params.get('asn')
        if asn and asn.isdigit():
            qs = qs.filter(origin_asn=int(asn))

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(prefix__icontains=search) | qs.filter(name__icontains=search)

        return qs

    @action(detail=False, methods=['post'], url_path='import-asn')
    def import_asn(self, request):
        """Discovers and imports prefixes for an ASN from RIPEstat."""
        req_serializer = AsnImportRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)

        asn = req_serializer.validated_data['asn']
        tag = req_serializer.validated_data.get('tag', '')
        import_v4 = req_serializer.validated_data.get('import_v4', True)
        import_v6 = req_serializer.validated_data.get('import_v6', True)

        try:
            result = AsnDiscoveryService.import_prefixes_for_asn(
                asn,
                tag=tag,
                import_v4=import_v4,
                import_v6=import_v6
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'detail': f'Error importing prefixes for AS{asn}: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

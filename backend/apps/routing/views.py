import logging
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.bgp_engine.permissions import IsAdminOrReadOnly, IsOperatorOrReadOnly
from apps.bgp_engine.manager import BgpManager
from apps.prefixes.models import IpPrefix
from apps.flowspec.models import FlowspecRule
from .models import PseudoRib, BgpCommunity, Rib, BgpAnnouncement
from .serializers import (
    PseudoRibSerializer,
    BgpCommunitySerializer,
    RibSerializer,
    BgpAnnouncementSerializer,
)

logger = logging.getLogger(__name__)


class PseudoRibViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Pseudo-RIB routing policy templates and containers.
    """
    queryset = PseudoRib.objects.prefetch_related('communities', 'prefixes', 'flowspec_rules').all()
    serializer_class = PseudoRibSerializer
    permission_classes = [IsOperatorOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        afi = self.request.query_params.get('afi_safi')
        if afi:
            qs = qs.filter(afi_safi=afi)
        ip_version = self.request.query_params.get('ip_version')
        if ip_version and ip_version in ['4', '6']:
            qs = qs.filter(ip_version=int(ip_version))
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(description__icontains=search)
        return qs

    @action(detail=True, methods=['post'], url_path='add-prefix')
    def add_prefix(self, request, pk=None):
        pseudo_rib = self.get_object()
        prefix_id = request.data.get('prefix_id')
        if not prefix_id:
            return Response({'detail': 'prefix_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            prefix = IpPrefix.objects.get(id=prefix_id)
        except IpPrefix.DoesNotExist:
            return Response({'detail': 'Prefix not found'}, status=status.HTTP_404_NOT_FOUND)

        if prefix.ip_version != pseudo_rib.ip_version:
            return Response(
                {'detail': f"Cannot add IPv{prefix.ip_version} prefix to IPv{pseudo_rib.ip_version} Pseudo-RIB"},
                status=status.HTTP_400_BAD_REQUEST
            )

        pseudo_rib.prefixes.add(prefix)
        serializer = self.get_serializer(pseudo_rib)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-prefix')
    def remove_prefix(self, request, pk=None):
        pseudo_rib = self.get_object()
        prefix_id = request.data.get('prefix_id')
        if not prefix_id:
            return Response({'detail': 'prefix_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        pseudo_rib.prefixes.remove(prefix_id)
        serializer = self.get_serializer(pseudo_rib)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='add-flowspec')
    def add_flowspec(self, request, pk=None):
        pseudo_rib = self.get_object()
        if 'flowspec' not in pseudo_rib.afi_safi:
            return Response(
                {'detail': 'Cannot attach Flowspec rules to a unicast Pseudo-RIB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        rule_id = request.data.get('rule_id')
        if not rule_id:
            return Response({'detail': 'rule_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rule = FlowspecRule.objects.get(id=rule_id)
        except FlowspecRule.DoesNotExist:
            return Response({'detail': 'Flowspec rule not found'}, status=status.HTTP_404_NOT_FOUND)

        pseudo_rib.flowspec_rules.add(rule)
        serializer = self.get_serializer(pseudo_rib)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-flowspec')
    def remove_flowspec(self, request, pk=None):
        pseudo_rib = self.get_object()
        rule_id = request.data.get('rule_id')
        if not rule_id:
            return Response({'detail': 'rule_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        pseudo_rib.flowspec_rules.remove(rule_id)
        serializer = self.get_serializer(pseudo_rib)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BgpCommunityViewSet(viewsets.ModelViewSet):
    """
    CRUD API for BGP Community tags attached to Pseudo-RIB profiles.
    """
    queryset = BgpCommunity.objects.select_related('pseudo_rib').all()
    serializer_class = BgpCommunitySerializer
    permission_classes = [IsOperatorOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        rib_id = self.request.query_params.get('pseudo_rib')
        if rib_id:
            qs = qs.filter(pseudo_rib_id=rib_id)
        return qs


class RibViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Named Master Routing Information Bases (RIB).
    Provides the master 'push' action to compile and inject all routes into GoBGP.
    """
    queryset = Rib.objects.prefetch_related(
        'pseudo_ribs__communities',
        'pseudo_ribs__prefixes',
        'pseudo_ribs__flowspec_rules'
    ).all()
    serializer_class = RibSerializer
    permission_classes = [IsOperatorOrReadOnly]

    @action(detail=True, methods=['post'], url_path='push')
    def push(self, request, pk=None):
        """
        Compiles all member routes from all attached Pseudo-RIBs and reconciles
        with the live GoBGP speaker (injecting newly compiled, withdrawing obsolete).
        """
        rib = self.get_object()
        user = request.user if request.user.is_authenticated else None
        now = timezone.now()

        active_announcements_keys = set()
        errors = []

        with transaction.atomic():
            for pseudo_rib in rib.pseudo_ribs.all():
                afi = pseudo_rib.afi_safi
                std_communities = list(
                    pseudo_rib.communities.filter(community_type=BgpCommunity.TYPE_STANDARD).values_list('value', flat=True)
                )
                large_communities = list(
                    pseudo_rib.communities.filter(community_type=BgpCommunity.TYPE_LARGE).values_list('value', flat=True)
                )

                # 1. Unicast Routes (IPv4 / IPv6)
                if 'unicast' in afi:
                    for prefix in pseudo_rib.prefixes.all():
                        prefix_str = str(prefix.prefix)
                        key = f"unicast:{afi}:{prefix_str}"
                        active_announcements_keys.add(key)

                        try:
                            ok = BgpManager.inject_unicast_route(
                                prefix=prefix_str,
                                next_hop=pseudo_rib.next_hop,
                                communities=std_communities,
                                large_communities=large_communities,
                                med=pseudo_rib.med,
                                local_pref=pseudo_rib.local_pref,
                                as_path_prepend=pseudo_rib.as_path_prepend,
                                origin=pseudo_rib.origin,
                                afi_safi=afi,
                            )
                            ann, _ = BgpAnnouncement.objects.get_or_create(
                                rib=rib,
                                pseudo_rib=pseudo_rib,
                                prefix=prefix,
                                defaults={'created_by': user}
                            )
                            ann.afi_safi = afi
                            ann.route_repr = prefix_str
                            ann.next_hop = pseudo_rib.next_hop
                            ann.communities = std_communities
                            ann.large_communities = large_communities
                            ann.is_active = True
                            ann.programmed_in_rib = ok
                            ann.status = BgpAnnouncement.STATUS_ACTIVE if ok else BgpAnnouncement.STATUS_ERROR
                            ann.error_message = '' if ok else 'BGP engine failed to inject route'
                            ann.last_synced_at = now
                            ann.save()
                        except Exception as e:
                            logger.exception(f"Error injecting unicast route {prefix_str}")
                            errors.append(f"{prefix_str}: {str(e)}")

                # 2. Flowspec Routes
                elif 'flowspec' in afi:
                    for rule in pseudo_rib.flowspec_rules.all():
                        rule_dict = {
                            "id": rule.id,
                            "name": rule.name,
                            "addr_fam": rule.addr_fam,
                            "dst_prefix": rule.dst_prefix,
                            "src_prefix": rule.src_prefix,
                            "proto_number": rule.proto_number,
                            "port": rule.port,
                            "src_port": rule.src_port,
                            "dst_port": rule.dst_port,
                            "tcp_flags": rule.tcp_flags,
                            "icmp_type": rule.icmp_type,
                            "icmp_code": rule.icmp_code,
                            "packet_len": rule.packet_len,
                            "dscp": rule.dscp,
                            "ip_frag": rule.ip_frag,
                            "action": rule.action,
                            "action_value": rule.action_value,
                        }
                        key = f"flowspec:{afi}:{rule.id}"
                        active_announcements_keys.add(key)

                        try:
                            ok = BgpManager.inject_flowspec_rule(rule_dict)
                            route_summary = f"[dst: {rule.dst_prefix or 'any'}, proto: {rule.proto_number or 'any'}, dport: {rule.dst_port or 'any'}] -> {rule.action}"
                            ann, _ = BgpAnnouncement.objects.get_or_create(
                                rib=rib,
                                pseudo_rib=pseudo_rib,
                                flowspec_rule=rule,
                                defaults={'created_by': user}
                            )
                            ann.afi_safi = afi
                            ann.route_repr = route_summary
                            ann.communities = std_communities
                            ann.large_communities = large_communities
                            ann.action = rule.action
                            ann.is_active = True
                            ann.programmed_in_rib = ok
                            ann.status = BgpAnnouncement.STATUS_ACTIVE if ok else BgpAnnouncement.STATUS_ERROR
                            ann.error_message = '' if ok else 'BGP engine failed to inject Flowspec rule'
                            ann.last_synced_at = now
                            ann.save()
                        except Exception as e:
                            logger.exception(f"Error injecting Flowspec rule {rule.id}")
                            errors.append(f"Flowspec #{rule.id}: {str(e)}")

            # 3. Withdraw any announcements that were previously active under this RIB but removed
            obsolete_announcements = BgpAnnouncement.objects.filter(rib=rib, is_active=True)
            for ann in obsolete_announcements:
                if ann.prefix:
                    key = f"unicast:{ann.afi_safi}:{ann.prefix.prefix}"
                    if key not in active_announcements_keys:
                        try:
                            BgpManager.withdraw_unicast_route(prefix=str(ann.prefix.prefix), afi_safi=ann.afi_safi)
                            ann.is_active = False
                            ann.programmed_in_rib = False
                            ann.status = BgpAnnouncement.STATUS_WITHDRAWN
                            ann.last_synced_at = now
                            ann.save()
                        except Exception as e:
                            logger.exception(f"Error withdrawing obsolete route {ann.prefix.prefix}")
                elif ann.flowspec_rule:
                    key = f"flowspec:{ann.afi_safi}:{ann.flowspec_rule.id}"
                    if key not in active_announcements_keys:
                        try:
                            rule = ann.flowspec_rule
                            rule_dict = {
                                "id": rule.id,
                                "name": rule.name,
                                "addr_fam": rule.addr_fam,
                                "dst_prefix": rule.dst_prefix,
                                "src_prefix": rule.src_prefix,
                                "proto_number": rule.proto_number,
                                "port": rule.port,
                                "src_port": rule.src_port,
                                "dst_port": rule.dst_port,
                                "tcp_flags": rule.tcp_flags,
                                "icmp_type": rule.icmp_type,
                                "icmp_code": rule.icmp_code,
                                "packet_len": rule.packet_len,
                                "dscp": rule.dscp,
                                "ip_frag": rule.ip_frag,
                                "action": rule.action,
                                "action_value": rule.action_value,
                            }
                            BgpManager.withdraw_flowspec_rule(rule_dict)
                            ann.is_active = False
                            ann.programmed_in_rib = False
                            ann.status = BgpAnnouncement.STATUS_WITHDRAWN
                            ann.last_synced_at = now
                            ann.save()
                        except Exception as e:
                            logger.exception(f"Error withdrawing obsolete Flowspec rule {ann.flowspec_rule.id}")

            # Update active Rib status
            Rib.objects.exclude(id=rib.id).update(is_active=False)
            rib.is_active = True
            rib.status = Rib.STATUS_ERROR if errors else Rib.STATUS_SYNCED
            rib.last_pushed_at = now
            rib.save()

        serializer = self.get_serializer(rib)
        return Response({
            'rib': serializer.data,
            'pushed_count': len(active_announcements_keys),
            'errors': errors,
        }, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)


class BgpAnnouncementViewSet(viewsets.ModelViewSet):
    """
    Global Loc-RIB Inspector and control plane across all AFI/SAFIs.
    """
    queryset = BgpAnnouncement.objects.select_related('prefix', 'pseudo_rib', 'flowspec_rule', 'rib', 'created_by').all()
    serializer_class = BgpAnnouncementSerializer
    permission_classes = [IsOperatorOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()

        rib_id = self.request.query_params.get('rib')
        if rib_id:
            qs = qs.filter(rib_id=rib_id)

        pseudo_rib_id = self.request.query_params.get('pseudo_rib')
        if pseudo_rib_id:
            qs = qs.filter(pseudo_rib_id=pseudo_rib_id)

        afi = self.request.query_params.get('afi_safi')
        if afi and afi != 'ALL':
            qs = qs.filter(afi_safi=afi)

        st = self.request.query_params.get('status')
        if st and st != 'ALL':
            qs = qs.filter(status=st.upper())

        # Flowspec tuple filters
        dst = self.request.query_params.get('dst_prefix')
        if dst:
            qs = qs.filter(route_repr__icontains=dst) | qs.filter(prefix__prefix__icontains=dst) | qs.filter(flowspec_rule__dst_prefix__icontains=dst)

        proto = self.request.query_params.get('proto_number')
        if proto:
            qs = qs.filter(flowspec_rule__proto_number=proto)

        port = self.request.query_params.get('port')
        if port:
            qs = qs.filter(flowspec_rule__dst_port__icontains=port) | qs.filter(flowspec_rule__src_port__icontains=port) | qs.filter(flowspec_rule__port__icontains=port)

        action_param = self.request.query_params.get('action')
        if action_param and action_param != 'ALL':
            qs = qs.filter(action=action_param)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(route_repr__icontains=search) | qs.filter(pseudo_rib__name__icontains=search)

        return qs

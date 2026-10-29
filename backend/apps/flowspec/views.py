import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import FlowspecRule
from .serializers import FlowspecRuleSerializer
from apps.bgp_engine.manager import BgpManager
from apps.bgp_engine.permissions import IsOperatorOrReadOnly

logger = logging.getLogger(__name__)


class FlowspecRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing BGP Flowspec mitigation rules.
    Provides standard list, create, retrieve, update, delete,
    plus an action to toggle live BGP RIB injection.
    Requires Operator or Admin role for any mutations.
    """
    queryset = FlowspecRule.objects.all()
    serializer_class = FlowspecRuleSerializer
    permission_classes = [IsOperatorOrReadOnly]

    def perform_create(self, serializer):
        rule = serializer.save()
        if rule.is_active:
            try:
                backend = BgpManager.get_active_backend()
                backend.add_flowspec_rule(serializer.data)
            except Exception as e:
                logger.error(f"Failed to inject Flowspec rule #{rule.id} into BGP backend: {e}")

    def perform_update(self, serializer):
        rule = serializer.save()
        try:
            backend = BgpManager.get_active_backend()
            if rule.is_active:
                backend.add_flowspec_rule(serializer.data)
            else:
                backend.delete_flowspec_rule(serializer.data)
        except Exception as e:
            logger.error(f"Failed to update Flowspec rule #{rule.id} in BGP backend: {e}")

    def perform_destroy(self, instance):
        if instance.is_active:
            try:
                backend = BgpManager.get_active_backend()
                serializer = self.get_serializer(instance)
                backend.delete_flowspec_rule(serializer.data)
            except Exception as e:
                logger.error(f"Failed to withdraw Flowspec rule #{instance.id} from BGP backend: {e}")
        instance.delete()

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle active status in BGP daemon."""
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()

        try:
            backend = BgpManager.get_active_backend()
            data = self.get_serializer(rule).data
            if rule.is_active:
                backend.add_flowspec_rule(data)
            else:
                backend.delete_flowspec_rule(data)
        except Exception as e:
            logger.error(f"Failed to toggle rule #{rule.id} in BGP backend: {e}")

        return Response({
            'id': rule.id,
            'is_active': rule.is_active,
            'message': f"Rule #{rule.id} is now {'active in RIB' if rule.is_active else 'withdrawn'}"
        })

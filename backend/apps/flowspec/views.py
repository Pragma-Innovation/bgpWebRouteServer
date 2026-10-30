import logging
from rest_framework import viewsets
from .models import FlowspecRule
from .serializers import FlowspecRuleSerializer
from apps.bgp_engine.permissions import IsOperatorOrReadOnly

logger = logging.getLogger(__name__)


class FlowspecRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing BGP Flowspec mitigation rule assets (RFC 5575 / RFC 8955).
    Provides standard list, create, retrieve, update, and delete actions.
    Per Invariant 1 (3-Tier Routing Architecture), injection into the live BGP
    Loc-RIB occurs when the rule is attached to a Pseudo-RIB and synchronized
    via Master RIB push.
    Requires Operator or Admin role for any mutations.
    """
    queryset = FlowspecRule.objects.all().prefetch_related('pseudo_ribs')
    serializer_class = FlowspecRuleSerializer
    permission_classes = [IsOperatorOrReadOnly]


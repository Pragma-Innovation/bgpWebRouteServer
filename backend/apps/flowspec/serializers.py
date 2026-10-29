from rest_framework import serializers
from .models import FlowspecRule


class FlowspecRuleSerializer(serializers.ModelSerializer):
    """Serializer for FlowspecRule CRUD operations."""

    class Meta:
        model = FlowspecRule
        fields = [
            'id',
            'name',
            'description',
            'is_active',
            'addr_fam',
            'dst_prefix',
            'src_prefix',
            'proto_number',
            'port',
            'src_port',
            'dst_port',
            'tcp_flags',
            'icmp_type',
            'icmp_code',
            'packet_len',
            'dscp',
            'ip_frag',
            'action',
            'action_value',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

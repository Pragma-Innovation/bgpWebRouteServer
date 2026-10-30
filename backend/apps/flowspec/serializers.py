from rest_framework import serializers
from .models import FlowspecRule


class FlowspecRuleSerializer(serializers.ModelSerializer):
    """Serializer for FlowspecRule CRUD operations."""
    pseudo_ribs = serializers.SerializerMethodField()

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
            'pseudo_ribs',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'pseudo_ribs', 'created_at', 'updated_at']

    def get_pseudo_ribs(self, obj):
        return [
            {'id': pr.id, 'name': pr.name, 'afi_safi': pr.afi_safi}
            for pr in obj.pseudo_ribs.all()
        ]

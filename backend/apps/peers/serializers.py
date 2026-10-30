from rest_framework import serializers
from .models import BgpPeerConfig, BgpGlobalConfig


class BgpGlobalConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BgpGlobalConfig
        fields = [
            'id',
            'local_as',
            'router_id',
            'listen_port',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class BgpPeerConfigSerializer(serializers.ModelSerializer):
    session_type = serializers.CharField(read_only=True)

    class Meta:
        model = BgpPeerConfig
        fields = [
            'id',
            'neighbor_address',
            'ip_version',
            'peer_as',
            'session_type',
            'description',
            'is_enabled',
            'multihop_enabled',
            'multihop_ttl',
            'md5_password',
            'passive_mode',
            'hold_time',
            'keepalive_interval',
            'families',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'ip_version', 'session_type', 'created_at', 'updated_at']

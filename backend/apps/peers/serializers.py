from rest_framework import serializers
from .models import BgpPeerConfig


class BgpPeerConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BgpPeerConfig
        fields = [
            'id',
            'neighbor_address',
            'peer_as',
            'description',
            'is_enabled',
            'passive_mode',
            'hold_time',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

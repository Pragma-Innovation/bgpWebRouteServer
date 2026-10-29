from rest_framework import serializers
from .models import IpPrefix


class IpPrefixSerializer(serializers.ModelSerializer):
    class Meta:
        model = IpPrefix
        fields = [
            'id',
            'prefix',
            'ip_version',
            'name',
            'description',
            'source',
            'origin_asn',
            'tags',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'ip_version', 'created_at', 'updated_at']


class AsnImportRequestSerializer(serializers.Serializer):
    asn = serializers.IntegerField(min_value=1, max_value=4294967295, help_text="Autonomous System Number (e.g. 15169)")
    tag = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    import_v4 = serializers.BooleanField(default=True, required=False)
    import_v6 = serializers.BooleanField(default=True, required=False)

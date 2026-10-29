from rest_framework import serializers
from apps.prefixes.models import IpPrefix
from apps.prefixes.serializers import IpPrefixSerializer
from apps.flowspec.models import FlowspecRule
from apps.flowspec.serializers import FlowspecRuleSerializer
from .models import PseudoRib, BgpCommunity, Rib, BgpAnnouncement


class BgpCommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = BgpCommunity
        fields = ['id', 'pseudo_rib', 'community_type', 'value', 'description']
        extra_kwargs = {'pseudo_rib': {'required': False}}


class PseudoRibSerializer(serializers.ModelSerializer):
    communities = BgpCommunitySerializer(many=True, read_only=True)
    communities_input = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of community objects: [{'type': 'STANDARD', 'value': '65535:666'}]"
    )
    prefixes_details = IpPrefixSerializer(source='prefixes', many=True, read_only=True)
    prefixes_count = serializers.IntegerField(source='prefixes.count', read_only=True)
    flowspec_rules_details = FlowspecRuleSerializer(source='flowspec_rules', many=True, read_only=True)
    flowspec_rules_count = serializers.IntegerField(source='flowspec_rules.count', read_only=True)

    class Meta:
        model = PseudoRib
        fields = [
            'id',
            'name',
            'description',
            'afi_safi',
            'ip_version',
            'next_hop',
            'local_pref',
            'med',
            'as_path_prepend',
            'origin',
            'is_default',
            'communities',
            'communities_input',
            'prefixes',
            'prefixes_details',
            'prefixes_count',
            'flowspec_rules',
            'flowspec_rules_details',
            'flowspec_rules_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'ip_version', 'created_at', 'updated_at']

    def create(self, validated_data):
        communities_data = validated_data.pop('communities_input', [])
        prefixes = validated_data.pop('prefixes', [])
        flowspec_rules = validated_data.pop('flowspec_rules', [])

        pseudo_rib = PseudoRib.objects.create(**validated_data)

        for comm in communities_data:
            BgpCommunity.objects.create(
                pseudo_rib=pseudo_rib,
                community_type=comm.get('type', comm.get('community_type', BgpCommunity.TYPE_STANDARD)),
                value=comm.get('value', '').strip(),
                description=comm.get('description', '')
            )

        if prefixes:
            pseudo_rib.prefixes.set(prefixes)
        if flowspec_rules:
            pseudo_rib.flowspec_rules.set(flowspec_rules)

        return pseudo_rib

    def update(self, instance, validated_data):
        communities_data = validated_data.pop('communities_input', None)
        prefixes = validated_data.pop('prefixes', None)
        flowspec_rules = validated_data.pop('flowspec_rules', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if communities_data is not None:
            instance.communities.all().delete()
            for comm in communities_data:
                BgpCommunity.objects.create(
                    pseudo_rib=instance,
                    community_type=comm.get('type', comm.get('community_type', BgpCommunity.TYPE_STANDARD)),
                    value=comm.get('value', '').strip(),
                    description=comm.get('description', '')
                )

        if prefixes is not None:
            instance.prefixes.set(prefixes)
        if flowspec_rules is not None:
            instance.flowspec_rules.set(flowspec_rules)

        return instance


class RibSerializer(serializers.ModelSerializer):
    pseudo_ribs_details = PseudoRibSerializer(source='pseudo_ribs', many=True, read_only=True)
    pseudo_ribs_count = serializers.IntegerField(source='pseudo_ribs.count', read_only=True)
    total_routes_count = serializers.SerializerMethodField()

    class Meta:
        model = Rib
        fields = [
            'id',
            'name',
            'description',
            'pseudo_ribs',
            'pseudo_ribs_details',
            'pseudo_ribs_count',
            'total_routes_count',
            'is_active',
            'status',
            'last_pushed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'last_pushed_at', 'created_at', 'updated_at']

    def get_total_routes_count(self, obj) -> int:
        total = 0
        for pr in obj.pseudo_ribs.all():
            if 'flowspec' in pr.afi_safi:
                total += pr.flowspec_rules.count()
            else:
                total += pr.prefixes.count()
        return total


class BgpAnnouncementSerializer(serializers.ModelSerializer):
    pseudo_rib_name = serializers.CharField(source='pseudo_rib.name', read_only=True)
    rib_name = serializers.CharField(source='rib.name', read_only=True)
    prefix_cidr = serializers.CharField(source='prefix.prefix', read_only=True)
    flowspec_tuple = serializers.SerializerMethodField()

    class Meta:
        model = BgpAnnouncement
        fields = [
            'id',
            'rib',
            'rib_name',
            'pseudo_rib',
            'pseudo_rib_name',
            'afi_safi',
            'prefix',
            'prefix_cidr',
            'flowspec_rule',
            'flowspec_tuple',
            'route_repr',
            'next_hop',
            'communities',
            'large_communities',
            'action',
            'is_active',
            'programmed_in_rib',
            'status',
            'error_message',
            'created_by',
            'created_at',
            'updated_at',
            'last_synced_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']

    def get_flowspec_tuple(self, obj):
        if not obj.flowspec_rule:
            return None
        rule = obj.flowspec_rule
        return {
            'id': rule.id,
            'name': rule.name,
            'addr_fam': rule.addr_fam,
            'dst_prefix': rule.dst_prefix,
            'src_prefix': rule.src_prefix,
            'proto_number': rule.proto_number,
            'port': rule.port,
            'src_port': rule.src_port,
            'dst_port': rule.dst_port,
            'tcp_flags': rule.tcp_flags,
            'action': rule.action,
            'action_value': rule.action_value,
        }

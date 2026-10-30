from django.contrib import admin
from .models import BgpPeerConfig, BgpGlobalConfig


@admin.register(BgpGlobalConfig)
class BgpGlobalConfigAdmin(admin.ModelAdmin):
    list_display = ('local_as', 'router_id', 'listen_port', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(BgpPeerConfig)
class BgpPeerConfigAdmin(admin.ModelAdmin):
    list_display = (
        'neighbor_address',
        'peer_as',
        'session_type',
        'ip_version',
        'multihop_enabled',
        'is_enabled',
        'description',
        'created_at'
    )
    list_filter = ('is_enabled', 'multihop_enabled', 'passive_mode')
    search_fields = ('neighbor_address', 'description', 'peer_as')
    readonly_fields = ('ip_version', 'created_at', 'updated_at')

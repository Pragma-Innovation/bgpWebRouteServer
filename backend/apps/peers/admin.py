from django.contrib import admin
from .models import BgpPeerConfig


@admin.register(BgpPeerConfig)
class BgpPeerConfigAdmin(admin.ModelAdmin):
    list_display = ('neighbor_address', 'peer_as', 'description', 'is_enabled', 'passive_mode', 'created_at')
    list_filter = ('is_enabled', 'passive_mode')
    search_fields = ('neighbor_address', 'description', 'peer_as')
    readonly_fields = ('created_at', 'updated_at')

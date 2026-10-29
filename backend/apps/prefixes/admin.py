from django.contrib import admin
from .models import IpPrefix


@admin.register(IpPrefix)
class IpPrefixAdmin(admin.ModelAdmin):
    list_display = ('prefix', 'ip_version', 'name', 'source', 'origin_asn', 'created_at')
    list_filter = ('ip_version', 'source')
    search_fields = ('prefix', 'name', 'description')

from django.contrib import admin
from .models import FlowspecRule


@admin.register(FlowspecRule)
class FlowspecRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'addr_fam', 'dst_prefix', 'src_prefix', 'action', 'is_active', 'created_at')
    list_filter = ('addr_fam', 'action', 'is_active')
    search_fields = ('name', 'description', 'dst_prefix', 'src_prefix')
    readonly_fields = ('created_at', 'updated_at')

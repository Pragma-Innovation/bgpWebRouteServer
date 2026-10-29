from django.contrib import admin
from .models import PseudoRib, BgpCommunity, BgpAnnouncement


class BgpCommunityInline(admin.TabularInline):
    model = BgpCommunity
    extra = 1


@admin.register(PseudoRib)
class PseudoRibAdmin(admin.ModelAdmin):
    list_display = ('name', 'afi_safi', 'ip_version', 'next_hop', 'local_pref', 'med', 'is_default')
    list_filter = ('afi_safi', 'ip_version', 'is_default')
    search_fields = ('name', 'description')
    inlines = [BgpCommunityInline]


@admin.register(BgpCommunity)
class BgpCommunityAdmin(admin.ModelAdmin):
    list_display = ('value', 'community_type', 'pseudo_rib', 'description')
    list_filter = ('community_type',)
    search_fields = ('value', 'description')


@admin.register(BgpAnnouncement)
class BgpAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('prefix', 'pseudo_rib', 'is_active', 'programmed_in_rib', 'status', 'last_synced_at')
    list_filter = ('is_active', 'status', 'programmed_in_rib')
    search_fields = ('prefix__prefix', 'pseudo_rib__name')

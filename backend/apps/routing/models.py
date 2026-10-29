import re
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.prefixes.models import IpPrefix

User = get_user_model()


class PseudoRib(models.Model):
    """
    Pseudo-RIB (Routing Policy Profile & Container):
    A reusable template defining BGP attributes (Next-Hop, Communities, MED, LocalPref)
    and containing its member route announcements (IP Prefixes for unicast, or Flowspec NLRIs).
    """
    AFI_IPV4_UNICAST = 'ipv4-unicast'
    AFI_IPV6_UNICAST = 'ipv6-unicast'
    AFI_IPV4_FLOWSPEC = 'ipv4-flowspec'
    AFI_IPV6_FLOWSPEC = 'ipv6-flowspec'

    AFI_CHOICES = [
        (AFI_IPV4_UNICAST, 'IPv4 Unicast (AFI 1, SAFI 1)'),
        (AFI_IPV6_UNICAST, 'IPv6 Unicast (AFI 2, SAFI 1)'),
        (AFI_IPV4_FLOWSPEC, 'IPv4 Flowspec (AFI 1, SAFI 133)'),
        (AFI_IPV6_FLOWSPEC, 'IPv6 Flowspec (AFI 2, SAFI 133)'),
    ]

    ORIGIN_IGP = 'igp'
    ORIGIN_EGP = 'egp'
    ORIGIN_INCOMPLETE = 'incomplete'
    ORIGIN_CHOICES = [
        (ORIGIN_IGP, 'IGP'),
        (ORIGIN_EGP, 'EGP'),
        (ORIGIN_INCOMPLETE, 'Incomplete'),
    ]

    name = models.CharField(max_length=128, unique=True, help_text="Profile name (e.g. RTBH Backbone Blackhole)")
    description = models.TextField(blank=True)
    afi_safi = models.CharField(max_length=32, choices=AFI_CHOICES, default=AFI_IPV4_UNICAST)
    ip_version = models.PositiveSmallIntegerField(default=4, editable=False)

    # Reusable BGP Path Attributes
    next_hop = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="BGP Next-Hop (e.g. 192.0.2.1 RFC 5737 discard or 2001:db8::1)"
    )
    local_pref = models.PositiveIntegerField(default=100, help_text="BGP Local Preference")
    med = models.PositiveIntegerField(null=True, blank=True, help_text="Multi-Exit Discriminator")
    as_path_prepend = models.CharField(max_length=128, blank=True, help_text="AS Path prepend string (e.g. 65000 65000)")
    origin = models.CharField(max_length=16, choices=ORIGIN_CHOICES, default=ORIGIN_IGP)

    is_default = models.BooleanField(default=False, help_text="Default policy profile for this AFI")

    # Member route assets
    prefixes = models.ManyToManyField('prefixes.IpPrefix', related_name='pseudo_ribs', blank=True)
    flowspec_rules = models.ManyToManyField('flowspec.FlowspecRule', related_name='pseudo_ribs', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Pseudo-RIB'
        verbose_name_plural = 'Pseudo-RIBs'

    def clean(self):
        super().clean()
        if 'ipv6' in self.afi_safi:
            self.ip_version = 6
        else:
            self.ip_version = 4

    def save(self, *args, **kwargs):
        if 'ipv6' in self.afi_safi:
            self.ip_version = 6
        else:
            self.ip_version = 4
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.afi_safi})"


class BgpCommunity(models.Model):
    """
    BGP Community tag attached to a Pseudo-RIB.
    Supports Standard Communities (RFC 1997 / RFC 7999) and Large Communities (RFC 8092).
    """
    TYPE_STANDARD = 'STANDARD'
    TYPE_LARGE = 'LARGE'
    TYPE_EXTENDED = 'EXTENDED'

    TYPE_CHOICES = [
        (TYPE_STANDARD, 'Standard Community (ASN:Value, e.g. 65535:666)'),
        (TYPE_LARGE, 'Large Community (ASN:Function:Target, e.g. 65000:666:1)'),
        (TYPE_EXTENDED, 'Extended Community (e.g. rt:65000:100)'),
    ]

    pseudo_rib = models.ForeignKey(PseudoRib, on_delete=models.CASCADE, related_name='communities')
    community_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_STANDARD)
    value = models.CharField(max_length=64, help_text="Community string (e.g. 65535:666, BLACKHOLE, NO_EXPORT, or 65000:666:1)")
    description = models.CharField(max_length=128, blank=True)

    class Meta:
        unique_together = ('pseudo_rib', 'value')
        ordering = ['community_type', 'value']

    def clean(self):
        super().clean()
        val = self.value.strip()
        well_known = {'BLACKHOLE': '65535:666', 'NO_EXPORT': '65535:65281', 'NO_ADVERTISE': '65535:65282'}
        if val.upper() in well_known:
            val = well_known[val.upper()]
            self.value = val

        if self.community_type == self.TYPE_STANDARD:
            if not re.match(r'^\d{1,5}:\d{1,5}$', val):
                raise ValidationError({'value': f"Invalid standard community '{val}'. Format must be ASN:Value (e.g. 65535:666)."})
            asn, val_part = map(int, val.split(':'))
            if asn > 65535 or val_part > 65535:
                raise ValidationError({'value': "Standard community components cannot exceed 65535. Use Large Community for 32-bit ASNs."})
        elif self.community_type == self.TYPE_LARGE:
            if not re.match(r'^\d{1,10}:\d{1,10}:\d{1,10}$', val):
                raise ValidationError({'value': f"Invalid large community '{val}'. Format must be ASN:Action:Target (e.g. 65000:666:1)."})
            parts = list(map(int, val.split(':')))
            for p in parts:
                if p > 4294967295:
                    raise ValidationError({'value': "Large community components cannot exceed 4294967295."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.value} ({self.community_type})"


class Rib(models.Model):
    """
    Named Master Routing Information Base (RIB):
    Assembles a collection of Pseudo-RIBs and synchronizes them into the live GoBGP speaker.
    """
    STATUS_DRAFT = 'DRAFT'
    STATUS_SYNCED = 'SYNCED'
    STATUS_OUT_OF_SYNC = 'OUT_OF_SYNC'
    STATUS_ERROR = 'ERROR'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SYNCED, 'Synced to GoBGP'),
        (STATUS_OUT_OF_SYNC, 'Modified / Pending Push'),
        (STATUS_ERROR, 'Sync Error'),
    ]

    name = models.CharField(max_length=128, unique=True, help_text="RIB name (e.g. Production Loc-RIB, Lab Peering RIB)")
    description = models.TextField(blank=True)
    pseudo_ribs = models.ManyToManyField(PseudoRib, related_name='parent_ribs', blank=True)
    is_active = models.BooleanField(default=False, help_text="True if this RIB is currently deployed in GoBGP")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    last_pushed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Master RIB'
        verbose_name_plural = 'Master RIBs'

    def __str__(self):
        return f"{self.name} [{self.status}]"


class BgpAnnouncement(models.Model):
    """
    An active or staged route announcement in GoBGP's Loc-RIB.
    Represents an individual compiled route entry belonging to a Pseudo-RIB and Master RIB.
    Supports IPv4/IPv6 Unicast and Flowspec.
    """
    STATUS_DRAFT = 'DRAFT'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_WITHDRAWN = 'WITHDRAWN'
    STATUS_ERROR = 'ERROR'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft / Staged'),
        (STATUS_ACTIVE, 'Active (Programmed in GoBGP)'),
        (STATUS_WITHDRAWN, 'Withdrawn from GoBGP'),
        (STATUS_ERROR, 'Error / Sync Failed'),
    ]

    rib = models.ForeignKey(Rib, on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    pseudo_rib = models.ForeignKey(PseudoRib, on_delete=models.CASCADE, related_name='announcements')
    afi_safi = models.CharField(max_length=32, choices=PseudoRib.AFI_CHOICES, default=PseudoRib.AFI_IPV4_UNICAST)

    # Target entities
    prefix = models.ForeignKey(IpPrefix, on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    flowspec_rule = models.ForeignKey('flowspec.FlowspecRule', on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')

    # Cached compiled attributes for fast inspection & filtering
    route_repr = models.CharField(max_length=256, default='', help_text="Human-readable route representation")
    next_hop = models.GenericIPAddressField(null=True, blank=True)
    communities = models.JSONField(default=list, blank=True)
    large_communities = models.JSONField(default=list, blank=True)
    action = models.CharField(max_length=32, blank=True, help_text="Flowspec action (Drop, Shape, Redirect, Mark)")

    is_active = models.BooleanField(default=True, help_text="True if route is announced in GoBGP")
    programmed_in_rib = models.BooleanField(default=False, editable=False, help_text="Confirmed state in GoBGP speaker")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def clean(self):
        super().clean()
        if self.prefix and self.pseudo_rib:
            if self.prefix.ip_version != self.pseudo_rib.ip_version:
                raise ValidationError(
                    f"Protocol mismatch: Cannot assign IPv{self.prefix.ip_version} prefix '{self.prefix.prefix}' "
                    f"to IPv{self.pseudo_rib.ip_version} Pseudo-RIB '{self.pseudo_rib.name}'."
                )
        if self.flowspec_rule and self.pseudo_rib:
            if 'flowspec' not in self.pseudo_rib.afi_safi:
                raise ValidationError(
                    f"Type mismatch: Cannot attach Flowspec rule to unicast Pseudo-RIB '{self.pseudo_rib.name}'."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.route_repr} via {self.pseudo_rib.name} [{self.status}]"

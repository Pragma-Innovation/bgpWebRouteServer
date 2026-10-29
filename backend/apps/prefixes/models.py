import ipaddress
from django.db import models
from django.core.exceptions import ValidationError
try:
    from django.contrib.postgres.fields import CIDRField
except ImportError:
    CIDRField = None


class IpPrefix(models.Model):
    """
    Unified IP Prefix inventory model supporting IPv4 and IPv6 networks.
    Backed by PostgreSQL native CIDR type when available.
    """
    SOURCE_MANUAL = 'MANUAL'
    SOURCE_RIPE_STAT = 'RIPE_STAT'
    SOURCE_IRR = 'IRR'
    SOURCE_IMPORT = 'IMPORT'

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, 'Manual Entry'),
        (SOURCE_RIPE_STAT, 'RIPEstat / RPKI Discovery'),
        (SOURCE_IRR, 'IRR Routing Registry'),
        (SOURCE_IMPORT, 'File / Bulk Import'),
    ]

    VERSION_IPV4 = 4
    VERSION_IPV6 = 6
    VERSION_CHOICES = [
        (VERSION_IPV4, 'IPv4'),
        (VERSION_IPV6, 'IPv6'),
    ]

    if CIDRField:
        prefix = CIDRField(unique=True, help_text="Network CIDR (e.g. 198.51.100.0/24 or 2001:db8::/32)")
    else:
        prefix = models.CharField(max_length=64, unique=True, help_text="Network CIDR (e.g. 198.51.100.0/24 or 2001:db8::/32)")

    ip_version = models.PositiveSmallIntegerField(choices=VERSION_CHOICES, editable=False, db_index=True)
    name = models.CharField(max_length=128, blank=True, help_text="Asset identifier (e.g. Core Web VIPs)")
    description = models.TextField(blank=True)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    origin_asn = models.BigIntegerField(null=True, blank=True, help_text="Origin Autonomous System Number")
    tags = models.JSONField(default=list, blank=True, help_text="Categorization tags (e.g. ['production', 'dmz'])")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ip_version', 'prefix']
        verbose_name = 'IP Prefix'
        verbose_name_plural = 'IP Prefixes'

    def clean(self):
        super().clean()
        if not self.prefix:
            raise ValidationError({'prefix': 'Prefix is required.'})
        try:
            net = ipaddress.ip_network(str(self.prefix), strict=False)
            self.prefix = str(net)
            self.ip_version = net.version
        except ValueError as e:
            raise ValidationError({'prefix': f'Invalid IP prefix format: {e}'})

    def save(self, *args, **kwargs):
        if self.prefix:
            net = ipaddress.ip_network(str(self.prefix), strict=False)
            self.prefix = str(net)
            self.ip_version = net.version
        super().save(*args, **kwargs)

    def __str__(self):
        label = f"{self.prefix} ({self.name})" if self.name else str(self.prefix)
        return label

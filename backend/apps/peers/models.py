import ipaddress
from django.db import models
from django.core.exceptions import ValidationError


class BgpGlobalConfig(models.Model):
    """
    Global BGP Router settings for the local daemon.
    Singleton pattern: a single active configuration instance defines router identity,
    local ASN, and listening port.
    """
    local_as = models.BigIntegerField(
        default=65000,
        help_text="Local Autonomous System Number (ASN) of this Route Server"
    )
    router_id = models.GenericIPAddressField(
        protocol="IPv4",
        default="10.100.0.10",
        help_text="BGP Router ID (IPv4 address format)"
    )
    listen_port = models.PositiveIntegerField(
        default=179,
        help_text="TCP port for incoming BGP connections"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Global BGP Router Configuration"
        verbose_name_plural = "Global BGP Router Configuration"

    def __str__(self):
        return f"AS{self.local_as} - RouterID {self.router_id} (Port {self.listen_port})"

    @classmethod
    def get_solo(cls) -> "BgpGlobalConfig":
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class BgpPeerConfig(models.Model):
    """
    Configuration model for BGP neighbors/peers.
    Stores administrative settings, peering parameters, transport protocol,
    eBGP multi-hop, MD5 password, and negotiated AFI/SAFIs.
    """
    DEFAULT_FAMILIES = [
        "ipv4-unicast",
        "ipv6-unicast",
        "ipv4-flowspec",
        "ipv6-flowspec",
    ]

    neighbor_address = models.GenericIPAddressField(
        unique=True,
        help_text="IP address of the peering router (IPv4 or IPv6)"
    )
    ip_version = models.PositiveSmallIntegerField(
        default=4,
        editable=False,
        help_text="IP address family version (4 or 6) inferred from neighbor address"
    )
    peer_as = models.BigIntegerField(
        help_text="Autonomous System Number (ASN) of the peering router"
    )
    description = models.CharField(max_length=256, blank=True, help_text="Human-friendly peer description")
    is_enabled = models.BooleanField(default=True, help_text="Administrative status (UP or DOWN)")
    multihop_enabled = models.BooleanField(
        default=False,
        help_text="Enable eBGP multi-hop for non-directly connected peers"
    )
    multihop_ttl = models.PositiveSmallIntegerField(
        default=255,
        help_text="Time-to-Live (TTL) for eBGP multi-hop packets (1-255)"
    )
    md5_password = models.CharField(
        max_length=128,
        blank=True,
        help_text="Optional MD5 TCP authentication password"
    )
    passive_mode = models.BooleanField(
        default=False,
        help_text="Wait for incoming BGP connection rather than actively initiating TCP session"
    )
    hold_time = models.PositiveIntegerField(default=90, help_text="Hold time in seconds")
    keepalive_interval = models.PositiveIntegerField(default=30, help_text="Keepalive interval in seconds")
    families = models.JSONField(
        default=list,
        blank=True,
        help_text="Negotiated AFI/SAFI families (e.g. ['ipv4-unicast', 'ipv4-flowspec'])"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['neighbor_address']
        verbose_name = 'BGP Peer Configuration'
        verbose_name_plural = 'BGP Peer Configurations'

    def clean(self):
        super().clean()
        if not self.neighbor_address:
            raise ValidationError({'neighbor_address': 'Neighbor IP address is required.'})

        try:
            ip = ipaddress.ip_address(self.neighbor_address.strip())
            self.neighbor_address = str(ip)
            self.ip_version = ip.version
        except ValueError as e:
            raise ValidationError({'neighbor_address': f'Invalid IP address: {e}'})

        if not self.families:
            self.families = self.DEFAULT_FAMILIES.copy()

        if self.multihop_enabled:
            if not self.multihop_ttl or self.multihop_ttl < 1 or self.multihop_ttl > 255:
                self.multihop_ttl = 255
        else:
            self.multihop_ttl = 1

    def save(self, *args, **kwargs):
        if self.neighbor_address:
            ip = ipaddress.ip_address(self.neighbor_address.strip())
            self.neighbor_address = str(ip)
            self.ip_version = ip.version
        if not self.families:
            self.families = self.DEFAULT_FAMILIES.copy()
        super().save(*args, **kwargs)

    @property
    def session_type(self) -> str:
        """Return 'iBGP' if peer_as matches local_as, otherwise 'eBGP'."""
        try:
            global_cfg = BgpGlobalConfig.get_solo()
            return "iBGP" if self.peer_as == global_cfg.local_as else "eBGP"
        except Exception:
            return "eBGP"

    def __str__(self):
        desc = f" ({self.description})" if self.description else ""
        return f"{self.session_type} AS{self.peer_as} @ {self.neighbor_address}{desc}"

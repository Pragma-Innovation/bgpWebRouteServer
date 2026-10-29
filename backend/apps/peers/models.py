from django.db import models


class BgpPeerConfig(models.Model):
    """
    Configuration model for BGP neighbors/peers.
    Stores administrative settings and policies for peering routers.
    """
    neighbor_address = models.GenericIPAddressField(
        unique=True,
        help_text="IP address of the peering router"
    )
    peer_as = models.PositiveIntegerField(
        help_text="Autonomous System Number (ASN) of the peer"
    )
    description = models.CharField(max_length=256, blank=True)
    is_enabled = models.BooleanField(default=True)
    passive_mode = models.BooleanField(
        default=False,
        help_text="Wait for incoming BGP connection rather than actively initiating"
    )
    hold_time = models.PositiveIntegerField(default=90, help_text="Hold time in seconds")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['neighbor_address']
        verbose_name = 'BGP Peer Configuration'
        verbose_name_plural = 'BGP Peer Configurations'

    def __str__(self):
        desc = f" ({self.description})" if self.description else ""
        return f"AS{self.peer_as} @ {self.neighbor_address}{desc}"

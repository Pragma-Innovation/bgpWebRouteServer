from django.db import models


class FlowspecRule(models.Model):
    """
    BGP Flowspec rule model according to RFC 5575 / RFC 8955,
    translating and modernizing the legacy BgpFsRule structure from bgpflowspectool.
    """
    ACTION_DROP = 'Drop'
    ACTION_SHAPE = 'Shape'
    ACTION_REDIRECT = 'Redirect'
    ACTION_MARK = 'Mark'

    ACTION_CHOICES = [
        (ACTION_DROP, 'Drop (Discard traffic)'),
        (ACTION_SHAPE, 'Rate-limit / Shape'),
        (ACTION_REDIRECT, 'Redirect (VRF / Next-hop)'),
        (ACTION_MARK, 'Mark (Set DSCP)'),
    ]

    FAMILY_IPV4 = 'IPv4'
    FAMILY_IPV6 = 'IPv6'

    FAMILY_CHOICES = [
        (FAMILY_IPV4, 'IPv4 Flowspec'),
        (FAMILY_IPV6, 'IPv6 Flowspec'),
    ]

    name = models.CharField(max_length=128, blank=True, help_text="Friendly rule identifier")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Whether this rule is injected into the BGP RIB")

    # Match criteria (RFC 5575 / RFC 8955)
    addr_fam = models.CharField(max_length=8, choices=FAMILY_CHOICES, default=FAMILY_IPV4)
    dst_prefix = models.CharField(max_length=64, blank=True, help_text="Destination IP/CIDR (e.g. 1.1.1.1/32)")
    src_prefix = models.CharField(max_length=64, blank=True, help_text="Source IP/CIDR (e.g. 2.2.2.2/32)")
    proto_number = models.CharField(max_length=64, blank=True, help_text="IP Protocol match (e.g. ==6, ==17)")
    port = models.CharField(max_length=64, blank=True, help_text="Source or Dest Port (e.g. ==8080)")
    src_port = models.CharField(max_length=64, blank=True, help_text="Source Port (e.g. ==80, <1024)")
    dst_port = models.CharField(max_length=64, blank=True, help_text="Destination Port (e.g. ==443)")
    tcp_flags = models.CharField(max_length=32, blank=True, help_text="TCP Flags match (e.g. =S, =SA, =!F)")
    icmp_type = models.CharField(max_length=32, blank=True, help_text="ICMP Type (e.g. ==8, ==0)")
    icmp_code = models.CharField(max_length=32, blank=True, help_text="ICMP Code (e.g. ==0, ==3)")
    packet_len = models.CharField(max_length=32, blank=True, help_text="Packet Length match (e.g. >1024)")
    dscp = models.CharField(max_length=32, blank=True, help_text="DSCP / Diffserv match (e.g. ==22)")
    ip_frag = models.CharField(max_length=32, blank=True, help_text="IP Fragmentation flags")

    # Actions
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, default=ACTION_DROP)
    action_value = models.CharField(
        max_length=64,
        blank=True,
        help_text="Parameter for Action (e.g. rate in bytes/sec for Shape, target RT for Redirect)"
    )

    # Metadata & Auditing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Flowspec Rule'
        verbose_name_plural = 'Flowspec Rules'

    def __str__(self):
        desc = self.name or f"Rule #{self.id}"
        dest = f" -> {self.dst_prefix}" if self.dst_prefix else ""
        return f"{desc} [{self.addr_fam}{dest}: {self.action}]"

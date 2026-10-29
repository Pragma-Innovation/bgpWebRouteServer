import ipaddress
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List
from ..models import IpPrefix

logger = logging.getLogger(__name__)


class AsnDiscoveryService:
    """
    Queries public routing registries & RPKI databases (via RIPEstat API)
    to automatically discover and import active BGP announced prefixes for an ASN.
    """
    RIPE_STAT_API_URL = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"

    @classmethod
    def fetch_announced_prefixes(cls, asn: int, timeout: int = 10) -> List[str]:
        """Fetch active announced prefixes for an ASN from RIPEstat."""
        url = cls.RIPE_STAT_API_URL.format(asn=asn)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "bgpWebRouteServer-AsnDiscovery/1.0",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))
                if payload.get("status") != "ok":
                    raise ValueError(f"RIPEstat API returned non-OK status: {payload.get('status')}")

                raw_prefixes = payload.get("data", {}).get("prefixes", [])
                result = []
                for item in raw_prefixes:
                    p = item.get("prefix")
                    if p:
                        result.append(p.strip())
                return result
        except urllib.error.URLError as e:
            logger.error(f"[AsnDiscovery] Failed to query RIPEstat for AS{asn}: {e}")
            raise RuntimeError(f"Network error querying RIPEstat: {e.reason if hasattr(e, 'reason') else e}")
        except Exception as e:
            logger.error(f"[AsnDiscovery] Unexpected error querying AS{asn}: {e}")
            raise

    @classmethod
    def import_prefixes_for_asn(
        cls,
        asn: int,
        tag: str = None,
        import_v4: bool = True,
        import_v6: bool = True
    ) -> Dict[str, Any]:
        """Discover and bulk-insert prefixes into IpPrefix table for IPv4, IPv6 or both."""
        prefixes = cls.fetch_announced_prefixes(asn)

        tags = [f"AS{asn}"]
        if tag and tag.strip():
            tags.append(tag.strip())

        seen_prefixes = set()
        to_create = []
        ipv4_found = 0
        ipv6_found = 0

        for p_str in prefixes:
            try:
                net = ipaddress.ip_network(p_str, strict=False)
                normalized_prefix = str(net)

                if net.version == 4:
                    ipv4_found += 1
                    if not import_v4:
                        continue
                elif net.version == 6:
                    ipv6_found += 1
                    if not import_v6:
                        continue
                else:
                    continue

                if normalized_prefix in seen_prefixes:
                    continue
                seen_prefixes.add(normalized_prefix)

                to_create.append(
                    IpPrefix(
                        prefix=normalized_prefix,
                        ip_version=net.version,
                        name=f"AS{asn} Auto-Discovered",
                        source=IpPrefix.SOURCE_RIPE_STAT,
                        origin_asn=asn,
                        tags=tags,
                    )
                )
            except ValueError:
                continue

        before_v4 = IpPrefix.objects.filter(ip_version=4).count()
        before_v6 = IpPrefix.objects.filter(ip_version=6).count()

        if to_create:
            batch_size = 1000
            for i in range(0, len(to_create), batch_size):
                IpPrefix.objects.bulk_create(to_create[i:i + batch_size], ignore_conflicts=True)

        after_v4 = IpPrefix.objects.filter(ip_version=4).count()
        after_v6 = IpPrefix.objects.filter(ip_version=6).count()

        v4_created = max(0, after_v4 - before_v4)
        v6_created = max(0, after_v6 - before_v6)
        total_created = v4_created + v6_created
        skipped_count = len(prefixes) - total_created

        return {
            "asn": asn,
            "total_found": len(prefixes),
            "ipv4_found": ipv4_found,
            "ipv6_found": ipv6_found,
            "created": total_created,
            "ipv4_created": v4_created,
            "ipv6_created": v6_created,
            "skipped_or_existing": skipped_count,
            # Backward compatibility aliases
            "discovered_count": len(prefixes),
            "imported_count": total_created,
            "duplicates_skipped": skipped_count,
            "imported_prefixes": [p.prefix for p in to_create[:100]],
        }

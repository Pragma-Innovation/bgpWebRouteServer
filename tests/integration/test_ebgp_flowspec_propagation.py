#!/usr/bin/env python3
"""
End-to-End Multi-Peer Integration Test (eBGP & iBGP):
Verifies the complete hierarchical workflow across a 3-router BIRD test lab:
- Router 1 (eBGP): bgpweb-bird (10.100.0.20, AS 65001)
- Router 2 (iBGP): bgpweb-bird-ibgp1 (10.100.0.30, AS 65000)
- Router 3 (iBGP): bgpweb-bird-ibgp2 (10.100.0.40, AS 65000)

Workflow tested:
1. Multi-Peer BGP Session Verification (eBGP + 2x iBGP).
2. Asset Creation: IP Prefixes & Flowspec NLRIs.
3. Pseudo-RIB Assignment: Add prefixes & Flowspec rules to Pseudo-RIBs.
4. Master RIB Assembly & Push: Synchronize Master RIB to GoBGP.
5. Multi-Peer Propagation Verification: Unicast RTBH and Flowspec active in all 3 routers.
6. Member Removal & Push Reconciliation: Verify clean withdrawal across all 3 routers.
7. Unified Announcements API: Test multi-facet filtering (pseudo-rib, afi_safi, tuple).
"""
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000/api/v1"
CONTAINER_CMD = "podman" if subprocess.run(["which", "podman"], capture_output=True).returncode == 0 else "docker"

BIRD_ROUTERS = [
    {"name": "bgpweb-bird", "type": "eBGP", "ip": "10.100.0.20", "asn": 65001},
    {"name": "bgpweb-bird-ibgp1", "type": "iBGP (Core 1)", "ip": "10.100.0.30", "asn": 65000},
    {"name": "bgpweb-bird-ibgp2", "type": "iBGP (Core 2)", "ip": "10.100.0.40", "asn": 65000},
]


def run_container_cmd(container: str, cmd_args: list) -> str:
    full_cmd = [CONTAINER_CMD, "exec", container, *cmd_args]
    proc = subprocess.run(full_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command '{' '.join(full_cmd)}' failed:\n{proc.stderr}")
    return proc.stdout.strip()


def get_auth_token(username: str = "operator", password: str = "bgppassword123") -> str:
    url = f"{BASE_URL}/auth/token/"
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data["access"]


def api_get(endpoint: str, token: str) -> any:
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        res = json.loads(response.read().decode("utf-8"))
        return res.get("results", res) if isinstance(res, dict) and "results" in res else res


def api_post(endpoint: str, payload: dict, token: str) -> dict:
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def api_delete(endpoint: str, token: str) -> int:
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE"
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return response.status


def main():
    print("=" * 80)
    print(" MULTI-PEER LAB: eBGP & iBGP PROPAGATION (1x eBGP + 2x iBGP ROUTERS)")
    print("=" * 80)

    # 1. Verify BGP Sessions Status for all 3 routers
    print("\n[Step 1] Verifying BGP Sessions between GoBGP (10.100.0.10) & 3 BIRD Routers...")
    for router in BIRD_ROUTERS:
        max_retries = 10
        established = False
        for attempt in range(max_retries):
            try:
                proto_status = run_container_cmd(router["name"], ["birdc", "show", "protocols", "all", "gobgp_peer"])
                if "BGP state:          Established" in proto_status:
                    print(f"  ✓ {router['name']} ({router['type']}, AS{router['asn']} @ {router['ip']}) -> Established")
                    established = True
                    break
            except Exception as e:
                pass
            time.sleep(1)

        if not established:
            print(f"  ✗ ERROR: BGP session with {router['name']} is not Established!")
            sys.exit(1)

    # 2. Authenticate as Operator
    print("\n[Step 2] Authenticating as 'operator' via Django REST JWT...")
    try:
        token = get_auth_token("operator", "bgppassword123")
        print("  ✓ Obtained JWT Access Token.")
    except Exception as e:
        print(f"  ✗ Auth failed: {e}")
        sys.exit(1)

    # 3. Create Route Assets: IP Prefix and Flowspec NLRI
    print("\n[Step 3] Creating Route Assets (IP Prefix & Flowspec Rule)...")
    prefix_data = api_post("/prefixes/", {
        "prefix": "198.51.100.77/32",
        "name": "Victim Host RTBH",
        "tags": ["rtbh-test"]
    }, token)
    prefix_id = prefix_data["id"]
    print(f"  ✓ Created IP Prefix #{prefix_id}: {prefix_data['prefix']}")

    flowspec_data = api_post("/flowspec/rules/", {
        "name": "Drop SSH Flood Attack",
        "addr_fam": "IPv4",
        "dst_prefix": "198.51.100.222/32",
        "proto_number": "6",
        "dst_port": "22",
        "action": "Drop",
        "is_active": True
    }, token)
    rule_id = flowspec_data["id"]
    print(f"  ✓ Created Flowspec Rule #{rule_id}: {flowspec_data['dst_prefix']} port 22 -> Drop")

    # 4. Find Target Pseudo-RIBs
    print("\n[Step 4] Finding Target Pseudo-RIB Policy Containers...")
    pseudo_ribs = api_get("/routing/pseudo-ribs/", token)
    rtbh_rib = next((r for r in pseudo_ribs if r["afi_safi"] == "ipv4-unicast" and ("Blackhole" in r["name"] or r.get("is_default"))), None)
    flow_rib = next((r for r in pseudo_ribs if r["afi_safi"] == "ipv4-flowspec"), None)
    assert rtbh_rib is not None, "RTBH Pseudo-RIB not found!"
    assert flow_rib is not None, "Flowspec Pseudo-RIB not found!"
    print(f"  ✓ Found Unicast Pseudo-RIB #{rtbh_rib['id']}: '{rtbh_rib['name']}' (NH: {rtbh_rib['next_hop']})")
    print(f"  ✓ Found Flowspec Pseudo-RIB #{flow_rib['id']}: '{flow_rib['name']}'")

    # 5. Add Assets into their respective Pseudo-RIBs
    print("\n[Step 5] Adding Assets into their respective Pseudo-RIB containers...")
    api_post(f"/routing/pseudo-ribs/{rtbh_rib['id']}/add-prefix/", {"prefix_id": prefix_id}, token)
    print(f"  ✓ Attached Prefix #{prefix_id} into Pseudo-RIB '{rtbh_rib['name']}'")

    api_post(f"/routing/pseudo-ribs/{flow_rib['id']}/add-flowspec/", {"rule_id": rule_id}, token)
    print(f"  ✓ Attached Flowspec Rule #{rule_id} into Pseudo-RIB '{flow_rib['name']}'")

    # 6. Find Master RIB and Push to GoBGP
    print("\n[Step 6] Pushing Master RIB ('Production Loc-RIB') to GoBGP...")
    ribs = api_get("/routing/ribs/", token)
    assert len(ribs) > 0, "No Master RIB found!"
    master_rib = ribs[0]
    push_res = api_post(f"/routing/ribs/{master_rib['id']}/push/", {}, token)
    print(f"  ✓ Master RIB pushed: {push_res.get('pushed_count')} routes synchronized to GoBGP!")

    # 7. Check GoBGP Loc-RIB for Unicast & Flowspec
    print("\n[Step 7] Checking GoBGP Global Loc-RIB via CLI...")
    time.sleep(1)
    gobgp_v4 = run_container_cmd("bgpweb-gobgp", ["gobgp", "global", "rib", "-a", "ipv4"])
    assert "198.51.100.77/32" in gobgp_v4, "Unicast RTBH route missing from GoBGP!"
    print("  ✓ GoBGP IPv4 Loc-RIB contains the RTBH route.")

    gobgp_flow = run_container_cmd("bgpweb-gobgp", ["gobgp", "global", "rib", "-a", "ipv4-flowspec"])
    assert "198.51.100.222/32" in gobgp_flow, "Flowspec rule missing from GoBGP!"
    print("  ✓ GoBGP Flowspec Loc-RIB contains the Flowspec rule.")

    # 8. Check BIRD Tables (t_unicast4 and t_flow4) across ALL 3 ROUTERS
    print("\n[Step 8] Checking BIRD Route Tables across all 3 routers (eBGP & 2x iBGP)...")
    for router in BIRD_ROUTERS:
        bird_v4 = run_container_cmd(router["name"], ["birdc", "show", "route", "table", "t_unicast4", "all"])
        assert "198.51.100.77/32" in bird_v4, f"RTBH Route missing in {router['name']} t_unicast4!"
        assert "blackhole" in bird_v4, f"{router['name']} did not set destination to blackhole!"
        assert "(65535,666)" in bird_v4 or "(65535, 666)" in bird_v4, f"RFC 7999 community missing in {router['name']}!"
        print(f"  ✓ {router['name']} ({router['type']}): 198.51.100.77/32 installed as RTD_BLACKHOLE!")

        bird_flow = run_container_cmd(router["name"], ["birdc", "show", "route", "table", "t_flow4", "all"])
        assert "198.51.100.222/32" in bird_flow, f"Flowspec route missing in {router['name']} t_flow4!"
        print(f"  ✓ {router['name']} ({router['type']}): Flowspec rule installed in t_flow4!")

    # 9. Verify Global Announcements API & Multi-Facet Filters
    print("\n[Step 9] Verifying Unified Announcements API & Filtering...")
    all_announcements = api_get("/routing/announcements/", token)
    print(f"  ✓ Total announcements in Loc-RIB API: {len(all_announcements)}")
    assert len(all_announcements) >= 2, "Expected at least 2 announcements in Loc-RIB API!"

    filtered_pr = api_get(f"/routing/announcements/?pseudo_rib={rtbh_rib['id']}", token)
    assert all(a["pseudo_rib"] == rtbh_rib["id"] for a in filtered_pr), "Pseudo-RIB filter failed!"
    print(f"  ✓ Pseudo-RIB filter verified ({len(filtered_pr)} routes).")

    filtered_port = api_get("/routing/announcements/?port=22", token)
    assert any("22" in a["route_repr"] or (a.get("flowspec_tuple") and a["flowspec_tuple"].get("dst_port") == "22") for a in filtered_port), "Port filter failed!"
    print(f"  ✓ Flowspec tuple filter (port=22) verified ({len(filtered_port)} routes).")

    # 10. Member Removal & Master RIB Reconciliation (Withdrawal across all 3 routers)
    print("\n[Step 10] Removing Prefix from Pseudo-RIB and Pushing Reconciliation...")
    api_post(f"/routing/pseudo-ribs/{rtbh_rib['id']}/remove-prefix/", {"prefix_id": prefix_id}, token)
    api_post(f"/routing/ribs/{master_rib['id']}/push/", {}, token)

    time.sleep(1)
    print("\n[Step 11] Verifying Clean Route Withdrawal across all 3 BIRD Routers...")
    for router in BIRD_ROUTERS:
        bird_v4_after = run_container_cmd(router["name"], ["birdc", "show", "route", "table", "t_unicast4", "all"])
        assert "198.51.100.77/32" not in bird_v4_after, f"RTBH Route was not purged from {router['name']}!"
        print(f"  ✓ {router['name']} ({router['type']}): RTBH Route purged from unicast table!")

    # Clean up flowspec rule from Pseudo-RIB and push again
    api_post(f"/routing/pseudo-ribs/{flow_rib['id']}/remove-flowspec/", {"rule_id": rule_id}, token)
    api_post(f"/routing/ribs/{master_rib['id']}/push/", {}, token)
    time.sleep(1)
    for router in BIRD_ROUTERS:
        bird_flow_after = run_container_cmd(router["name"], ["birdc", "show", "route", "table", "t_flow4", "all"])
        assert "198.51.100.222/32" not in bird_flow_after, f"Flowspec rule was not purged from {router['name']}!"
        print(f"  ✓ {router['name']} ({router['type']}): Flowspec rule purged from flow table!")

    # 11. Cleanup test inventory records
    print("\n[Step 12] Cleaning up test inventory records...")
    api_delete(f"/prefixes/{prefix_id}/", token)
    api_delete(f"/flowspec/rules/{rule_id}/", token)
    print("  ✓ Test inventory records deleted.")

    print("\n" + "=" * 80)
    print(" ALL MULTI-PEER PROPAGATION TESTS PASSED (eBGP + 2x iBGP ROUTERS)! ")
    print(" Verified: Asset -> Pseudo-RIB -> Master RIB -> GoBGP -> 3x BIRD Routers")
    print("=" * 80)


if __name__ == "__main__":
    main()

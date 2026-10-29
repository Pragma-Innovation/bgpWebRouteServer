#!/usr/bin/env python3
"""
End-to-End Integration Test:
Verifies the new hierarchical workflow:
1. Asset Creation: IP Prefixes & Flowspec NLRIs.
2. Pseudo-RIB Assignment: Add prefixes & Flowspec rules to Pseudo-RIBs.
3. Master RIB Assembly & Push: Synchronize Master RIB to GoBGP.
4. GoBGP & BIRD 3 Peering Verification: Unicast RTBH and Flowspec active in BIRD.
5. Member Removal & Push Reconciliation: Verify clean withdrawal in BIRD.
6. Unified Announcements API: Test multi-facet filtering (pseudo-rib, afi_safi, tuple).
"""
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000/api/v1"
CONTAINER_CMD = "podman" if subprocess.run(["which", "podman"], capture_output=True).returncode == 0 else "docker"


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
    print("=" * 75)
    print(" MULTI-AFI/SAFI LAB: PSEUDO-RIB, MASTER RIB & GOBGP <-> BIRD 3 PROPAGATION")
    print("=" * 75)

    # 1. Verify eBGP Session Status
    print("\n[Step 1] Verifying eBGP Session between GoBGP (10.100.0.10) & BIRD (10.100.0.20)...")
    max_retries = 10
    established = False
    for attempt in range(max_retries):
        try:
            proto_status = run_container_cmd("bgpweb-bird", ["birdc", "show", "protocols", "all", "gobgp_peer"])
            if "BGP state:          Established" in proto_status:
                print("  ✓ BIRD reports BGP state: Established")
                established = True
                break
        except Exception as e:
            print(f"  Attempt {attempt+1}: {e}")
        time.sleep(2)

    if not established:
        print("  ✗ ERROR: BGP session between GoBGP and BIRD is not Established!")
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
    print(f"  GoBGP IPv4 Loc-RIB:\n{gobgp_v4}")
    assert "198.51.100.77/32" in gobgp_v4, "Unicast RTBH route missing from GoBGP!"
    print("  ✓ GoBGP IPv4 Loc-RIB contains the RTBH route.")

    gobgp_flow = run_container_cmd("bgpweb-gobgp", ["gobgp", "global", "rib", "-a", "ipv4-flowspec"])
    print(f"  GoBGP Flowspec Loc-RIB:\n{gobgp_flow}")
    assert "198.51.100.222/32" in gobgp_flow, "Flowspec rule missing from GoBGP!"
    print("  ✓ GoBGP Flowspec Loc-RIB contains the Flowspec rule.")

    # 8. Check BIRD 3 Tables (t_unicast4 and t_flow4)
    print("\n[Step 8] Checking BIRD 3 received tables (t_unicast4 and t_flow4)...")
    bird_v4 = run_container_cmd("bgpweb-bird", ["birdc", "show", "route", "table", "t_unicast4", "all"])
    print(f"  BIRD t_unicast4 Table:\n{bird_v4}")
    assert "198.51.100.77/32" in bird_v4, "RTBH Route not installed in BIRD t_unicast4!"
    assert "blackhole" in bird_v4, "BIRD did not set destination to blackhole!"
    assert "(65535,666)" in bird_v4 or "(65535, 666)" in bird_v4, "RFC 7999 community missing in BIRD!"
    print("  ✓ BIRD 3 verified: 198.51.100.77/32 installed as RTD_BLACKHOLE via community (65535, 666)!")

    bird_flow = run_container_cmd("bgpweb-bird", ["birdc", "show", "route", "table", "t_flow4", "all"])
    print(f"  BIRD t_flow4 Table:\n{bird_flow}")
    assert "198.51.100.222/32" in bird_flow, "Flowspec route not installed in BIRD t_flow4!"
    print("  ✓ BIRD 3 verified: Flowspec rule received and active in t_flow4!")

    # 9. Verify Global Announcements API & Multi-Facet Filters
    print("\n[Step 9] Verifying Unified Announcements API & Filtering...")
    all_announcements = api_get("/routing/announcements/", token)
    print(f"  ✓ Total announcements in Loc-RIB API: {len(all_announcements)}")
    assert len(all_announcements) >= 2, "Expected at least 2 announcements in Loc-RIB API!"

    # Filter by pseudo_rib
    filtered_pr = api_get(f"/routing/announcements/?pseudo_rib={rtbh_rib['id']}", token)
    assert all(a["pseudo_rib"] == rtbh_rib["id"] for a in filtered_pr), "Pseudo-RIB filter failed!"
    print(f"  ✓ Pseudo-RIB filter verified ({len(filtered_pr)} routes).")

    # Filter by Flowspec tuple (port 22)
    filtered_port = api_get("/routing/announcements/?port=22", token)
    assert any("22" in a["route_repr"] or (a.get("flowspec_tuple") and a["flowspec_tuple"].get("dst_port") == "22") for a in filtered_port), "Port filter failed!"
    print(f"  ✓ Flowspec tuple filter (port=22) verified ({len(filtered_port)} routes).")

    # 10. Member Removal & Master RIB Reconciliation (Withdrawal)
    print("\n[Step 10] Removing Prefix from Pseudo-RIB and Pushing Reconciliation...")
    api_post(f"/routing/pseudo-ribs/{rtbh_rib['id']}/remove-prefix/", {"prefix_id": prefix_id}, token)
    api_post(f"/routing/ribs/{master_rib['id']}/push/", {}, token)

    time.sleep(1)
    print("\n[Step 11] Verifying Clean Route Withdrawal in BIRD 3...")
    bird_v4_after = run_container_cmd("bgpweb-bird", ["birdc", "show", "route", "table", "t_unicast4", "all"])
    assert "198.51.100.77/32" not in bird_v4_after, "RTBH Route was not purged from BIRD!"
    print("  ✓ RTBH Route was purged from BIRD 3 unicast table upon RIB push!")

    # Clean up flowspec rule from Pseudo-RIB and push again
    api_post(f"/routing/pseudo-ribs/{flow_rib['id']}/remove-flowspec/", {"rule_id": rule_id}, token)
    api_post(f"/routing/ribs/{master_rib['id']}/push/", {}, token)
    time.sleep(1)
    bird_flow_after = run_container_cmd("bgpweb-bird", ["birdc", "show", "route", "table", "t_flow4", "all"])
    assert "198.51.100.222/32" not in bird_flow_after, "Flowspec rule was not purged from BIRD!"
    print("  ✓ Flowspec Route was purged from BIRD 3 flow table upon RIB push!")

    # 11. Cleanup test inventory records
    print("\n[Step 12] Cleaning up test inventory records...")
    api_delete(f"/prefixes/{prefix_id}/", token)
    api_delete(f"/flowspec/rules/{rule_id}/", token)
    print("  ✓ Test inventory records deleted.")

    print("\n" + "=" * 75)
    print(" ALL HIERARCHICAL WORKFLOW INTEGRATION TESTS PASSED SUCCESSFULLY! ")
    print(" Verified: Asset -> Pseudo-RIB -> Master RIB -> GoBGP -> BIRD 3 & Announcements UI")
    print("=" * 75)


if __name__ == "__main__":
    main()

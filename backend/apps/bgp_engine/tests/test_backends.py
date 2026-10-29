"""
Contract test suite for pluggable BGP stack drivers.
Verifies that all implementations conform to BaseBgpBackend interface contracts.
"""
import unittest
from apps.bgp_engine.base import BaseBgpBackend
from apps.bgp_engine.backends.mock.driver import MockBgpBackend
from apps.bgp_engine.backends.gobgp.driver import GoBgpBackend
from apps.bgp_engine.backends.bird.driver import BirdBackend
from apps.bgp_engine.backends.frr.driver import FrrBackend
from apps.bgp_engine.backends.exabgp.driver import ExaBgpBackend
from apps.bgp_engine.manager import BgpManager


class TestBgpBackendContracts(unittest.TestCase):
    DRIVERS = [
        MockBgpBackend,
        GoBgpBackend,
        BirdBackend,
        FrrBackend,
        ExaBgpBackend,
    ]

    def test_all_drivers_subclass_base(self):
        for driver_cls in self.DRIVERS:
            with self.subTest(driver=driver_cls.__name__):
                self.assertTrue(
                    issubclass(driver_cls, BaseBgpBackend),
                    f"{driver_cls.__name__} must subclass BaseBgpBackend"
                )

    def test_server_status_structure(self):
        for driver_cls in self.DRIVERS:
            with self.subTest(driver=driver_cls.__name__):
                driver = driver_cls()
                status = driver.get_server_status()
                self.assertIsInstance(status, dict)
                self.assertIn("backend", status)
                self.assertIn("ready", status)
                self.assertIsInstance(status["ready"], bool)

    def test_get_neighbors_returns_list(self):
        for driver_cls in self.DRIVERS:
            with self.subTest(driver=driver_cls.__name__):
                driver = driver_cls()
                neighbors = driver.get_neighbors()
                self.assertIsInstance(neighbors, list)

    def test_get_rib_returns_list(self):
        for driver_cls in self.DRIVERS:
            with self.subTest(driver=driver_cls.__name__):
                driver = driver_cls()
                rib = driver.get_rib("ipv4-flowspec")
                self.assertIsInstance(rib, list)

    def test_flowspec_injection_and_withdrawal_safety(self):
        sample_rule = {
            "id": 101,
            "addr_fam": "IPv4",
            "dst_prefix": "198.51.100.1/32",
            "action": "Drop",
            "action_value": "",
        }
        for driver_cls in self.DRIVERS:
            with self.subTest(driver=driver_cls.__name__):
                driver = driver_cls()
                # Must not raise unhandled exception even if daemon offline
                add_res = driver.add_flowspec_rule(sample_rule)
                self.assertIsInstance(add_res, bool)

                del_res = driver.delete_flowspec_rule(sample_rule)
                self.assertIsInstance(del_res, bool)

    def test_mock_backend_functionality(self):
        mock = MockBgpBackend()
        self.assertTrue(mock.connect())
        status = mock.get_server_status()
        self.assertTrue(status["ready"])
        self.assertGreater(len(mock.get_neighbors()), 0)

        # Test rule injection
        rule = {"id": 99, "action": "Drop", "dst_prefix": "10.10.10.1/32"}
        self.assertTrue(mock.add_flowspec_rule(rule))
        self.assertEqual(len(mock.get_rib()), 1)
        self.assertTrue(mock.delete_flowspec_rule(rule))
        self.assertEqual(len(mock.get_rib()), 0)

    def test_unicast_injection_and_withdrawal_safety(self):
        for driver_cls in self.DRIVERS:
            with self.subTest(driver=driver_cls.__name__):
                driver = driver_cls()
                add_res = driver.add_unicast_route(
                    prefix="198.51.100.0/24",
                    next_hop="192.0.2.1",
                    communities=["65535:666"],
                    large_communities=["65000:666:1"],
                    afi_safi="ipv4-unicast",
                )
                self.assertIsInstance(add_res, bool)
                del_res = driver.delete_unicast_route(
                    prefix="198.51.100.0/24",
                    afi_safi="ipv4-unicast",
                )
                self.assertIsInstance(del_res, bool)

    def test_mock_backend_unicast_tracking(self):
        mock = MockBgpBackend()
        self.assertTrue(mock.connect())
        ok = mock.add_unicast_route(
            prefix="198.51.100.50/32",
            next_hop="192.0.2.1",
            communities=["65535:666"],
            afi_safi="ipv4-unicast"
        )
        self.assertTrue(ok)
        rib = mock.get_rib("ipv4-unicast")
        self.assertEqual(len(rib), 1)
        self.assertEqual(rib[0]["prefix"], "198.51.100.50/32")
        self.assertEqual(rib[0]["communities"], ["65535:666"])

        del_ok = mock.delete_unicast_route("198.51.100.50/32", "ipv4-unicast")
        self.assertTrue(del_ok)
        self.assertEqual(len(mock.get_rib("ipv4-unicast")), 0)

    def test_bgp_manager_fallback(self):
        BgpManager.reset()
        backend = BgpManager.get_active_backend()
        self.assertIsInstance(backend, BaseBgpBackend)
        self.assertTrue(backend.get_server_status()["ready"])

    def test_manager_dynamic_backend_loading(self):
        paths = [
            ("apps.bgp_engine.backends.mock.MockBgpBackend", MockBgpBackend),
            ("apps.bgp_engine.backends.gobgp.GoBgpBackend", GoBgpBackend),
            ("apps.bgp_engine.backends.bird.BirdBackend", BirdBackend),
            ("apps.bgp_engine.backends.frr.FrrBackend", FrrBackend),
            ("apps.bgp_engine.backends.exabgp.ExaBgpBackend", ExaBgpBackend),
        ]
        for path, expected_cls in paths:
            with self.subTest(backend_path=path):
                BgpManager.reset()
                # Mock settings object or monkeypatch
                class FakeSettings:
                    BGP_ENGINE_BACKEND = path
                import apps.bgp_engine.manager as mgr
                old_settings = mgr.settings
                mgr.settings = FakeSettings()
                try:
                    backend = BgpManager.get_active_backend()
                    self.assertIsInstance(backend, expected_cls)
                finally:
                    mgr.settings = old_settings
                    BgpManager.reset()

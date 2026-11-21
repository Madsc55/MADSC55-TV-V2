import ipaddress
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from v2.public_egress_guard import (
    CHAIN, IPV4_BLOCKED, IPV6_BLOCKED, chain_rules, is_installed, parse_nameservers,
)


class PublicEgressGuardTests(unittest.TestCase):
    def test_parses_only_valid_dns_resolver_addresses(self):
        result = parse_nameservers([
            "search runner.local\nnameserver 127.0.0.53\nnameserver 10.0.0.2",
            "nameserver 2001:4860:4860::8888\nnameserver invalid",
            "nameserver 127.0.0.53",
        ])
        self.assertEqual([str(x) for x in result],
                         ["127.0.0.53", "10.0.0.2", "2001:4860:4860::8888"])

    def test_dns_exceptions_precede_private_range_rejects(self):
        ns = [ipaddress.ip_address("127.0.0.53")]
        rules = chain_rules("iptables", ns, IPV4_BLOCKED)
        dns_positions = [i for i, rule in enumerate(rules) if "--dport" in rule]
        reject_positions = [i for i, rule in enumerate(rules) if "REJECT" in rule]
        self.assertEqual(len(dns_positions), 2)
        self.assertEqual(len(reject_positions), len(IPV4_BLOCKED))
        self.assertLess(max(dns_positions), min(reject_positions))
        self.assertTrue(all(rule[rule.index("-j") + 1] == "ACCEPT"
                            for rule in rules if "--dport" in rule))
        self.assertEqual(rules[-1][-1], "RETURN")

    def test_private_metadata_and_loopback_ranges_are_blocked(self):
        v4 = [ipaddress.ip_network(x) for x in IPV4_BLOCKED]
        v6 = [ipaddress.ip_network(x) for x in IPV6_BLOCKED]
        for address in ("127.0.0.1", "10.1.2.3", "172.17.0.1",
                        "192.168.1.1", "169.254.169.254", "100.64.0.1"):
            self.assertTrue(any(ipaddress.ip_address(address) in net for net in v4), address)
        for address in ("::1", "fc00::1", "fe80::1", "ff02::1",
                        "fd00:ec2::254", "::ffff:127.0.0.1", "64:ff9b::7f00:1"):
            self.assertTrue(any(ipaddress.ip_address(address) in net for net in v6), address)

    def test_public_resolver_and_public_stream_addresses_are_not_blocked(self):
        v4 = [ipaddress.ip_network(x) for x in IPV4_BLOCKED]
        v6 = [ipaddress.ip_network(x) for x in IPV6_BLOCKED]
        for address in ("1.1.1.1", "8.8.8.8", "93.184.216.34"):
            self.assertFalse(any(ipaddress.ip_address(address) in net for net in v4), address)
        for address in ("2606:4700:4700::1111", "2001:4860:4860::8888"):
            self.assertFalse(any(ipaddress.ip_address(address) in net for net in v6), address)

    def test_firewall_requires_both_ip_families(self):
        def which(name):
            return "/usr/sbin/" + name
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            tool = command[1] if command[0] == "/usr/bin/sudo" else command[0]
            code = 0 if tool == "iptables" else 1
            return SimpleNamespace(returncode=code, stdout="", stderr="")
        with patch("v2.public_egress_guard.os.geteuid", return_value=1000):
            self.assertFalse(is_installed(runner=runner, which=lambda n: "/usr/bin/sudo" if n == "sudo" else which(n)))
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()

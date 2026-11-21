#!/usr/bin/env python3
"""Temporary public-only egress firewall for bounded FFmpeg/ffprobe network jobs.

DNS is allowed only to the runner's configured resolvers. Loopback, private,
link-local, shared, documentation, multicast and other special-purpose ranges
are blocked for both IP families. The runner is ephemeral; callers must remove
the rules in a finally block.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess

CHAIN = "M55V2_EGRESS"
IPV4_BLOCKED = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.88.99.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
)
IPV6_BLOCKED = (
    "::/128",
    "::1/128",
    "::ffff:0:0/96",
    "64:ff9b::/96",
    "64:ff9b:1::/48",
    "100::/64",
    "2001::/23",
    "2001:db8::/32",
    "2002::/16",
    "fc00::/7",
    "fe80::/10",
    "ff00::/8",
)
RESOLVER_FILES = (
    "/etc/resolv.conf",
    "/run/systemd/resolve/resolv.conf",
    "/run/systemd/resolve/stub-resolv.conf",
)


def parse_nameservers(texts):
    found = set()
    for text in texts:
        for line in str(text).splitlines():
            parts = line.split()
            if len(parts) < 2 or parts[0].lower() != "nameserver":
                continue
            value = parts[1].split("%", 1)[0]
            try:
                found.add(ipaddress.ip_address(value))
            except ValueError:
                continue
    return tuple(sorted(found, key=lambda item: (item.version, int(item))))


def resolver_addresses(paths=RESOLVER_FILES):
    texts = []
    for name in paths:
        try:
            texts.append(Path(name).read_text(encoding="utf-8"))
        except OSError:
            continue
    result = parse_nameservers(texts)
    if not result:
        raise RuntimeError("No valid DNS resolver is configured; refusing network access")
    return result


def chain_rules(tool, nameservers, blocked):
    """Return ordered chain rules: DNS exceptions first, private-range rejects next."""
    rules = []
    for address in nameservers:
        parsed = ipaddress.ip_address(address)
        for protocol in ("udp", "tcp"):
            rules.append([
                tool, "-w", "-A", CHAIN, "-d", str(parsed),
                "-p", protocol, "--dport", "53", "-j", "ACCEPT",
            ])
    for network in blocked:
        parsed = ipaddress.ip_network(network, strict=True)
        rules.append([tool, "-w", "-A", CHAIN, "-d", str(parsed), "-j", "REJECT"])
    rules.append([tool, "-w", "-A", CHAIN, "-j", "RETURN"])
    return rules


def _prefix(which=shutil.which, is_root=None):
    if is_root is None:
        is_root = hasattr(os, "geteuid") and os.geteuid() == 0
    if is_root:
        return []
    sudo = which("sudo")
    if not sudo:
        raise RuntimeError("sudo is required to install the egress firewall")
    return [sudo]


def _run(command, runner=subprocess.run, check=True):
    result = runner(command, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError("Egress firewall command failed: " + " ".join(command[1:]))
    return result


def _remove_jump(tool, prefix, runner):
    for _ in range(16):
        result = _run(prefix + [tool, "-w", "-C", "OUTPUT", "-j", CHAIN],
                      runner=runner, check=False)
        if result.returncode != 0:
            return
        _run(prefix + [tool, "-w", "-D", "OUTPUT", "-j", CHAIN],
             runner=runner, check=True)
    raise RuntimeError("Too many duplicate egress firewall jumps")


def is_installed(runner=subprocess.run, which=shutil.which):
    try:
        prefix = _prefix(which=which)
        for tool in ("iptables", "ip6tables"):
            if not which(tool):
                return False
            result = _run(prefix + [tool, "-w", "-C", "OUTPUT", "-j", CHAIN],
                          runner=runner, check=False)
            if result.returncode != 0:
                return False
        return True
    except (OSError, RuntimeError, TypeError):
        return False


def remove(runner=subprocess.run, which=shutil.which):
    prefix = _prefix(which=which)
    for tool in ("iptables", "ip6tables"):
        if not which(tool):
            continue
        _remove_jump(tool, prefix, runner)
        _run(prefix + [tool, "-w", "-F", CHAIN], runner=runner, check=False)
        _run(prefix + [tool, "-w", "-X", CHAIN], runner=runner, check=False)


def install(runner=subprocess.run, which=shutil.which, resolver_texts=None, is_root=None):
    """Install both IPv4 and IPv6 guards, or fail before any probe can run."""
    prefix = _prefix(which=which, is_root=is_root)
    tools = ("iptables", "ip6tables")
    for tool in tools:
        if not which(tool):
            raise RuntimeError(tool + " is required; refusing unguarded network access")
    if resolver_texts is None:
        resolver_texts = []
        for name in RESOLVER_FILES:
            try:
                resolver_texts.append(Path(name).read_text(encoding="utf-8"))
            except OSError:
                continue
    nameservers = parse_nameservers(resolver_texts)
    if not nameservers:
        raise RuntimeError("No valid DNS resolver is configured; refusing network access")

    try:
        for tool in tools:
            _remove_jump(tool, prefix, runner)
        for tool, addresses, blocked in (
            ("iptables", [x for x in nameservers if x.version == 4], IPV4_BLOCKED),
            ("ip6tables", [x for x in nameservers if x.version == 6], IPV6_BLOCKED),
        ):
            _run(prefix + [tool, "-w", "-N", CHAIN], runner=runner, check=False)
            _run(prefix + [tool, "-w", "-F", CHAIN], runner=runner, check=True)
            for rule in chain_rules(tool, addresses, blocked):
                _run(prefix + rule, runner=runner, check=True)
        for tool in tools:
            _run(prefix + [tool, "-w", "-I", "OUTPUT", "1", "-j", CHAIN],
                 runner=runner, check=True)
        if not is_installed(runner=runner, which=which):
            raise RuntimeError("Both IPv4 and IPv6 egress guards were not installed")
    except Exception:
        try:
            remove(runner=runner, which=which)
        except Exception:
            pass
        raise
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "remove", "check"))
    args = parser.parse_args()
    if args.action == "install":
        install()
        print(json.dumps({"installed": True, "ipv4": True, "ipv6": True}))
    elif args.action == "remove":
        remove()
        print(json.dumps({"removed": True}))
    else:
        ready = is_installed()
        print(json.dumps({"installed": ready}))
        if not ready:
            raise SystemExit(1)


if __name__ == "__main__":
    main()

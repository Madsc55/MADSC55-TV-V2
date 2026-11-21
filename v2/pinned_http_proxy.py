#!/usr/bin/env python3
"""Loopback HTTP proxy that pins approved DNS names to public IPs per capture.

The proxy supports HTTP GET/HEAD and HTTPS CONNECT only. It has an exact
hostname allowlist, rejects any DNS answer that is not globally routable,
pins the first DNS answer set for the capture, and re-checks it on reuse.
No URL, headers, or credentials are logged.
"""
import ipaddress
import select
import socket
import socketserver
import threading
import time
from urllib.parse import urlsplit

MAX_HEADER_BYTES = 64 * 1024
MAX_PROXY_BYTES = 64 * 1024 * 1024
MAX_PROXY_SECONDS = 20


class ProxyPolicyError(ValueError):
    pass


def normalize_host(host):
    if not isinstance(host, str) or not host or len(host) > 253:
        raise ProxyPolicyError("Invalid hostname")
    host = host.rstrip(".")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            normalized = host.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ProxyPolicyError("Invalid hostname encoding") from exc
        if (not normalized or normalized == "localhost" or
                normalized.endswith((".localhost", ".local", ".internal"))):
            raise ProxyPolicyError("Local hostname is not allowed")
        labels = normalized.split(".")
        if any(not label or len(label) > 63 or label.startswith("-") or
               label.endswith("-") or not all(c.isalnum() or c == "-" for c in label)
               for label in labels):
            raise ProxyPolicyError("Invalid hostname label")
        return normalized
    if not address.is_global:
        raise ProxyPolicyError("Non-public IP address is not allowed")
    return str(address)


def parse_authority(authority):
    if not isinstance(authority, str) or not authority:
        raise ProxyPolicyError("Missing proxy authority")
    if authority.startswith("["):
        end = authority.find("]")
        if end < 0 or authority[end + 1:end + 2] != ":":
            raise ProxyPolicyError("Invalid IPv6 proxy authority")
        host, port_text = authority[1:end], authority[end + 2:]
    else:
        if authority.count(":") != 1:
            raise ProxyPolicyError("Invalid proxy authority")
        host, port_text = authority.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError as exc:
        raise ProxyPolicyError("Invalid proxy port") from exc
    if not 1 <= port <= 65535:
        raise ProxyPolicyError("Invalid proxy port")
    return normalize_host(host), port


class _ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = True


class PinnedHTTPProxy:
    """Short-lived local proxy."""

    def __init__(self, allowed_hosts, allowed_ports=(80, 443), *, timeout=4,
                 max_bytes=MAX_PROXY_BYTES, max_seconds=MAX_PROXY_SECONDS,
                 resolver=None, connector=None):
        self.allowed_hosts = frozenset(normalize_host(h) for h in allowed_hosts)
        self.allowed_ports = frozenset(int(p) for p in allowed_ports)
        if not self.allowed_hosts or any(not 1 <= p <= 65535 for p in self.allowed_ports):
            raise ValueError("A non-empty host and valid port allowlist is required")
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_seconds = max_seconds
        self.resolver = resolver or socket.getaddrinfo
        self.connector = connector or socket.create_connection
        self._pins = {}
        self._pin_lock = threading.Lock()
        self._byte_count = 0
        self._byte_lock = threading.Lock()
        owner = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                owner._handle(self.request)

        self._server = _ThreadingServer(("127.0.0.1", 0), Handler)
        self._thread = None

    @property
    def url(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self):
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="madsc55-pinned-proxy", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)

    def resolve(self, host, port):
        host = normalize_host(host)
        if host not in self.allowed_hosts:
            raise ProxyPolicyError("Hostname is outside the explicit allowlist")
        if port not in self.allowed_ports:
            raise ProxyPolicyError("Port is outside the explicit allowlist")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            infos = self.resolver(host, port, type=socket.SOCK_STREAM)
            addresses = set()
            for info in infos:
                address = ipaddress.ip_address(info[4][0].split("%", 1)[0])
                if not address.is_global:
                    raise ProxyPolicyError("DNS returned a non-public address")
                addresses.add(str(address))
            if not addresses:
                raise ProxyPolicyError("DNS returned no addresses")
            resolved = tuple(sorted(addresses))
        else:
            if not literal.is_global:
                raise ProxyPolicyError("Non-public IP address is not allowed")
            resolved = (str(literal),)
        key = (host, port)
        with self._pin_lock:
            previous = self._pins.get(key)
            if previous is not None and previous != resolved:
                raise ProxyPolicyError("DNS answer changed during the capture")
            self._pins[key] = resolved
        return resolved[0]

    def _consume(self, count):
        with self._byte_lock:
            self._byte_count += count
            if self._byte_count > self.max_bytes:
                raise ProxyPolicyError("Capture network byte budget exceeded")

    @staticmethod
    def _read_request(sock):
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                raise ProxyPolicyError("Incomplete proxy request")
            data.extend(chunk)
            if len(data) > MAX_HEADER_BYTES:
                raise ProxyPolicyError("Proxy request headers too large")
        header, buffered = bytes(data).split(b"\r\n\r\n", 1)
        try:
            lines = header.decode("iso-8859-1").split("\r\n")
        except UnicodeError as exc:
            raise ProxyPolicyError("Invalid proxy request encoding") from exc
        parts = lines[0].split(" ")
        if len(parts) != 3 or parts[2] not in ("HTTP/1.0", "HTTP/1.1"):
            raise ProxyPolicyError("Invalid proxy request line")
        headers = []
        for line in lines[1:]:
            if not line or ":" not in line:
                raise ProxyPolicyError("Invalid proxy header")
            name, value = line.split(":", 1)
            name = name.strip()
            if not name or any(not (c.isalnum() or c in "!#$%&'*+-.^_|~") for c in name):
                raise ProxyPolicyError("Invalid proxy header name")
            headers.append((name, value.strip()))
        return parts[0].upper(), parts[1], parts[2], headers, buffered

    @staticmethod
    def _reply(client, status, reason):
        try:
            client.sendall(f"HTTP/1.1 {status} {reason}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n".encode("ascii"))
        except OSError:
            pass

    def _handle(self, client):
        client.settimeout(self.timeout)
        upstream = None
        try:
            method, target, version, headers, buffered = self._read_request(client)
            if method == "CONNECT":
                host, port = parse_authority(target)
                address = self.resolve(host, port)
                upstream = self.connector((address, port), timeout=self.timeout)
                client.sendall(b"HTTP/1.1 200 Connection Established\r\nProxy-Agent: Madsc55-Pinned-Proxy\r\n\r\n")
                if buffered:
                    self._consume(len(buffered))
                    upstream.sendall(buffered)
                self._tunnel(client, upstream)
                return
            if method not in ("GET", "HEAD") or buffered:
                raise ProxyPolicyError("Only bodyless HTTP GET/HEAD and HTTPS CONNECT are supported")
            parsed = urlsplit(target)
            if parsed.scheme.lower() != "http" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ProxyPolicyError("Only absolute HTTP URLs are supported outside CONNECT")
            host = normalize_host(parsed.hostname)
            port = parsed.port or 80
            address = self.resolve(host, port)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            for name, value in headers:
                lower = name.lower()
                if lower == "transfer-encoding" or (lower == "content-length" and value not in ("", "0")):
                    raise ProxyPolicyError("Request bodies are not supported")
            forwarded = []
            for name, value in headers:
                lower = name.lower()
                if lower in ("host", "connection", "proxy-connection", "keep-alive",
                             "proxy-authorization", "transfer-encoding", "content-length"):
                    continue
                forwarded.append(f"{name}: {value}\r\n")
            host_header = f"[{host}]" if ":" in host else host
            if port != 80:
                host_header += f":{port}"
            request = (f"{method} {path} {version}\r\nHost: {host_header}\r\n" +
                       "".join(forwarded) + "Connection: close\r\n\r\n").encode("iso-8859-1")
            upstream = self.connector((address, port), timeout=self.timeout)
            upstream.sendall(request)
            self._relay_http_response(upstream, client)
        except (OSError, ValueError, ProxyPolicyError):
            self._reply(client, 502, "Proxy Request Rejected")
        finally:
            if upstream is not None:
                try:
                    upstream.close()
                except OSError:
                    pass
            try:
                client.close()
            except OSError:
                pass

    def _tunnel(self, client, upstream):
        deadline = time.monotonic() + self.max_seconds
        while time.monotonic() < deadline:
            readable, _, _ = select.select([client, upstream], [], [], 0.25)
            if not readable:
                continue
            for source in readable:
                target = upstream if source is client else client
                chunk = source.recv(65536)
                if not chunk:
                    return
                self._consume(len(chunk))
                target.sendall(chunk)

    def _relay_http_response(self, upstream, client):
        deadline = time.monotonic() + self.max_seconds
        while time.monotonic() < deadline:
            readable, _, _ = select.select([upstream], [], [], 0.25)
            if not readable:
                continue
            chunk = upstream.recv(65536)
            if not chunk:
                return
            self._consume(len(chunk))
            client.sendall(chunk)

"""Size/time bounded reads of public directory pages; no account credentials."""
import hashlib
import ipaddress
import socket
import time
import json
import re
from urllib.parse import urljoin, urlsplit

import certifi
import urllib3


class PublicFetchError(ValueError):
    """A public request failed; callers may use a bounded browser fallback."""


class URLPolicyError(ValueError):
    """The URL is forbidden; another transport must not bypass this decision."""


def check_public_url(url):
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise URLPolicyError("Malformed public URL") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise URLPolicyError("Expected a public HTTP(S) URL")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise URLPolicyError("Invalid URL port") from exc
    try:
        addresses = socket.getaddrinfo(parsed.hostname, port)
    except OSError as exc:
        raise PublicFetchError("Public address lookup failed") from exc
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise URLPolicyError("Directory requests require a public internet address")
    return addresses[0][4][0]


def _connection(url, address, timeout):
    """Connect to the checked IP, while authenticating the original HTTPS host."""
    parsed = urlsplit(url)
    options = {"host": address, "port": parsed.port or (443 if parsed.scheme == "https" else 80),
               "timeout": timeout, "maxsize": 1}
    if parsed.scheme == "https":
        return urllib3.HTTPSConnectionPool(**options, server_hostname=parsed.hostname,
            assert_hostname=parsed.hostname, cert_reqs="CERT_REQUIRED", ca_certs=certifi.where())
    return urllib3.HTTPConnectionPool(**options)


def fetch_public(url, context, *, json_body=None, max_bytes=3_000_000):
    for redirect in range(4):
        context.checkpoint()
        address = check_public_url(url)
        context.take_page()
        operation = context.reserve("public_http", 0, url=url)
        pool = response = None
        try:
            parsed = urlsplit(url)
            pool = _connection(url, address, max(1, min(15, context.remaining_seconds())))
            host = parsed.hostname
            if ":" in host:
                host = "[" + host + "]"
            if parsed.port:
                host += ":" + str(parsed.port)
            headers = {"Host": host, "User-Agent": "SupplierResearchAgent/1.0"}
            if json_body is not None:
                headers["Content-Type"] = "application/json"
            response = pool.urlopen("POST" if json_body is not None else "GET",
                (parsed.path or "/") + ("?" + parsed.query if parsed.query else ""),
                body=json.dumps(json_body).encode() if json_body is not None else None,
                headers=headers, redirect=False, retries=False, assert_same_host=False,
                preload_content=False)
            if response.status in {301, 302, 303, 307, 308}:
                if json_body is not None or redirect == 3:
                    raise PublicFetchError("Unexpected directory redirect")
                if not response.headers.get("Location"):
                    raise PublicFetchError("Directory redirect has no location")
                url = urljoin(url, response.headers.get("Location", ""))
                context.record(operation, status="redirect", location=url)
                continue
            if response.status >= 400:
                raise PublicFetchError("Public request failed with HTTP " + str(response.status))
            chunks, size = [], 0
            for chunk in response.stream(32768, decode_content=True):
                context.checkpoint()
                size += len(chunk)
                if size > max_bytes:
                    raise PublicFetchError("Public response exceeds the size limit")
                chunks.append(chunk)
            body = b"".join(chunks)
            charset = re.search(r"charset=([\w-]+)", response.headers.get("Content-Type", ""), re.I)
            encoding = charset.group(1) if charset else "utf-8"
            try:
                decoded = body.decode(encoding, errors="replace")
            except LookupError:
                decoded = body.decode("utf-8", errors="replace")
            result = {"url": url, "text": decoded,
                          "retrieved_at": time.time(), "body_sha256": hashlib.sha256(body).hexdigest()}
            context.record(operation, status="completed", bytes=size, body_sha256=result["body_sha256"])
            return result
        except (urllib3.exceptions.HTTPError, OSError) as exc:
            context.record(operation, status="error", error_type=type(exc).__name__)
            raise PublicFetchError("Public transport failed") from exc
        except Exception as exc:
            context.record(operation, status="error", error_type=type(exc).__name__)
            raise
        finally:
            if response is not None:
                response.close()
            if pool is not None:
                pool.close()

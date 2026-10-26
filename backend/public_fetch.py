"""Size/time bounded reads of public directory pages; no account credentials."""
import hashlib
import ipaddress
import socket
import time
from urllib.parse import urljoin, urlsplit

import requests


def check_public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Expected a public HTTP(S) URL")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Directory requests require a public internet address")


def fetch_public(url, context, *, json_body=None, max_bytes=3_000_000):
    session = requests.Session()
    session.trust_env = False
    try:
        for redirect in range(4):
            context.checkpoint()
            check_public_url(url)
            context.take_page()
            operation = context.reserve("public_http", 0, url=url)
            try:
                with session.request("POST" if json_body else "GET", url, json=json_body,
                                     headers={"User-Agent": "SupplierResearchAgent/1.0"},
                                     timeout=max(1, min(15, context.remaining_seconds())),
                                     allow_redirects=False, stream=True) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if json_body or redirect == 3:
                            raise ValueError("Unexpected directory redirect")
                        url = urljoin(url, response.headers.get("Location", ""))
                        context.record(operation, status="redirect", location=url)
                        continue
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_content(32768):
                        context.checkpoint()
                        size += len(chunk)
                        if size > max_bytes:
                            raise ValueError("Public response exceeds the size limit")
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    result = {"url": url, "text": body.decode(response.encoding or "utf-8", errors="replace"),
                              "retrieved_at": time.time(), "body_sha256": hashlib.sha256(body).hexdigest()}
                    context.record(operation, status="completed", bytes=size, body_sha256=result["body_sha256"])
                    return result
            except Exception as exc:
                context.record(operation, status="error", error_type=type(exc).__name__)
                raise
    finally:
        session.close()

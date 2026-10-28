"""HTTPX 0.28-compatible environment routing without mutating process environment."""

import ipaddress
import re
from urllib.request import getproxies

import httpx


def proxy_mounts(proxy_info: dict[str, str]) -> dict[str, str | None]:
    """Preserve HTTPX's bypass semantics, accepting standalone bracketed IPv6 too.

    getproxies preserves HTTPX's lowercase/uppercase precedence and OS fallback.
    Only valid bracketed IPv6 literals (optionally with port) are normalized.
    Arbitrary invalid entries are still errors, never a reason to bypass all proxies.
    """
    mounts: dict[str, str | None] = {}
    for scheme in ("http", "https", "all"):
        if value := proxy_info.get(scheme):
            mounts[f"{scheme}://"] = value if "://" in value else f"http://{value}"
    entries = [entry.strip() for entry in proxy_info.get("no", "").split(",")]
    if "*" in entries:
        return {}
    for entry in entries:
        if not entry:
            continue
        if "://" in entry:
            mounts[entry] = None
            continue
        bracketed = re.fullmatch(r"\[([^\]]+)\](?::([0-9]+))?", entry)
        if bracketed:
            ipv6 = ipaddress.IPv6Address(bracketed[1])
            port = f":{bracketed[2]}" if bracketed[2] else ""
            mounts[f"all://[{ipv6}]{port}"] = None
            continue
        try:
            address = ipaddress.ip_address(entry.split("/")[0])
        except ValueError:
            address = None
        if isinstance(address, ipaddress.IPv6Address):
            mounts[f"all://[{entry}]"] = None
        elif isinstance(address, ipaddress.IPv4Address) or entry.lower() == "localhost":
            mounts[f"all://{entry}"] = None
        else:
            mounts[f"all://*{entry}"] = None
    return mounts


def create_http_client(settings) -> httpx.AsyncClient:
    """Use public transports/mounts, keeping CA environment even in direct mode.

    An explicit base transport prevents HTTPX from parsing the unnormalized global
    NO_PROXY again. We never replace os.environ, monkeypatch HTTPX, or change Host files.
    """
    try:
        mapping = proxy_mounts(getproxies()) if settings.proxy_mode == "environment" else {}
        # Validate routing before allocating transports. URL credentials are never logged.
        for pattern, proxy in mapping.items():
            httpx.URL(pattern)
            if proxy is not None:
                httpx.Proxy(proxy)
        mounts = {
            pattern: httpx.AsyncHTTPTransport(proxy=proxy, trust_env=True)
            if proxy is not None
            else None
            for pattern, proxy in mapping.items()
        }
        return httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(trust_env=True),
            mounts=mounts,
            trust_env=True,
            timeout=httpx.Timeout(settings.http_timeout),
            follow_redirects=False,
        )
    except Exception:
        raise ValueError(
            "HTTP client configuration invalid; check proxy/bypass and CA settings. "
            "No direct fallback was attempted."
        ) from None

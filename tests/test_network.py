import os
import subprocess
import sys

import httpx
import pytest

from image_replicator.config import KEYS, Settings
from image_replicator.network import create_http_client, proxy_mounts
from image_replicator.provider import Provider


@pytest.mark.parametrize("bypass", ["::1", "[::1]", "::1,[::1]", "localhost,127.0.0.1,::1,[::1]"])
async def test_real_httpx_accepts_host_ipv6_without_environment_mutation(
    tmp_path, monkeypatch, bypass
):
    from image_replicator import network

    monkeypatch.setattr(
        network, "getproxies", lambda: {"http": "http://127.0.0.1:10888", "no": bypass}
    )
    before = dict(os.environ)
    provider = Provider(Settings(tmp_path, tmp_path), dict.fromkeys(KEYS, "fixture-only"))
    assert dict(os.environ) == before
    await provider.close()
    assert dict(os.environ) == before


async def test_requests_preserve_http_https_all_bypass_ports_and_close(tmp_path, monkeypatch):
    from image_replicator import network

    transports = []

    class Transport(httpx.AsyncBaseTransport):
        def __init__(self, **kwargs):
            self.options = kwargs
            self.closed = False
            transports.append(self)

        async def handle_async_request(self, request):
            return httpx.Response(200, json={"route": self.options.get("proxy", "direct")})

        async def aclose(self):
            self.closed = True

    monkeypatch.setattr(network.httpx, "AsyncHTTPTransport", Transport)
    monkeypatch.setattr(
        network,
        "getproxies",
        lambda: {
            "http": "http://http-proxy.test:8080",
            "https": "http://https-proxy.test:8081",
            "all": "http://all-proxy.test:8082",
            "no": "localhost,127.0.0.1,[::1],[2001:db8::1]:8443,.internal.test,exact.test",
        },
    )
    before = dict(os.environ)
    async with create_http_client(Settings(tmp_path, tmp_path)) as client:
        for url, route in (
            ("http://remote.test", "http://http-proxy.test:8080"),
            ("https://remote.test", "http://https-proxy.test:8081"),
            ("ftp://remote.test", "http://all-proxy.test:8082"),
            ("https://localhost", "direct"),
            ("https://127.0.0.1", "direct"),
            ("https://[::1]", "direct"),
            ("https://[2001:db8::1]:8443", "direct"),
            ("https://[2001:db8::1]:9443", "http://https-proxy.test:8081"),
            ("https://sub.internal.test", "direct"),
            ("https://internal.test", "http://https-proxy.test:8081"),
            ("https://exact.test", "direct"),
            ("https://sub.exact.test", "direct"),
            ("https://notexact.test", "http://https-proxy.test:8081"),
        ):
            assert (await client.get(url)).json()["route"] == route
    assert all(t.closed and t.options["trust_env"] for t in transports)
    assert dict(os.environ) == before


async def test_explicit_direct_ignores_proxy_env_but_retains_ca(tmp_path, monkeypatch):
    from image_replicator import network

    def forbidden():
        raise AssertionError("Direct mode must not read proxy configuration")

    monkeypatch.setattr(network, "getproxies", forbidden)
    settings = Settings(tmp_path, tmp_path, proxy_mode="direct")
    client = create_http_client(settings)
    await client.aclose()
    # A broken CA file must still fail; direct does not silently disable certificate checks.
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "missing-ca.pem"))
    with pytest.raises(ValueError, match="CA settings"):
        create_http_client(settings)


@pytest.mark.parametrize("entry", ["*", "localhost,*,[::1]"])
async def test_wildcard_keeps_direct_semantics(tmp_path, monkeypatch, entry):
    from image_replicator import network

    monkeypatch.setattr(
        network, "getproxies", lambda: {"http": "invalid://fixture-secret", "no": entry}
    )
    assert proxy_mounts(network.getproxies()) == {}
    await create_http_client(Settings(tmp_path, tmp_path)).aclose()


@pytest.mark.parametrize(
    "proxy_info",
    [
        {"https": "invalid://fixture-secret"},
        {"http": "http://user:fixture-secret@proxy.test:bad"},
        {"no": "[not-an-ipv6]"},
    ],
)
def test_invalid_configuration_fails_without_secret_or_silent_direct(
    tmp_path, monkeypatch, proxy_info
):
    from image_replicator import network

    monkeypatch.setattr(network, "getproxies", lambda: proxy_info)
    with pytest.raises(ValueError) as caught:
        create_http_client(Settings(tmp_path, tmp_path))
    assert "fixture-secret" not in str(caught.value)
    assert "No direct fallback" in str(caught.value)


def test_standard_environment_precedence_and_existing_httpx_mounts(monkeypatch):
    from httpx._utils import get_environment_proxies

    from image_replicator import network

    monkeypatch.setenv("HTTP_PROXY", "http://upper.test:8080")
    monkeypatch.setenv("http_proxy", "http://lower.test:8081")
    monkeypatch.setenv("NO_PROXY", "upper.test")
    monkeypatch.setenv("no_proxy", "localhost,::1,.example.test,10.0.0.1,port.test:8080")
    assert proxy_mounts(network.getproxies()) == get_environment_proxies()
    assert proxy_mounts(network.getproxies())["http://"] == "http://lower.test:8081"


def test_proxy_mode_cli_and_setting_validation(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "image_replicator", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--proxy-mode {environment,direct}" in result.stdout
    with pytest.raises(ValueError, match="proxy-mode"):
        Settings(tmp_path, tmp_path, proxy_mode="invalid")

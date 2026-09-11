from __future__ import annotations

import argparse

import pytest

from poyto.mcp import server as mcp_server
from poyto.mcp.config import MCPSettings, build_parser, settings_from_args
from poyto.mcp.server import require_confirmation


def test_mcp_parser_defaults_to_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "POYTO_MCP_TRANSPORT",
        "POYTO_MCP_HOST",
        "POYTO_MCP_PORT",
        "POYTO_MCP_READ_ONLY",
    ):
        monkeypatch.delenv(name, raising=False)
    args = build_parser().parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.read_only is False
    assert args.print_config is False


def test_mcp_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POYTO_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("POYTO_MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("POYTO_MCP_PORT", "9000")
    monkeypatch.setenv("POYTO_MCP_READ_ONLY", "true")
    settings = MCPSettings.from_env()
    assert settings.transport == "streamable-http"
    assert settings.host == "127.0.0.1"
    assert settings.port == 9000
    assert settings.read_only is True


def test_mcp_parser_accepts_streamable_http() -> None:
    args = build_parser().parse_args(
        [
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--read-only",
        ]
    )
    assert args.transport == "streamable-http"
    assert args.host == "0.0.0.0"
    assert args.port == 9000
    assert args.read_only is True


def test_settings_public_dict_contains_no_credentials() -> None:
    settings = MCPSettings(transport="stdio", host="127.0.0.1", port=8765, read_only=True)
    assert settings.as_public_dict() == {
        "transport": "stdio",
        "host": "127.0.0.1",
        "port": 8765,
        "read_only": True,
    }


def test_settings_reject_invalid_port() -> None:
    args = argparse.Namespace(
        transport="streamable-http",
        host="127.0.0.1",
        port=70000,
        read_only=True,
    )
    with pytest.raises(ValueError, match="between 1 and 65535"):
        settings_from_args(args)


def test_mutation_requires_explicit_confirmation() -> None:
    with pytest.raises(ValueError, match="confirm=true"):
        require_confirmation(False, "buy")


def test_mutation_accepts_confirmation() -> None:
    require_confirmation(True, "sell")


def test_health_call_disables_auto_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, auto_refresh: bool) -> None:
            seen["auto_refresh"] = auto_refresh

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def health(self) -> dict[str, bool]:
            return {"ok": True}

    monkeypatch.setattr(mcp_server, "PoytoClient", FakeClient)

    assert mcp_server._health_call() == {"ok": True}
    assert seen["auto_refresh"] is False


def test_mcp_refresh_reloads_saved_pair_over_stale_environment(tmp_path, monkeypatch):
    import json
    import time

    import httpx

    from poyto import AuthSession, PoytoClient, SessionStore
    from poyto.mcp import server as mcp_server

    path = tmp_path / "session.json"
    store = SessionStore(path)
    store.save(AuthSession(access_token="old-access", refresh_token="old-refresh", expires_at=1))
    monkeypatch.setenv("POYTO_SESSION_FILE", str(path))
    monkeypatch.setenv("POYTO_ACCESS_TOKEN", "environment-access")
    monkeypatch.setenv("POYTO_REFRESH_TOKEN", "environment-refresh")
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.host == "auth.poyp.app":
            assert json.loads(request.content) == {"refresh_token": "old-refresh"}
            return httpx.Response(200, json={
                "access_token": "rotated-access", "refresh_token": "rotated-refresh",
                "expires_at": int(time.time()) + 3600,
            })
        assert request.headers["authorization"] == "Bearer rotated-access"
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(mcp_server, "PoytoClient", lambda **kw: PoytoClient(
        **kw, transport=httpx.MockTransport(handler),
    ))
    assert mcp_server._client_call("balances") == {"ok": True}
    assert mcp_server._client_call("balances") == {"ok": True}
    assert len([r for r in calls if r.url.host == "auth.poyp.app"]) == 1
    assert store.load().refresh_token == "rotated-refresh"


def test_mcp_environment_bootstrap_then_401_rotation(tmp_path, monkeypatch):
    import json

    import httpx

    from poyto import PoytoClient, SessionStore
    from poyto.mcp import server as mcp_server

    path = tmp_path / "session.json"
    monkeypatch.setenv("POYTO_SESSION_FILE", str(path))
    monkeypatch.setenv("POYTO_ACCESS_TOKEN", "bootstrap-access")
    monkeypatch.setenv("POYTO_REFRESH_TOKEN", "bootstrap-refresh")
    refreshes = []
    authorizations = []

    def handler(request):
        if request.url.host == "auth.poyp.app":
            refreshes.append(json.loads(request.content))
            return httpx.Response(200, json={
                "access_token": "new-access", "refresh_token": "new-refresh",
            })
        authorization = request.headers["authorization"]
        authorizations.append(authorization)
        return httpx.Response(401 if authorization == "Bearer bootstrap-access" else 200,
                              json={"ok": authorization == "Bearer new-access"})

    monkeypatch.setattr(mcp_server, "PoytoClient", lambda **kw: PoytoClient(
        **kw, transport=httpx.MockTransport(handler),
    ))
    mcp_server._client_call("balances")
    mcp_server._client_call("balances")
    assert refreshes == [{"refresh_token": "bootstrap-refresh"}]
    assert authorizations == ["Bearer bootstrap-access", "Bearer new-access", "Bearer new-access"]
    assert SessionStore(path).load().refresh_token == "new-refresh"


def test_mcp_parallel_calls_do_not_reuse_refresh_token(tmp_path, monkeypatch):
    import json
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    import httpx

    from poyto import AuthSession, PoytoClient, SessionStore
    from poyto.mcp import server as mcp_server

    path = tmp_path / "session.json"
    SessionStore(path).save(AuthSession(access_token="old", refresh_token="old-refresh", expires_at=1))
    monkeypatch.setenv("POYTO_SESSION_FILE", str(path))
    refreshing = threading.Event()
    release = threading.Event()
    second_started = threading.Event()
    refreshes = []

    def handler(request):
        if request.url.host == "auth.poyp.app":
            refreshes.append(json.loads(request.content))
            refreshing.set()
            assert release.wait(5)
            return httpx.Response(200, json={
                "access_token": "new", "refresh_token": "new-refresh",
                "expires_at": int(time.time()) + 3600,
            })
        assert request.headers["authorization"] == "Bearer new"
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(mcp_server, "PoytoClient", lambda **kw: PoytoClient(
        **kw, transport=httpx.MockTransport(handler),
    ))

    def second_call():
        second_started.set()
        return mcp_server._client_call("balances")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(mcp_server._client_call, "balances")
        try:
            assert refreshing.wait(5)
            second = pool.submit(second_call)
            assert second_started.wait(5)
        finally:
            release.set()
        assert first.result(timeout=5) == second.result(timeout=5) == {"ok": True}
    assert refreshes == [{"refresh_token": "old-refresh"}]


def test_mcp_can_explicitly_disable_saved_session_loading(tmp_path, monkeypatch):
    import httpx

    from poyto import AuthSession, PoytoClient, SessionStore
    from poyto.mcp import server as mcp_server

    path = tmp_path / "session.json"
    SessionStore(path).save(AuthSession(access_token="saved", refresh_token="saved-refresh"))
    monkeypatch.setenv("POYTO_SESSION_FILE", str(path))
    monkeypatch.setenv("POYTO_AUTO_LOAD_SESSION", "false")
    monkeypatch.setenv("POYTO_ACCESS_TOKEN", "explicit-environment")

    def handler(request):
        assert request.headers["authorization"] == "Bearer explicit-environment"
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(mcp_server, "PoytoClient", lambda **kw: PoytoClient(
        **kw, transport=httpx.MockTransport(handler),
    ))
    assert mcp_server._client_call("balances") == {"ok": True}
    assert SessionStore(path).load().access_token == "saved"


@pytest.mark.anyio
async def test_merged_mcp_surface_and_legacy_builder() -> None:
    from poyto.mcp_server import build_server

    server = build_server(read_only=True)
    tools = {tool.name: tool for tool in await server.list_tools()}
    assert {
        'mcp_info', 'account_snapshot', 'market_context', 'home_sections',
        'home_tabs', 'interest_subcategories', 'campaign_banners',
    } <= tools.keys()
    assert {'settlement_claim', 'buy', 'sell', 'loss_gacha_claim'}.isdisjoint(tools)
    assert all(tool.annotations and tool.annotations.readOnlyHint for tool in tools.values())
    full = {tool.name: tool for tool in await build_server().list_tools()}
    assert full['buy'].annotations.destructiveHint is True
    assert 'coin_ratio' in full['settlement_claim'].inputSchema['properties']


@pytest.mark.parametrize('overview', ['_account_snapshot', '_market_context'])
def test_overview_uses_latest_saved_pair(tmp_path, monkeypatch, overview):
    import httpx

    from poyto import AuthSession, PoytoClient, SessionStore

    path = tmp_path / 'session.json'
    SessionStore(path).save(AuthSession(access_token='saved', refresh_token='saved-refresh'))
    monkeypatch.setenv('POYTO_SESSION_FILE', str(path))
    monkeypatch.setenv('POYTO_ACCESS_TOKEN', 'stale-environment')
    seen = []

    def handler(request):
        assert request.headers['authorization'] == 'Bearer saved'
        seen.append(request.url.path)
        return httpx.Response(200, json={})

    monkeypatch.setattr(mcp_server, 'PoytoClient', lambda **kw: PoytoClient(
        **kw, transport=httpx.MockTransport(handler),
    ))
    args = ('market-id',) if overview == '_market_context' else ()
    getattr(mcp_server, overview)(*args)
    assert len(seen) == (2 if args else 5)

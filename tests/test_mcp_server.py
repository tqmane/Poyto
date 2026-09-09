from __future__ import annotations

import pytest

from poyto.mcp_server import _require_confirmation, build_parser, build_server


def test_mcp_parser_defaults_to_stdio() -> None:
    args = build_parser().parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.read_only is False


def test_mcp_parser_accepts_streamable_http_and_read_only() -> None:
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


def test_mcp_parser_reads_read_only_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POYTO_MCP_READ_ONLY", "true")
    assert build_parser().parse_args([]).read_only is True


def test_mutation_requires_explicit_confirmation() -> None:
    with pytest.raises(ValueError, match="confirm=true"):
        _require_confirmation(False, "buy")


def test_mutation_accepts_confirmation() -> None:
    _require_confirmation(True, "sell")


@pytest.mark.anyio
async def test_read_only_server_exposes_only_read_tools() -> None:
    server = build_server(read_only=True)
    tools = await server.list_tools()
    names = {tool.name for tool in tools}
    assert {"health", "profile", "balances", "portfolio", "markets", "market"} <= names
    assert {"buy", "sell", "loss_gacha_ticket", "loss_gacha_claim"}.isdisjoint(names)
    assert all(tool.annotations and tool.annotations.readOnlyHint for tool in tools)


@pytest.mark.anyio
async def test_full_server_marks_mutations_as_writes() -> None:
    server = build_server(read_only=False)
    tools = {tool.name: tool for tool in await server.list_tools()}
    assert tools["markets"].annotations and tools["markets"].annotations.readOnlyHint is True
    assert tools["buy"].annotations and tools["buy"].annotations.readOnlyHint is False
    assert tools["buy"].annotations.destructiveHint is True


def test_mcp_refresh_reloads_saved_pair_over_stale_environment(tmp_path, monkeypatch):
    import json
    import time

    import httpx

    from poyto import AuthSession, PoytoClient, SessionStore, mcp_server

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

    from poyto import PoytoClient, SessionStore, mcp_server

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

    from poyto import AuthSession, PoytoClient, SessionStore, mcp_server

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

    from poyto import AuthSession, PoytoClient, SessionStore, mcp_server

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

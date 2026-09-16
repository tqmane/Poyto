from __future__ import annotations

import httpx
import pytest
 
from poyto import PoytoClient
from poyto.cli_dispatch import execute
from poyto.cli_parser import build_parser
from poyto.mcp_server import build_server


def _client(handler):
    return PoytoClient(
        access_token="test-access",
        auto_load_session=False,
        save_session=False,
        transport=httpx.MockTransport(handler),
    )


def test_claim_login_streak_posts_without_body() -> None:
    seen: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    with _client(handler) as client:
        assert client.claim_login_streak() == {"ok": True}

    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/api/me/login-streak/claim"
    assert request.content == b""


def test_claim_login_bonus_alias_posts_same_route() -> None:
    seen: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    with _client(handler) as client:
        assert client.claim_login_bonus() == {"ok": True}

    assert seen[0].method == "POST"
    assert seen[0].url.path == "/api/me/login-streak/claim"
    assert seen[0].content == b""


def test_claim_daily_trade_posts_mission_slug() -> None:
    seen: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    with _client(handler) as client:
        assert client.claim_daily_trade() == {"ok": True}

    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/api/me/missions/daily_trade/claim"
    assert request.content == b""


def test_claim_mission_uses_slug_path() -> None:
    seen: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    with _client(handler) as client:
        assert client.claim_mission("daily_trade") == {"ok": True}

    assert seen[0].url.path == "/api/me/missions/daily_trade/claim"
    assert seen[0].content == b""


def test_claim_mission_rejects_bad_slug() -> None:
    bad = ["", "/", "a/b"]
    for slug in bad:
        with _client(lambda _: httpx.Response(200, json={})) as client:
            try:
                client.claim_mission(slug)
            except ValueError:
                pass
            else:
                raise AssertionError("expected ValueError")


def test_cli_daily_claims_require_yes() -> None:
    parser = build_parser()
    argv_list = [["claim-login-bonus"], ["claim-daily-trade"]]
    for argv in argv_list:
        args = parser.parse_args(argv)

        class Client:
            def __getattr__(self, _name):
                def _fail(*_a, **_k):
                    raise AssertionError("should not be called")
                return _fail

        try:
            execute(parser, args, Client())  # type: ignore[arg-type]
        except SystemExit:
            pass
        else:
            raise AssertionError("expected SystemExit")


def test_cli_daily_claims_dispatch() -> None:
    parser = build_parser()
    calls: list = []

    class Client:
        def claim_login_bonus(self):
            calls.append("login")
            return {"ok": True}

        def __getattr__(self, _name):
            def _missing(*_a, **_k):
                raise AssertionError("unexpected")
            return _missing

        def claim_daily_trade(self):
            calls.append("daily")
            return {"ok": True}

        def claim_mission(self, slug: str):
            calls.append(slug)
            return {"ok": True}

    assert execute(parser, parser.parse_args(["claim-login-bonus", "--yes"]), Client()) == {"ok": True}  # type: ignore[arg-type]
    assert execute(parser, parser.parse_args(["claim-daily-trade", "--yes"]), Client()) == {"ok": True}  # type: ignore[arg-type]
    assert execute(parser, parser.parse_args(["claim-mission", "daily_trade", "--yes"]), Client()) == {"ok": True}  # type: ignore[arg-type]
    assert calls == ["login", "daily", "daily_trade"]


@pytest.mark.anyio
async def test_mcp_daily_claims_are_confirmed_mutations(monkeypatch) -> None:
    calls: list = []

    def call(method, *args, **kwargs):
        calls.append((method, args, kwargs))
        return {"ok": True}

    monkeypatch.setattr("poyto.mcp_server._client_call", call)
    server = build_server(read_only=False)
    tools = {tool.name: tool for tool in await server.list_tools()}
    for name in ("claim_login_bonus", "claim_daily_trade", "claim_mission"):
        assert name in tools
        assert tools[name].annotations and tools[name].annotations.readOnlyHint is False
    from mcp.server.fastmcp.exceptions import ToolError

    try:
        await server.call_tool("claim_login_bonus", {})
    except ToolError:
        pass
    else:
        raise AssertionError("expected ToolError")
    assert calls == []
    await server.call_tool("claim_login_bonus", {"confirm": True})
    await server.call_tool("claim_daily_trade", {"confirm": True})
    await server.call_tool("claim_mission", {"slug": "daily_trade", "confirm": True})
    assert calls == [
        ("claim_login_bonus", (), {}),
        ("claim_daily_trade", (), {}),
        ("claim_mission", ("daily_trade",), {}),
    ]


@pytest.mark.anyio
async def test_mcp_read_only_omits_daily_claims() -> None:
    server = build_server(read_only=True)
    names = {tool.name for tool in await server.list_tools()}
    assert "claim_login_bonus" not in names
    assert "claim_daily_trade" not in names
    assert "claim_mission" not in names

from __future__ import annotations

import json

import httpx
import pytest

from poyto import PoytoClient
from poyto.cli_parser import build_parser
from poyto.mcp_server import build_server


def _client(handler):
    return PoytoClient(
        access_token="test-access",
        auto_load_session=False,
        save_session=False,
        transport=httpx.MockTransport(handler),
    )


def test_loss_gacha_claim_sends_default_video_gacha() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"grantedPoints": 1, "grantedCoins": 0, "roll": "normal", "balanceAfter": 2},
        )

    with _client(handler) as client:
        client.claim_loss_gacha("market-id", "ticket-id")

    assert seen == [
        {"marketId": "market-id", "kind": "video_gacha", "ticketId": "ticket-id"}
    ]


def test_loss_gacha_claim_sends_instant_point() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"grantedPoints": 1, "grantedCoins": 0, "roll": "fallback", "balanceAfter": 2},
        )

    with _client(handler) as client:
        client.claim_loss_gacha("market-id", "ticket-id", kind="instant_point")

    assert seen == [
        {"marketId": "market-id", "kind": "instant_point", "ticketId": "ticket-id"}
    ]


def test_cli_loss_gacha_claim_rejects_invalid_kind() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["loss-gacha-claim", "market-id", "ticket-id", "--kind", "not-a-kind", "--yes"]
        )


def test_cli_loss_gacha_claim_accepts_all_supported_kinds() -> None:
    parser = build_parser()
    for kind in ("video_gacha", "instant_point", "video_coin"):
        args = parser.parse_args(
            ["loss-gacha-claim", "market-id", "ticket-id", "--kind", kind, "--yes"]
        )
        assert args.kind == kind


@pytest.mark.anyio
async def test_mcp_loss_gacha_claim_kind_is_enum() -> None:
    server = build_server(read_only=False)
    tools = {tool.name: tool for tool in await server.list_tools()}
    tool = tools["loss_gacha_claim"]
    kind_schema = tool.inputSchema["properties"]["kind"]

    assert kind_schema["enum"] == ["video_gacha", "instant_point", "video_coin"]
    assert kind_schema["default"] == "video_gacha"
    assert "fallback" in tool.description
    assert "instant_point" in tool.description
    assert "invalid_kind_for_state" in tool.description

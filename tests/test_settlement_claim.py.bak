from __future__ import annotations

import json

import httpx
import pytest

from poyto import PoytoClient
from poyto.cli_dispatch import execute
from poyto.cli_parser import build_parser
from poyto.mcp_server import build_server


def test_client_claim_settlement_matches_observed_shape() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    with PoytoClient(
        access_token="test-access",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.claim_settlement("market-id", 3) == {"ok": True}

    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/api/settlements/claim"
    assert json.loads(request.content) == {"marketId": "market-id", "positionIndex": 3}


def test_cli_settlement_claim_requires_yes() -> None:
    parser = build_parser()
    args = parser.parse_args(["settlement-claim", "market-id", "3"])

    class Client:
        def claim_settlement(self, market_id: str, position_index: int):
            pytest.fail("claim_settlement should not be called without --yes")

    with pytest.raises(SystemExit):
        execute(parser, args, Client())  # type: ignore[arg-type]


def test_cli_settlement_claim_dispatches() -> None:
    parser = build_parser()
    args = parser.parse_args(["settlement-claim", "market-id", "3", "--yes"])

    class Client:
        def claim_settlement(self, market_id: str, position_index: int):
            return {"marketId": market_id, "positionIndex": position_index}

    assert execute(parser, args, Client()) == {  # type: ignore[arg-type]
        "marketId": "market-id",
        "positionIndex": 3,
    }


@pytest.mark.anyio
async def test_mcp_exposes_settlement_claim_as_confirmed_mutation() -> None:
    server = build_server(read_only=False)
    tools = {tool.name: tool for tool in await server.list_tools()}
    assert "settlement_claim" in tools
    assert tools["settlement_claim"].annotations
    assert tools["settlement_claim"].annotations.readOnlyHint is False
    assert tools["settlement_claim"].annotations.destructiveHint is True


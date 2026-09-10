
from __future__ import annotations

import json
from unittest.mock import Mock

import httpx
import pytest

from poyto import PoytoClient
from poyto.cli_dispatch import execute
from poyto.cli_parser import build_parser


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

    client = Mock(spec=PoytoClient)

    with pytest.raises(SystemExit):
        execute(parser, args, client)

    client.claim_settlement.assert_not_called()

def test_cli_settlement_claim_dispatches() -> None:
    parser = build_parser()
    args = parser.parse_args(["settlement-claim", "market-id", "3", "--yes"])

    client = Mock(spec=PoytoClient)
    client.claim_settlement.return_value = {
        "marketId": "market-id",
        "positionIndex": 3,
    }

    assert execute(parser, args, client) == {
        "marketId": "market-id",
        "positionIndex": 3,
    }

    client.claim_settlement.assert_called_once_with("market-id", 3)

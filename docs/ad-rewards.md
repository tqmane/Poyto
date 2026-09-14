# Ad reward request

This note documents the established POYP ad-reward request and successful response shape.

## Request

```text
POST https://api.poyp.app/api/me/ad-rewards/claim?source=watch_ad
```

No JSON request body is required by the established request shape. Authenticated POYP bearer credentials and normal `x-poyp-*` device headers are used by the client transport.

Poyto exposes the operation directly:

```python
result = client.claim_ad_reward()
print(result["rewardPoints"])
```

The CLI exposes it as an explicit state-changing command:

```text
poyto claim-ad-reward --yes
```

`--yes` is intentionally required because this call changes account reward state.

Both Poyto MCP and Poyto Server Control expose `claim_ad_reward` with arguments
`{"confirm": true}`. After the user authorizes a claim following the normal ad flow,
the tool calls the existing client method once with `source=watch_ad` and returns
the server response. It reuses MCP session loading and refresh handling, requires
explicit confirmation, and is omitted from the read-only MCP server. Restart the
updated server and refresh the connected client's tool list to discover it.

## Successful response

A successful response uses HTTP 200 and includes these fields:

```json
{
  "earnId": "<uuid>",
  "rewardPoints": 5,
  "pointBalanceAfter": 8,
  "dailyViewCount": 2,
  "dailyViewLimit": 5
}
```

The numeric values above are an example of one successful response and are not universal constants. The server remains authoritative for reward amounts, balances, counts, and limits.

Poyto exports `AdRewardClaimResponse` as a `TypedDict` matching the established success fields while preserving the runtime response as the original JSON dictionary.

## Scope

Poyto keeps `claim_ad_reward(source="watch_ad")` limited to the established request shape. It does not invent proof fields, alternate sources, ad-completion events, or undocumented endpoints.

The endpoint is intended to be called as part of the service's normal reward flow. Poyto does not fabricate advertisement-completion signals or attempt to bypass server-side eligibility checks.

For offline verification, tests use `httpx.MockTransport` and assert the method, path, query string, absence of a request body, and successful response keys.

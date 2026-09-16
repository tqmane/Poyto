# Login bonus

Poyto exposes the current login-bonus / streak state through:

```python
status = client.login_bonus()
```

CLI:

```text
poyto login-bonus
```

Claim the daily login reward through:

```python
client.claim_login_bonus()
```

CLI:

```text
poyto claim-login-bonus --yes
```

MCP: `claim_login_bonus(confirm=true)`.

The claim posts to login-streak/claim with no JSON body. Live success was verified on 2026-09-16; the success response schema is intentionally untyped and the server response remains authoritative.

The current service response shape contains:

- `currentStreakDay`
- `todayReward`
- `claimedToday`
- `bonusClaimedToday`
- `bonusReward`
- `cycle`

Example sanitized response:

```json
{
  "currentStreakDay": 8,
  "todayReward": 1,
  "claimedToday": true,
  "bonusClaimedToday": false,
  "bonusReward": 1,
  "cycle": [1, 2, 2, 6, 3, 3, 8]
}
```

`claimedToday` reports whether the normal daily login reward has already been granted. An earlier observed flow had the reward already marked claimed with no separate claim request; the dedicated POST claim above is now established and should be used when the status shows it as unclaimed.

`bonusClaimedToday` and `bonusReward` describe a separate bonus state. The APK-static inventory also contains login-streak/bonus-claim, but its live request and response have not been established, so Poyto does not invent that wrapper.

The reward values and cycle above are one observed response and are not hard-coded as global constants. The server response remains authoritative.

# Poyto

Unofficial typed Python client, CLI, and optional MCP server for **POYP**.

> [!IMPORTANT]
> Poyto is an independent project and is not affiliated with, endorsed by, sponsored by, or otherwise connected to POYP. The service interface is undocumented and may change without notice. Use Poyto only with accounts, credentials, devices, and data you are authorized to access. See [DISCLAIMER.md](DISCLAIMER.md).

## Overview

Poyto turns the observed POYP HTTP surface into a reusable Python package instead of tying API behavior to one script or automation host.

```text
POYP API
   ↑
HTTP transport + session lifecycle
   ↑
resource modules
   ↑
PoytoClient
   ├─ Python API
   ├─ CLI
   └─ MCP
```

The project currently covers authentication/session persistence, account state, balances, portfolio, markets, activity, asset prices, trading, social features, notifications, rewards and selected discovery/event surfaces. Exact support and evidence level are tracked in [docs/capabilities.md](docs/capabilities.md) and [docs/known-gaps.md](docs/known-gaps.md).

## Install

```bash
git clone https://github.com/nezumi0627/Poyto.git
cd Poyto
python -m venv .venv
pip install -e '.[dev]'
```

For MCP / conversational-agent support:

```bash
pip install -e '.[agent]'
```

## Quick start

```python
from poyto import PoytoClient

with PoytoClient() as client:
    print(client.profile())
    print(client.balances())
    print(client.markets(limit=20))
```

The CLI uses the same session/configuration layer:

```bash
poyto profile
poyto balances
poyto markets --limit 20
```

State-changing CLI commands require explicit `--yes` where defined.

## Authentication and persistent sessions

A practical initial bootstrap is importing an authorized POYP authentication response from a `.har` or `.har.zip` capture:

```bash
poyto login --har capture.har.zip
poyto profile
```

Poyto stores the imported session outside the repository and can persist refreshed credentials when the server accepts the refresh token.

Default session locations:

```text
Windows: %LOCALAPPDATA%/Poyto/session.json
Other:   $XDG_STATE_HOME/poyto/session.json
         or ~/.local/state/poyto/session.json
```

`POYTO_SESSION_FILE` overrides the path. HAR files and session files may contain sensitive credentials; never commit or paste them into issues/chats.

See [Authentication](docs/authentication.md), [Configuration](docs/configuration.md), and [Refresh tokens](docs/refresh-tokens.md).

## MCP

Poyto includes first-class optional Model Context Protocol support under `src/poyto/mcp/`.

```text
src/poyto/mcp/
├─ config.py      environment + CLI settings
├─ server.py      FastMCP server and POYP tool registration
└─ __main__.py    poyto-mcp entrypoint
```

The old `poyto.mcp_server` module remains as a compatibility shim; new code should use `poyto.mcp`.

Start the default local stdio server:

```bash
poyto-mcp
```

Start a local Streamable HTTP endpoint:

```bash
poyto-mcp --transport streamable-http --host 127.0.0.1 --port 8765
```

For remote/research-only use, enable read-only mode so mutation tools are not registered:

```bash
poyto-mcp --transport streamable-http --host 127.0.0.1 --port 8765 --read-only
```

or set:

```bash
POYTO_MCP_READ_ONLY=true
```

Read tools expose POYP account/market state. Mutation tools such as `buy` and `sell` require an explicit `confirm=true` even when the server is not read-only. MCP tool annotations describe read/destructive intent to compatible hosts.

Poyto MCP deliberately does **not** mix generic filesystem/root-server control into the default server. The MCP endpoint is for POYP capabilities; generic shell or host administration should remain a separate trust boundary as provided by this fork’s separate `poyto-plugin` entrypoint.

Full setup, tool policy, environment variables, and security guidance: **[MCP integration](docs/mcp.md)**.

## What Poyto can do

- existing-token, HAR/HAR.zip, and supported Apple id-token authentication paths
- persistent sessions, expiry metadata, refresh handling, and one-time authenticated 401 retry
- profile, balances, portfolio/history, transactions, missions, streaks, campaigns and notifications
- market listing/detail/activity/charts/prices and portfolio positions
- buy/sell operations
- comments, replies, likes, follows and user/social reads
- selected discovery, event, reward, referral and loss-gacha surfaces
- Python API, CLI, MCP and reusable agent skill
- typed package metadata and network-free regression tests

See [Capability inventory](docs/capabilities.md) for the precise supported surface.

## What is not proven

Poyto intentionally separates observed behavior from assumptions. Important unknowns include service-side trading formulas, settlement/slippage/fees, complete rate-limit and anti-abuse behavior, several account/session edge cases, realtime/private messaging, moderation/market-admin APIs, and server-side reward eligibility rules.

See [Known gaps](docs/known-gaps.md).

## Referral

If you are new to POYP, the maintainer currently provides this referral:

- Referral link: https://poyp.go.link/fjwo2?referral_code=S-0627
- Invite code: `S-0627`

POYP controls reward amounts and eligibility and may change them. The maintainer may receive a referral reward when an eligible new account registers through the link/code.

## Project layout

```text
src/poyto/
├─ resources/       API responsibility modules
├─ mcp/             optional MCP integration
├─ _http.py         HTTP/auth exchange
├─ auto.py          client lifecycle + session policy
├─ client.py        low-level client composition
├─ cli*.py          CLI parser/dispatch/entrypoint
├─ har_loader.py    secret-aware HAR import
└─ session_store.py persistent session storage
```

Architecture details: [docs/architecture.md](docs/architecture.md).

## Documentation

- [MCP integration](docs/mcp.md)
- [Capability inventory](docs/capabilities.md)
- [Known gaps](docs/known-gaps.md)
- [Observed endpoints](docs/endpoints.md)
- [Android APK/Hermes endpoint inventory](docs/apk-endpoints.md)
- [Endpoint inventory workflow](docs/endpoint-inventory.md)
- [Trading](docs/trading.md)
- [Configuration](docs/configuration.md)
- [Authentication](docs/authentication.md)
- [Refresh tokens](docs/refresh-tokens.md)
- [Python API](docs/python-api.md)
- [CLI reference](docs/cli.md)
- [AI agents and scheduled runs](docs/agents.md)
- [Service model, age/automation evidence, and legal context](docs/service-model-and-legal-context.md)
- [Architecture](docs/architecture.md)
- [Reverse-engineering notes](docs/reverse-engineering.md)
- [Poyto agent skill](skills/poyto/SKILL.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Contributors

- [nezumi0627](https://github.com/nezumi0627) — project maintainer and original author
- [tqmane](https://github.com/tqmane) — contributed the original Docker / ChatGPT MCP integration work in [PR #15](https://github.com/nezumi0627/Poyto/pull/15)

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for more details.

## Development

```bash
pip install -e '.[dev]'
pytest
ruff check .
mypy src/poyto
python scripts/code_stats.py
python -m build
```

CI validates Python 3.10–3.14.

## Security

Never commit access tokens, refresh tokens, identity tokens, cookies, session files, HAR captures, tunnel credentials, or stable device identifiers. Keep remote MCP endpoints private or behind an appropriate authenticated transport. See [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).

## Use from ChatGPT Web

**Portainer:** [日本語セットアップ](docs/setup-portainer.md) / [amd64（x64）用 YAML](compose.portainer.amd64.yaml) / [arm64 用 YAML](compose.portainer.arm64.yaml)

別の Linux マシンへの導入は **[日本語セットアップ手順](docs/setup-ja.md)** を参照してください。セッション移行、Tunnel 作成、ChatGPT 登録、常駐・自動起動、Docker 構成を説明しています。

Poyto Server Control exposes POYP tools, file edits and shell execution directly
through [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
Chat On Steroids is an interaction-model reference only, not a dependency.
Use `poyto-plugin --transport stdio` as the tunnel subprocess, or the Docker
loopback HTTP overlay. Follow [ChatGPT Web setup](docs/chatgpt-web.md) to configure
the tunnel and register the connection; writes are supported when the ChatGPT
workspace permits them. The CLI is available through the shell for operations
without a dedicated MCP wrapper.


## Docker

For the standalone POYP-only, read-only MCP image, run `docker compose -f compose.mcp.yaml up -d --build`; see [MCP Docker setup](docs/docker.md). The existing Server Control deployment is described below.

GitHub Actions publishes a multi-architecture image to `ghcr.io/tqmane/poyto`. The image contains both `linux/amd64` and `linux/arm64` variants, built on native GitHub-hosted x64 and Arm64 runners rather than through QEMU emulation.

The image starts **Poyto Server Control**, a standalone Streamable HTTP MCP endpoint that can be registered directly as a ChatGPT custom app. It combines the normal Poyto MCP tools with Linux server primitives inspired by Codex/Chat On Steroids Core: `read`, `apply_patch`, `exec_command`, and `write_stdin`. Chat On Steroids is only an implementation reference; it is not a runtime dependency and is not required for deployment.

Pull and run the published image:

```bash
docker pull ghcr.io/tqmane/poyto:latest
docker volume create poyto-data
docker run -d \
  --name poyto \
  --restart unless-stopped \
  -p 127.0.0.1:8765:8765 \
  -v poyto-data:/data \
  -v /srv/projects:/workspace \
  ghcr.io/tqmane/poyto:latest
```

The plugin endpoint is `/mcp` on port `8765`. It requires `Authorization: Bearer ...`; on first start a random token is created at `/data/control-plugin.token`. Retrieve it explicitly with:

```bash
docker exec poyto poyto-plugin-token
```

For ChatGPT Web, connect this endpoint directly as a custom MCP app. ChatGPT cannot connect straight to a loopback-only MCP server, so use OpenAI Secure MCP Tunnel for a private/on-prem deployment, or expose an authenticated HTTPS MCP endpoint. The POYP session remains separately persisted at `/data/session.json`.

For **Secure MCP Tunnel on the same Linux server**, start the loopback-only tunnel profile:

```bash
docker compose -f compose.yaml -f compose.secure-tunnel.yaml up -d --build
```

This uses host networking, removes Docker's published port, binds MCP only to `127.0.0.1:8765`, and disables the built-in static Bearer token. Use this mode only when Secure MCP Tunnel is the intended ingress. To combine it with root-equivalent host control, also add `-f compose.host-control.yaml`.

The built-in static Bearer token is useful for generic MCP clients and authenticated gateways. ChatGPT's current custom-app documentation explicitly covers direct MCP endpoints and OAuth; do not assume a particular ChatGPT account/UI can inject an arbitrary static Bearer token. For direct ChatGPT deployment, prefer Secure MCP Tunnel or an OAuth-capable authentication layer.

The normal container mode executes commands inside the container and confines file tools to `POYTO_PLUGIN_ROOTS` (default `/workspace:/data`). To grant full Linux-host command execution, explicitly layer the host-control compose file:

```bash
docker compose -f compose.yaml -f compose.host-control.yaml up -d --build
```

Host-control mode runs the plugin as root with `pid: host`, `privileged: true`, a writable `/host` bind, and `nsenter`. It is intentionally root-equivalent authority over the server. Never expose that endpoint without a private/authenticated transport and an authentication mechanism supported by the client or gateway.

GitHub Container Registry creates a newly published package as private by default. If anonymous pulls are desired, set the `poyto` package visibility to **Public** in GitHub after its first publication.

For the initial HAR bootstrap, use the same persistent volume and mount the capture read-only:

```bash
docker run --rm \
  -v poyto-data:/data \
  -v /absolute/path/to/capture.har.zip:/tmp/capture.har.zip:ro \
  ghcr.io/tqmane/poyto:latest \
  poyto login --har /tmp/capture.har.zip
```

The repository also includes `compose.yaml` for local builds/development:

```bash
docker compose up -d --build
docker compose ps
```

On pushes to `main`, version tags, and manual workflow runs, `.github/workflows/docker.yml` publishes to GHCR. Pull requests build both architectures without publishing. Release tags such as `v1.2.3` additionally produce `1.2.3`, `1.2`, and `1` image tags; the default branch produces `latest`, and every published build gets a `sha-*` tag.

If access is needed from another machine, keep the MCP port behind an authenticated HTTPS reverse proxy/tunnel rather than exposing it directly to the public internet. For ChatGPT Web setup and the intended Poyto + web-search workflow, see [ChatGPT Web + Poyto MCP](docs/chatgpt-web.md).


### Android ADB + su session extraction

This procedure was verified on an already logged-in, rooted Android emulator on
2026-09-09. It reads POYP's saved session, not Apple credentials, and does not log
the app out. The observed storage location and schema are app-version-specific;
this is not a guaranteed method for every Android build or a way to perform the
initial Apple login.

Prerequisites: your own authorized POYP account is logged in in `com.poyp.poyp`,
ADB is installed on the Linux host, and `su` works on the device. The standalone
script uses only the Python 3.10+ standard library; installing Poyto is not needed
for extraction.

From the repository root, run:

```bash
python3 scripts/extract_android_session.py
```

With exactly one attached device, the script selects it automatically and checks
root access. Accept the Android USB-debugging/root prompt if shown, then rerun.
Keep the app idle during extraction. It saves credentials with mode `0600` to
`$XDG_STATE_HOME/poyto/android-session.json`, or
`~/.local/state/poyto/android-session.json` when `XDG_STATE_HOME` is unset.
If that default filename already exists, a new uniquely named file is created;
existing credentials are never overwritten. The script prints the saved path and
an import command, not the token values.

To choose a device or output file:

```bash
adb devices -l
python3 scripts/extract_android_session.py --serial DEVICE_SERIAL
python3 scripts/extract_android_session.py --output /absolute/private/path/session.json
```

`ANDROID_SERIAL` is also supported. Replace `DEVICE_SERIAL` with the intended
serial shown by ADB. An explicit `--output` must not already exist and must be
outside this repository.

The script checks for pending journal/WAL bytes and changes between two database
reads. If the app is writing, leave it idle and retry. The raw database is parsed
in a private temporary directory under `/tmp`, removed when parsing finishes;
only the session credentials and expiry fields remain in the output. The script
makes no POYP network calls, changes no Android files, and does not import into
or overwrite Poyto's active session automatically. Changed/encrypted app storage
is not supported; do not assume another storage format when extraction fails.

After extraction, use the exact path printed by the script to import into the
Poyto installation used by your plugin. For a checkout with `.venv`:

```bash
.venv/bin/poyto login @/absolute/path/printed/by/the/script.json
.venv/bin/poyto balances
```

Import and plugin must run as the same Linux user with the same
`POYTO_SESSION_FILE` setting. Docker has a separate session store: mount the
extracted JSON read-only and import it into the container's persistent `/data`
volume, as in the HAR bootstrap above, using `poyto login @/tmp/session.json`.

Extraction alone does not prove that the server still accepts the credentials.
An expired access token may be renewed by Poyto if the refresh token remains valid;
the `balances` call verifies access and may rotate the saved credentials. Do not
re-import an old extraction after rotation. Keep the extracted file outside Git and
chat, and remove it after successful import if you no longer need the extra copy.

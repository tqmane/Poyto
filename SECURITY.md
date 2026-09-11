# Security

Poyto handles authentication material and can perform account-changing actions, so credentials and remote-control surfaces must be treated as sensitive.

## Never commit

- POYP access or refresh tokens
- Apple identity/access tokens or nonces
- cookies
- raw private traffic exports or HAR captures
- session JSON files
- `.env` files
- tunnel/API credentials
- stable device/vendor identifiers copied from real sessions

The repository `.gitignore` blocks common secret-bearing files, but review every commit before pushing.

## Server Control plugin

The Docker image includes `poyto-plugin`, a standalone MCP app that combines Poyto account/market tools with Linux file and command primitives. Chat On Steroids is not part of the deployment.

- The HTTP endpoint requires a separate Bearer token. By default it is generated at `/data/control-plugin.token` with mode `0600`. Treat it as an administrative credential and never commit it or put it in a URL/query string.
- POYP access/refresh credentials remain separate in `/data/session.json`; they are not plugin tool arguments.
- `read` and `apply_patch` are constrained to `POYTO_PLUGIN_ROOTS` and reject symlink escapes. `exec_command` is intentionally a real shell capability: once a command starts in an approved workdir, the command itself is not a filesystem sandbox.
- `compose.host-control.yaml` is explicitly root-equivalent host administration. It uses `privileged: true`, the host PID namespace, a writable bind of `/`, and `nsenter`. Anyone able to invoke its command tools should be considered to have root access to the Linux server.
- Keep the plugin private. For ChatGPT Web, use Secure MCP Tunnel for private/on-prem access or a properly authenticated HTTPS/OAuth deployment. Do not expose host-control mode as an anonymous public endpoint.
- `compose.secure-tunnel.yaml` deliberately disables the plugin's static Bearer token, but also uses host networking and binds the MCP server only to `127.0.0.1`. Use that overlay only when Secure MCP Tunnel is the intended ingress; do not change its bind to a public interface.

`poyto-plugin --transport stdio` uses parent-owned pipes and creates no HTTP token or listener. Native stdio commands run with the launching OS user's permissions. The tunnel runtime key (`CONTROL_PLANE_API_KEY`) is omitted from shell child environments; this does not isolate the shell from other files or processes accessible to that user.

Android/ADB/Frida are development-time verification tools only and are not part of the production server-control runtime.

## MCP

The default `poyto-mcp` server exposes POYP operations only. It does not expose a generic shell, arbitrary filesystem editor, Docker socket, host PID namespace, or host-root mount.

For remote/research use, prefer `--read-only`; mutation tools are then omitted entirely. Outside read-only mode, state-changing tools still require explicit `confirm=true`.

`stdio` is the safest default because the MCP host owns the local process pipes. For Streamable HTTP, bind to loopback (`127.0.0.1`) unless the endpoint is behind an appropriate private/authenticated transport. Do not publish an unauthenticated mutation-capable MCP endpoint directly to the Internet.

The standalone `compose.mcp.yaml` configuration publishes MCP only on host loopback and defaults to read-only mode. Expanding Poyto into generic server administration should use a separate package/entrypoint and separate authentication boundary rather than widening the default MCP server.

## Reporting a security issue

Please avoid filing public issues that contain working credentials, private traffic exports, private account data, tunnel credentials, or reproducible secrets. Revoke or rotate any credential that may have been exposed.

## Scope

This is an unofficial client. It does not attempt to bypass POYP authorization controls; requests are made using credentials supplied by the authorized account user.

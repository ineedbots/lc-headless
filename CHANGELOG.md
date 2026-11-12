# Changelog

## 1.0.0

This is the first 1.0 release for the project. Publish after the release commit
is promoted to `master` and its CI checks pass.

### Highlights

- Subscribe to live account progress reports over the optional HTTP listener's
  WebSocket endpoint, with snapshots, filters and bounded delivery.

- Support LostCity private servers using protocol revisions 289, 274 and 225,
  with WebSocket, secure WebSocket and raw TCP connections and optional SOCKS5
  proxies.
- Run up to 16 accounts in one process, each with its own embedded Python
  interpreter, script, settings and logs.
- Provide cache-backed game state, collision-aware navigation, reusable bot
  APIs, script reload, VS Code debugging, profiling and editor type stubs.
- Add fleet tracking with experience, bank, backpack and equipment logs and a
  local fleet view.
- Expand the standard library with account leveling, quest coverage and
  recovery improvements, additional upstream rs2b0t features, and Tutorial
  Island completion before script startup.
- Build and package Windows x64, Windows x86, Linux x64 and Linux arm64
  releases through the tag-triggered workflow.

See [Features](docs/Features.md), [Requirements](docs/Requirements.md),
[Running](docs/Running.md) and the [scripting reference](docs/scripting/README.md)
for capabilities, setup and known revision-specific limitations.

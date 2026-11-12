# WebSocket progress validation

Local Windows x64 evidence, 2026-11-12. Base: `056d04e` on `develop`.
The initial protocol design was committed before implementation as `4cb8d43`.

## Automated checks

Run from the repository root:

```powershell
cmake --build --preset windows-debug --parallel 4
ctest --preset windows-debug --parallel 2 --output-on-failure
cmake --build --preset windows-release --parallel 4
ctest --preset windows-release --parallel 2 --output-on-failure
```

Both full suites completed without failures: 947 discovered cases, with expected
real-cache skips. Debug took 313.35 s; Release took 131.96 s. Release builds passed
with warnings treated as errors.

An earlier Debug run while compiling Release failed an existing reconnect timing
assertion by approximately 5 ms and hit a stdlib import watchdog. Both passed in a
56-case serial rerun, then the full Debug rerun passed. No unrelated test or
watchdog changes were made.

The final review tightened journal reservations to cover typed-to-serialized
conversion and added client-observed load timing. After rebuilding, run the
affected regression group:

```powershell
build/windows-msvc/Release/Rs2004HeadlessTests.exe "[Events],[ProgressReporter],[Http]"
build/windows-msvc/Debug/Rs2004HeadlessTests.exe "[Events],[ProgressReporter],[Http]"
```

Both configurations passed all 64 cases / 2726 assertions. These checks include bridge ordering/filter/admission
tests, the real report-hook callback, existing REST/command capture tests, and
loopback upgrade, coalesced/fragmented messages, reconnect, binary/oversize close,
Origin policy, shutdown/overflow close handshakes and shared connection admission.
The native Python client example also passed a syntax check.

## Reproducible mixed workload

Run `"[Events][Load]"` with the same test executable. The test opens 32 native
WebSocket connections, subscribes each once, then publishes a single burst of 20
reports. It reads 640 live envelopes and verifies every client's ordering while a
REST status request completes and an account logs in/steps on the shared network
loop against `FakeGameServer`/`TestWorld`. It asserts that the account reached game
state and the fake game server reported no errors.

Final local Release sample:

| Measurement | Result |
|---|---:|
| Connections / subscriptions | 32 / 32 |
| Reports / ordered live deliveries | 20 / 640 |
| Safe-point/account steps | 176 |
| Total test elapsed | 52 ms |
| Maximum client-observed publication-to-read latency | 23 ms |
| Maximum publication-to-outbox lag | 4 ms |
| Peak journal items / reserved bytes | 20 / 163840 |
| Peak per-client outgoing items / bytes | 17 / 3812 |
| Publisher resets / subscriber overflow disconnects | 0 / 0 |

These are one local burst's observations, not a sustained-throughput or maximum
fleet claim. Byte counters describe application content/reservations; process
RSS, allocator overhead and kernel buffers were not measured. A separate
admission test holds 64 ordinary HTTP and 64 upgraded connections and verifies
that the 129th connection is rejected. Bridge and transport overload tests verify
bounded rejection/reset and close 1013 independently of the healthy workload.

## Remaining verification

All nine CI jobs for implementation commit `e1e8c6a` passed, including Linux native
and stdlib coverage, Linux x64/arm64 Debug/Release, and Windows x64/x86 Debug/Release:
[CI run 43291918554](https://github.com/ineedbots/lc-headless/actions/runs/43291918554).
Docker was unavailable during the initial local run and is available for the
readiness follow-up. Local Ubuntu/Arch results and current-head CI are recorded
in [PR #79](https://github.com/ineedbots/lc-headless/pull/79).

Readiness review added coverage for 3000-byte HTTP header padding and a 3000-byte
padded subscription coalesced with the upgrade, separately and together. The
handoff now uses the parsed request and a bounded buffered stream, avoiding
Beast's 1536-byte internal raw-handshake buffer limit.

No real-engine acceptance, sustained fleet soak, 60-second heartbeat expiry, or fault-injected
allocation/upgrade failure run is claimed. The fixed conservative limits remain
provisional; measure representative sustained workloads before raising them.

# All individual quest phases on local 289

This publishes the orchestrator used for the November 24 grand run, replacing its
hard-coded run folder and Windows executable with command-line options. It runs
phase 16's individual suite and phases 17a–i: **65 fresh accounts**, with both
Arrav and Hero gang partners kept together. Optional phase 16 full queues are a
separate scenario.

Use the build/server prerequisites in [the E2E guide](../README.md) and the linked
phase guides. Start the local members-enabled 289 server yourself at normal
600 ms ticks. The orchestrator leaves server code, settings and speed unchanged;
each existing phase suite supplies its documented preparation. The default
per-character infinite run setting matches the recorded tests.

From the repository root:

```powershell
python e2e/grand/run.py --run-dir build/e2e/grand-night1
```

To select another executable or installation:

```powershell
python e2e/grand/run.py --run-dir build/e2e/grand-night2 --client build/walk-actions/Release/Rs2004Headless.exe --server-dir ../289server/engine --cache-dir data/cache --nav-dir data/nav
```

The run directory must be new and beneath this checkout's ignored `build/`.
The launcher copies the chosen executable into that directory and records its
source SHA and binary hash. It prepares all ten suites, seeds them concurrently,
waits for **every seed to pass**, then starts all quest suites concurrently.
Phase 16 uses two client batches, so there are eleven quest client processes.
Allow several hours and sufficient memory for the simultaneous clients.

Default operator ports occupy slots in `8200–8229` (phase 16 uses `8200/8201`,
phase 17a starts at `8203`, and phase 17i uses `8227`). Ensure these ports are
available; `--operator-port 8400` moves the entire range. Other options:

- `--server-port 80`: local WebSocket endpoint.
- `--seed-timeout-minutes 45`: each phase's seed timeout.
- `--timeout-minutes 720`: each phase's quest timeout.
- `--natural-run`: omit per-account infinite run, forwarded to every phase.

## Artifacts and acceptance

The root retains the frozen client, `provenance.json`, `status.json`,
`results.json`, and per-phase stdout/stderr. Each `phase*` folder retains the
existing suite's generated credentials, preparation, script snapshots, manifests,
versions and session logs. Credentials remain under ignored `build/`.

`status.json` tracks launcher PIDs/exit codes and ends at `complete`, `failed`, or
`interrupted`. `results.json` includes each account's original result, start/end
timestamps and `elapsed_seconds`. **Time taken** runs from its first
`AIOQuester, queue:` through `E2E_RESULT`, including final banking and automatic
retries, excluding seeding and login staggering. Failed-case time ends at its
failure result. Missing records, duplicate/restarted sessions or mismatched
accounts cannot pass. The aggregate requires every phase launcher and every
individual case to pass; a completed account in a failed phase is not an
aggregate pass.
Results are written after the quest launchers finish. Earlier setup failures or
interruption leave a failed status and retained logs; malformed phase evidence is
reported in `phase_errors`.

Ctrl+C requests shutdown through verified per-phase operator listeners, then
stops any remaining owned launcher/client process trees. An interrupted run is
never accepted. Keep its artifacts and use a fresh directory for another grand
run. The launcher does not automatically reseed, resume or erase failed evidence.

The original run's results and subsequent fixes remain in
[the validation tables](../VALIDATION.md#grand-concurrent-run). The generalized
launcher is validated with host-side orchestration tests; publishing it does not
claim another live 65-account run.

```powershell
python -B -m unittest discover -s e2e/grand -p 'test_*.py'
```

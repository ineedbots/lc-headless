# Script coverage backlog

What's left to test in the embedded stdlib, `src/Script/Stdlib/`, for anyone adding coverage. Script tests live in
`tests/Stdlib/`, and [Building.md](../Building.md#stdlib-script-coverage) describes the report these figures come from.
The figures are a snapshot: rerun the report rather than trusting them once tests have moved on.

**Snapshot (2026-11-04):** 75,525 of 77,160 executable lines (97.88%). All 432 files meet the 95% line-coverage
floor; 1,635 lines remain uncovered.
Taken on Windows with no game caches, so real-cache tests were skipped. Hidden `[Slow]` tests are excluded.
Scripts under `scripts/` are not measured.

The coverage command and CI now fail when any embedded stdlib file falls below 95%, using unrounded counts.
The previous snapshot was 86.50% overall. Runtime specs now exercise quest actions, failed prerequisites,
interrupted combat, pocket recovery, journal boundaries and bank-first provisioning.

## Writing a runtime spec

1. Put it in `tests/Stdlib/rs2b0t/quests/test_<quest>_<area>_runtime.py`. New files are picked up without a rebuild.
2. Build the world from `Scene` in `tests/Stdlib/rs2b0t/spec.py`, which fakes the pack, worn items, locs, NPCs, ground
   items, messages, chat, walking and the clock. A failed `delay_until` costs its whole timeout, so a leg's own deadlines
   expire as they do live.
3. Take each leg through its success and each of its failures, asserting on the outcome rather than only running the
   lines. `test_touristtrap_legs_runtime.py` and `test_legends_trials_runtime.py` are the models to follow.
4. Run the spec alone, then lint it:

   ```sh
   build/windows-script-coverage/Debug/Rs2004HeadlessTests.exe "rs2b0t's ported Python tests pass" -c test_<name>.py
   python -I tools/port/lint.py tests/Stdlib/rs2b0t/quests/test_<name>.py
   ```

To see one spec's coverage without a full run, set `RS2004_SCRIPT_COVERAGE_DIR` to an empty folder for that command, and
compare the JSON profiles it writes with `build/windows-script-coverage/script-coverage/manifest.json`.

Two pocketpy traps catch these specs:

- A closure captures an enclosing local when it's defined. A sibling function defined later is a `NameError`, and
  rebinding a local afterwards isn't seen, so define callees first and build effects in a helper for each object.
- Default arguments must be literals, so `stage=STAGE.STARTED` won't load.

## Known findings

Coverage work should report these rather than pin them in a test.

| Where | Finding |
|---|---|
| `grandtree/journal.py`, `read_grand_tree_stage` | A recognized older page returns its parsed stage even when `last_stage` holds a newer one. The cache stays ahead, but the returned stage can temporarily regress; an unreadable page then returns the newer cached stage again. |
| `touristtrap.py`, lines 2448 and 2484 | `leave_camp` here looks unreachable, since `safe_recovery_route` has already answered for both camp areas. |

Holy Grail's premature bell-landing check was fixed in the [2026-11-04 upstream port](Rs2b0tUpstreamReview.md): it now drives the bell dialogue and requires the exact castle landing tile. Regression tests cover both a real landing and remaining outside after ringing.

Some of what remains can't be reached by a test at all. `elementalworkshop/workshop.py` lines 129–130 and 657 and
`chompybird/hunt.py` lines 109–110 and 160 are guards on states the lines before them rule out, so 100% isn't the goal
for every file.

## Files nearest the coverage floor

These are follow-up opportunities beyond the enforced 95% floor. The generated HTML report lists every missed line.

| File | Covered / executable | Coverage |
|---|---:|---:|
| `rs2004/quests/defs/elementalworkshop/supplies.py` | 190 / 200 | 95.00% |
| `rs2004/quests/defs/hazeelcult.py` | 342 / 360 | 95.00% |
| `rs2004/quests/defs/ikov/__init__.py` | 171 / 180 | 95.00% |
| `rs2004/quests/defs/witchshouse/house.py` | 171 / 180 | 95.00% |
| `rs2004/quests/defs/waterfall.py` | 1088 / 1145 | 95.02% |
| `rs2004/quests/defs/watchtower/caves.py` | 134 / 141 | 95.04% |
| `rs2004/traversal.py` | 1150 / 1210 | 95.04% |
| `rs2004/quests/defs/legends/shaman.py` | 307 / 323 | 95.05% |
| `rs2004/quests/defs/horror/journal.py` | 96 / 101 | 95.05% |
| `rs2004/random_events.py` | 461 / 485 | 95.05% |
| `rs2004/quests/defs/upass/doll.py` | 289 / 304 | 95.07% |
| `rs2004/quests/defs/piratestreasure/journal.py` | 58 / 61 | 95.08% |
| `rs2004/hunting/supply.py` | 758 / 797 | 95.11% |
| `rs2004/quests/defs/upass/pass_.py` | 564 / 593 | 95.11% |
| `rs2004/quests/defs/deathplateau/__init__.py` | 584 / 614 | 95.11% |
| `rs2004/clues/solve.py` | 721 / 758 | 95.12% |
| `rs2004/quests/defs/piratestreasure/supplies.py` | 39 / 41 | 95.12% |
| `rs2004/quests/defs/upass/__init__.py` | 156 / 164 | 95.12% |
| `rs2004/quests/defs/witchshouse/patrol.py` | 137 / 144 | 95.14% |
| `rs2004/quests/defs/digsite/__init__.py` | 236 / 248 | 95.16% |
| `rs2004/quests/defs/fremenniktrials/hunter.py` | 138 / 145 | 95.17% |
| `rs2004/catalogs/tool_acquire.py` | 336 / 353 | 95.18% |
| `rs2004/quests/defs/familycrest/__init__.py` | 258 / 271 | 95.20% |
| `rs2004/quests/defs/ernest/__init__.py` | 60 / 63 | 95.24% |
| `rs2004/quests/defs/plaguecity/supplies.py` | 100 / 105 | 95.24% |

# rs2b0t review for issue 29

Review date: 2026-11-11. Resolves [issue 29](https://github.com/ineedbots/lc-headless/issues/29)
when the implementation is reviewed and merged into `develop`.

## Pinned sources

The source repository is [rs2b2t/rs2b0t](https://github.com/rs2b2t/rs2b0t).
The original port baseline remains `4417d0b7`. The last completed review was
`8b7db422597894be063249697209dcefebf94c43`. This review fetches and pins upstream
`origin/main` at `95175bcc17c28d5b5ac3d80e13eb4d9ef584b642` and also inspects the sibling
`rs2b0t` checkout at `af3235b4237e4f3df028dfc6723b1fa0e7268958`.
The sibling checkout is not reset or modified. Detached checkouts under `build/`
provide the review baseline and endpoint.

There are three commits in `8b7db422..95175bcc`, and eleven commits unique to the
sibling branch. The union contains fourteen commits; the sibling also contains
the first two upstream commits below.

## Commit inventory

| Commit | Changes | Disposition |
|---|---|---|
| `281c7b62244e9464bb3f30e229740e4243238375` | Superheater goldsmith gauntlets, fast bank leg, interruption yields | Ported. Gauntlets are required only for gold when enabled; the fused bank leg has a confirmed fallback. Native inventory and bank acknowledgements replace browser packet helpers. |
| `759a36efc71f878d277ab50bf760ce3ba0ceac8b` | DragonfireShield farming at Duke Horacio | Ported as `DragonfireShield`, with trip timing, note handling, drop/loot cycles and bank trips. |
| `95175bcc17c28d5b5ac3d80e13eb4d9ef584b642` | AIOQuester preparation, recovery, cooperative quests and supply/quest fixes | Ported and adapted to the native runtime; details below. |
| `2691277157b0a2a4567cb4748cad9f499148ee39` | MuleTrader and browser client changes | Native MuleTrader already implements the applicable trade flow. Browser rendering/input changes do not apply. |
| `17121dd65600342eaa7ec30ed1c6d79c44b28123` | Minimap orbs | Browser UI only. |
| `52c5002aaf50f0e570075e5215b4ef481fe59ab2` | Interface mouse scrolling | Browser input only. |
| `304a6e3b5a75600c9c4e91b9a4b7baf8b17b0ed3` | Documentation | Reviewed; no native runtime change. |
| `05aa5617d694c5c52ddabc2fc12c879b64ecfc97` | Documentation clarification | Reviewed; no native runtime change. |
| `d65c71c42a291abb33c13e2a30d2fb89b47d9b3e` | Roof toggle | Browser rendering only. |
| `3dbef8d29a3518cbf899b0859d68ec318142e7c2` | Escape closes interfaces | Browser keyboard input only. |
| `b2e879bb56faebbf42ec20d266b61047a8a81030` | Chat keyboard behavior | Browser keyboard input only. |
| `2df77fe791aea6ee9bfe1a4c47fbb6ac20d90600` | Disable browser idle behavior | Native sessions do not use the browser's input-idle mechanism. |
| `43f907e17b7a492693642dbb9ea3a66e08fd8ddd` | Bind development live proxy beyond localhost | Browser development proxy only; native connections use configured endpoints. |
| `af3235b4237e4f3df028dfc6723b1fa0e7268958` | XP drop paint | Browser rendering only. |

## Applicable behavior

AIOQuester expands prerequisites and quest-point requirements while respecting
explicit exclusions. Preparation reads bank stock, plans missing skills and
ordinary supplies, and runs AccountLeveler activities without recursively
starting another quest. Food selection keeps quest ingredients out of emergency
food. Special producers cover cakes, seaweed, bat bones, arena toadflax and
potions. PotionMaker supports bounded output and partial unfinished stock;
HerbloreSecondaries carries and replenishes the Dusty key for blue dragon scales.

Preparation is interruptible on skip, restart and death. Temporary food, loadout
and prayer overrides are restored when a child activity stops. Bounded retry and
progress checks prevent a failed supply activity from cycling indefinitely.
Restart and stalled-step recovery retreat through quest exits, bank the loadout,
and retain an exact-ID snapshot until inventory and equipment restoration are
acknowledged. Rum and filled Legends bowls block unsafe bank resets.

Shield of Arrav and Hero's Quest exchange stage/key state, choose compatible
partners through mutual claims, and expire stale heartbeats. Native
`send_bot_message('*', ...)` broadcasts JSON copies to other accounts in the same
process. Configured world identity replaces browser node IDs; explicit partner
settings remain available. Pause and stop advertise unavailability immediately.
Cross-process automatic discovery is not provided by the native messenger.

Quest changes include confirmed auto-retaliate policy, safe transport recovery,
Nature Spirit pouch replacement, owned pyre confirmation in Shades of Mort'ton,
Tai Bwo Wannai Trio fishing guards and phase-specific inventory caps, Watch Tower
phase kits/potion recovery/slot reservations, and Tourist Trap food and waterskin
limits. Existing native cache-verified Watch Tower shops are preserved: accounts
below Magic 66 use Aubury, and eligible accounts may use the Magic Guild.
Coin provisioning withdraws only the missing amount. Browser paint, DOM controls,
BroadcastChannel and packet-click helpers are replaced by native settings,
commands, messaging and acknowledged inventory operations.

## Validation

The review uses the repository's embedded pocketpy runtime, rather than treating
CPython importability as runtime validation. Regression scenarios exercise the
fast bank ordering and fallback, interruption gates, gauntlet requirement, shield
notes and full inventories, bounded potion output, prerequisite exclusions,
partner claims/expiry, preparation interruption, loadout restoration and stalled
quest recovery. Updated upstream quest specifications retain native runtime
regressions for local cache and server behavior.

| Check | Result |
|---|---|
| `cmake --build --preset windows-debug --parallel 8` | Passed. |
| `ctest --preset windows-debug --parallel 8 --output-on-failure` | Passed: 828 cases, zero failures; 27 cache-dependent skips. |
| `cmake --build --preset windows-release --parallel 8` | Passed. |
| `ctest --preset windows-release --parallel 8 --output-on-failure` | Passed: 828 cases, zero failures; 27 cache-dependent skips. |
| `python tools/coverage/script.py --no-build --parallel 8` after building `windows-script-coverage` | Passed: all 442 stdlib files meet the 95% per-file gate; 78,547/80,271 executable lines covered (97.85%). All 828 CTest cases pass, with the same 27 skips. |
| `python -I tools/port/coverage.py build/issue29-upstream --all` | Passed: nothing missing at the pinned endpoint. |
| `python -I tools/port/lint.py src/Script/Stdlib scripts tests/Stdlib` | Passed: nothing found. |
| `python -B -m unittest discover -s tools/port` | Passed: 11 tests. |
| `git diff --check` | Passed. |

Focused preparation, recovery, supply and quest scenarios also ran against the
coverage binary, with profiles collected alongside the full suite under the same
verified embedded-source manifest. Reports and logs are local build artifacts in
`build/issue29-*.txt` and `build/windows-script-coverage/script-coverage/`.
Cache-dependent tests require supplied cache data. Live game acceptance and
throughput comparisons were not run.

This review advances the reviewed upstream endpoint to `95175bcc`; later upstream
commits require a new pinned inventory and review. The issue stays open until the
feature branch is merged, following [DevelopmentWorkflow.md](DevelopmentWorkflow.md).

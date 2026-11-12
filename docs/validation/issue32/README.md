# Issue 32: live acceptance, 2026-11-11

Validated on the local revision-289 members engine at **600 ms/tick, XP rate 1**.
All participants were new scratch accounts. The engine ran with a separate working
directory, config, player saves and ports (TCP 43632, web 18032, management 18033).
The user's account/config/save directories were not used. Log timestamps are UTC;
the runs occurred on November 11 in America/Regina.

## Versions and evidence

- Client base: `57b0e47ee2d4be540b3b3f6c873157a93d2238d9` (`develop`).
- Engine: `278bd51cc17cc0d093e1ea3895536a8054583f97`.
- Existing Release executable was built from
  `87049a4c844bafd440b8a39436d4b521cdac0e27`. Its native `src/` tree is identical
  to the client base. The script fix is loaded from the scratch scripts directory.
- [manifest.json](manifest.json) records the executable SHA-256, script hashes and
  engine configuration. The engine checkout had existing changes under `public/`
  only; no engine logic/content edits were made for these runs.
- [fixtures.json](fixtures.json) records the actual account settings and references
  the exact [harnesses](harnesses). Passwords are excluded. Logs include inventory
  item IDs/counts, positions, elapsed ticks/milliseconds, reports and server messages.
  Setup and Tutorial Island are excluded from `ACCEPT_START` timing.
- Unmodified bots were used except the MuleCrafter fix described below. Each case
  has its own copied bot modules. Ground acquisition calls the production acquisition
  generator directly after Fisher initialization; the stall fixture deliberately
  omits the first next-tick observation per fishing controller to exercise fallback.

## Results

| Workflow / log | Measured ticks / elapsed | Result |
|---|---|---|
| [Cosmic](logs/cosmic.log) | Master 600 / 360,005 ms; runner 600 / 359,976 ms | Walked Zanaris bank to Cosmic ruins, entered the correct altar, completed two inside trades delivering 50 essence, crafted 75 essence into 150 Cosmic runes for 600 XP. Runner exited, used the Zanaris dialogue banker, withdrew another load and returned. Both retained Cosmic talisman 1454 and Dramen staff 772. |
| [Dump/Mule + Dump/Supermule](logs/dump3.log) | Giver 126 / 75,550 ms | Thirty distinct tradeable item types, one unit each, required two trades: 28 + 2 units. Receiver confirmed both and banked the goods. Giver stopped after three empty bank reads. Some stackable items produce the engine's harmless “cannot be withdrawn as a note” message while still withdrawing normally. |
| [Supply/Supplier + two Supply/Clients](logs/sup2a.log) | Supplier 175 / 105,036 ms | Four trades moved all 450 seeded units: client 1 received 100 Air + 200 Mind; client 2 received 50 Air + 100 Mind. One-slot batches, partial stock and client rotation worked. Final shortfalls were exactly client 1: 5 Law; client 2: 50 Air, 100 Mind, 5 Law. |
| [MuleCrafter inside, bank_fill=false](logs/infix.log) | Crafter 600 / 359,953 ms | Four confirmed 27-essence deliveries; 135 essence crafted, 675 XP. Crafter stayed inside, kept its talisman and made no bank visits. Mule banked and returned repeatedly. |
| [MuleCrafter outside, bank_fill=true, trades_per_bank=1](logs/outfix.log) | Crafter 600 / 359,952 ms | Four deliveries; 189 essence crafted, 945 XP. Met outside without requiring a mule talisman, and crafter banked after each confirmed delivery. |
| [MuleCrafter inside, bank_fill=true, trades_per_bank=1](logs/inbank.log) | Crafter 600 / 359,987 ms | Four deliveries; 216 essence crafted, 1,080 XP. Crafter exited for scheduled banking and returned inside to trade. |
| [MuleCrafter solo, bank_fill=true, trades_per_bank=0](logs/solo.log) | 600 / 359,960 ms | No partners/trades; four 27-essence crafting loads, 540 XP, repeated bank trips. |
| [Fisher ground acquisition](logs/ground.log) | 15 / 9,019 ms | Starting without knife/log, took the knife ground spawn and chopped a carrier log with the seeded bronze axe. Returned true with rod, feathers, knife and log present. |
| [Fisher bank acquisition](logs/kitbank.log) | 20 / 12,004 ms | Starting with empty inventory, withdrew fly rod, 1,000 feathers, knife and log from seeded Seers bank through the normal restock tasks. |
| [Fisher missed-cycle fallback](logs/stall.log) | 160 / 95,989 ms | The omitted landing observation caused `fallback click`, then normal batches resumed. 37 catches and 2,270 XP by the end of the run. This is an induced observation stall, not evidence of naturally occurring network loss. |

Runecrafting's `Crafted` report counts essence processed, not output runes. Air
crafting at level 99 makes ten runes per essence. Delivery totals above come from
confirmed exchanges and inventory changes. The mule role's existing `Trades`
counter also increments when depositing runes at the bank, so it is **not** an
exchange count; use the crafter counter and exchange logs.

### Real-speed fishing throughput

Fishing/Fletching 99, Barbarian Village, fly rod and 10,000 initial feathers,
cooking/mule modes Off, `bank=false`. Compared each account's ticks 21–581:

| Mode | Ticks | Actual elapsed | Catches | XP | Catches/hour | XP/hour |
|---|---:|---:|---:|---:|---:|---:|
| [three_tick_fly=true](logs/fish.log) | 560 | 336,181 ms | 126 | 7,600 | 1,349 | 81,385 |
| [Native fishing](logs/native.log) | 560 | 336,050 ms | 79 | 4,850 | 846 | 51,957 |

[throughput.json](throughput.json) records the calculation inputs. Rates use actual
elapsed milliseconds, not accelerated ticks or the bot's rounded display. The
three-tick run consumed its carrier log, banked startup junk, acquired a replacement
log and resumed fishing; this downtime is included. Its initial inventory retained
Tutorial Island items, whereas the native fixture cleared them. These are short,
unseeded-RNG live observations with different start times, not a controlled speedup
estimate or long-run performance guarantee. Both observation windows use real
600 ms ticks. An earlier acquisition pilot died while walking with tutorial combat
stats; the successful ground fixture seeds Hitpoints/Defence 99 and isolates kit
acquisition. Ground axe acquisition was not live-tested; the axe was seeded.

## Live-discovered fix

[The pre-fix inside run](logs/inside.log) repeatedly reached confirmation but moved
zero essence. Between offer and confirm, both interfaces temporarily report closed.
The dispatcher selected `CrafterRequestTrade`, sending a fresh request that declined
the existing exchange. Stable closure at the end of confirmation did not protect
the earlier transition.

Both active trade tasks now retain dispatcher priority until closure is stable for
600 ms. The regression exercises both roles across a temporary gap, a returning
screen and final sustained closure. The fixed inside/outside runs above each
completed four exchanges without the cancellation loop. No protocol/native change
was required.

## Reproduction

Use an empty scratch working directory for the engine. Create `data/config` and
`data/players`; copy the engine's PEM files and `world.json` into the former. Link
`data/pack`, `data/raw`, `public` and `view` to the engine's matching directories.
Never link `data/players` to an existing save directory. Apply the settings in
`manifest.json`: revision 289, nonproduction members, XP rate 1, profile `issue32`,
dedicated ports, build startup/liveReload false, and absolute content `srcDir`.
Launch the engine from that scratch working directory with Node 24 and its tsx
loader (on Windows, `--import` needs the loader's `file:///` URI):

```powershell
node --import file:///C:/path/to/engine/node_modules/tsx/dist/loader.mjs C:/path/to/engine/src/app.ts
```

Create a scratch JSON client template with that engine's RSA key and matching cache
and nav paths. From this repository root:

```powershell
python tools/live_issue32.py --config build/scratch-template.json --output build/issue32-replay
.\build\windows-msvc\Release\Rs2004Headless.exe build/issue32-replay/infix/client.json --raw-console
```

The tool prepares all cases or selected repeated `--case` arguments; it refuses an
existing output directory, generates new passwords and selects only the fixture
accounts. Account names are fixed, so use empty isolated engine saves for each
replay. Run each case's `client.json` separately. Preparation copies the current
bot scripts; replaying the cancelled pilot requires the pre-fix MuleCrafter source.
Stop each scratch client after its result: `request_finish` stops the script but
leaves the account logged in. Engine setup commands run at 600 ms too. The stall
fixture's finish text says 600 ticks but its actual limit is 160; use its recorded
`ACCEPT_FINAL ticks=160`, not that inherited label.

## Checks and remaining limits

- Release CTest: **878 cases, zero failures, 27 cache-dependent skips**;
  [full output](logs/ctest-release.log). Existing binaries were used because only
  Python scripts/specs and evidence changed.
- Focused feature specs passed in Release and Debug; MuleCrafter logic specs passed
  in Release. Port dialect lint and `git diff --check` passed.
- The fixture preparation tool was compiled and smoke-tested against two cases.
- Ground axe recovery, prolonged multi-mule contention, other rune types, other
  revisions and production/network-latency behavior remain outside this live sample.
  The supply clients keep requesting after the supplier completes; they receive no
  terminal shortage notification. Delivery accounting remains per script run.
- The failed dump pilot used a same-named untradeable quest Unicorn horn; it was a
  fixture error, not evidence that a supported tradeable dump fails. The final
  thirty-type dump uses tradeable content definitions and drains all stock.

This evidence covers issue #32's requested live workflows. Closure remains subject
to merging the MuleCrafter correction under the repository's development workflow.

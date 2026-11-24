# Phase 17d on local 289

Four fresh scratch accounts each run one quest through the real
`bots.aio_quester.AIOQuester`. Tracks [#156](https://github.com/ineedbots/lc-headless/issues/156).

| Case | Quest | Seeded completed prerequisites | Initial QP | Final QP |
|---|---|---|---|---|
| `ns` | Nature Spirit | Rune Mysteries, Priest in Peril, The Restless Ghost | 3 | 5 |
| `sm` | Shades of Mort'ton | Rune Mysteries, Priest in Peril | 2 | 5 |
| `tw` | Tai Bwo Wannai Trio | Druidic Ritual, Jungle Potion | 5 | 7 |
| `sv` | Shilo Village | Druidic Ritual, Jungle Potion | 5 | 7 |

Shades also seeds Nature Spirit **started** (`druidspirit=5`) solely to open
the Mort Myre gate; this awards no QP. Nature Spirit's own account starts at zero
target progress. All four target quests remain unstarted after preparation.

## Prepare and run

Use the [phase 17g prerequisites](../phase17g/README.md#prerequisites): a built
Release client, Python 3.12+, Node and the local members development server with
`node.production=false` and `login.enabled=false`. If stopped, start it with
`node --import tsx src/app.ts` from `../289server/engine` and wait for **World ready**.
From the headless repository root:

```powershell
python e2e/phase17d/run.py prepare --run-dir build/e2e/phase17d-night1 --operator-port 8111
python e2e/phase17d/run.py seed --run-dir build/e2e/phase17d-night1 --timeout-minutes 15
python e2e/phase17d/run.py run --run-dir build/e2e/phase17d-night1 --timeout-minutes 240
```

Preparation snapshots scripts, source revisions and the client binary hash and
generates four independent random credentials. Existing run directories and saved
characters are refused. Credentials and raw evidence remain under ignored `build/`.
Wait for seed `PASS` before starting quests. Seeding is one-shot; a failed attempt
requires fresh accounts. The launcher does not edit server files or existing saves.

## Preparation and limits

Skills are 75 melee, 85 hitpoints, 70 prayer, 60 magic/ranged, 65 fishing,
50 cooking, 35 herblore and 40 mining/smithing/crafting/woodcutting/firemaking/
thieving/agility. Fishing exceeds the Trio record's minimum because catching
Karambwan requires 65. Mining and Smithing cover Nature Spirit's silver chain;
Firemaking covers Trio's Jogre bones.

Banks contain one million coins, 1,000 lobsters, 100 prayer potions(3), rune melee
equipment, combat runes and ordinary tools. Trio additionally receives an ordinary
iron spear, one agility potion(4), a magic shortbow, 500 adamant arrows and a rune
med helm. It must poison the spear itself. No silver bar, sickle, ghostspeak amulet,
pouch, serum, shade remains, sacred oil, temple materials, Karambwan, rum, monkey
skin, Jogre bones, manuals, Shilo scrolls, beads, keys or quest remains are seeded.
The scripts must obtain these live. Bank contents and prerequisite completion
journals are verified. A 20-tick probe must take approximately 12 seconds.

Use normal 600 ms server ticks. Per-character infinite run is enabled by default;
`prepare --natural-run` omits it. This suite measures prepared quest completion.

## Results and monitoring

Each account emits `E2E_RESULT` and logs out after its queue ends. Acceptance
requires a complete target journal, exactly one newly completed quest, no stuck
queue entries, zero deaths, expected final QP and a clean process exit. The
launcher writes `results.json` only when all selected accounts pass.

Use the [shared operator examples](../phase17g/README.md#observe-stop-and-resume)
with port 8111 and generated account names. The read-only `inspect` command reports
dialogue, location, inventory, prayer and nearby NPCs. Resume unfinished cases with:

```powershell
python e2e/phase17d/run.py run --run-dir build/e2e/phase17d-night1 --cases tw
```

Record a **Time taken** column from the first per-account `AIOQuester, queue:`
entry to its passing `E2E_RESULT`, including the final bank return and excluding
seeding/login staggering. Disclose restarts and include their gaps. Fresh accounts
are required for an uninterrupted rerun. Pending runs are not passes.

```powershell
python -B -m unittest discover -s e2e/phase17d -p 'test_*.py'
```

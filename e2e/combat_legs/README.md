# Combat legs on local 289

These focused tests reproduce the dangerous legs found in the 65-account grand
run tracked by [#162](https://github.com/ineedbots/lc-headless/issues/162).
They seed **target quest checkpoints**, so their results are leg evidence rather
than fresh full-quest completion evidence. Use the phase suites afterward for
full acceptance. The launcher uses the same local-server checks, fresh-account
rules, logs, and script snapshots described in [the E2E guide](../README.md).
Keep the server unchanged at normal 600 ms ticks.

| Case | Seeded checkpoint | Required result |
|---|---|---|
| `hq` | Ice Queen chamber, no gloves | Kill the Queen and obtain her gloves, zero deaths |
| `rg` | Regicide stage 8, old camp | Kill the Tyras soldier and cross to the Arandar quarry, zero deaths |
| `lq` | Legends stage 16, top Viyeldi ledge | Descend, defeat the three guardians and forge the heart crystal, zero deaths |

Each account has Attack/Strength/Defence 75, Hitpoints 85, Prayer 70, and
Mining/Agility/Magic/Cooking/Crafting 70. Ordinary worn equipment is a rune
chainbody, platelegs and longsword. Heroes and Regicide carry eight food and two
prayer potions(3); Legends carries nine lobsters and three potions(3). No ice
gloves, crystal sections or finished heart are seeded. The runner uses real
quest functions and AIOQuester food/prayer upkeep, then logs out.

```powershell
python e2e/combat_legs/run.py prepare --run-dir build/e2e/combat-legs-night1
python e2e/combat_legs/run.py seed --run-dir build/e2e/combat-legs-night1
python e2e/combat_legs/run.py run --run-dir build/e2e/combat-legs-night1 --timeout-minutes 45
```

Use `--client <executable>` on prepare to select a build, and a fresh folder and
prefix for each new checkpoint run. `run --cases hq` selects an individual
prepared case. Preserve failed setup and run artifacts; do not reseed an existing
character. The runner records elapsed leg execution time in `elapsed_ms`.

## Original failure evidence

All timestamps below are UTC on 2026-11-24. Logs are retained under
`build/e2e/grand-20261124`.

| Quest/account | Death and failed leg | Findings |
|---|---|---|
| Heroes, `g178f773bph` | 22:17:36, leaving the Ice Queen chamber to bank after the fight timed out | No prayer potions were drawn by the inventory-owning quest. Prayer reached zero; eight lobsters were consumed. The shared fight's hungry branch could keep skipping attacks after food ran out. The long escape began in combat and death moved the account to Lumbridge. |
| Regicide, `h17178307rg` | 22:28:29, crossing toward the Arandar quarry | The soldier consumed all seven remaining sharks. The quest selected only a weapon and left banked armour behind; it declared no protection prayer. It continued gathering at 12% HP without food, then died on the quarry route. |
| Legends, `i17da08c3lq` | 22:54:12, fighting Ranalph Devere | A descent fall reached the cave floor inside a ledge retry loop, which continued trying an unreachable stand and spent food under attack. The guardian fight checked hunger before prayer restoration and kept skipping potion use after food was exhausted. Prayer ran out before the third guardian. |

The first focused batch retained two setup failures with zero deaths: the Heroes
starting tile `(2838,3515)` was unreachable, and the Legends account lacked the
furnace's Crafting requirement. Corrected tests use fresh characters and the
checkpoints and stats documented above. These setup failures are not passes.

## Full quest acceptance after the legs

Prepare new runs using [phase 17g](../phase17g/README.md),
[phase 17h](../phase17h/README.md), and [phase 17i](../phase17i/README.md).
Run both Hero gang partners together (`run --cases ph ba`), Regicide
(`run --cases rg`), and Legends (`run --cases lq`). Preserve the original failed
grand-run results. Record fresh uninterrupted elapsed times and zero deaths
before accepting the fixes.

# AccountLeveler

Set the account's `script.file` to `bots/leveler.py`. AccountLeveler plans training for all
19 skills, prepares supplies, and runs the selected bot through `ScriptActivity`.
It builds balanced melee stats first, then the remaining combat skills, then other skills.
A method can produce supplies for another: fishing and cooking food, collecting hides and
leather, mining and smelting bars, or collecting herbs and potion ingredients.

```jsonc
{
    "server": {"transport": "tcp", "host": "localhost", "port": 43594, "world": 0},
    "script": {
        "file": "bots/leveler.py",
        "settings": {
            "AccountLeveler": {
                "target_level": 60,
                "market_axes": true,
                "market_axe_budget": 50000,
                "wilderness": false
            }
        }
    }
}
```

Merge those sections into an existing account configuration with its login credentials.
Start off Tutorial Island with access to a bank and enough coins to buy equipment, supplies
and travel. The planner sources many consumables itself; it does not generate a starting
coin allowance. Missing funds, inaccessible producers or exhausted shop stock can block an
objective. Progress reports give the current action, shortage, cooldown and remaining work.

| Setting | Default | Meaning |
|---|---|---|
| `target_level` | `60` | Every skill's target, from 2 to 60 |
| `market_axes` | `true` | Try an optional Rune axe purchase near Seers on world 1 |
| `market_axe_budget` | `50000` | Maximum price, also limited to 10% of banked coins with a 200-coin travel reserve |
| `wilderness` | `true` | Allow eligible Wilderness camps and Edgeville monkey bars |

`server.world` is an explicit nonnegative identifier. Zero means unknown; a hostname or port
does not establish a world number. The optional player-market purchase requires world 1,
a fresh quote, the expected partner and exact axe/coin quantities on both trade screens,
followed by receipt. A failed optional purchase leaves normal equipment selection available.

With Wilderness disabled the planner excludes those camps and delegates Dragon Slayer with
`gather_wilderness_planks=false`. Its own supply and activity travel avoids the Wilderness
unless an allowed destination needs it, and avoids White Wolf Mountain.
Dragon progression checks food, armour, Prayer and quest readiness. It can prepare Lost City,
Druidic Ritual and Dragon Slayer, collect Paladin chaos runes, and buy dragon weapons after
Lost City using the Zanaris bank, diamond gate and an escape route.

Combat camps progress through tougher surface and dungeon targets as stats improve.
Quest, skill, food, tool and fare requirements gate each camp; Wilderness camps still
require `wilderness=true`. Dungeon trips retain and restock their travel coins and tools.
Baby blue dragons require a Dusty key and Dragonfire shield, and their bones are buried.
Combat loot includes herbs, potion secondaries and runes for later supply preparation.
Eligible melee and ranged weapons use their special attacks.

At Ranged 40, an affordable Ranging Guild session takes priority over ordinary combat.
It keeps a shopping coin reserve across the pack and bank; a failed guild activity enters
the same persistent cooldown as other failed combat routes. Ranged combat stays at the
lower two camp tiers. Lobster and shark fishing can prepare travel food before departure.

A parent tick observes XP and bank changes even while a child is waiting. Sessions end at
their skill, stock, quest or duration goal; failures retain actionable shortages, back off
preparation, and cool down failed combat routes. Death interrupts the child and replans.
Recent camps encourage rotation. This is best-effort unattended training, not a guarantee
that every account can reach 60 without intervention.

Progress is saved under `script.settings.AccountLevelerState.progress`, separate from the
bot's settings schema. It contains the objective, recent camps, attempts, death count,
remaining cooldown durations and diagnostics. Restarting restores valid planner memory;
a child generator is recreated from current bank and skill state. Stop the account before
removing that namespace to reset its remembered history.

The implementation is `scripts/bots/account_leveler/`: `planner`, `methods`, `combat`,
`priority` and `session` choose and bound work; `shopping`, `supplies`, `stock`, `offers`
and `equipment` prepare it; `dragons`, `dragon_weapons`, `runes`, `zanaris` and `travel`
handle the higher-level prerequisites. `manifests` imports only a selected child's `BOT`.
The entry is named `leveler.py` so pocketpy can distinguish it from the package.

# The side tabs: quests, prayer, special attacks, combat styles and magic

Each is found in its tab's interface by what it is, so a weapon swap that changes the combat tab just works. The combat-style and spell-casting methods live on [`game`](game.md#combat-styles); the helpers they use are here.

- [`quests`](#quests)
- [`prayer`](#prayer)
- [`special`](#special)
- [Combat style functions](#combat-style-functions)
- [Spells](#spells) and [`autocast`](#autocast)

## `quests`

The quest list. Only the list's colours, the quest points and the journals reach the client; the engine sends nothing else about a quest's progress.

| Method | Gives |
|---|---|
| `quests.all()` | Every quest in the list, as `Quest`s |
| `quests.status(name)` | `'not_started'`, `'in_progress'` or `'complete'`, from the row's colour (red, yellow or green), or `'unknown'` when there's no such row. Names match whole, without regard to case |
| `quests.points()` | Your quest points |
| `quests.journal(name)` | **Wait.** Opens the quest's journal and gives its lines, or `[]` when it didn't open within 5 seconds |

A `Quest` has `name`, `status` (as above) and `com` (the row's button).

```python
if quests.status("Cook's Assistant") != 'complete':
    lines = yield from quests.journal("Cook's Assistant")
```

## `prayer`

Prayers by name, lower case, as `PRAYER_NAMES` has them.

| Method | Gives or does |
|---|---|
| `prayer.points()` | Prayer points left |
| `prayer.max()` | Your Prayer level |
| `prayer.full()` | Points are at the maximum |
| `prayer.known(name)` | Whether `name` is a prayer |
| `prayer.available(name)` | Your level is high enough and you have points left |
| `prayer.active(name)` | Whether it's on |
| `prayer.set(name, on)` | **Wait.** Turns it on or off, and waits up to 2 seconds for the server to agree. `True` when it's as asked, including when it already was; `False` when unknown or not available |
| `prayer.clear()` | **Wait.** Turns off every prayer that's on |

`PRAYER_NAMES`, with the level each needs:

| Prayer | Level | Prayer | Level |
|---|---|---|---|
| `'thick skin'` | 1 | `'protect item'` | 25 |
| `'burst of strength'` | 4 | `'steel skin'` | 28 |
| `'clarity of thought'` | 7 | `'ultimate strength'` | 31 |
| `'rock skin'` | 10 | `'incredible reflexes'` | 34 |
| `'superhuman strength'` | 13 | `'protect from magic'` | 37 |
| `'improved reflexes'` | 16 | `'protect from missiles'` | 40 |
| `'rapid restore'` | 19 | `'protect from melee'` | 43 |
| `'rapid heal'` | 22 | | |

```python
if not prayer.active('protect from melee') and prayer.available('protect from melee'):
    yield from prayer.set('protect from melee', True)
```

## `special`

The special attack bar. Arming is one-shot: the next attack spends it.

| Method | Gives or does |
|---|---|
| `special.energy()` | Special energy, 0 to 1000 (`SA_MAX_ENERGY`); 1000 is the full bar |
| `special.armed()` | Whether the next attack is a special |
| `special.wielded()` | The wielded weapon's name, or `''` with empty hands |
| `special.cost(weapon_name)` | The energy its special costs, or `None` for a weapon without one |
| `special.ready(weapon_name)` | It has a special and the energy is there |
| `special.bar_component()` | The combat tab's "Use Special Attack" bar, or -1 when the weapon has none |
| `special.arm()` | **Wait.** Clicks the bar and waits up to 2 ticks for it to arm. `True` when armed, including when it already was |

Costs known to `special.cost`: dragon dagger, dragon dagger(p), dragon longsword, dragon mace, dragon spear (and (p), (kp)), rune claws: 250; dragon halberd: 300; rune thrownaxe: 100; magic shortbow and magic longbow: 350.

```python
weapon = special.wielded()
if game.in_combat() and special.ready(weapon):
    yield from special.arm()
```

## Combat style functions

`game.set_combat_style(style)` and its friends are on [`game`](game.md#combat-styles). These are the rules beneath them.

| Function or constant | Gives |
|---|---|
| `COMBAT_STYLE_OPTIONS` | `['attack', 'strength', 'controlled', 'defence']`, the melee training styles |
| `parse_combat_style(name)` | The training style a name means, `'strength'` when it doesn't know it. Takes `attack`/`accurate`, `strength`/`aggressive`, `controlled`/`shared`, `defence`/`defense`/`defensive`, without regard to case |
| `try_parse_combat_style(name)` | The same, or `None` for an unknown name |
| `parse_interface_combat_style(label)` | The training style a combat tab label names, such as `'attack'` for `'(Accurate)'`, or `None` |
| `resolve_combat_style(style, offered)` | Among `offered` `(mode, label)` pairs, a `CombatStyleResolution` for the mode that trains `style`, else for the last defensive one, else `None` |
| `RANGE_STYLE_OPTIONS` | `['accurate', 'rapid', 'longrange']` |
| `parse_range_style(name)` | The combat mode of a ranged style: 0 accurate, 1 rapid, 2 long range (`'longrange'`, `'long range'` or `'long-range'`). 1 for an unknown name |

### `CombatStyleResolution`

| Field | Meaning |
|---|---|
| `requested` | The style asked for |
| `effective` | The style the weapon gives, which is `'defence'` when it fell back |
| `mode` | The combat mode to select |

## Spells

Cast with [`game.cast_on_npc`, `cast_on_item` and the rest](game.md#casting-spells), by the spell's name. A spell is the magic tab's Target button whose spell name matches, without regard to case. [`game.teleport(name)`](game.md#actions) clicks a "Cast ... Teleport" button.

## `autocast`

Autocasting from a staff.

| Method | Gives or does |
|---|---|
| `autocast.armed()` | Autocast is on |
| `autocast.staff_tab_attached()` | The combat tab is a staff's, with its Choose Spell button |
| `autocast.arm(spell, log=None)` | **Wait.** Opens the spell chooser, chooses `spell`, and turns autocast on, waiting up to 3 seconds at each step. `False`, with a line to `log`, when the spell isn't an autocast spell, no staff is wielded, or your Magic level is too low |

`AUTOCAST_SPELLS` lists the spells, in the chooser's order: `'wind strike'`, `'water strike'`, `'earth strike'`, `'fire strike'`, `'wind bolt'`, `'water bolt'`, `'earth bolt'`, `'fire bolt'`, `'wind blast'`, `'water blast'`, `'earth blast'`, `'fire blast'`, `'wind wave'`, `'water wave'`, `'earth wave'`, `'fire wave'`.

```python
if not autocast.armed():
    yield from autocast.arm('fire strike', log)
```

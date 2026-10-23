# Quest steps: `rs2004.quests`

rs2b0t's quest engine is built from small steps: talk to an NPC through its dialogue, walk to one across a ladder, act on a loc and answer what it asks. Bots outside quests use them too, so they come ahead of the engine itself. They're imported, not builtins:

```python
from rs2004.quests.exec import talk_through, goto_npc, NpcStop, LadderHop
```

Each step takes a `log` function for its progress lines, such as a bot's `self.log`, and each that walks or clicks is a **Wait**. A step that takes a description of where to go, a stop, a hop or a door, reads its fields as attributes: use the classes below, or a [`Record`](catalogs.md#records), whose missing fields read as `None`, as rs2b0t's object literals translate.

## Talking: `rs2004.quests.exec`

| Function | Does |
|---|---|
| `talk_through(npc_name, prefer, log, gap_ms=None)` | **Wait.** `open_dialogue`, then `drive_dialog`. `True` once the dialogue closed |
| `open_dialogue(npc_name, log)` | **Wait.** Talks to the nearest NPC of that name with a Talk option, opening a door it stands behind. `True` once a dialogue is up |
| `drive_dialog(prefer, log, gap_ms=None)` | **Wait.** Clicks through the open dialogue, choosing the first option holding a `prefer` fragment, and the last option when none does, until the dialogue closes or stays quiet for `gap_ms` (1.5 seconds by default, `DIALOG_GAP_MS`). Stops when a random event is pending |
| `talk_strict(npc_name, prefer, log)` | **Wait.** Like `talk_through`, but stops instead of guessing when no option matches: several ogres offer "I have come to kill you" as the alternative |
| `talk_choosing_by(npc_name, rules, prefer, log)` | **Wait.** For a dialogue whose right answer depends on what the NPC said: the first `LineRule` whose `when_line` is in the NPC's last line picks the option, else `prefer` does, else it stops |
| `pick_preferred(options, prefer)` | The first option holding a preferred fragment, trying the fragments in order, by part and without regard to case, or `None` |
| `pick_by_line(lines, options, rules)` | The option the matching rule names, longest `when_line` first, ignoring colour tags and pipes, or `None` |
| `talk_op(actions)` | The first option starting "talk", or `None` |

`LineRule(when_line, choose)` is a rule: choose the option holding `choose` when the NPC's line holds `when_line`, in lower case.

```python
from rs2004.quests.exec import LineRule, talk_choosing_by

SKAVID = [LineRule('ar cur', 'Gor.'), LineRule('cur tanath', 'Bidith.')]
ok = yield from talk_choosing_by('Mad skavid', SKAVID, [], self.log)
```

## Getting to NPCs

| Function | Does |
|---|---|
| `goto_npc(stop, hops, log)` | **Wait.** Walks to an `NpcStop`: across a ladder in `hops` first when its anchor is on the other side of the ground, through its `approach` tiles, then to the anchor. `True` once the NPC is within its leash. Landing somewhere underground the anchor can't be reached from, it climbs back up to try the landing again, and gives `False` |
| `walk_with_hops(dest, radius, hops, log)` | **Wait.** Walks to `dest`, climbing the nearest ladder in `hops` first when `dest` is on the other side of the ground |
| `is_underground(t)`, `needs_hop(here, anchor)` | Whether a tile is underground (`z` 5000 and up), and whether two are on different sides |

| Class | Fields |
|---|---|
| `NpcStop(npc, anchor, leash, prefer, approach=None, gap_ms=None)` | The NPC's name; the tile it's found near and how far it wanders; the options to prefer when talking; tiles to walk through on the way; how long a lull in its dialogue may last, for a scene that walks it about |
| `LadderHop(stand, loc_name, op, arrive, open=None, walk=None)` | A ladder between the surface and underground: stand by it, use `op` on the `loc_name` loc within 3 tiles, and arrive. `open` is the option that opens it first, as a trapdoor's; `walk` a tile to walk to first when `stand` is behind a door the route can't pin |

```python
from rs2004.quests.exec import LadderHop, NpcStop, goto_npc, talk_through

HOPS = [
    LadderHop(Tile(3105, 3162, 0), 'Ladder', 'Climb-down', Tile(3104, 9576, 0), walk=Tile(3108, 3162, 0)),
    LadderHop(Tile(3104, 9576, 0), 'Ladder', 'Climb-up', Tile(3105, 3162, 0)),
]
SEDRIDOR = NpcStop('Sedridor', Tile(3103, 9572, 0), 8, ["I'm looking for the head wizard."])

arrived = yield from goto_npc(SEDRIDOR, HOPS, self.log)
if arrived:
    yield from talk_through(SEDRIDOR.npc, SEDRIDOR.prefer, self.log)
```

## Locs and doors

| Function | Does |
|---|---|
| `prompt_loc(step, log)` | **Wait.** Walks to a `LocPrompt`'s loc, uses its option, and answers whatever it raised, in either the chat box or the main modal, until `step.expect()` holds. `True` then. On failure it clears the boxes left standing, so a retry can click |
| `use_on_loc(item_id, loc, prefer, expect, log)` | **Wait.** Walks near a loc, uses the carried `item_id` on it, and answers what it raised until `expect()` holds. `loc` has a `name` and a `near` tile, and may have `within` (12 by default) and an `id` for when the name is shared |
| `cross_teleport_door(door)` | **Wait.** Crosses a `DoorCrossing`, a quest door whose Open teleports you through and shuts behind you. A game message after the click is a refusal; the far side is the only proof of a crossing |
| `drive_choice(prefer, log)` | **Wait.** Like `drive_dialog`, but stops on an option list none of `prefer` matches: a loc's prompt often offers the refusal first |
| `drive_until(expect, prefer, log, ms=30000)` | **Wait.** Keeps answering prompts until `expect()` holds or `ms` pass, holding the quest's protection prayer between them |
| `drive_boxes(expect, ms, prefer=None, log=None)` | **Wait.** Clicks a chain of message boxes away one at a time, in either widget, testing `expect()` before each, so the box carrying the answer is still readable |
| `clear_boxes(max_boxes=8)` | **Wait.** Dismisses every standing message box |
| `settle_scene()` | **Wait.** 2 ticks after a level or region change, as rs2b0t waits for its loc queries |
| `loc_near(name, op, within=12)` | The nearest loc of that name offering `op`, or `None` |
| `held_id(id)` | How many of the item id you carry |

| Class | Fields |
|---|---|
| `LocPrompt(name, op, near, expect, prefer=None, expect_ms=None, within=None, id=None, refused=None)` | Use `op` on the `name` loc near `near`, then answer with `prefer` until `expect()`, within `expect_ms` (20 seconds). `within` is how far from `near` to look (10), `id` picks a loc whose name is shared, and `refused` is a game message [pattern](walking.md#game_messages) the loc answers with when the option can't work yet |
| `DoorCrossing(id, stand, is_far, log, prefer=None, name=None, op=None, use_item=None, stand_radius=None)` | The door's loc id; the tile to click from, on the side you're leaving; `is_far()`, true once you're past it; the options for a door that asks something; its name and option when it isn't a Door offering Open; a key's item id for a locked door; and how far from `stand` counts as there, 0 for a door that tests your side by one coordinate |

```python
from rs2004.quests.exec import LocPrompt, prompt_loc

mark = game_messages.mark()
step = LocPrompt('Crate', 'Search', Tile(3208, 3210), lambda: game_messages.saw_since(mark, 'You find'))
found = yield from prompt_loc(step, self.log)
```

## Prayer: `rs2004.quests.prayer`

A quest declares the protection prayer it fights under as `{'protect': 'melee', 'magic' or 'missiles', 'potions': doses}`. `set_quest_prayer` points the upkeep at it, and `prayer_upkeep`, which `drive_until` calls between prompts, spends one tick on it when needed: raising the prayer in a fight, drinking a dose at the floor, and dropping the prayer when the fight ends.

| Name | Is |
|---|---|
| `set_quest_prayer(pray, log)` | Points the upkeep at a quest's prayer; `None` for one that declares none |
| `prayer_upkeep()` | **Wait.** At most one tick of upkeep. `True` when it acted |
| `prayer_upkeep_action(in_combat, protect_active, protect_available, points, doses)` | The one thing to do: `'none'`, `'protect'`, `'drink'` or `'drop'` |
| `PRAYER_FLOOR` | 25: the points at which a dose is drunk |
| `PROTECT_LEVEL`, `PROTECTION_NAME` | Each kind's Prayer level (37, 40, 43) and prayer name |
| `protection_name(pray)`, `protection_level(pray)` | The same, for a declaration |
| `PRAYER_POTION`, `PRAYER_POTION_IDS` | `'Prayer potion(4)'`, and the ids of every dose |
| `quest_prayer_state` | The running quest's `current` declaration, whether it `warned` that the level is too low, and its `log` |

# You and the game: `game`, `skills`, `reader`, `chat`, `friends`, `ignores`

## `game`

Your own state, and actions on yourself.

### State

| Method | Gives |
|---|---|
| `game.ingame()` | Logged in and placed in the world, so the map is built and actions are taken |
| `game.scene_ready()`, `game.scene_state()` | rs2b0t's: `ingame()`, and 2 once placed or 0 before |
| `game.tile()` | Your [`Tile`](geometry.md#tile), or `None` before you're placed |
| `game.energy()` | Run energy, 0 to 100 |
| `game.run_enabled()` | Whether run is on |
| `game.weight()` | Carried weight in kg |
| `game.in_combat()` | You were hit within the last 8 ticks. 2004 has no combat-state packet, so this is the only signal |
| `game.animating()` | You're playing an animation, such as a swing or a chop |
| `game.moving()` | You're walking or running |
| `game.tick()` | Server ticks since the first login. It carries on across reconnects and server restarts, so a tick kept to compare against later stays valid |
| `game.revision()` | The server revision the client speaks: `225`, `274` or `289` (`login.revision` in `client.jsonc`) |
| `game.my_name()` | Your name |
| `game.combat_level()` | Your combat level |
| `game.attacked_by_player()` | You're in combat and facing a player, which for a bot that doesn't start fights means one attacked you |
| `game.facing()` | Who you face, as an entity's `target`: `('npc', index)`, `('player', index)` or `None` |
| `game.overhead_text()` | rs2b0t's `reader.selfChat`: the text over your head while the webclient would show it, 5 ticks, else `None` |
| `game.appearance_screen_open()` | The character design screen is open, as on a new account |

### Actions

| Method | Does |
|---|---|
| `game.set_run(on)` | Turns run on or off. Note that the [run manager](upkeep.md#the-run-manager) turns it back on by default |
| `game.open_side_tab(tab)` | **Wait.** rs2b0t's: opens a side tab. Every tab's interface is readable here without opening it, so it gives `True` at once |
| `game.set_appearance(female, kits, colours)` | Saves a character design and accepts it. `kits` is 7 identity-kit ids (head, jaw, torso, arms, hands, legs, feet); `colours` is 5 colour indexes (hair, torso, legs, feet, skin). `False` when the design screen isn't open. The server checks the design and ignores one it doesn't allow. The engine's default man is `(False, [0, 10, 18, 26, 33, 36, 42], [0, 0, 0, 0, 0])` |
| `game.teleport(name)` | Casts a standard teleport by name: `'Varrock'` or `'Varrock teleport'`. `True` once the click is sent; check the arrival yourself. `False` when the spellbook has no such button |

### Combat styles

The combat tab's style buttons, found by what they are, so they follow whatever weapon is wielded.

| Method | Gives or does |
|---|---|
| `game.combat_mode()` | The selected mode, the value of varp 43, which the style buttons set |
| `game.combat_styles()` | The wielded weapon's styles as `(mode, label)` pairs, top to bottom, such as `[(0, '(Accurate)'), (1, '(Aggressive)'), (3, '(Defensive)')]`. `None` before the combat tab has been sent |
| `game.combat_style_resolution(style)` | How the weapon trains `style`: a [`CombatStyleResolution`](side-tabs.md#combatstyleresolution), falling back to its last defensive style, or `None` |
| `game.combat_style_mode(style)` | That resolution's mode, or `None` |
| `game.has_combat_style(style)` | Whether that style's mode is selected now |
| `game.set_combat_style(style)` | Selects a style. `style` is `'attack'`, `'strength'`, `'controlled'` or `'defence'`, or a label's word such as `'aggressive'` or `'accurate'`, or a mode number. An unknown name raises `ValueError`. `False` when the weapon has neither the style nor a defensive one |
| `game.set_combat_mode(mode)` | Clicks the button that sets this mode. Use it for ranged styles, with [`parse_range_style`](side-tabs.md#combat-style-functions) |
| `game.auto_retaliate_on()` | Whether auto retaliate is on |
| `game.set_auto_retaliate(on)` | Clicks the auto-retaliate button to turn it on or off |

```python
game.set_combat_style('strength')
game.set_combat_mode(parse_range_style('rapid'))
```

rs2b0t's helpers for the same reads, which take the raw values:

| Name | Gives |
|---|---|
| `retaliate_on_from_varp(value)` | Whether auto retaliate is on, given varp 172's value: it's inverted, 0 for on |
| `PLAYER_FACE_BASE` | 32768. The server encodes a player face target as the player's index plus this, and an NPC's as its index |
| `facing_player(face_entity)` | Whether a face target is a player: rs2b0t's raw number, or a `target` pair such as `game.facing()` gives. `None` faces nothing |

### Casting spells

Each takes the spell's name as the magic tab's button names it, such as `'Wind strike'` or `'High level alchemy'`, matched without regard to case, and returns `False` when the spellbook has no such spell. Casting doesn't wait.

| Method | Casts on |
|---|---|
| `game.cast_on_npc(spell, npc)` | An [`Npc`](world.md#npc) |
| `game.cast_on_player(spell, player)` | A [`Player`](world.md#player) |
| `game.cast_on_loc(spell, loc)` | A [`Loc`](world.md#loc) |
| `game.cast_on_ground_item(spell, item)` | A [`GroundItem`](world.md#grounditem) |
| `game.cast_on_item(spell, item)` | A backpack [`InvItem`](items.md#invitem), as alchemy and Superheat Item are cast |

```python
nats = inventory.count('Nature rune')
bow = inventory.first('Yew longbow')
if nats > 0 and bow is not None:
    game.cast_on_item('High level alchemy', bow)
```

See also [`autocast`](side-tabs.md#autocast).

## `skills`

Levels and experience. Skill names are lower case: `'attack'`, `'defence'`, `'strength'`, `'hitpoints'`, `'ranged'`, `'prayer'`, `'magic'`, `'cooking'`, `'woodcutting'`, `'fletching'`, `'fishing'`, `'firemaking'`, `'crafting'`, `'smithing'`, `'mining'`, `'herblore'`, `'agility'`, `'thieving'`, `'runecraft'`. Surrounding spaces and case are ignored.

| Method | Gives |
|---|---|
| `skills.level(name)` | The base level, unboosted |
| `skills.effective(name)` | The current level, boosted or drained. For hitpoints and prayer, the points left |
| `skills.xp(name)` | Experience |
| `skills.index(name)` | The skill's index, the same as the [skill constant](constants.md#skills), or -1 for a name that isn't a skill |
| `skills.hp_fraction()` | Current hitpoints over base, 0 to 1 (more when boosted); 1 while they aren't known yet |

`level`, `effective` and `xp` raise `ValueError` for a name that isn't a skill.

```python
if skills.hp_fraction() < 0.5:
    food = inventory.first('Lobster')
    if food is not None:
        food.interact('Eat')
```

## `reader`

Raw reads, for what no facade covers.

| Method | Gives |
|---|---|
| `reader.varp(id)` | A player variable's value |
| `reader.pid()` | Your index in the server's player list |
| `reader.main_modal()` | The main interface's id, such as the bank's, or -1 |
| `reader.main_modal_texts()` | The open main interface's text lines, or `[]` when none is open |
| `reader.modal_buttons(root)` | rs2b0t's `modalButtons`: every button under that interface but close buttons, each a `ModalButton` with `com_id`, `label` (its caption), `menu`, `hidden` (it or a layer above it hidden, as `if_sethide` arms it) and `pause` (a continue button, which `_core.click_component` answers with a resume) |
| `reader.main_modal_button_near_text(label)` | rs2b0t's `mainModalButtonNearText`: the button nearest the main interface's first text containing `label`, or -1 |
| `reader.side_modal()` | The interface replacing the side tabs, or -1 |
| `reader.chat_modal()` | The chat box interface, such as a dialogue, or -1 |
| `reader.modals()` | rs2b0t's: all three, as an object with `main`, `side` and `chat` |
| `reader.interface_open(id)` | Whether that interface is open |
| `reader.component_text(com)` | A component's text as the player sees it, or `None` |
| `reader.count_dialog_open()` | Whether an "Enter amount" dialog is open |
| `reader.inventory(com)` | The [`InvItem`](items.md#invitem)s of any inventory the server sent, such as `BANK` |
| `reader.npc_type(id)` | An [`NpcType`](world.md#npctype--readernpc_typeid), or `None` |
| `reader.item_type(id)` | An [`ItemType`](world.md#itemtype--readeritem_typeid), or `None` |
| `reader.obj_catalog()` | rs2b0t's `reader.objCatalog`: every named obj in the cache as an `ObjRecord` (`id`, `name`, `cost`, `stackable`, `members`, `equippable`, `note_of`, `stack_variant`), read once and kept. The [market's catalog](market.md#the-catalog) is built from it |
| `reader.loc_type(id)` | A [`LocType`](world.md#loctype--readerloc_typeid), or `None` |
| `reader.item_ids(name)` | Every item id with that name in the cache, without regard to case |
| `reader.npc_ids(name)` | The same for NPCs |
| `reader.loc_ids(name)` | The same for scenery |
| `reader.hint_arrow()` | The arrow the server points with, a [`HintArrow`](#hintarrow), or `None` |
| `reader.hint_tile()` | rs2b0t's: the tile the hint arrow points at, or `None` when there's no arrow or it points at an NPC or a player |

```python
name = reader.item_type(1511).name     # 'Logs'
oak_ids = reader.loc_ids('Oak')
```

For interfaces in depth, see [`interfaces`](interfaces.md).

### `HintArrow`

| Attribute | Is |
|---|---|
| `kind` | `'tile'`, `'npc'` or `'player'` |
| `index` | The NPC's or player's index, for those kinds; match it against `Npc.index` |
| `tile` | The [`Tile`](geometry.md#tile) pointed at, for a `'tile'` arrow, else `None` |

```python
arrow = reader.hint_arrow()
if arrow is not None and arrow.kind == 'npc':
    target = npcs.query().where(lambda n: n.index == arrow.index).first()
```

## `chat`

| Method | Does |
|---|---|
| `chat.say(text)` | Says `text` in public chat |
| `chat.send_pm(name, text)` | Sends a private message |
| `chat.command(text)` | Sends a `::command`, for staff accounts on servers that allow them: `chat.command('tele 0,50,51,30,34')`. Leave out the `::` |

## `friends` and `ignores`

| Method | Gives or does |
|---|---|
| `friends.list()` | Your friends as `[(name, world)]`, world 0 when offline |
| `friends.add(name)`, `friends.remove(name)` | Adds or removes a friend |
| `ignores.list()` | The names on your ignore list |
| `ignores.add(name)`, `ignores.remove(name)` | Adds or removes one |

Private messages and chat arrive as [events](events.md): `on_private_message(sender, msg)` and `on_chat_message(e)`.

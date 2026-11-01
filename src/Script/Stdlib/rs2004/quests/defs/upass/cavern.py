"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/cavern.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import npcs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_LOC, UP_NPC, UP_TILE, inside_witch_house
from rs2004.quests.defs.upass.bridge import drive_through_boxes, loc_by_id, walk_to
from rs2004.quests.defs.upass.chest import chest_form
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.reach import reach

__all__ = ['descend_to_dwarves', 'ascend_from_dwarves', 'ask_nilhoof', 'ask_klank', 'wear_gauntlets', 'catch_cat', 'steal_the_doll', 'leave_witch_house', 'distract_witch', 'loot_witch_chest']

def talk_to(npc_id, name, near, prefer, log):
    _w1 = yield from walk_to(near, 2, log)
    if not (_w1):
        return False
    yield from settle_scene()
    npc = npcs.query().where(lambda n: n.id == npc_id).within(12).nearest()
    if not npc:
        log(f'no {name} near ({near.x},{near.z})')
        return False
    _w2 = yield from reach.npc_dialog((npc.name if npc.name is not None else name), near, log=log)
    if (_w2) != 'done':
        log(f'no dialogue with {name}')
        return False
    _result3 = yield from talk_strict((npc.name if npc.name is not None else name), prefer, log)
    return _result3


def descend_to_dwarves(log):
    """Down the wall tunnel into the dwarves' cave."""
    _w4 = yield from walk_to(UP_TILE.TUNNEL_TO_DWARVES, 3, log)
    if not (_w4):
        return False
    yield from settle_scene()
    tunnel = loc_by_id(UP_LOC.TUNNEL_DOWN, None, 8)
    op = ((tunnel.actions() if tunnel is not None else None) or [None])[0]
    if not tunnel or not op or not (tunnel.interact(op)):
        log('no wall tunnel down to the dwarves')
        return False
    # Why: the first descent adds Koftik and opens his `~mesbox` greeting, which a chat driver cannot dismiss.
    _result5 = yield from drive_through_boxes(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 0)) > 9700, [], log, 20000)
    return _result5


def ascend_from_dwarves(log):
    """Back up the tunnel to the level-1 platforms."""
    _w6 = yield from walk_to(UP_TILE.TUNNEL_FROM_DWARVES, 3, log)
    if not (_w6):
        return False
    yield from settle_scene()
    tunnel = loc_by_id(UP_LOC.TUNNEL_UP, None, 8)
    op = ((tunnel.actions() if tunnel is not None else None) or [None])[0]
    if not tunnel or not op or not (tunnel.interact(op)):
        log('no wall tunnel up out of the dwarves cave')
        return False
    _result7 = yield from drive_until(lambda: (((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else 0)) == 1, [], log, 15000)
    return _result7


def ask_nilhoof(log):
    return talk_to(UP_NPC.NILHOOF, 'Nilhoof', UP_TILE.NILHOOF, [], log)


def ask_klank(log):
    return talk_to(UP_NPC.KLANK, 'Klank', UP_TILE.KLANK, ['What happened to them?', 'Take care Klank'], log)


def wear_gauntlets(log):
    """The soulless bite for 10 unless the gauntlets are on."""
    if held_id(UP_ITEM.GAUNTLETS.id) == 0:
        return True
    _w8 = yield from equipment.equip(UP_ITEM.GAUNTLETS.name)
    if not (_w8):
        log("could not wear Klank's gauntlets")
        return False
    return True


def catch_cat(log):
    """Bag the witch's cat from the platform below her house."""
    if held_id(UP_ITEM.WITCH_CAT.id) > 0:
        return True
    _w9 = yield from walk_to(UP_TILE.WITCH_CAT, 2, log)
    if not (_w9):
        return False
    yield from settle_scene()
    # Why: the cat wanders its platform, so the query reaches further than the walk radius, and it says what it found because a silent false alternates the step between fetching a cat and knocking with nothing.
    cat = npcs.query().where(lambda n: n.id == UP_NPC.WITCH_CAT).within(20).nearest()
    op = ((cat.actions() if cat is not None else None) or [None])[0]
    if not cat or not op:
        at = game.tile()
        log(f'no witches cat within twenty of ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) — free slots {inventory.free()}')
        return False
    if not (cat.interact(op)):
        log(f'\'{op}\' would not send at the cat')
        return False
    _result10 = yield from drive_until(lambda: held_id(UP_ITEM.WITCH_CAT.id) > 0, [], log, 12000)
    return _result10


# Why: knocking draws Kardia out only if the cat is already by the door; the door's op1 answers with 25% damage while she's inside.
# Why: the knock takes the cat and the journal never records it, so a snapshot reads "no cat, no doll" before and after the knock. Catching, knocking and opening the chest are one step, ending on the doll, which the journal does record.
def steal_the_doll(log):
    """Take the cat to Kardia's door, knock, and lift the doll from her chest while she is outside."""
    for round in range(3):
        if held_id(UP_ITEM.DOLL.id) > 0:
            return True
        # Why: the cat first, because the chest is across the platforms and finding her still inside costs the trip twice. A cat that can't be caught is usually already at her door from an earlier round, so the chest is still tried.
        if held_id(UP_ITEM.WITCH_CAT.id) == 0:
            yield from catch_cat(log)
        _c11 = held_id(UP_ITEM.WITCH_CAT.id) > 0
        if _c11:
            _w12 = yield from distract_witch(log)
            _c11 = not (_w12)
        if _c11:
            log('Kardia would not come to the door')
        _w13 = yield from loot_witch_chest(log)
        if _w13:
            return True
    return held_id(UP_ITEM.DOLL.id) > 0


# Why: from the door's own tile the knock draws no reply at all, no "You knock on the door...", no "I can't reach that!", so the op is dropped before the script. A wall is operated from a side and which side isn't knowable here, so every side gets a turn and reports the chat on one line, because the harness only surfaces a few log lines per poll.
def leave_witch_house(log):
    """Out of Kardia's house, which the navigator has no way out of."""
    mark = game_messages.mark()
    for tries in range(4):
        if not (inside_witch_house(game.tile())):
            break
        shut = loc_by_id(UP_LOC.WITCH_DOOR, 'Open', 8)
        if shut and not (shut.interact('Open')):
            log("the way out of Kardia's house would not open")
        yield from drive_until(lambda: loc_by_id(UP_LOC.WITCH_DOOR, 'Open', 8) is None, [], log, 6000)
        # Why: the collision pack still calls the door tile blocked, so the navigator won't click; a raw walk leaves the pathing to the server, which can see the opened door.
        yield from direct_navigator.walk_to(UP_TILE.WITCH_DOOR_OUT, 0, 15000)
    if not inside_witch_house(game.tile()):
        return True
    at = game.tile()
    said = ' / '.join([t for t in [m.text for m in game_messages.since(mark)] if not t.startswith('get ')][-3:])
    log(f"still shut in Kardia's house at ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) — said: {said or 'nothing'}")
    return False


def distract_witch(log):
    """Knock with the cat in the pack, which puts it down and takes her away from the chest."""

    def gone():
        return held_id(UP_ITEM.WITCH_CAT.id) == 0

    door = UP_TILE.WITCH_DOOR
    stands = [
        door,
        Tile(door.x, door.z + 1, door.level),
        Tile(door.x, door.z - 1, door.level),
        Tile(door.x - 1, door.z, door.level),
        Tile(door.x + 1, door.z, door.level),
    ]
    tried = []
    for stand in stands:
        _w14 = yield from walk_to(stand, 0, log)
        if not (_w14):
            tried.append(f'({stand.x},{stand.z}) unreachable')
            continue
        yield from settle_scene()
        loc = loc_by_id(UP_LOC.WITCH_DOOR, None, 16)
        if not loc:
            tried.append(f'({stand.x},{stand.z}) no door')
            continue
        mark = game_messages.mark()
        _c15 = loc.interact('Knock')
        if _c15:
            _w16 = yield from drive_until(gone, [], log, 8000)
            _c15 = _w16
        if _c15:
            return True
        # Why: `oplocu` reaches the same drop label with no op index to resolve.
        cat = ([item for item in inventory.items() if item.id == UP_ITEM.WITCH_CAT.id] or [None])[0]
        _c17 = cat and cat.use_on(loc)
        if _c17:
            _w18 = yield from drive_until(gone, [], log, 8000)
            _c17 = _w18
        if _c17:
            return True
        said = ' '.join([t for t in [m.text for m in game_messages.since(mark)] if not t.startswith('get ')][-2:])
        # Why: the drop sets a bit that's never cleared, so a later knock says she's busy with the cat. That's the distraction holding, and the cat respawns, so reading it as failure catches a second cat and knocks all day.
        if ('talking to her cat' in said):
            return True
        tried.append(f"({stand.x},{stand.z}) {said or 'silence'}")
    log(f"the door would not take the cat — {' | '.join(tried)}")
    return False


# Why: the second box at any stage past `^upass_spoken_nilhoof` is the chest saying the doll isn't coming, which is an answer.
DOLL_GONE = "doll's gone"


def loot_witch_chest(log):
    """Open the house and take the doll out of the chest."""
    if held_id(UP_ITEM.DOLL.id) > 0:
        return True
    # Why: the chest is 2 locs and the first Open turns it into the other for 20 ticks, so a retry inside that window asks for the form standing there, see `chest.ts`.
    form = chest_form(lambda id, op: loc_by_id(id, op, 10) is not None)

    # Why: `~mesbox` ends in `.if_openchat`, so the chest's box is a chat modal and `Modals.isOpen()` reads `main` alone and never sees it. Both modals count.
    def prompted():
        return held_id(UP_ITEM.DOLL.id) > 0 or chat_dialog.is_open() or chat_dialog.can_continue() or modals.is_open()

    # Why: the chest is 2 tiles from the door on the other side of Kardia's wall, so a distance walk reports arrival from the street and the server refuses the click. `Reach.locOp` opens what stands in the way.
    status = yield from reach.loc_op('Chest', form.op, UP_TILE.WITCH_CHEST, prompted, id=form.id, within=10, expect_ms=20000, log=log)
    if status == 'unreachable':
        log("could not get inside Kardia's house")
        return False
    # Why: `@search_cavewitch_chest` is `~mesbox`, `p_pausebutton`, 3 ticks, `~mesbox`, `inv_add`, so the doll lands only once both boxes are clicked through, with nothing open in between. Only continue advances a `p_pausebutton`; `Player.closeModal` throws the suspended script away.
    # Why: at any stage past `^upass_spoken_nilhoof` the second box says the doll is gone and `~chatplayer` frames follow, so the chain is driven to its end and reported.
    chest = Record({'empty': False})

    def done():
        if any([DOLL_GONE in text.lower() for text in chat_dialog.texts()]):
            chest.empty = True
        return held_id(UP_ITEM.DOLL.id) > 0 or (chest.empty and not chat_dialog.is_open() and not chat_dialog.can_continue())

    yield from drive_through_boxes(done, [], log, 25000)
    if held_id(UP_ITEM.DOLL.id) > 0:
        return True
    log(("Kardia's chest is empty — the doll has already been taken" if chest.empty else 'the chest gave up no doll'))
    return False


"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidspirit/camp.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.druidspirit.areas import FILLIMAN, NS_ID, NS_LOC, NS_NAME, NS_TILE, in_swamp
from rs2004.quests.defs.druidspirit.journal import NS_FLAG
from rs2004.quests.exec.primitives import drive_dialog, open_dialogue, pick_preferred
from rs2004.quests.exec.prompts import drive_until, held_id, prompt_loc, settle_scene
from rs2004.traversal import traversal

__all__ = ['talk_filliman', 'mirror_leg', 'journal_leg', 'ask_to_help', 'pickable', 'stand_beside', 'bloom_with_scroll', 'feed_stones', 'solve_puzzle']


def find_spirit():
    return npcs.query().name(FILLIMAN.npc).within(8).nearest()


def reach_camp(log):
    _result1 = yield from traversal.walk_resilient(NS_TILE.CAMP, radius=3, attempts=4, timeout_ms=300000, log=log)
    return _result1


LEAVE = ['Ok, thanks.', 'Ok thanks.']


# Why: every topic in Filliman's tree ends by re-offering the same list, so a prefer list picks it again every pass; take the topic once and then the goodbye.
def drive_once(topic, log):
    """Drive an open dialogue, taking `topic` once and then leaving."""
    taken = False
    for i in range(40):
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            leave = pick_preferred(options, LEAVE)
            _v2 = ((None if taken else pick_preferred(options, [topic])))
            pick = (_v2 if _v2 is not None else leave)
            if not pick:
                log(f"no '{topic}' and no goodbye in [{' | '.join(options)}]")
                return False
            if pick != leave:
                taken = True
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            continue
        if not chat_dialog.is_open():
            return True
        yield from execution.delay_ticks(1)
    return not chat_dialog.is_open()


# Why: `Enter` on the grotto door npc_adds the spirit and he despawns after 100 ticks, so an empty camp means knock.
# Why: Before the ritual stage, the same door op opens Filliman's dialogue.
def talk_filliman(topic, log):
    """Summon the spirit, take `topic` once if there is one, then leave."""
    _w3 = yield from reach_camp(log)
    if not (_w3):
        return False
    yield from settle_scene()

    def drive():
        if topic is None:
            _result = yield from drive_dialog(LEAVE, log)
            return _result
        _result = yield from drive_once(topic, log)
        return _result

    if find_spirit():
        _w4 = yield from open_dialogue(FILLIMAN.npc, log)
        if not (_w4):
            return False
        _result5 = yield from drive()
        return _result5
    door = locs.query().name(NS_LOC.GROTTO_DOOR).action('Enter').within(8).nearest()
    if not door:
        log('no grotto door at the camp to summon the spirit with')
        return False
    if not (door.interact('Enter')):
        return False
    yield from execution.delay_until(lambda: find_spirit() is not None or chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    _result6 = yield from drive()
    return _result6


def ensure_spirit(log):
    """The spirit, summoned if he has despawned."""
    if find_spirit():
        return True
    _w7 = yield from talk_filliman(None, log)
    if not (_w7):
        return False
    yield from settle_scene()
    return find_spirit() is not None


# Why: taking the washing bowl uncovers the mirror under it, which is a second ground spawn.
def mirror_leg(log):
    """Take the bowl, take the mirror it uncovers, then show the mirror to the spirit."""
    if held_id(NS_ID.MIRROR) == 0:
        _w8 = yield from traversal.walk_resilient(NS_TILE.BOWL, radius=1, attempts=3, timeout_ms=180000, log=log)
        if not (_w8):
            return False
        yield from settle_scene()
        mirror = ground_items.query().name(NS_NAME.MIRROR).within(4).nearest()
        if mirror:
            mirror.interact('Take')
            _result9 = yield from execution.delay_until(lambda: held_id(NS_ID.MIRROR) > 0, 6000)
            return _result9
        bowl = ground_items.query().name(NS_NAME.BOWL).within(4).nearest()
        if not bowl:
            log(f'no {NS_NAME.BOWL} at ({NS_TILE.BOWL.x},{NS_TILE.BOWL.z}) — the mirror is already taken')
            return False
        if not (bowl.interact('Take')):
            return False
        _result10 = yield from execution.delay_until(lambda: ground_items.query().name(NS_NAME.MIRROR).within(4).nearest() is not None, 6000)
        return _result10
    _w11 = yield from ensure_spirit(log)
    if not (_w11):
        return False
    target = find_spirit()
    mirror = ([i for i in inventory.items() if i.id == NS_ID.MIRROR] or [None])[0]
    if not target or not mirror:
        return False
    # Why: the spirit hands the mirror back, so the dialogue completing is the only oracle this leg has.
    if not (mirror.use_on(target)):
        return False
    _result12 = yield from drive_dialog(['Ok, thanks.', 'Ok thanks.'], log)
    return _result12


def journal_leg(log):
    """Search the grotto tree for Tarlock's journal, then hand it over."""
    if held_id(NS_ID.JOURNAL) == 0:
        _result13 = yield from prompt_loc(Record({
            'name': NS_LOC.GROTTO_TREE,
            'op': 'Search',
            'near': NS_TILE.GROTTO_TREE,
            'expect': lambda: held_id(NS_ID.JOURNAL) > 0,
        }), log)
        return _result13
    _w14 = yield from ensure_spirit(log)
    if not (_w14):
        return False
    target = find_spirit()
    journal = ([i for i in inventory.items() if i.id == NS_ID.JOURNAL] or [None])[0]
    if not target or not journal:
        return False
    if not (journal.use_on(target)):
        return False
    _result15 = yield from drive_until(lambda: held_id(NS_ID.JOURNAL) == 0, ['Ok thanks.', 'Ok, thanks.'], log)
    return _result15


def ask_to_help(log):
    """The option that hands over the bloom scroll."""
    _w16 = yield from talk_filliman('How can I help?', log)
    if not (_w16):
        return False
    _result17 = yield from execution.delay_until(lambda: held_id(NS_ID.SPELL) > 0, 6000)
    return _result17


BLOOMABLE = [NS_LOC.LOG, NS_LOC.BRANCH, NS_LOC.BUSH]
PICKABLE = [[NS_LOC.FUNGI_LOG, 'Pick'], [NS_LOC.BUDDING_BRANCH, 'Take-cutting'], [NS_LOC.PEAR_BUSH, 'Pick']]


def pickable(within=10):
    """A bloomed loc within reach, or null."""
    for name, op in PICKABLE:
        if locs.query().name(name).action(op).within(within).nearest():
            return Record({'name': name, 'op': op})
    return None


# Why: the bloom affects the 8 tiles around the caster, and every bloomable is blockwalk=no, so standing on one misses it.
# Why: every bloomable is inside Mort Myre and the blessing before this leg is in the mausoleum, from where a scene query sees no swamp.
def stand_beside(log, names=None):
    """Stand next to something bloomable, never on it."""
    if names is None:
        names = BLOOMABLE
    if not in_swamp(game.tile()):
        _w18 = yield from reach_camp(log)
        if not (_w18):
            return False
        yield from settle_scene()

    def beside():
        here = game.tile()
        if not here:
            return False
        return any([locs.query().name(name).where(lambda l: l.tile().distance_to(here) == 1).nearest() is not None for name in names])

    if beside():
        return True
    target = ([l for l in [locs.query().name(name).within(40).nearest() for name in names] if l is not None and l is not None] or [None])[0]
    if not target:
        log('nothing bloomable within 40 tiles')
        return False
    at = target.tile()
    for dx, dz in [[1, 0], [-1, 0], [0, 1], [0, -1]]:
        stand = at.translate(dx, dz)
        _w19 = yield from traversal.walk_resilient(stand, radius=0, attempts=2, timeout_ms=120000, log=log)
        if _w19:
            yield from settle_scene()
            if beside():
                return True
    return beside()


def pick_harvest(log):
    """Take one item off whatever bloomed."""
    target = pickable()
    if not target:
        log('nothing bloomed within reach')
        return False
    before = inventory.used()
    loc = locs.query().name(target.name).action(target.op).within(10).nearest()
    if not loc or not (loc.interact(target.op)):
        return False
    _result20 = yield from execution.delay_until(lambda: inventory.used() > before, 8000)
    return _result20


# Why: a bloomed loc reverts 25 ticks after it grows, so casting and picking can't be 2 decide ticks; a resume with neither does both in one step.
def bloom_with_scroll(log):
    """Cast the paper scroll beside a rotting log and take the fungus it grows."""
    for cycle in range(8):
        if not (held_id(NS_ID.FUNGI) == 0):
            break
        if pickable():
            yield from pick_harvest(log)
            continue
        _w21 = yield from stand_beside(log, [NS_LOC.LOG])
        if not (_w21):
            return False
        scroll = ([i for i in inventory.items() if i.id == NS_ID.SPELL] or [None])[0]
        if not scroll:
            log('no Druidic spell held — Filliman re-issues one on request')
            return False
        if not (scroll.interact('Cast')):
            return False
        yield from execution.delay_until(lambda: pickable() is not None, 8000)
    return held_id(NS_ID.FUNGI) > 0


# Why: all 3 ritual stones render as "Stone" on adjacent tiles, so each is addressed by its own tile.
def use_on_stone(item_id, at, expect, log):
    """Use a carried item on one named stone."""
    if expect():
        return True
    _w22 = yield from traversal.walk_resilient(at, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w22):
        return False
    yield from settle_scene()
    stone = locs.query().name(NS_LOC.STONE).where(lambda l: l.tile().distance_to(at) == 0).nearest()
    item = ([i for i in inventory.items() if i.id == item_id] or [None])[0]
    if not stone or not item:
        log(f'no stone at ({at.x},{at.z}) or no item {item_id} to place on it')
        return False
    if not (item.use_on(stone)):
        return False
    _result23 = yield from drive_until(expect, ['Ok, thanks.', 'Ok thanks.'], log)
    return _result23


# Why: each stone consumes what it's given, so never re-feed one; the journal flags say which are done.
def feed_stones(flags, log):
    """Feed the fungus to the nature stone and the spent scroll to the spirit stone."""
    if not (NS_FLAG.NATURE in flags):
        if held_id(NS_ID.FUNGI) == 0:
            log('no Mort myre fungi held for the nature stone')
            return False
        _result24 = yield from use_on_stone(NS_ID.FUNGI, NS_TILE.NATURE_STONE, lambda: held_id(NS_ID.FUNGI) == 0, log)
        return _result24
    scroll = (NS_ID.SPELL_USED if held_id(NS_ID.SPELL_USED) > 0 else NS_ID.SPELL)
    if held_id(scroll) == 0:
        log('no bloom scroll held for the spirit stone')
        return False
    _result25 = yield from use_on_stone(scroll, NS_TILE.SPIRIT_STONE, lambda: held_id(scroll) == 0, log)
    return _result25


# Why: the ritual is judged on the player's own tile, `coord = 0_53_52_48_7`, so stand on the faith stone.
# Why: the summon is `Enter` on the grotto door, 2 tiles off the faith stone, so call the spirit first and take the stone second or the puzzle option opens from the wrong tile.
def solve_puzzle(log):
    """Stand on the faith stone and tell the spirit the puzzle is solved."""
    _w26 = yield from ensure_spirit(log)
    if not (_w26):
        return False
    _w27 = yield from traversal.walk_resilient(NS_TILE.FAITH_STONE, radius=0, attempts=4, timeout_ms=180000, log=log)
    if not (_w27):
        log('could not reach the faith stone')
        return False
    here = game.tile()
    if not here or here.x != NS_TILE.FAITH_STONE.x or here.z != NS_TILE.FAITH_STONE.z:
        log(f'standing at ({(here.x if here is not None else None)},{(here.z if here is not None else None)}) rather than on the faith stone — the ritual is judged on the tile')
        return False
    yield from settle_scene()
    if not find_spirit():
        log('the spirit despawned between the summon and the stone')
        return False
    _w28 = yield from open_dialogue(FILLIMAN.npc, log)
    if not (_w28):
        return False
    # Why: the option is judged on the tile you stand on when chosen, so a talk that walked us off the stone is abandoned.
    at = game.tile()
    if not at or at.x != NS_TILE.FAITH_STONE.x or at.z != NS_TILE.FAITH_STONE.z:
        log(f'the talk moved the character to ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) — off the faith stone')
        return False
    _result29 = yield from drive_once("I think I've solved the puzzle!", log)
    return _result29

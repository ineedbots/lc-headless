"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/viyeldi.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.legends.areas import HEROES, LQ_ID, LQ_LOC, LQ_LOC_ID, LQ_NPC, LQ_TILE, legends_area
from rs2004.quests.defs.legends.fight import fight
from rs2004.quests.defs.legends.pockets import legends_pocket
from rs2004.quests.defs.legends.scene import clear_boxes, drive_boxes, drive_until, held_id, loc_near, modal_text, offer_to, prompt_loc, settle_scene, use_on_loc
from rs2004.quests.defs.legends.trials import climb_out_of_trials, leave_octagram, leave_shaman_cave, pocket
from rs2004.quests.engine.trace import format_tile
from rs2004.traversal import traversal

__all__ = ['descend_ledges', 'climb_ledges', 'forge_heart_crystal', 'charge_heart_crystal', 'fill_recess', 'cross_barrier', 'recross_barrier', 'take_black_dagger', 'trade_dagger_for_spell', 'banish_source_demon', 'collect_sacred_water', 'leave_caves']

# Why: 6 one-way climbs separate the rope landing from the cave floor, each rolling `stat_random(agility, 110, 250)` downward and nothing upward.
# Why: the pockets between them are 4 to 19 tiles, so a stand is exact.
LEDGES = [
    Record({
    'id': LQ_LOC_ID.ROCKY_LEDGE_0,
    'name': LQ_LOC.ROCKY_LEDGE,
    'down': Record({'stand': Tile(2378, 4717, 0), 'to': 'descent_one'}),
    'up': Record({'stand': Tile(2376, 4717, 0), 'to': 'viyeldi_ledge'}),
}),
    Record({
    'id': LQ_LOC_ID.ROCKY_LEDGE_1,
    'name': LQ_LOC.ROCKY_LEDGE,
    'down': Record({'stand': Tile(2377, 4727, 0), 'to': 'descent_two'}),
    'up': Record({'stand': Tile(2378, 4728, 0), 'to': 'descent_one'}),
}),
    Record({
    'id': LQ_LOC_ID.ROCKY_LEDGE_2,
    'name': LQ_LOC.ROCKY_LEDGE,
    'down': Record({'stand': Tile(2382, 4730, 0), 'to': 'descent_three'}),
    'up': Record({'stand': Tile(2382, 4728, 0), 'to': 'descent_two'}),
}),
    Record({
    'id': LQ_LOC_ID.CLIMB_ROCK_1,
    'name': LQ_LOC.ROCKS,
    'down': Record({'stand': Tile(2386, 4727, 0), 'to': 'descent_four'}),
    'up': Record({'stand': Tile(2388, 4728, 0), 'to': 'descent_three'}),
}),
    Record({
    'id': LQ_LOC_ID.CLIMB_ROCK_2,
    'name': LQ_LOC.ROCKS,
    'down': Record({'stand': Tile(2390, 4725, 0), 'to': 'descent_five'}),
    'up': Record({'stand': Tile(2390, 4723, 0), 'to': 'descent_four'}),
}),
    Record({
    'id': LQ_LOC_ID.CLIMB_ROCK_3,
    'name': LQ_LOC.ROCKS,
    'down': Record({'stand': Tile(2390, 4719, 0), 'to': 'viyeldi_main'}),
    'up': Record({'stand': Tile(2390, 4717, 0), 'to': 'descent_five'}),
}),
]
CLIMB_ATTEMPTS = 8


def climb(ledge, dir, log):
    leg = ledge.down if dir == 'down' else ledge.up
    if pocket() == leg.to:
        return True
    # Why: a climb that overshoots lands on the cave floor, and from there the stand above is behind the rock already climbed.
    at = pocket()
    if dir == 'down' and (at == 'viyeldi_main' or at == 'viyeldi_source'):
        return True
    if dir == 'up' and at == 'viyeldi_ledge':
        return True
    _w1 = yield from traversal.walk_resilient(leg.stand, radius=1, attempts=4, timeout_ms=60000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    for i in range(CLIMB_ATTEMPTS):
        if pocket() == leg.to:
            yield from settle_scene()
            return True
        ok = yield from prompt_loc(Record({
            'name': ledge.name,
            'op': 'Climb-over',
            'near': leg.stand,
            'within': 6,
            'id': ledge.id,
            'prefer': ['Yes, I can think of nothing more exciting!', 'Yes, I want to climb over the rocks.'],
            'expect': lambda: pocket() == leg.to,
            'expect_ms': 25000,
        }), log)
        if ok:
            yield from settle_scene()
            return True
        yield from traversal.walk_resilient(leg.stand, radius=0, attempts=2, timeout_ms=30000, log=log)
    log(f'eight tries and ledge {ledge.id} would not let us {dir}')
    return False


# Why: every climb rolls `stat_random(agility, 110, 250)` and a miss drops you down the rock, so a descent lands anywhere from the next pocket to the cave floor.
DESCENT_ORDER = ['viyeldi_ledge', 'descent_one', 'descent_two', 'descent_three', 'descent_four', 'descent_five', 'viyeldi_main']


def descend_ledges(log):
    """Work down the 6 ledges from the rope landing to the cave floor."""
    if legends_area(game.tile()) != 'viyeldi_caves':
        log('the ledges are below the winch and we are not')
        return False
    for ledge in LEDGES:
        at = pocket()
        if at == 'viyeldi_main' or at == 'viyeldi_source':
            return True
        # Why: a fall past a ledge leaves its stand one-way behind us, so walking the list from the top sends you at a tile this pocket can't reach: `no path to (2386,4727,0): unreachable` for as long as the leg is given.
        if at is not None and (DESCENT_ORDER.index(at) if at in DESCENT_ORDER else -1) >= (DESCENT_ORDER.index(ledge.down.to) if ledge.down.to in DESCENT_ORDER else -1):
            continue
        _w2 = yield from climb(ledge, 'down', log)
        if not (_w2):
            # Why: `pockets.ts` covers the ledges and the floor but not every tile a fall can bounce off, and from an uncovered tile the stand above may be one-way behind us, which reads as a climb that won't take.
            # Why: the loop is finite either way, so trying the next rung down costs one climb and recovers a run that would sit at a stand it can't reach.
            if at is None:
                log(f'no pocket covers {format_tile(game.tile())} — trying the next ledge down')
                continue
            return False
    return pocket() == 'viyeldi_main'


def climb_ledges(log):
    """Work back up the 6 ledges to the rope landing."""
    # Why: the ledges only exist below the winch, so a leg that has already climbed the rope is done.
    if legends_area(game.tile()) != 'viyeldi_caves':
        return True
    # Why: the source sits past the barrier and the ledges are north of it, so the way up starts with a step back through the field.
    _w3 = yield from recross_barrier(log)
    if not (_w3):
        return False
    for ledge in list(reversed(LEDGES)):
        if pocket() == 'viyeldi_ledge':
            return True
        _w4 = yield from climb(ledge, 'up', log)
        if not (_w4):
            return False
    return pocket() == 'viyeldi_ledge'


HERO_FIGHT_MS = 300000
# Why: each guardian yields its own third of the dragon heart and nothing once that third is accounted for, and which thirds are in the furnace is `%legends_bits`, invisible.
# Why: the loop visits all 3 in turn and lets a guardian that owes nothing drop nothing.
# Why: the 3 stand 60 tiles apart in a cave the scene only half covers, so a query from the rope landing finds none of them.
HERO_SWEEP = [Tile(2410, 4700, 0), Tile(2385, 4710, 0), Tile(2400, 4725, 0)]


# Why: `nearest` picks by straight line and the descent pockets are sealed one-way, so a guardian 3 tiles up a ledge already climbed past beats the one on the cave floor, and the walk answers `no path to (2386,4727,0): unreachable`.
# Why: the pocket you're standing in is the test, since every guardian worth fighting shares it.
def guardian_here(name):
    """The named guardian, if one is standing somewhere this pocket can walk to."""
    at = pocket()
    return npcs.query().name(name).where(lambda npc: at is None or legends_pocket(npc.tile()) == at).within(48).nearest()


def find_guardian(name, log):
    """Walk the cave until the named guardian is in the scene."""
    for anchor in HERO_SWEEP:
        seen = guardian_here(name)
        if seen:
            return seen
        _w5 = yield from traversal.walk_resilient(anchor, radius=4, attempts=2, timeout_ms=90000, log=log)
        if _w5:
            yield from settle_scene()
    return guardian_here(name)


def fight_guardian(name, section, log):
    if held_id(section) > 0:
        return True
    guardian = yield from find_guardian(name, log)
    if not guardian:
        log(f'{name} is nowhere in the Viyeldi caves')
        return False
    _w6 = yield from traversal.walk_resilient(guardian.tile(), radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w6):
        return False
    _result7 = yield from fight(Record({
        'npc': name,
        'done': lambda: held_id(section) > 0 or npcs.query().name(name).within(14).nearest() is None,
        'ms': HERO_FIGHT_MS,
    }), log)
    return _result7


def smelt_section(section, log):
    """Fuse one crystal section into the lava furnace."""
    if held_id(section) == 0:
        return True
    _result8 = yield from use_on_loc(section, Record({'name': LQ_LOC.FURNACE, 'near': LQ_TILE.LAVA_FURNACE, 'within': 8, 'id': LQ_LOC_ID.FURNACE}), [], lambda: held_id(section) == 0, log)
    return _result8


# Why: the third section fuses the heart on the spot, so a heart crystal in the pack ends the leg.
def forge_heart_crystal(log):
    """Take all 3 guardians apart and fuse the dragon heart out of them."""
    if held_id(LQ_ID.HEART_CRYSTAL) > 0 or held_id(LQ_ID.HEART_CRYSTAL_GLOW) > 0:
        return True
    _w9 = yield from descend_ledges(log)
    if not (_w9):
        return False
    for hero in HEROES:
        if held_id(LQ_ID.HEART_CRYSTAL) > 0:
            return True
        if held_id(hero.section) == 0:
            yield from fight_guardian(hero.npc, hero.section, log)
        _c10 = held_id(hero.section) > 0
        if _c10:
            _w11 = yield from smelt_section(hero.section, log)
            _c10 = not (_w11)
        if _c10:
            return False
    return held_id(LQ_ID.HEART_CRYSTAL) > 0


def charge_heart_crystal(log):
    """Charge the heart on the dragon's eye, which is what makes it glow."""
    if held_id(LQ_ID.HEART_CRYSTAL_GLOW) > 0:
        return True
    _w12 = yield from descend_ledges(log)
    if not (_w12):
        return False
    _result13 = yield from use_on_loc(LQ_ID.HEART_CRYSTAL, Record({'name': LQ_LOC.MOSSY_ROCK, 'near': LQ_TILE.DRAGONS_EYE, 'within': 8, 'id': LQ_LOC_ID.DRAGONS_EYE_ROCK}), [], lambda: held_id(LQ_ID.HEART_CRYSTAL_GLOW) > 0, log)
    return _result13


def fill_recess(log):
    """Slot the glowing heart into the recess, which drops the barrier."""
    if loc_near(LQ_LOC.RECESS_FULL, 'Look', 8):
        return True
    _w14 = yield from descend_ledges(log)
    if not (_w14):
        return False
    _result15 = yield from use_on_loc(LQ_ID.HEART_CRYSTAL_GLOW, Record({'name': LQ_LOC.RECESS, 'near': LQ_TILE.HEART_RECESS, 'within': 8, 'id': LQ_LOC_ID.RECESS_EMPTY}), [], lambda: held_id(LQ_ID.HEART_CRYSTAL_GLOW) == 0, log)
    return _result15


def cross_barrier(log):
    """Walk through the shimmering field into the half of the cave that holds the source."""
    if pocket() == 'viyeldi_source':
        return True
    # Why: the rope drops us on the top ledge and the barrier is 6 climbs below it, so a leg that starts at the landing has to fall the rest of the way first.
    _w16 = yield from descend_ledges(log)
    if not (_w16):
        return False
    ok = yield from prompt_loc(Record({
        'name': LQ_LOC.BARRIER,
        'op': 'Walk-through',
        'near': LQ_TILE.BARRIER_NORTH,
        'within': 6,
        'expect': lambda: pocket() == 'viyeldi_source',
        'expect_ms': 20000,
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def recross_barrier(log):
    """Walk back north through the shimmering field."""
    if pocket() != 'viyeldi_source':
        return True
    ok = yield from prompt_loc(Record({
        'name': LQ_LOC.BARRIER,
        'op': 'Walk-through',
        'near': LQ_TILE.BARRIER_SOUTH,
        'within': 6,
        'expect': lambda: pocket() == 'viyeldi_main',
        'expect_ms': 20000,
    }), log)
    if ok:
        yield from settle_scene()
    return ok


ECHNED_PREFER = [
    "I'll do what I must to get the water.",
    "Ok, I'll do it.",
    'Er... me?',
    'Yes, I need it for my quest.',
    'What can I do about that?',
    "Who's asking?",
]


# Why: the boulder is an NPC, it only shifts when pushed from its east side, and before the demon is dealt with pushing it summons Echned Zekin.
def push_source_boulder(log):
    """Push the source boulder; before stage 22 this is what conjures the spirit."""
    _w17 = yield from cross_barrier(log)
    if not (_w17):
        return False
    _w18 = yield from traversal.walk_resilient(LQ_TILE.SOURCE_STAND, radius=0, attempts=4, timeout_ms=120000, log=log)
    if not (_w18):
        return False
    yield from settle_scene()
    boulder = npcs.query().name(LQ_NPC.BOULDER).within(8).nearest()
    if not boulder:
        log('no boulder within reach of the source stand')
        return False
    return boulder.interact('Push')


def take_black_dagger(log):
    """Take the black dagger from Echned Zekin."""
    if held_id(LQ_ID.DEATH_DAGGER) > 0 or held_id(LQ_ID.HOLY_FORCE) > 0:
        return True

    def spirit():
        return npcs.query().name(LQ_NPC.ECHNED).within(10).exists()

    _c19 = not spirit()
    if _c19:
        _w20 = yield from push_source_boulder(log)
        _c19 = not (_w20)
    if _c19:
        return False
    yield from execution.delay_until(lambda: spirit(), 12000)
    # Why: Echned hands the dagger through `~objbox`, and the `inv_add` behind it only runs once the box is clicked; a chat-only driver holds the script shut.
    _result21 = yield from drive_boxes(lambda: held_id(LQ_ID.DEATH_DAGGER) > 0, 120000, ECHNED_PREFER, log)
    return _result21


# Why: Ungadulu is the only source of the Holy Force spell and he wants the dagger for it, so the climb back up the trials is part of the quest.
def trade_dagger_for_spell(log):
    """Hand the black dagger to Ungadulu for the Holy Force spell."""
    if held_id(LQ_ID.HOLY_FORCE) > 0:
        return True
    # Why: the climb out lands at the cave mouth 20 tiles from the octagram, so the shaman is out of range until this walk has run.
    _c22 = not npcs.query().name(LQ_NPC.UNGADULU).within(12).exists()
    if _c22:
        _w23 = yield from traversal.walk_resilient(LQ_TILE.FIRE_WALL_WEST, radius=1, attempts=3, timeout_ms=120000, log=log)
        _c22 = not (_w23)
    if _c22:
        return False
    yield from settle_scene()
    shaman = npcs.query().name(LQ_NPC.UNGADULU).within(12).nearest()
    if not shaman:
        log('no Ungadulu in range for the black dagger')
        return False
    _w24 = yield from offer_to(LQ_ID.DEATH_DAGGER, shaman, log)
    if not (_w24):
        return False
    _result25 = yield from drive_until(lambda: held_id(LQ_ID.HOLY_FORCE) > 0, [], log, 60000)
    return _result25


# Why: every one of these ends the conversation without `npc_del`; the goodbye dismisses him.
ECHNED_STAY = ["I don't have the dagger.", "I haven't slayed Viyeldi yet.", 'I have something else in mind!']
SOURCE_FIGHT_MS = 420000


def banish_source_demon(log):
    """Read the Holy Force at the spirit, then kill what it turns into."""

    def demon():
        return npcs.query().name(LQ_NPC.NEZIKCHENED).within(14).exists()

    def spirit():
        return npcs.query().name(LQ_NPC.ECHNED).within(10).exists()

    # Why: the cast is one op with no dialogue and no readable message, so the demon appearing is the only oracle, and a miss is worth another go.
    for i in range(4):
        if demon():
            break
        _w26 = yield from cross_barrier(log)
        if not (_w26):
            return False
        _c27 = not spirit()
        if _c27:
            _w28 = yield from push_source_boulder(log)
            _c27 = not (_w28)
        if _c27:
            return False
        yield from execution.delay_until(spirit, 12000)
        # Why: the push opens a conversation and its only polite exit is "I have to be going...", which `npc_del`s the spirit, so the rude answers are the ones that leave him standing there to be cast at.
        # Why: he spawns within 3 tiles of whoever pushed the boulder, so no walk is wanted either; walking off would close the chat and take him with it.
        yield from drive_until(lambda: modal_text() == '', ECHNED_STAY, log, 30000)
        scroll = ([item for item in inventory.items() if item.id == LQ_ID.HOLY_FORCE] or [None])[0]
        if not scroll:
            log('no Holy Force spell in the pack')
            return False
        # Why: the scroll's own op is "Cast Spell", Read is the Book of Binding's, and an op that isn't there fails in a tick without a word.
        if scroll.interact('Cast Spell'):
            yield from drive_until(demon, [], log, 25000)
    if not demon():
        log('four casts of the Holy Force and the spirit never showed its face')
        return False
    _result29 = yield from fight(Record({'npc': LQ_NPC.NEZIKCHENED, 'done': lambda: not demon(), 'ms': SOURCE_FIGHT_MS}), log)
    return _result29


# Why: pushing the boulder adds the pool as a 30-tick loc, so the push and the fill are one step or the water is gone before the next decide.
def collect_sacred_water(log):
    """Shift the boulder off the spring and fill the blessed bowl from it."""
    if held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
        return True
    if held_id(LQ_ID.GOLD_BOWL_BLESSED) == 0:
        log('no empty blessed bowl to fill at the source')
        return False
    _w30 = yield from cross_barrier(log)
    if not (_w30):
        return False
    for i in range(4):
        if not loc_near(LQ_LOC.SOURCE_POOL, 'Look', 8):
            _w31 = yield from push_source_boulder(log)
            if not (_w31):
                return False
            yield from execution.delay_until(lambda: loc_near(LQ_LOC.SOURCE_POOL, 'Look', 8) is not None, 8000)
        filled = yield from use_on_loc(LQ_ID.GOLD_BOWL_BLESSED, Record({
            'name': LQ_LOC.SOURCE_POOL,
            'near': LQ_TILE.SOURCE_STAND,
            'within': 8,
            'id': LQ_LOC_ID.WATER_POOL_SOURCE,
        }), [], lambda: held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0, log)
        if filled:
            yield from clear_boxes()
            return True
    log('the spring would not fill the bowl')
    return False


# Why: every leg that starts on the mainland walks to a mainland tile, so a run resumed anywhere under Karamja has to climb all the way out before the walker has a path at all.
def leave_caves(log):
    """Climb, crawl and squeeze out of the cave complex onto open jungle."""
    # Why: a shaman-cave tile carries no pocket and isn't `viyeldiCaves`, so without the area check this reads as already outside while underground and the caller walks for the jungle mouth from a cave floor.
    area = legends_area(game.tile())
    if legends_pocket(game.tile()) is None and area != 'viyeldi_caves' and area != 'shaman_caves':
        return True
    _c32 = legends_area(game.tile()) == 'viyeldi_caves'
    if _c32:
        _w33 = yield from climb_ledges(log)
        _c32 = not (_w33)
    if _c32:
        return False
    _w34 = yield from leave_octagram(log)
    if not (_w34):
        return False
    _w35 = yield from climb_out_of_trials(log)
    if not (_w35):
        return False
    _result36 = yield from leave_shaman_cave(log)
    return _result36

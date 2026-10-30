"""Ported from rs2b0t's src/bot/api/ai/quests/defs/monksfriend.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.exec.primitives import is_underground, talk_strict, walk_with_hops
from rs2004.quests.exec.prompts import held_id, settle_scene, use_on_loc
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['MF_STAGE', 'BLANKET_OBJ', 'parse_monks_friend_journal', 'read_monks_friend_stage', 'gather_water', 'gather_logs', 'decide', 'monksfriend']

QUEST = "Monk's Friend"
MF_STAGE = Record({
    'NOT_STARTED': 0,
    'SPOKEN_TO_OMAD': 10,
    'RETRIEVED_BLANKET': 20,
    'LOOKING_CEDRIC': 30,
    'FINDING_WATER': 40,
    'MENDING_CART': 50,
    'FIXED_CART': 70,
    'COMPLETE': 80,
})
BLANKET_OBJ = 90
JUG_OBJ = 1935
JUG_WATER_OBJ = 1937
SINK_LOC = 873
BLANKET = "Child's blanket"
JUG = 'Jug'
JUG_WATER = 'Jug of water'
LOGS = 'Logs'
# Why: "axe" alone also matches battleaxe and pickaxe, and neither chops.
AXES = ['Rune axe', 'Adamant axe', 'Mithril axe', 'Black axe', 'Steel axe', 'Iron axe', 'Bronze axe']
ARDOUGNE_BANK = Tile(2655, 3283, 0)
# Why: the `blanket_ladder` timer `loc_add`s the ladder once you stand within 2 tiles, so the stand is a neighbour of the ladder's own tile.
RING_STAND = Tile(2562, 3222, 0)
CAVE_FOOT = Tile(2561, 9621, 0)
CAVE_LADDER = Tile(2561, 9622, 0)
BLANKET_SPAWN = Tile(2570, 9604, 0)
SINK = Tile(2610, 3195, 0)
TREE = Tile(2613, 3252, 0)
KHAZARD_SHOP = Record({'npc': 'Shop keeper', 'anchor': Tile(2641, 3171, 0)})
ARDOUGNE_SHOP = Record({'npc': 'Kortan', 'anchor': Tile(2615, 3292, 0)})
# Why: `ladder_cellar` stands 5 tiles away at (2566,3227) and also offers Climb-down; `hopLadder` keeps it out by wanting the loc within 3 tiles of the stand.
HOPS = [
    Record({'stand': RING_STAND, 'loc_name': 'Ladder', 'op': 'Climb-down', 'arrive': CAVE_FOOT}),
    Record({'stand': CAVE_LADDER, 'loc_name': 'Ladder', 'op': 'Climb-up', 'arrive': Tile(2561, 3222, 0)}),
]


def omad(prefer):
    return Record({'npc': 'Brother Omad', 'anchor': Tile(2604, 3209, 0), 'leash': 6, 'prefer': prefer})


CEDRIC = Record({'npc': 'Brother Cedric', 'anchor': Tile(2614, 3259, 0), 'leash': 8, 'prefer': ["Yes, I'd be happy to!"]})
START = omad(["Why can't you sleep, what's wrong?", 'Can I help at all?'])
HAND_IN_BLANKET = omad([])
ASK_FOR_CEDRIC = omad(["Who's Brother Cedric?", 'Where should I look?'])
# Why: every page from stage 20 on repeats the blanket line, so test the newest marker first.
JOURNAL_MARKERS = [
    ['quest complete!', MF_STAGE.COMPLETE],
    ['he is on the way', MF_STAGE.FIXED_CART],
    ['he needs some wood for his cart', MF_STAGE.MENDING_CART],
    ['i need to take him a jug of water', MF_STAGE.FINDING_WATER],
    ['i agreed to find brother cedric', MF_STAGE.LOOKING_CEDRIC],
    ['i found the secret cave and gave back the blanket', MF_STAGE.RETRIEVED_BLANKET],
    ['i need to find a secret cave', MF_STAGE.SPOKEN_TO_OMAD],
    ['i can start this quest by speaking to brother omad', MF_STAGE.NOT_STARTED],
]


def parse_monks_friend_journal(lines):
    text = normalize_journal(lines)
    for marker, stage in JOURNAL_MARKERS:
        if (marker in text):
            return stage
    return None


def read_monks_friend_stage():
    status = quests.status(QUEST)
    if status == 'complete':
        return MF_STAGE.COMPLETE
    if status == 'not_started':
        return MF_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    stage = parse_monks_friend_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage


def in_cave(tile):
    return tile is not None and is_underground(tile) and tile.x >= 2555 and tile.x <= 2580


def enter_cave(log):
    """The timer adds the ladder the tick after the player is within 2 tiles, so it is never in the scene on arrival."""
    if in_cave(game.tile()):
        return True
    _w2 = yield from traversal.walk_resilient(RING_STAND, radius=1, attempts=3, timeout_ms=180000, log=log)
    if not (_w2):
        return False

    def ladder():
        return locs.query().name('Ladder').action('Climb-down').where(lambda l: l.tile().distance_to(RING_STAND) <= 3).nearest()

    _w3 = yield from execution.delay_until(lambda: ladder() is not None, 15000)
    if not (_w3):
        log('monksfriend: no hidden ladder appeared inside the ring of stones')
        return False
    found = ladder()
    if not found or not (found.interact('Climb-down')):
        return False
    _w4 = yield from execution.delay_until(lambda: in_cave(game.tile()), 10000)
    if not (_w4):
        return False
    yield from settle_scene()
    return True


def leave_cave(log):
    if not in_cave(game.tile()):
        return True
    _w5 = yield from traversal.walk_resilient(CAVE_LADDER, radius=1, attempts=3, timeout_ms=180000, log=log)
    if not (_w5):
        return False
    ladder = locs.query().name('Ladder').action('Climb-up').within(4).nearest()
    if not ladder or not (ladder.interact('Climb-up')):
        log(f'monksfriend: no way out of the cave at ({CAVE_LADDER.x},{CAVE_LADDER.z})')
        return False
    _w6 = yield from execution.delay_until(lambda: not in_cave(game.tile()), 10000)
    if not (_w6):
        return False
    yield from settle_scene()
    return True


def fetch_blanket(log):
    if held_id(BLANKET_OBJ) > 0:
        _result7 = yield from leave_cave(log)
        return _result7
    _w8 = yield from enter_cave(log)
    if not (_w8):
        return False
    _w9 = yield from traversal.walk_resilient(BLANKET_SPAWN, radius=1, attempts=3, timeout_ms=180000, log=log)
    if not (_w9):
        return False
    blanket = ground_items.query().where(lambda g: g.id == BLANKET_OBJ).within(8).nearest()
    if not blanket:
        log(f'monksfriend: no {BLANKET} on the floor at ({BLANKET_SPAWN.x},{BLANKET_SPAWN.z})')
        return False
    if not (blanket.interact('Take')):
        return False
    _w10 = yield from execution.delay_until(lambda: held_id(BLANKET_OBJ) > 0, 8000)
    if not (_w10):
        return False
    _result11 = yield from leave_cave(log)
    return _result11


# Why: a regular tree gives 1 log then stumps, and at 600ms ticks a `pickLoc` step's 8s wait can lose the race.
def chop_logs(log):
    if inventory.contains(LOGS):
        return True
    _w12 = yield from walk_with_hops(TREE, 2, HOPS, log)
    if not (_w12):
        return False
    for attempt in range(3):
        tree = locs.query().name('Tree').action('Chop down').within(8).nearest()
        if not tree:
            log(f'monksfriend: no standing tree near ({TREE.x},{TREE.z})')
            return False
        if not (tree.interact('Chop down')):
            return False
        _w13 = yield from execution.delay_until(lambda: inventory.contains(LOGS), 30000)
        if _w13:
            return True
    log('monksfriend: three trees chopped without a log landing')
    return False


# Why: a `useOn` step clicks as soon as the walk returns, which from the sink lands inside the arrive window and is dropped; a retry from a standstill filled the jug in 295ms.
def fill_jug(log):
    result = yield from use_on_loc(JUG_OBJ, Record({'name': 'Sink', 'near': SINK, 'id': SINK_LOC, 'within': 4}), [], lambda: held_id(JUG_WATER_OBJ) > 0, log)
    return result


# Why: the party is ~23 ticks of `p_delay` and `%drunkmonkquest` only moves in the `drunkmonk_complete` queue, so returning at the end of the dialogue would re-enter `omad_party`.
def throw_party(log):
    _w14 = yield from leave_cave(log)
    if not (_w14):
        return False
    _w15 = yield from walk_with_hops(START.anchor, 1, HOPS, log)
    if not (_w15):
        return False
    _w16 = yield from talk_strict('Brother Omad', [], log)
    if not (_w16):
        return False
    log('monksfriend: dancing with the monks — waiting for the quest list to turn green')
    _result17 = yield from execution.delay_until(lambda: quests.status(QUEST) == 'complete', 60000)
    return _result17


def banked_axe(snap):
    return ([axe for axe in AXES if (snap.bank or {}).get(axe.lower(), 0) > 0] or [None])[0]


def held_axe(snap):
    return any([snap.inv.get(axe.lower(), 0) > 0 for axe in AXES])


def gather_water(snap):
    """Bank first, then Port Khazard's general store, then the guardhouse sink."""
    if snap.inv.get(JUG.lower(), 0) > 0:
        return Record({'kind': 'custom', 'name': 'fill the jug at the guardhouse sink', 'run': fill_jug})
    if snap.bank_known != True:
        return Record({'kind': 'scan_bank'})
    for name in [JUG_WATER, JUG]:
        if (snap.bank or {}).get(name.lower(), 0) > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': 1}]})
    return Record({'kind': 'buy', 'item': JUG, 'qty': 1, 'shop': KHAZARD_SHOP, 'est_gp': 100})


def gather_logs(snap):
    """Bank first, then Aemad's Adventuring Supplies, then a tree in Cedric's own forest."""
    if held_axe(snap):
        return Record({'kind': 'custom', 'name': 'chop logs for the cart', 'run': chop_logs})
    if snap.bank_known != True:
        return Record({'kind': 'scan_bank'})
    banked = banked_axe(snap)
    if banked:
        return Record({'kind': 'withdraw', 'items': [{'name': banked, 'qty': 1}]})
    return Record({'kind': 'buy', 'item': 'Iron axe', 'qty': 1, 'shop': ARDOUGNE_SHOP, 'est_gp': 200})


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': "Monk's Friend journal stage unavailable"})
    # Why: at stage 10 the journal reads "find the secret cave" with or without the blanket, so the carried obj is the only evidence the cave was robbed.
    if stage <= MF_STAGE.SPOKEN_TO_OMAD and (snap.inv_ids or {}).get(BLANKET_OBJ, 0) > 0:
        return Record({'kind': 'talk', 'stop': HAND_IN_BLANKET})
    if stage == MF_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': START})
    elif stage == MF_STAGE.SPOKEN_TO_OMAD:
        return Record({'kind': 'custom', 'name': "fetch the child's blanket", 'run': fetch_blanket})
    elif stage == MF_STAGE.RETRIEVED_BLANKET:
        return Record({'kind': 'talk', 'stop': ASK_FOR_CEDRIC})
    elif stage == MF_STAGE.LOOKING_CEDRIC:
        return Record({'kind': 'talk', 'stop': CEDRIC})
    elif stage == MF_STAGE.FINDING_WATER:
        return Record({'kind': 'talk', 'stop': CEDRIC}) if snap.inv.get(JUG_WATER.lower(), 0) > 0 else gather_water(snap)
    elif stage == MF_STAGE.MENDING_CART:
        return Record({'kind': 'talk', 'stop': CEDRIC}) if snap.inv.get(LOGS.lower(), 0) > 0 else gather_logs(snap)
    elif stage == MF_STAGE.FIXED_CART:
        return Record({'kind': 'custom', 'name': 'tell Omad that Cedric is on his way', 'run': throw_party})
    else:
        return Record({'kind': 'wait', 'reason': f"Monk's Friend stage {stage} is not implemented"})


monksfriend = QuestModule(
    record=quest_record('drunkmonk'),
    bank=ARDOUGNE_BANK,
    hops=HOPS,
    food=6,
    tools=[BLANKET.lower(), 'jug', 'logs', 'axe', 'coins'],
    read_stage=read_monks_friend_stage,
    decide=decide,
)

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/gertrudescat.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs, npcs
from rs2004.game import direct_navigator, game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, QuestProgress, banked_id, quest_step
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.defs.cooksassistant import gather_milk
from rs2004.quests.exec.primitives import goto_npc, talk_strict, talk_through
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.quests.exec.steps import execute_step
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['FLUFFS_STAGE', 'FLUFFS_OBJ', 'parse_gertrudes_cat_journal', 'read_gertrudes_cat_progress', 'decide', 'gertrudescat']

QUEST = "Gertrude's Cat"
FLUFFS_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'PAID_BOY': 2,
    'GAVE_MILK': 3,
    'GAVE_SARDINE': 4,
    'RESCUED': 5,
    'COMPLETE': 6,
})
FLUFFS_OBJ = Record({'doogle_leaves': 1573, 'raw_sardine': 327, 'seasoned_sardine': 1552, 'bucket_of_milk': 1927, 'kitten': 1554})
CAT_NPC = 759
CRATE_NPC = 767
BOY_PAYMENT = 100
COIN_TOPUP = 1000
SARDINE_GP = 100
QUEST_BANK = Tile(3185, 3440, 0)
GERTRUDE = Record({'npc': 'Gertrude', 'anchor': Tile(3151, 3410, 0), 'leash': 8, 'prefer': ['Well, I suppose I could']})
MARKET = Tile(3221, 3434, 0)
# Why: option 2 buys the location; option 1 threatens the boy and option 3 walks away, and both end the dialogue with nothing learnt.
PAY_PREFER = ['What will make you tell me?', "I'll pay"]
DOOGLE_WOODS = Tile(3153, 3400, 0)
SARDINE_SHOP = Record({'npc': 'Gerrant', 'anchor': Tile(3016, 3223, 0)})
YARD_ENTRY = Tile(3305, 3496, 0)
LADDER_BASE = Tile(3310, 3509, 0)
LADDER_TOP = Tile(3310, 3509, 1)
CAT_STAND = Tile(3306, 3512, 1)
# Why: the server routes here from every crate, the ladder and the fence; aim anywhere else from beside a crate and the walk is silently refused.
YARD_HUB = Tile(3305, 3504, 0)
# Why: the 6th crate sits in the corner behind the shed and the route is long enough that the server's finder gives up 9 tiles short with no refusal.
# Why: it's searched first since the walk in only works from the open ground by the fence.
NW_CORNER_IN = [YARD_HUB, Tile(3304, 3511, 0), Tile(3300, 3512, 0), Tile(3298, 3513, 0)]
NW_CORNER_OUT = [Tile(3300, 3512, 0), Tile(3304, 3511, 0), YARD_HUB]
YARD_EXIT = [YARD_HUB, YARD_ENTRY]
CRATES = [
    Record({'tile': Tile(3298, 3514, 0), 'approach': Record({'in_': NW_CORNER_IN, 'out': NW_CORNER_OUT})}),
    Record({'tile': Tile(3307, 3507, 0)}),
    Record({'tile': Tile(3311, 3511, 0)}),
    Record({'tile': Tile(3303, 3506, 0)}),
    Record({'tile': Tile(3305, 3500, 0)}),
    Record({'tile': Tile(3310, 3499, 0)}),
]
FOUND_NOTHING = 'you find nothing'
CRATE_SEARCH_MS = 30000
# Why: `npc_find` measures the brothers against each other, and both wander 2 tiles from their own spawn.
# Why: the check runs 4 chat lines in, so the gap has to start inside the script's limit of 3; at 2 the pair drifted out of range 2 attempts in 3.
BROTHER_GAP = 1
PAY_ATTEMPTS = 6
SEASON_ATTEMPTS = 3
OFFER_ATTEMPTS = 3
CUTSCENE_TICKS = 8


# Why: the pages are cumulative, so test the newest sentence first.
def parse_gertrudes_cat_journal(lines):
    text = normalize_journal(lines)

    def at(stage):
        return (QuestProgress(stage))

    if ('quest complete!' in text):
        return at(FLUFFS_STAGE.COMPLETE)
    if ('i gave fluffs her kitten back' in text):
        return at(FLUFFS_STAGE.RESCUED)
    if ('i gave the cat milk and sardines' in text):
        return at(FLUFFS_STAGE.GAVE_SARDINE)
    if ('i found the lost cat but it' in text):
        return at(FLUFFS_STAGE.GAVE_MILK)
    if ('go to their play area' in text):
        return at(FLUFFS_STAGE.PAID_BOY)
    if ('i accepted the challenge of finding' in text):
        return at(FLUFFS_STAGE.STARTED)
    if ('i can start this quest by talking to' in text):
        return at(FLUFFS_STAGE.NOT_STARTED)
    return None


def read_gertrudes_cat_progress():
    status = quests.status(QUEST)
    if status == 'complete':
        return QuestProgress(FLUFFS_STAGE.COMPLETE)
    if status == 'not_started':
        return QuestProgress(FLUFFS_STAGE.NOT_STARTED)
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    progress = parse_gertrudes_cat_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress


def in_yard(t):
    return t.level == 0 and t.x >= 3288 and t.x <= 3327 and t.z >= 3494 and t.z <= 3527


# Why: the yard's inner walls make the walk south unplannable from where the crate legs end; the walker spent 5 repaths clicking the fence approach from 9 tiles away.
def leave_yard(log):
    """Walk back to the fence side, where a route out can be planned."""
    _w2 = yield from climb_down_to_yard(log)
    if not (_w2):
        return False
    _result3 = yield from walk_via(YARD_EXIT, log)
    return _result3


def enter_yard(log):
    """Walk in through the broken fence, the yard's only way in."""
    _w4 = yield from climb_down_to_yard(log)
    if not (_w4):
        return False
    here = game.tile()
    if here and in_yard(here):
        return True
    _w5 = yield from traversal.walk_resilient(YARD_ENTRY, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w5):
        return False
    yield from settle_scene()
    landed = game.tile()
    return landed is not None and in_yard(landed)


def on_platform():
    """Fluffs sits on the yard's raised walkway, which the baked graph has no edge onto."""
    here = game.tile()
    return here is not None and here.level == LADDER_TOP.level and LADDER_TOP.distance_to(here) <= 20


def climb_to_cat(log):
    if on_platform():
        return True
    # Why: from outside the yard this is the fence route; from beside a crate it is the one leg the server will walk.
    _w6 = yield from walk_via([YARD_HUB], log)
    if not (_w6):
        return False
    _w7 = yield from traversal.walk_resilient(LADDER_BASE, radius=1, attempts=3, timeout_ms=180000, log=log)
    if not (_w7):
        return False
    yield from settle_scene()
    ladder = locs.query().name('Ladder').action('Climb-up').within(4).nearest()
    if not ladder:
        log(f'gertrudescat: no ladder up to Fluffs at ({LADDER_BASE.x},{LADDER_BASE.z})')
        return False
    if not (ladder.interact('Climb-up')):
        return False
    up = yield from execution.delay_until(on_platform, 10000)
    if up:
        yield from settle_scene()
    return up


def climb_down_to_yard(log):
    if not on_platform():
        return True
    _w8 = yield from traversal.walk_resilient(LADDER_TOP, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w8):
        return False
    ladder = locs.query().name('Ladder').action('Climb-down').within(4).nearest()
    if not ladder:
        log(f'gertrudescat: no ladder down off the platform at ({LADDER_TOP.x},{LADDER_TOP.z})')
        return False
    if not (ladder.interact('Climb-down')):
        return False
    down = yield from execution.delay_until(lambda: not on_platform(), 10000)
    if down:
        yield from settle_scene()
    return down


# Why: Pick-up and Stroke both make Fluffs claw for 3 damage and give nothing, so every interaction here is a use-on.
def offer_to_cat(obj_id, what):
    def offer(log):
        item_id = obj_id
        def gone():
            return held_id(item_id) == 0
        if gone():
            return True
        _w10 = yield from climb_to_cat(log)
        if not (_w10):
            return False

        def find_cat():
            return npcs.query().where(lambda n: n.id == CAT_NPC).nearest()
        if not find_cat():
            yield from traversal.walk_resilient(CAT_STAND, radius=2, attempts=2, timeout_ms=30000, log=log)
            yield from settle_scene()
        # Why: the first use lands while the ladder still has you delayed and the engine drops it, which looks the same as a refusal.
        attempt = 0
        while attempt < OFFER_ATTEMPTS and not gone():
            cat = find_cat()
            held = ([item for item in inventory.items() if item.id == item_id] or [None])[0]
            if not cat or not held:
                log(f'gertrudescat: no Fluffs in reach, or no {what} to offer her')
                return False
            log(f'gertrudescat: offering Fluffs the {what}')
            if not (held.use_on(cat)):
                return False
            yield from drive_until(gone, [], log, 12000)
            attempt += 1
        if not gone():
            return False
        yield from settle_cutscene(log)
        return True
    return offer


# Why: the kitten leaves the pack 6 ticks before the hand-over cutscene ends, so a pack watch returns while Fluffs is still walking home.
# Why: holding the closing mesbox blocks all movement; the walker spent 100s clicking 3 tiles away.
def settle_cutscene(log):
    yield from execution.delay_ticks(CUTSCENE_TICKS)
    yield from drive_until(lambda: not chat_dialog.is_open() and not chat_dialog.can_continue(), [], log, 15000)
    yield from modals.close_if_open()


# Why: which crate holds the kitten is a server-side coord the client never sees, so search them all.
# Why: the yard is one scene and every crate blocks its own tile, so Search is sent from wherever the bot stands and the server walks the rest.
def search_crates_for_kitten(log):
    def found():
        return held_id(FLUFFS_OBJ.kitten) > 0

    if found():
        return True
    _w11 = yield from enter_yard(log)
    if not (_w11):
        return False
    for stop in CRATES:
        _v12 = (stop.approach.in_ if stop.approach is not None else None)
        _w13 = yield from walk_via((_v12 if _v12 is not None else []), log)
        if _w13:
            yield from search_crate(stop.tile, found, log)
        # Why: the corner is as hard to leave as to enter, and the next leg's walk assumes you're out.
        _v14 = (stop.approach.out if stop.approach is not None else None)
        yield from walk_via((_v14 if _v14 is not None else []), log)
        if found():
            return True
    log('gertrudescat: none of the six crates held the kitten')
    return False


# Why: inside the yard the planner and the server disagree, so the raw walk packet lets the server route a leg the planner gave up on.
def walk_via(waypoints, log):
    for wp in waypoints:
        _w15 = yield from traversal.walk_resilient(wp, radius=1, attempts=2, timeout_ms=45000, log=log)
        if _w15:
            continue
        log(f'gertrudescat: the planner gave up short of ({wp.x},{wp.z}) — walking there directly')
        _w16 = yield from direct_navigator.walk_to(wp, 1, 12000)
        if not (_w16):
            return False
    return True


def search_crate(spot, found, log):
    crate = npcs.query().where(lambda n: n.id == CRATE_NPC).within_of(spot, 0).nearest()
    if not crate:
        log(f'gertrudescat: no crate standing at ({spot.x},{spot.z})')
        return
    log(f'gertrudescat: searching the crate at ({spot.x},{spot.z})')
    mark = game_messages.mark()
    if not (crate.interact('Search')):
        return
    yield from drive_until(lambda: found() or game_messages.saw_since(mark, FOUND_NOTHING), [], log, CRATE_SEARCH_MS)


# Why: this runs the tick after Gerrant's shop closes, and a half-shut shop screen swallows the use with no refusal; the pack is untouched and the wait times out.
def season_sardine(log):
    def seasoned():
        return held_id(FLUFFS_OBJ.seasoned_sardine) > 0

    attempt = 0
    while attempt < SEASON_ATTEMPTS and not seasoned():
        yield from modals.close_if_open()
        yield from execution.delay_ticks(1)
        leaves = ([item for item in inventory.items() if item.id == FLUFFS_OBJ.doogle_leaves] or [None])[0]
        raw = ([item for item in inventory.items() if item.id == FLUFFS_OBJ.raw_sardine] or [None])[0]
        if not leaves or not raw:
            log('gertrudescat: no doogle leaves or no raw sardine to rub them over')
            return False
        if not (leaves.use_on(raw)):
            return False
        # Why: "You rub the doogle leaves over the sardine." is a mesbox, and the seasoned sardine only lands once it is dismissed.
        yield from drive_until(seasoned, [], log, 8000)
        attempt += 1
    return seasoned()


def report_to_gertrude(log):
    # Why: a resumed session can pick the quest up holding the hand-over's closing mesbox, and nothing walks until it is shut.
    yield from drive_until(lambda: not chat_dialog.is_open() and not chat_dialog.can_continue(), [], log, 5000)
    here = game.tile()
    if on_platform() or (here is not None and in_yard(here)):
        _w17 = yield from leave_yard(log)
        if not (_w17):
            return False
    _w18 = yield from goto_npc(GERTRUDE, [], log)
    if not (_w18):
        return False
    _result19 = yield from talk_through(GERTRUDE.npc, GERTRUDE.prefer, log)
    return _result19


def pay_brothers(log):
    def paired():
        shilop = npcs.query().name('Shilop').nearest()
        wilough = npcs.query().name('Wilough').nearest()
        if not shilop or not wilough:
            return None
        return (shilop if shilop.tile().distance_to(wilough.tile()) <= BROTHER_GAP else None)

    for attempt in range(PAY_ATTEMPTS):
        _w20 = yield from traversal.walk_resilient(MARKET, radius=3, attempts=3, timeout_ms=180000, log=log)
        if not (_w20):
            return False
        yield from settle_scene()
        _w21 = yield from execution.delay_until(lambda: paired() is not None, 60000)
        if not (_w21):
            log('gertrudescat: Shilop and Wilough never wandered within earshot of each other')
            continue
        before = inventory.count('Coins')
        _w22 = yield from talk_strict('Shilop', PAY_PREFER, log)
        if not (_w22):
            continue
        # Why: the brothers drift apart mid-dialogue and that branch ends with no options, so only the payment proves the location was bought.
        _w23 = yield from execution.delay_until(lambda: inventory.count('Coins') <= before - BOY_PAYMENT, 5000)
        if _w23:
            return True
        log('gertrudescat: the dialogue ended without paying — the brothers had drifted apart')
    return False


def gather_seasoned_sardine(snap):
    """Doogle leaves first: they grow behind Gertrude's house, and the sardine is a walk to Port Sarim."""
    _v24 = (snap.inv_ids or {}).get(FLUFFS_OBJ.seasoned_sardine)
    if ((_v24 if _v24 is not None else 0)) > 0:
        return None
    _v25 = (snap.inv_ids or {}).get(FLUFFS_OBJ.doogle_leaves)
    if ((_v25 if _v25 is not None else 0)) == 0:
        return Record({'kind': 'grab_ground', 'item': 'Doogle leaves', 'anchor': DOOGLE_WOODS, 'wait_if_missing': True})
    _v26 = (snap.inv_ids or {}).get(FLUFFS_OBJ.raw_sardine)
    if ((_v26 if _v26 is not None else 0)) == 0:
        return Record({'kind': 'buy', 'item': 'Raw sardine', 'qty': 1, 'shop': SARDINE_SHOP, 'est_gp': SARDINE_GP})
    return Record({'kind': 'custom', 'name': 'season the sardine with doogle leaves', 'run': season_sardine})


def recover_banked_kitten(log):
    here = game.tile()
    if on_platform() or (here is not None and in_yard(here)):
        escaped = yield from leave_yard(log)
        if not escaped:
            return False
    step = quest_step('withdraw', bank=QUEST_BANK,
                      items=[{'name': "Fluffs' kitten", 'id': FLUFFS_OBJ.kitten, 'qty': 1}])
    recovered = yield from execute_step(step, [], log)
    return recovered


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': GERTRUDE})
    progress = snap.progress
    if progress is None:
        return Record({'kind': 'wait', 'reason': f'{QUEST} journal stage unavailable'})
    if progress.stage == FLUFFS_STAGE.STARTED:
        _v27 = snap.inv.get('coins')
        if ((_v27 if _v27 is not None else 0)) < BOY_PAYMENT:
            return Record({'kind': 'withdraw', 'items': [{'name': 'Coins', 'qty': COIN_TOPUP}], 'bank': QUEST_BANK})
        return Record({'kind': 'custom', 'name': 'buy the play area out of Shilop', 'run': pay_brothers})
    elif progress.stage == FLUFFS_STAGE.PAID_BOY:
        sardine = gather_seasoned_sardine(snap)
        if sardine is not None:
            return sardine
        if not ('bucket of milk' in snap.inv):
            return gather_milk(snap)
        return Record({
            'kind': 'custom',
            'name': 'give Fluffs the milk',
            'run': offer_to_cat(FLUFFS_OBJ.bucket_of_milk, 'bucket of milk'),
        })
    elif progress.stage == FLUFFS_STAGE.GAVE_MILK:
        sardine = gather_seasoned_sardine(snap)
        if sardine is not None:
            return sardine
        return Record({
            'kind': 'custom',
            'name': 'give Fluffs the doogle sardine',
            'run': offer_to_cat(FLUFFS_OBJ.seasoned_sardine, 'seasoned sardine'),
        })
    elif progress.stage == FLUFFS_STAGE.GAVE_SARDINE:
        _v28 = (snap.inv_ids or {}).get(FLUFFS_OBJ.kitten)
        if ((_v28 if _v28 is not None else 0)) == 0:
            if banked_id(snap, FLUFFS_OBJ.kitten) > 0:
                return quest_step('custom', name='retrieve the banked kitten', run=recover_banked_kitten)
            return Record({'kind': 'custom', 'name': 'search the crates for the kitten', 'run': search_crates_for_kitten})
        return Record({'kind': 'custom', 'name': 'give Fluffs her kitten', 'run': offer_to_cat(FLUFFS_OBJ.kitten, 'kitten')})
    elif progress.stage == FLUFFS_STAGE.RESCUED:
        return Record({'kind': 'custom', 'name': 'take the news back to Gertrude', 'run': report_to_gertrude})
    else:
        return Record({'kind': 'wait', 'reason': f'unexpected {QUEST} stage {progress.stage}'})


gertrudescat = QuestModule(
    record=quest_record('fluffs'),
    bank=QUEST_BANK,
    food=4,
    tools=['coins', 'bucket', 'doogle leaves', 'sardine', "fluffs' kitten"],
    read_progress=read_gertrudes_cat_progress,
    decide=decide,
)

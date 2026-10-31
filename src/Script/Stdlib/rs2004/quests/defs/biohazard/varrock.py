"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/varrock.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, BIO_LOC, BIO_NPC, BIO_TILE, VIALS, in_guidor_quarter
from rs2004.quests.defs.biohazard.gear import held_id, wear
from rs2004.quests.defs.biohazard.travel import loc_by_id, talk_at, walk_to
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.trade import shop

__all__ = ['ERRANDS', 'PRIEST_SUIT_GP', 'get_touch_paper', 'hand_to_errand_boys', 'collect_from_errand_boys', 'buy_priest_suit', 'visit_guidor', 'cross_east_gate', 'leave_quarter']

# Why: the first option hands the chemist the plague sample and he confiscates it, as does the touch-paper-for-the-sample line; only the Guidor errand keeps it.
CHEMIST_PREFER = ["It's ok, I'm Elena's friend.", 'for a guy called Guidor']
# Why: the third page comes after the stage has already moved, so a run that abandons it still finishes the quest but reports the leg failed, and the next leg has to walk that back.
GUIDOR_PREFER = [
    "I've come to ask your assistance in stopping a plague.",
    "I've been sent by your old pupil Elena.",
    'So what does that mean exactly?',
]
# Why: the boys who lost a vial open a two-way choice whose branches are both harmless, and an unlisted choice makes `talkStrict` abandon the dialogue.
COLLECT_PREFER = ['No! Nothing could be further from the truth!', "I'm getting a bad feeling about this."]
# Why: Hops drinks anything but the broline, Chancy sells anything but the honey, and DeVinci paints with anything but the ethenea; a wrong pairing destroys that vial.
ERRANDS = [
    Record({'npc': BIO_NPC.HOPS, 'vial': BIO_ITEM.SULPHURIC_BROLINE, 'give': 'vial of sulphuric broline', 'stand': BIO_TILE.HOPS}),
    Record({'npc': BIO_NPC.DEVINCI, 'vial': BIO_ITEM.ETHENEA, 'give': 'vial of ethenea', 'stand': BIO_TILE.DEVINCI}),
    Record({'npc': BIO_NPC.CHANCY, 'vial': BIO_ITEM.LIQUID_HONEY, 'give': 'vial of liquid honey', 'stand': BIO_TILE.CHANCY}),
]
PRIEST_SUIT = [BIO_ITEM.PRIEST_GOWN, BIO_ITEM.PRIEST_ROBE]
PRIEST_SUIT_GP = 200


def get_touch_paper(log):
    return talk_at(BIO_NPC.CHEMIST, BIO_TILE.CHEMIST, CHEMIST_PREFER, log)


def hand_to_errand_boys(log):
    """Hand every vial still in the pack to the boy who won't ruin it."""
    given = 0
    for errand in ERRANDS:
        if held_id(errand.vial.id) == 0:
            continue
        _w1 = yield from talk_at(errand.npc, errand.stand, [errand.give], log)
        if not (_w1):
            log(f'{errand.npc} would not take the {errand.vial.name}')
            continue
        _w2 = yield from execution.delay_until(lambda: held_id(errand.vial.id) == 0, 8000)
        if _w2:
            given += 1
            log(f'{errand.npc} is carrying the {errand.vial.name} to Varrock')
    return given > 0


def collect_from_errand_boys(log):
    """Collect from all 3 at the Dancing Donkey. A boy who ruined his vial gives nothing back."""
    got = 0
    for errand in ERRANDS:
        if held_id(errand.vial.id) > 0:
            continue
        _w3 = yield from talk_at(errand.npc, BIO_TILE.DANCING_DONKEY, COLLECT_PREFER, log, 4)
        if not (_w3):
            continue
        _w4 = yield from execution.delay_until(lambda: held_id(errand.vial.id) > 0, 4000)
        if _w4:
            got += 1
        else:
            log(f'{errand.npc} did not hand back the {errand.vial.name}')
    return got > 0


def buy_priest_suit(log):
    _w5 = yield from walk_to(BIO_TILE.THESSALIA, 3, log)
    if not (_w5):
        return False
    _w6 = yield from shop.open(BIO_NPC.THESSALIA)
    if not (_w6):
        log(f'could not open {BIO_NPC.THESSALIA}\'s shop')
        return False
    bought = 0
    for half in PRIEST_SUIT:
        if held_id(half.id) > 0:
            continue
        # Why: both halves render "Priest gown", so a name buy takes the top twice.
        got = yield from shop.buy_by_id(half.id, 1)
        bought += got
    yield from shop.close()
    if bought == 0:
        log('Thessalia sold no priest gown — out of stock or out of coins')
    return bought > 0


def visit_guidor(log):
    """Robe up, get past Guidor's wife, and hand the kit over."""
    for half in PRIEST_SUIT:
        _w7 = yield from wear(half, log)
        if not (_w7):
            return False
    _w8 = yield from walk_to(BIO_TILE.GUIDOR_DOOR, 0, log)
    if not (_w8):
        return False
    yield from settle_scene()
    door = loc_by_id(BIO_LOC.GUIDOR_DOOR, 'Open', 6)
    if door and not (door.interact('Open')):
        return False
    yield from execution.delay_ticks(2)
    _w9 = yield from talk_at(BIO_NPC.GUIDOR, BIO_TILE.GUIDOR, GUIDOR_PREFER, log)
    if not (_w9):
        return False
    _result10 = yield from drive_until(lambda: held_id(BIO_ITEM.PLAGUE_SAMPLE.id) == 0, [], log, 15000)
    return _result10


# Why: The guard opens a two-page search near the gate, which the generic door crossing cannot continue.
def pass_varrock_gate(log):
    """Open the Varrock east gate and sit out the guard's search, in whichever direction."""
    before = in_guidor_quarter(game.tile())
    stand = (BIO_TILE.GATE_INSIDE if before else BIO_TILE.GATE_OUTSIDE)
    landing = (BIO_TILE.GATE_OUTSIDE if before else BIO_TILE.GATE_INSIDE)
    _w11 = yield from walk_to(stand, 0, log)
    if not (_w11):
        return False
    yield from settle_scene()
    gate = loc_by_id(BIO_LOC.VARROCK_GATE, 'Open', 6)
    if not gate:
        log(f'no Varrock east gate at ({BIO_TILE.GATE_OUTSIDE.x},{BIO_TILE.GATE_OUTSIDE.z})')
        return False
    if not (gate.interact('Open')):
        return False

    # Why: the search ends by teleporting you onto the gate's own tile in either direction, so the landing is a step clear of the gateway.
    def _fn12():
        here = game.tile()
        return here is not None and here.x != stand.x
    yield from drive_until(_fn12, [], log, 25000)
    _result13 = yield from walk_to(landing, 0, log)
    return _result13


def cross_east_gate(log):
    """Walk into the walled quarter the gate guards, carrying nothing it would confiscate."""
    if any([held_id(vial.id) > 0 for vial in VIALS]):
        log('the gate guard would take these vials — they have to go with the errand boys first')
        return False
    _c14 = not in_guidor_quarter(game.tile())
    if _c14:
        _w15 = yield from pass_varrock_gate(log)
        _c14 = not (_w15)
    if _c14:
        return False
    _result16 = yield from walk_to(BIO_TILE.DANCING_DONKEY, 4, log)
    return _result16


def leave_quarter(log):
    """Get back out to Elena or the chemist; the guard takes any vial still carried."""
    if not in_guidor_quarter(game.tile()):
        return True
    _result17 = yield from pass_varrock_gate(log)
    return _result17

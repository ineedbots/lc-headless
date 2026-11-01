"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/reveller.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.fremenniktrials.areas import FT_ID, FT_LOC, FT_TILE, MANNI, in_longhall
from rs2004.quests.defs.fremenniktrials.supplies import gather_coins, gather_tinderbox, held_id, talk_until, walk_to
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.reach import reach

__all__ = ['reveller_step']

KEG_PRICE = 250
BEER_PRICE = 100
CONTEST_WON = "completed the Revellers' trial"


def holding(id):
    return inventory.count_by_id(id) > 0


# Why: the contest is unwinnable straight, `viking_reveller_drinkcontest` only concedes when the `keg_lowalc` bit is set.
# Why: that bit is only set by swapping the kegs, and the swap is refused while Manni can see you, so the firecracker in the drain pipe is required.
def reveller_step(snap):
    """Manni's drinking contest: swap the keg for Peter Potter's alcohol-free brew behind a firecracker, then drink."""
    if has_flag(snap.progress, 'reveller-done'):
        return None
    if not has_flag(snap.progress, 'reveller-started'):
        return Record({'kind': 'talk', 'stop': MANNI(['Yes'])})
    low_alcohol = held_id(snap, FT_ID.LOW_ALCOHOL_KEG) > 0
    keg = held_id(snap, FT_ID.BEER_KEG) > 0
    if not low_alcohol and keg:
        return Record({'kind': 'custom', 'name': 'drink Manni under the table', 'run': drinking_contest})
    if not low_alcohol:
        _v1 = gather_coins(snap, KEG_PRICE)
        return (_v1 if _v1 is not None else Record({'kind': 'custom', 'name': 'buy a low alcohol keg (250gp)', 'run': buy_low_alcohol_keg}))
    # Why: this order follows the road: the keg and beer in the Forester's Arms, then Catherby, then the workman on the bridge north of it, then Rellekka.
    cracker = held_id(snap, FT_ID.FIRECRACKER) > 0 or held_id(snap, FT_ID.FIRECRACKER_LIT) > 0
    if not cracker and not ('beer' in snap.inv):
        _v2 = gather_coins(snap, BEER_PRICE)
        return (_v2 if _v2 is not None else Record({'kind': 'custom', 'name': "buy a beer at the Forester's Arms", 'run': buy_beer}))
    tinderbox = gather_tinderbox(snap)
    if tinderbox:
        return tinderbox
    if not cracker:
        return Record({
            'kind': 'use_on',
            'item': 'Beer',
            'target_kind': 'npc',
            'target': 'Council workman',
            'anchor': FT_TILE.COUNCIL_WORKMAN,
            'product': 'Strange object',
        })
    if not keg:
        return Record({'kind': 'grab_ground', 'item': 'Keg of beer', 'anchor': FT_TILE.KEG_TABLE})
    return Record({'kind': 'custom', 'name': 'swap the keg for low alcohol beer', 'run': swap_keg})


# Why: the salesman runs his pitch before he sells and only offers the keg once Manni's trial is live, so this drives to a goal.
def buy_low_alcohol_keg(log):
    return talk_until('Poison salesman', FT_TILE.POISON_SALESMAN, ['Talk about the Fremennik Trials', 'Yes'], lambda: holding(FT_ID.LOW_ALCOHOL_KEG), log, 90000)


# Why: the Forester's Arms bartender has no Trade op for `Shop.open` to find, so the beer comes through dialogue.
def buy_beer(log):
    return talk_until('Bartender', FT_TILE.FORESTERS_ARMS, ['Beer please.'], lambda: inventory.count('Beer') > 0, log)


def swap_keg(log):
    if not holding(FT_ID.FIRECRACKER_LIT) and holding(FT_ID.FIRECRACKER):
        _w3 = yield from walk_to(FT_TILE.PIPE_STAND, 1, log)
        if not (_w3):
            return False
        tinderbox = inventory.first('Tinderbox')
        cracker = ([i for i in inventory.items() if i.id == FT_ID.FIRECRACKER] or [None])[0]
        if not tinderbox or not cracker:
            log('no tinderbox or strange object to light')
            return False
        log('lighting the strange object beside the drain pipe — its fuse runs 140-200 ticks')
        if not (tinderbox.use_on(cracker)):
            return False
        _w4 = yield from execution.delay_until(lambda: holding(FT_ID.FIRECRACKER_LIT), 6000)
        if not (_w4):
            return False
    if holding(FT_ID.FIRECRACKER_LIT):
        status = yield from reach.loc_op('Pipe', 'Put-inside', FT_TILE.PIPE_STAND, lambda: not holding(FT_ID.FIRECRACKER_LIT), id=FT_LOC.PIPE, log=log)
        if status != 'done':
            return False
        yield from drive_until(lambda: not holding(FT_ID.FIRECRACKER_LIT), [], log, 10000)
    _w5 = yield from walk_to(FT_TILE.LONGHALL, 2, log)
    if not (_w5):
        return False
    yield from settle_scene()
    if not in_longhall(game.tile()):
        log('the keg swap only works inside the longhall')
        return False
    keg = ([i for i in inventory.items() if i.id == FT_ID.BEER_KEG] or [None])[0]
    low_alcohol = ([i for i in inventory.items() if i.id == FT_ID.LOW_ALCOHOL_KEG] or [None])[0]
    if not keg or not low_alcohol:
        return False
    if not (keg.use_on(low_alcohol)):
        return False
    swapped = yield from execution.delay_until(lambda: not holding(FT_ID.LOW_ALCOHOL_KEG), 8000)
    if not swapped:
        log('Manni refused the swap — the firecracker never reached the pipe')
    return swapped


# Why: the contest is a chain of `p_delay`s with the chat shut between beats, which outlasts driveDialog's own gap.
def drinking_contest(log):
    mark = game_messages.mark()
    return talk_until('Manni the Reveller', FT_TILE.LONGHALL, ['Yes'], lambda: game_messages.saw_since(mark, CONTEST_WON), log, 90000)

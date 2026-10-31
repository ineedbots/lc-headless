"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/observatory.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.observatory import decide, observatory
from rs2004.quests.defs.observatory.areas import OBS_ID, OBS_STAGE, OBS_TILE
from rs2004.quests.engine.types import QuestSnapshot


def snap(journal='in_progress', stage=None, inv=None, inv_names=None, bank=None, bank_known=True, free_slots=20):
    return QuestSnapshot(**{
        'journal': journal,
        'stage': stage,
        'inv': {n.lower(): 1 for n in (inv_names if inv_names is not None else [])},
        'inv_ids': {k: v for k, v in (inv if inv is not None else {}).items()},
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 100000,
        'bank': {},
        'bank_ids': {k: v for k, v in (bank if bank is not None else {}).items()},
        'bank_known': bank_known,
        'free_slots': free_slots,
    })


PICKAXE = ['bronze pickaxe']
READY = {OBS_ID.PLANK: 3, OBS_ID.BRONZE_BAR: 1, OBS_ID.MOLTEN_GLASS: 1, OBS_ID.LENS_MOULD: 1}
STARTED = OBS_STAGE.STARTED


def step(**options):
    return decide(snap(**options))


def _decide():
    def _done():
        expect(step(journal='complete')).to_equal(Record({'kind': 'done'}))
    test('a green journal is done', _done)

    def _unknown():
        expect(step(journal='unknown')).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('an unloaded quest list waits rather than restarting the quest', _unknown)

    def _red():
        s = step(journal='not_started')
        expect(s.kind).to_be('talk')
        expect(s.kind == 'talk' and s.stop.anchor).to_equal(OBS_TILE.PROFESSOR)
    test('a red journal opens with the professor', _red)

    def _unreadable():
        expect(step(stage=None).kind).to_be('wait')
    test('an unreadable stage waits', _unreadable)

    def _past():
        expect(step(stage=OBS_STAGE.COMPLETE)).to_equal(Record({'kind': 'done'}))
    test('a stage past complete is done', _past)


describe('observatory decide', _decide)


# Why: the errand order is the map, not the quest, every one of these fixes a leg of the single loop the bot walks.
def _errands():
    def _scan():
        expect(step(stage=STARTED, bank_known=False)).to_equal(Record({'kind': 'scan_bank'}))
    test('an unread bank is checked before any walk', _scan)

    def _sand():
        s = step(stage=STARTED)
        expect(s.kind == 'grab_ground' and s.item).to_be('Bucket of sand')
        expect(s.kind == 'grab_ground' and s.anchor).to_equal(OBS_TILE.SAND_SPAWN)
    test('the sand by the reception comes first', _sand)

    def _pickaxe():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1})
        expect(s).to_match_object(Record({'kind': 'buy', 'item': 'Bronze pickaxe'}))
    test('the pickaxe and the seam come next', _pickaxe)

    def _planks():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1, OBS_ID.COPPER_ORE: 1, OBS_ID.TIN_ORE: 1}, inv_names=PICKAXE)
        expect(s.kind == 'grab_ground' and s.item).to_be('Plank')
    test('the planks come after the ore', _planks)

    def _seaweed():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1, OBS_ID.COPPER_ORE: 1, OBS_ID.TIN_ORE: 1, OBS_ID.PLANK: 3}, inv_names=PICKAXE)
        expect(s.kind == 'grab_ground' and s.item).to_be('Seaweed')
        expect(s.kind == 'grab_ground' and s.anchor).to_equal(OBS_TILE.SEAWEED_SPAWN)
    test('the seaweed shore comes after the planks', _seaweed)

    def _range():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1, OBS_ID.PLANK: 3, OBS_ID.SEAWEED: 1, OBS_ID.BRONZE_BAR: 1})
        expect(s).to_match_object(Record({'kind': 'custom', 'name': 'cook seaweed into soda ash'}))
    test('held seaweed goes on the range on the way home', _range)

    def _glass():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1, OBS_ID.SODA_ASH: 1, OBS_ID.PLANK: 3, OBS_ID.COPPER_ORE: 1, OBS_ID.TIN_ORE: 1}, inv_names=PICKAXE)
        expect(s).to_match_object(Record({'kind': 'custom', 'name': 'smelt molten glass'}))
    test('the glass is smelted before the bar, so one furnace visit does both', _glass)

    def _bar():
        s = step(stage=STARTED, inv={OBS_ID.MOLTEN_GLASS: 1, OBS_ID.PLANK: 3, OBS_ID.COPPER_ORE: 1, OBS_ID.TIN_ORE: 1}, inv_names=PICKAXE)
        expect(s).to_match_object(Record({'kind': 'custom', 'name': 'smelt a bronze bar'}))
    test('the bar follows on the same visit', _bar)

    def _cavern():
        s = step(stage=STARTED, inv={OBS_ID.MOLTEN_GLASS: 1, OBS_ID.PLANK: 3, OBS_ID.BRONZE_BAR: 1})
        expect(s).to_match_object(Record({'kind': 'custom', 'name': 'fetch the lens mould'}))
    test('the cavern is last, once nothing above ground is outstanding', _cavern)


describe('observatory errand order', _errands)

MINED = {OBS_ID.BUCKET_OF_SAND: 1, OBS_ID.COPPER_ORE: 1, OBS_ID.TIN_ORE: 1}


def _bank_first():
    def _planks():
        s = step(stage=STARTED, inv=MINED, bank={OBS_ID.PLANK: 5}, inv_names=PICKAXE)
        expect(s).to_equal(Record({'kind': 'withdraw', 'items': [{'name': 'Plank', 'qty': 3, 'id': OBS_ID.PLANK}]}))
    test('banked planks are withdrawn rather than walked to', _planks)

    def _top_up():
        inv = {k: v for k, v in MINED.items()}
        inv[OBS_ID.PLANK] = 2
        s = step(stage=STARTED, inv=inv, bank={OBS_ID.PLANK: 5}, inv_names=PICKAXE)
        expect(s.kind == 'withdraw' and s.items[0]['qty']).to_be(1)
    test('a part-filled bank is topped up rather than re-withdrawn', _top_up)

    def _bar():
        s = step(stage=STARTED, bank={OBS_ID.BRONZE_BAR: 1, OBS_ID.MOLTEN_GLASS: 1})
        expect(s.kind == 'withdraw' and s.items[0]['name']).to_be('Molten glass')
    test('a banked bar skips the counter and the seam', _bar)

    def _glass():
        s = step(stage=STARTED, bank={OBS_ID.MOLTEN_GLASS: 1})
        expect(s.kind == 'withdraw' and s.items[0]['name']).to_be('Molten glass')
    test('banked glass skips the whole glass chain', _glass)

    def _pickaxe():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1}, bank={OBS_ID.BRONZE_PICKAXE: 1})
        expect(s.kind == 'withdraw' and s.items[0]['name']).to_be('Bronze pickaxe')
    test('a banked pickaxe is withdrawn rather than bought', _pickaxe)

    def _mould():
        s = step(stage=STARTED, inv={OBS_ID.MOLTEN_GLASS: 1, OBS_ID.PLANK: 3, OBS_ID.BRONZE_BAR: 1}, bank={OBS_ID.LENS_MOULD: 1})
        expect(s.kind == 'withdraw' and s.items[0]['name']).to_be('Lens mould')
    test('a banked mould skips the cavern', _mould)

    def _copper():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1}, inv_names=PICKAXE)
        expect(s).to_equal(Record({'kind': 'mine_rock', 'rock': 'Copper ore', 'item': 'Copper ore', 'qty': 1, 'anchor': OBS_TILE.MINE}))
    test('copper comes before tin', _copper)

    def _tin():
        s = step(stage=STARTED, inv={OBS_ID.BUCKET_OF_SAND: 1, OBS_ID.COPPER_ORE: 1}, inv_names=PICKAXE)
        expect(s.kind == 'mine_rock' and s.item).to_be('Tin ore')
    test('tin follows the copper', _tin)


describe('observatory bank-first sourcing', _bank_first)


def _hand_overs():
    def _full_pack():
        s = step(stage=OBS_STAGE.GIVEN_GLASS, inv={OBS_ID.LENS_MOULD: 1}, free_slots=0)
        expect(s.kind).to_be('deposit')
    test('a full pack is banked before the stage that hands the glass back', _full_pack)

    def _full_load():
        for stage in [OBS_STAGE.STARTED, OBS_STAGE.GIVEN_PLANKS, OBS_STAGE.GIVEN_BRONZE, OBS_STAGE.GIVEN_GLASS]:
            expect(step(stage=stage, inv=READY)).to_match_object(Record({'kind': 'talk'}))
    test('a full load walks back to the professor', _full_load)

    def _lens():
        s = step(stage=OBS_STAGE.GIVEN_MOULD, inv={OBS_ID.MOLTEN_GLASS: 1, OBS_ID.LENS_MOULD: 1})
        expect(s).to_match_object(Record({'kind': 'use_on', 'item': 'Lens mould', 'target': 'Molten glass', 'product': 'Lens'}))
    test('the stage past the mould never re-fetches the planks or the bar', _lens)

    def _lost_glass():
        s = step(stage=OBS_STAGE.GIVEN_MOULD, inv={OBS_ID.LENS_MOULD: 1})
        expect(s.kind == 'grab_ground' and s.item).to_be('Bucket of sand')
    test('a lost glass at the lens stage is remade rather than asked for', _lost_glass)

    def _no_refetch():
        s = step(stage=OBS_STAGE.GIVEN_MOULD, inv={OBS_ID.LENS_MOULD: 1, OBS_ID.BUCKET_OF_SAND: 1})
        expect(s.kind == 'grab_ground' and s.item).to_be('Seaweed')
    test('the lens stage never re-fetches the planks or the ore', _no_refetch)

    def _lost_mould():
        s = step(stage=OBS_STAGE.GIVEN_MOULD, inv={OBS_ID.MOLTEN_GLASS: 1})
        expect(s).to_match_object(Record({'kind': 'custom', 'name': 'fetch the lens mould'}))
    test('a lost mould at the lens stage sends the bot back to the sack', _lost_mould)

    def _finished():
        s = step(stage=OBS_STAGE.GIVEN_MOULD, inv={OBS_ID.LENS: 1})
        expect(s).to_match_object(Record({'kind': 'talk'}))
    test('a finished lens goes to the professor', _finished)

    def _telescope():
        expect(step(stage=OBS_STAGE.SENT_TELESCOPE)).to_match_object(Record({'kind': 'custom', 'name': 'look through the telescope'}))
    test('the last stage is the telescope', _telescope)


describe('observatory lens mould and hand-overs', _hand_overs)


def _module():
    def _wired():
        expect(observatory.record.id).to_be('itgronigen')
        expect(observatory.record.quest_points).to_be(2)
        expect(observatory.bank).to_equal(OBS_TILE.BANK)
    test('is wired to its record and the Ardougne bank', _wired)

    def _tools():
        for item in ['plank', 'bronze bar', 'molten glass', 'lens mould', 'lens', 'keep key', 'seaweed', 'soda ash', 'bucket of sand', 'copper ore', 'tin ore', 'pickaxe']:
            expect(observatory.tools).to_contain(item)
    test('keeps every intermediate through a spillover deposit', _tools)


describe('observatory module', _module)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/treegnome.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.treegnome import decide, treegnome
from rs2004.quests.defs.treegnome.areas import TG_ITEM, TG_TILE
from rs2004.quests.defs.treegnome.journal import TG_STAGE
from rs2004.quests.gear import quest_loadout
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.engine.types import QuestProgress

# Why: `QuestLoadout` is one module-level singleton, so a neighbouring suite's declared kit decides this one's gear step.
def _fn1():
    quest_loadout.current = None


before_each(_fn1)


def tally(values):
    out = {}
    for value in values:
        _v2 = out.get(value)
        out[value] = ((_v2 if _v2 is not None else 0)) + 1
    return out


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else TG_STAGE.STARTED)
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': tally([n.lower() for n in ((options.inv if options.inv is not None else []))]),
        'inv_ids': tally((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, set()),
        'bank': tally([n.lower() for n in ((options.bank if options.bank is not None else []))]),
        'bank_ids': tally((options.bank_ids if options.bank_ids is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (options.tile if options.tile is not None else TG_TILE.BANK),
        'free_slots': 20,
    })


def name(step):
    return ((step.name if step.kind == 'custom' else None))


def talker(step):
    return ((step.stop.npc if step.kind == 'talk' else None))


def logs(count):
    return [TG_ITEM.LOGS.id for _ in range(count)]


def _fn4():
    def _fn5():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('waits while the quest list is still loading', _fn5)

    def _fn6():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn6)

    def _fn7():
        blind = snap().with_fields({'progress': None, 'stage': None})
        expect(decide(blind).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn7)

    def _fn9():
        expect(talker(decide(snap(Record({'journal': 'not_started', 'stage': TG_STAGE.NOT_STARTED}))))).to_be('King Bolren')
    test('opens with King Bolren', _fn9)

    def _fn10():
        expect(talker(decide(snap(Record({'stage': TG_STAGE.STARTED}))))).to_be('Commander Montai')
    test('reports to Montai once Bolren has sent us north', _fn10)

    def _fn11():
        step = decide(snap(Record({'stage': TG_STAGE.SPOKEN_MONTAI})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Iron axe')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Aemad')
    test('buys an axe when neither the pack nor the bank has one', _fn11)

    def _fn12():
        step = decide(snap(Record({'stage': TG_STAGE.SPOKEN_MONTAI, 'bank_ids': [1349]})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['id']).to_be(1349)
    test('takes the banked axe rather than walking to Aemad', _fn12)

    def _fn13():
        expect(decide(snap(Record({'stage': TG_STAGE.SPOKEN_MONTAI, 'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before believing it has no axe', _fn13)

    def _fn14():
        expect(name(decide(snap(Record({'stage': TG_STAGE.SPOKEN_MONTAI, 'inv_ids': [1349]}))))).to_be('chop 6 logs on the battlefield')
    test('chops once an axe is carried', _fn14)

    def _fn15():
        step = decide(snap(Record({'stage': TG_STAGE.SPOKEN_MONTAI, 'inv_ids': [1349] + list(logs(6))})))
        expect(talker(step)).to_be('Commander Montai')
    test('hands the six logs over rather than chopping a seventh', _fn15)

    def _fn16():
        expect(name(decide(snap(Record({'stage': TG_STAGE.FINDING_TRACKERS}))))).to_be('fire the gnome ballista at the stronghold')
    test('fires the ballista once Montai has briefed us', _fn16)

    def _fn17():
        expect(name(decide(snap(Record({'stage': TG_STAGE.BALLISTA_FIRED}))))).to_be("search the Khazard chest for the gnomes' orb")
    test('goes for the chest once the stronghold is breached', _fn17)

    def _fn18():
        expect(talker(decide(snap(Record({'stage': TG_STAGE.RETRIEVED_ORB, 'inv_ids': [TG_ITEM.ORB.id]}))))).to_be('King Bolren')
    test('carries the orb back to Bolren', _fn18)

    # Why: the chest refuses while a copy sits in the bank, so a banked orb has to come back out rather than be re-earned.
    def _fn19():
        step = decide(snap(Record({'stage': TG_STAGE.RETRIEVED_ORB, 'bank_ids': [TG_ITEM.ORB.id]})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['id']).to_be(TG_ITEM.ORB.id)
    test('withdraws a banked orb rather than searching the chest again', _fn19)

    def _fn20():
        expect(name(decide(snap(Record({'stage': TG_STAGE.RETRIEVED_ORB}))))).to_be("search the Khazard chest for the gnomes' orb")
    test('goes back to the chest when the orb is nowhere', _fn20)

    def _fn21():
        expect(name(decide(snap(Record({'stage': TG_STAGE.RETURNED_FIRST_ORB}))))).to_be('kill the Khazard warlord for the last two orbs')
    test('hunts the warlord after the village is raided', _fn21)

    def _fn22():
        wrong_orb = decide(snap(Record({'stage': TG_STAGE.DEFEATED_WARLORD, 'inv_ids': [TG_ITEM.ORB.id]})))
        expect(name(wrong_orb)).to_be('kill the Khazard warlord for the last two orbs')
        expect(talker(decide(snap(Record({'stage': TG_STAGE.DEFEATED_WARLORD, 'inv_ids': [TG_ITEM.ORBS.id]}))))).to_be('King Bolren')
    test('tells the two orbs from the one by id', _fn22)

    # Why: Bolren deletes the orbs a tick before the queue that finishes the quest, and a walk back to the warlord in that gap is 200 tiles wasted.
    def _fn23():
        step = decide(snap(Record({'stage': TG_STAGE.DEFEATED_WARLORD, 'tile': TG_TILE.BOLREN})))
        expect(step.kind).to_be('wait')
    test("waits out the ceremony rather than re-hunting from Bolren's feet", _fn23)

    def _fn25():
        inside = TG_TILE.LADDER_STAND
        expect(name(decide(snap(Record({'stage': TG_STAGE.RETURNED_FIRST_ORB, 'tile': inside}))))).to_be('walk out of the Khazard stronghold')
        expect(name(decide(snap(Record({'stage': TG_STAGE.RETRIEVED_ORB, 'inv_ids': [TG_ITEM.ORB.id], 'tile': inside}))))).to_be('walk out of the Khazard stronghold')
    test('walks out of the stronghold before any errand that is not the chest', _fn25)

    def _fn27():
        step = decide(snap(Record({'stage': TG_STAGE.BALLISTA_FIRED, 'tile': TG_TILE.CHEST_STAND})))
        expect(name(step)).to_be("search the Khazard chest for the gnomes' orb")
    test('stays for the chest while the orb is still in it', _fn27)

    # Why: armed at the first fight instead, the bot walks the battlefield back to Ardougne for a kit the opening bank trip could have carried.
    def _fn29():
        step = decide(snap(Record({'stage': TG_STAGE.NOT_STARTED, 'journal': 'not_started', 'bank': ['Rune scimitar']})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Rune scimitar')
    test('arms itself on the opening bank trip', _fn29)

    def _fn30():
        step = decide(snap(Record({'stage': TG_STAGE.STARTED, 'inv': ['Rune scimitar']})))
        expect(name(step)).to_be('wear Rune scimitar')
    test('wears the kit it is carrying before walking on', _fn30)


describe('Tree Gnome Village decide', _fn4)


def _fn31():
    def _fn32():
        expect(treegnome.record.items).to_equal([])
    test('leaves the logs off the record, so a resume past Montai chops nothing', _fn32)

    def _fn33():
        for tool in ['logs', 'axe', 'orb of protection']:
            expect(treegnome.tools).to_contain(tool)
    test('keeps the logs, the axe and both orbs off the deposit list', _fn33)

    def _fn34():
        expect(treegnome.bank).to_be(TG_TILE.BANK)
    test('banks in East Ardougne, the nearest booth to the maze', _fn34)


describe('Tree Gnome Village module', _fn31)

"""rs2b0t's test/api/ai/quests/engine/exact-item-snapshot.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.game import game, skills
from rs2004.items import equipment, inventory
from rs2004.quests.engine.quest_engine import QuestEngine
from rs2004.tabs import quests


def _fn2():
    state = {'bank_open': True}
    spy_on(skills, 'effective', impl=lambda skill: 13 if skill == 'magic' else 1)
    spy_on(bank, 'is_open', impl=lambda: state['bank_open'])
    spy_on(bank, 'ready', returns=True)
    spy_on(bank, 'loaded', returns=True)
    spy_on(bank, 'items', returns=[Record({'id': 293, 'name': 'A key', 'count': 2}), Record({'id': 298, 'name': 'A key', 'count': 1})])
    spy_on(inventory, 'items', returns=[
        Record({'id': 293, 'name': 'A key', 'count': 1}),
        Record({'id': 298, 'name': 'A key', 'count': 1}),
        Record({'id': 954, 'name': 'Rope', 'count': 1}),
    ])
    spy_on(equipment, 'items', returns=[Record({'id': 295, 'name': "Glarial's amulet", 'count': 1})])
    spy_on(quests, 'status', returns='in_progress')
    spy_on(game, 'tile', returns=Record({'x': 2565, 'z': 9915, 'level': 0}))
    spy_on(inventory, 'free', returns=25)
    internals = QuestEngine(Record({}))
    internals._refresh_bank_counts()
    state['bank_open'] = False
    module = Record({'record': Record({'name': 'Waterfall Quest'})})
    snap = internals._build_snapshot(module, 6)
    expect(snap.inv.get('a key')).to_be(2)
    expect(snap.inv_ids).to_equal({293: 1, 298: 1, 954: 1})
    expect(snap.worn).to_equal(set(["glarial's amulet"]))
    expect(snap.worn_ids).to_equal(set([295]))
    expect(snap.bank.get('a key')).to_be(3)
    expect(snap.bank_ids).to_equal({293: 2, 298: 1})
    expect(snap.stage).to_be(6)
    expect(snap.magic).to_be(13)


test('quest snapshots retain exact IDs alongside legacy name totals', _fn2)

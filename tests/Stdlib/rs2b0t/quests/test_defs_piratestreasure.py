"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/piratestreasure.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.piratestreasure import decide, piratestreasure
from rs2004.quests.defs.piratestreasure.areas import PT_ID, PT_STAGE
FUNDED = [[PT_ID.COINS, 5000]]
PORT_SARIM = Fake(**{'x': 3014, 'z': 3204, 'level': 0})
PLANTATION = Fake(**{'x': 2943, 'z': 3151, 'level': 0})

def snap(journal, stage, flags=None, ids=None, over=None):
    if flags is None:
        flags = []
    if ids is None:
        ids = FUNDED
    if over is None:
        over = Fake(**{})
    _merged2 = {}
    for _k, _v in {'journal': journal, 'inv': {_k: _v for _k, _v in [[str(id), n] for id, n in ids]}, 'inv_ids': {_k: _v for _k, _v in ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 100000, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set(flags)}), 'bank': {_k: _v for _k, _v in [['coins', 100000]]}, 'bank_ids': {}, 'bank_known': True, 'tile': PORT_SARIM}.items():
        _merged2[_k] = _v
    for _k, _v in (over._fields if isinstance(over, (Record, Fake)) else over).items():
        _merged2[_k] = _v
    return _snapshot(**_merged2)

def _fn3():

    def _fn4():
        expect(decide(snap('complete', PT_STAGE.COMPLETE)).kind).to_be('done')
        expect(decide(snap('unknown', PT_STAGE.NOT_STARTED)).kind).to_be('wait')
    test('complete is done and unknown waits', _fn4)

    def _fn5():
        s = snap('in_progress', PT_STAGE.FETCH_RUM)
        s.progress = None
        s.stage = None
        expect(decide(s).kind).to_be('wait')
    test('an unreadable journal waits rather than restarting the quest', _fn5)
describe('pirate decide — guards', _fn3)

def _fn6():

    def _fn7():
        s = decide(snap('not_started', PT_STAGE.NOT_STARTED))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Redbeard Frank')
        expect(s.kind == 'talk' and s.stop.prefer[0]).to_be("I'm in search of treasure.")
    test('not started talks to Frank with the treasure line', _fn7)

    def _fn8():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['need-rum']))
        expect(s.kind == 'buy' and s.item).to_be('White apron')
    test('need-rum with no apron buys the apron first', _fn8)

    def _fn9():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['need-rum'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1]]))
        expect(s.kind == 'buy' and s.shop.npc).to_be('Zambo')
    test('need-rum with the apron held buys the rum at Zambo', _fn9)

    def _fn10():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-held-unemployed'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1], [PT_ID.RUM, 1]]))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Luthas')
    test('rum held but unemployed talks to Luthas', _fn10)

    def _fn11():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-held-employed'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1], [PT_ID.RUM, 1]]))
        expect(s.kind == 'custom' and s.name).to_contain('ship')
    test('employed with the rum ships the crate', _fn11)

    def _fn12():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-in-crate'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1]]))
        expect(s.kind == 'custom' and s.name).to_contain('ship')
    test('rum in the crate ships it', _fn12)

    def _fn13():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['crate-full'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1]]))
        expect(s.kind == 'custom' and s.name).to_contain('ship')
    test('a full crate ships it', _fn13)

    def _fn14():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-shipped'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1]]))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Wydin')
    test('shipped takes the job at Wydin', _fn14)

    def _fn15():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['store-job'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1]]))
        expect(s.kind == 'equip' and s.item).to_be('White apron')
    test('store-job equips the apron before the door refuses it', _fn15)

    def _fn16():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['store-job'], FUNDED, Fake(**{'worn_ids': set([PT_ID.WHITE_APRON])})))
        expect(s.kind == 'custom' and s.name).to_contain('back room')
    test('store-job with the apron worn searches the back room', _fn16)

    def _fn17():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['store-job'], FUNDED, Fake(**{'worn_ids': set([PT_ID.WHITE_APRON]), 'tile': PLANTATION})))
        expect(s.kind == 'custom' and s.name).to_contain('ship')
    test('store-job on Karamja ships the crate rather than searching an empty back room', _fn17)

    def _fn18():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-in-hand'], list(FUNDED) + [[PT_ID.RUM, 1]]))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Redbeard Frank')
    test('rum in hand on the mainland goes back to Frank', _fn18)

    def _fn19():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-in-hand'], list(FUNDED) + [[PT_ID.RUM, 1]], Fake(**{'tile': PLANTATION})))
        expect(s.kind == 'custom' and s.name).to_contain('ship')
    test('rum in hand on Karamja ships it rather than carrying it past the customs officer', _fn19)

    def _fn20():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-lost'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1]]))
        expect(s.kind == 'buy' and s.shop.npc).to_be('Zambo')
    test('lost rum restarts the smuggle rather than parking', _fn20)

    def _fn21():
        s = decide(snap('in_progress', PT_STAGE.FETCH_RUM, ['rum-held-employed'], list(FUNDED) + [[PT_ID.WHITE_APRON, 1], [3164, 1]]))
        expect(s.kind == 'custom' and s.name).to_contain('ship')
    test('a Tai Bwo Wannai look-alike is not the quest rum', _fn21)
describe('pirate decide — the smuggle ladder', _fn6)

def _fn22():

    def _fn23():
        s = decide(snap('in_progress', PT_STAGE.RECEIVED_KEY))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Redbeard Frank')
    test('the key is re-issued by Frank when neither key nor note is held', _fn23)

    def _fn24():
        s = decide(snap('in_progress', PT_STAGE.RECEIVED_KEY, [], list(FUNDED) + [[PT_ID.CHEST_KEY, 1]]))
        expect(s.kind == 'custom' and s.name).to_contain('chest')
    test('the key opens the chest', _fn24)

    def _fn25():
        s = decide(snap('in_progress', PT_STAGE.RECEIVED_KEY, [], list(FUNDED) + [[PT_ID.PIRATE_MESSAGE, 1]]))
        expect(s.kind == 'custom' and s.name).to_contain('read')
    test('the note is read', _fn25)

    def _fn26():
        s = decide(snap('in_progress', PT_STAGE.READ_NOTE, [], list(FUNDED) + [[PT_ID.PIRATE_MESSAGE, 1]]))
        expect(s.kind).to_be('grab_ground')
    test('a read note with no spade fetches one before digging', _fn26)

    def _fn27():
        s = decide(snap('in_progress', PT_STAGE.READ_NOTE, [], list(FUNDED) + [[PT_ID.SPADE, 1]]))
        expect(s.kind == 'custom' and s.name).to_contain('dig')
    test('spade in hand digs', _fn27)
describe('pirate decide — the treasure', _fn22)

def _fn28():

    def _fn29():
        expect(piratestreasure.owns_inventory).to_be(True)
        expect(piratestreasure.record.id).to_be('hunt')
        expect(piratestreasure.record.name).to_be("Pirate's Treasure")
    test('owns its inventory so every leg is re-derived on resume', _fn29)
describe('pirate module wiring', _fn28)

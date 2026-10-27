"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/dragonslayerDecide.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.dragonslayer.areas import DS_ID, DS_ITEM
from rs2004.quests.defs.dragonslayer import decide
from rs2004.quests.defs.dragonslayer.journal import DRAGON_STAGE
from rs2004.game import skills
levels = spy_on(skills, 'effective')

def _fn1():
    global levels
    levels = spy_on(skills, 'effective').mock_return_value(99)
before_each(_fn1)

def counts(stacks):
    return {_k: _v for _k, _v in [s if isinstance(s, list) else [s, 1] for s in stacks]}

def snapshot(over=None):
    if over is None:
        over = Fake(**{})
    flags = over.flags if over.flags is not None else []
    carried = over.carried if over.carried is not None else []
    banked = over.banked if over.banked is not None else []
    rest = {k: v for k, v in over._fields.items() if k not in ['flags', 'carried', 'banked']}
    _merged2 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': {}, 'inv_ids': counts(carried), 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank_ids': counts(banked), 'bank_known': True, 'progress': Fake(**{'stage': DRAGON_STAGE.SPOKEN_OZIACH, 'flags': set(flags)}), 'tile': Fake(**{'x': 3013, 'z': 3355, 'level': 0})}.items():
        _merged2[_k] = _v
    for _k, _v in (rest._fields if isinstance(rest, (Record, Fake)) else rest).items():
        _merged2[_k] = _v
    return snapshot_fields(**_merged2)
NAILS = [DS_ID.NAILS, 12]

class RowCase:

    def __init__(self, body, row):
        self.body = body
        self.row = row

    def __call__(self):
        return self.body(self.row)

def test_each(rows):

    def register(label, body):
        for row in rows:
            test(label.replace('$label', row.label), RowCase(body, row))
    return register

def _fn3():
    boat = Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.BOUGHT_SHIP, 'flags': set()})})
    hull = [DS_ID.HAMMER, [DS_ID.PLANK, 3]]
    charms = [DS_ID.MAZE_KEY, DS_ID.MAP_MELZAR, DS_ID.LOBSTER_POT, DS_ID.MIND_BOMB, DS_ID.SILK]

    def _fn5(_arg6):
        smithing, mining, items, kind = (_arg6.smithing, _arg6.mining, _arg6.items, _arg6.kind)
        levels.mock_implementation(lambda skill: smithing if skill == 'smithing' else mining)
        _merged7 = {}
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged7[_k] = _v
        for _k, _v in {'carried': hull, 'inv': {_k: _v for _k, _v in items}}.items():
            _merged7[_k] = _v
        given = snapshot(Fake(**_merged7))
        step = decide(given)
        expect(step.kind).to_be(kind)
        if step.kind == 'wait':
            expect('bank' in step.reason.lower() or 'obtain' in step.reason.lower()).to_be(True)
    test_each([Fake(**{'label': 'Smithing 33 with steel', 'smithing': 33, 'mining': 99, 'items': [['steel bar', 6]], 'kind': 'wait'}), Fake(**{'label': 'Smithing 34 with steel and Mining 1', 'smithing': 34, 'mining': 1, 'items': [['steel bar', 6]], 'kind': 'custom'}), Fake(**{'label': 'one steel bar with Mining 1', 'smithing': 34, 'mining': 1, 'items': [['steel bar', 1]], 'kind': 'custom'}), Fake(**{'label': 'Smithing 29 with all ore', 'smithing': 29, 'mining': 99, 'items': [['iron ore', 6], ['coal', 12]], 'kind': 'wait'}), Fake(**{'label': 'Smithing 30 still cannot hammer nails', 'smithing': 30, 'mining': 99, 'items': [['iron ore', 6], ['coal', 12]], 'kind': 'wait'}), Fake(**{'label': 'all ore with Mining 1', 'smithing': 34, 'mining': 1, 'items': [['iron ore', 6], ['coal', 12]], 'kind': 'custom'}), Fake(**{'label': 'missing iron at Mining 14', 'smithing': 34, 'mining': 14, 'items': [['coal', 12]], 'kind': 'wait'}), Fake(**{'label': 'missing iron at Mining 15', 'smithing': 34, 'mining': 15, 'items': [['coal', 12]], 'kind': 'custom'}), Fake(**{'label': 'missing coal at Mining 29', 'smithing': 34, 'mining': 29, 'items': [['iron ore', 6]], 'kind': 'wait'}), Fake(**{'label': 'missing coal at Mining 30', 'smithing': 34, 'mining': 30, 'items': [['iron ore', 6]], 'kind': 'custom'}), Fake(**{'label': 'partial coal at Mining 29', 'smithing': 34, 'mining': 29, 'items': [['iron ore', 6], ['coal', 11]], 'kind': 'wait'})])('selects the feasible nail stage when $label', _fn5)

    def _fn8():
        levels.mock_return_value(1)
        _merged9 = {}
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged9[_k] = _v
        for _k, _v in {'carried': list(hull) + [[DS_ID.NAILS, 4]], 'banked': [[DS_ID.NAILS, 3]]}.items():
            _merged9[_k] = _v
        given = snapshot(Fake(**_merged9))
        step = decide(given)
        expect(step).to_match_object(Fake(**{'kind': 'withdraw', 'items': [Fake(**{'id': DS_ID.NAILS, 'qty': 3})]}))
    test('withdraws partial banked nails before checking production skills', _fn8)

    def _fn10():
        levels.mock_return_value(1)
        _merged11 = {}
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged11[_k] = _v
        for _k, _v in {'carried': [DS_ID.HAMMER, [DS_ID.PLANK, 2], [DS_ID.NAILS, 8]]}.items():
            _merged11[_k] = _v
        given = snapshot(Fake(**_merged11))
        step = decide(given)
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'patch the Lady Lumbridge'}))
    test('patches a partial hull with carried supplies despite low skills', _fn10)

    def _fn13(_arg14):
        kind = _arg14.kind
        held = Fake(**{k: v for k, v in _arg14._fields.items() if k not in ['label', 'kind']})
        levels.mock_return_value(7)
        _merged15 = {}
        for _k, _v in (held._fields if isinstance(held, (Record, Fake)) else held).items():
            _merged15[_k] = _v
        for _k, _v in {'carried': list(held._fields.get('carried')), 'banked': list(held._fields.get('banked'))}.items():
            _merged15[_k] = _v
        given = snapshot(Fake(**_merged15))
        step = decide(given)
        expect(step.kind).to_be(kind)
    test_each([Fake(**{'label': 'unknown bank', 'bank_known': False, 'banked': [], 'carried': charms, 'kind': 'scan_bank'}), Fake(**{'label': 'banked bowl', 'bank_known': True, 'banked': [DS_ID.UNFIRED_BOWL], 'carried': charms, 'kind': 'withdraw'}), Fake(**{'label': 'carried bowl', 'bank_known': True, 'banked': [], 'carried': list(charms) + [DS_ID.UNFIRED_BOWL], 'kind': 'talk'}), Fake(**{'label': 'absent bowl', 'bank_known': True, 'banked': [], 'carried': charms, 'kind': 'wait'})])('uses $label before bowl production at Crafting 7', _fn13)
describe('Dragon Slayer production prerequisites', _fn3)

def _fn16():

    def _fn17():
        step = decide(snapshot(Fake(**{'banked': [DS_ID.MAZE_KEY, DS_ID.SHIELD, NAILS], 'flags': ['has-shield']})))
        _v18 = step.name
        expect(_v18 if _v18 is not None else '').not_.to_contain('Oziach')
    test('a banked maze key is not a missing one', _fn17)

    def _fn19():
        step = decide(snapshot(Fake(**{'banked': [DS_ID.MAZE_KEY], 'flags': []})))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw', 'items': [Fake(**{'id': DS_ID.MAZE_KEY, 'qty': 1, 'name': DS_ITEM.MAZE_KEY})]}))
    test('#379 banked maze key withdraws instead of Oziach', _fn19)

    def _fn20():
        step = decide(snapshot(Fake(**{'bank_known': False, 'banked': [], 'carried': [], 'flags': []})))
        expect(step).to_match_object(Fake(**{'kind': 'scan_bank'}))
    test('#379 unseen bank scans before Oziach when key is nowhere', _fn20)

    def _fn21():
        step = decide(snapshot(Fake(**{'flags': ['needs-briefing'], 'carried': [DS_ID.MAZE_KEY]})))
        expect(step).to_match_object(Fake(**{'kind': 'custom'}))
        expect(step.name).to_contain('Oziach')
    test('an unfinished briefing outranks everything else', _fn21)

    def _fn22():
        step = decide(snapshot(Fake(**{'flags': ['has-shield']})))
        expect(step.name).to_contain('Oziach')
    test('no maze key anywhere sends the bot back to Oziach', _fn22)

    def _fn23():
        step = decide(snapshot(Fake(**{'flags': ['needs-briefing']})))
        name = step.name
        expect(name).to_contain('mazekey=nowhere')
        expect(name).to_contain('stage=')
    test('the step name says why it was chosen', _fn23)

    def _fn24():
        cases = [Fake(**{'carried': [DS_ID.MAZE_KEY]}), Fake(**{'carried': [DS_ID.MAZE_KEY], 'flags': ['has-shield']}), Fake(**{'carried': [DS_ID.MAZE_KEY, DS_ID.SHIELD]})]
        for held in cases:
            step = decide(snapshot(held))
            expect(step.name).to_contain("Melzar's Maze")
    test('the map is finished before anything else is fetched', _fn24)

    def _fn25():
        missing = decide(snapshot(Fake(**{'carried': [DS_ID.MAZE_KEY, DS_ID.MAP]})))
        expect(missing).to_match_object(Fake(**{'kind': 'talk', 'stop': Fake(**{'npc': 'Duke Horacio'})}))
        for held in [Fake(**{'carried': [DS_ID.MAZE_KEY, DS_ID.MAP, DS_ID.SHIELD]}), Fake(**{'carried': [DS_ID.MAZE_KEY, DS_ID.MAP], 'banked': [DS_ID.SHIELD]})]:
            step = decide(snapshot(held))
            _v26 = step.stop.npc if step.stop is not None else None
            expect(_v26 if _v26 is not None else '').not_.to_be('Duke Horacio')
    test('the shield is asked of the Duke once the map is whole', _fn25)

    def _fn27():
        shopping = decide(snapshot(Fake(**{'carried': [DS_ID.MAZE_KEY, DS_ID.MAP, DS_ID.SHIELD]})))
        _v28 = shopping.name
        expect(_v28 if _v28 is not None else '').not_.to_contain('nails')
        boat = decide(snapshot(Fake(**{'carried': [DS_ID.MAP, DS_ID.HAMMER, [DS_ID.PLANK, 3]], 'progress': Fake(**{'stage': DRAGON_STAGE.BOUGHT_SHIP, 'flags': set()})})))
        expect(boat.name).to_contain('nails')
    test('nails are smithed for the boat, not before the map', _fn27)

    def _fn29():
        patching = [Fake(**{'carried': [DS_ID.MAP, DS_ID.HAMMER, [DS_ID.PLANK, 2], [DS_ID.NAILS, 8]]}), Fake(**{'carried': [DS_ID.MAP, DS_ID.HAMMER, [DS_ID.PLANK, 1], [DS_ID.NAILS, 4]]})]
        for held in patching:
            _merged30 = {}
            for _k, _v in (held._fields if isinstance(held, (Record, Fake)) else held).items():
                _merged30[_k] = _v
            for _k, _v in {'progress': Fake(**{'stage': DRAGON_STAGE.BOUGHT_SHIP, 'flags': set()})}.items():
                _merged30[_k] = _v
            step = decide(snapshot(Fake(**_merged30)))
            expect(step.name).to_contain('patch')
    test('a patched hole is not a nail shortage', _fn29)

    def _fn31():
        step = decide(snapshot(Fake(**{'carried': [DS_ID.MAP, DS_ID.HAMMER, [DS_ID.PLANK, 2], [DS_ID.NAILS, 4]], 'progress': Fake(**{'stage': DRAGON_STAGE.BOUGHT_SHIP, 'flags': set()})})))
        expect(step.name).to_contain('smith 4 nails')
    test('a real shortage still sends the bot to the anvil', _fn31)

    def _fn32():
        step = decide(snapshot(Fake(**{'carried': [DS_ID.MAP, DS_ID.HAMMER, [DS_ID.PLANK, 3]], 'banked': [NAILS], 'progress': Fake(**{'stage': DRAGON_STAGE.BOUGHT_SHIP, 'flags': set()})})))
        expect(step.kind).to_be('withdraw')
    test('nails already banked are not smithed again', _fn32)

    def _fn33():
        step = decide(snapshot(Fake(**{'carried': [DS_ID.MAZE_KEY, DS_ID.SHIELD], 'banked': [DS_ID.MAP_MELZAR], 'flags': ['has-shield']})))
        expect(step.kind).to_be('withdraw')
    test('map pieces left in the bank are withdrawn, not re-earned', _fn33)

    def _fn34():
        sailing = Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.NED_GIVEN_MAP, 'flags': set()})})
        _merged35 = {}
        for _k, _v in {'banked': [DS_ID.SHIELD]}.items():
            _merged35[_k] = _v
        for _k, _v in (sailing._fields if isinstance(sailing, (Record, Fake)) else sailing).items():
            _merged35[_k] = _v
        expect(decide(snapshot(Fake(**_merged35))).kind).to_be('withdraw')
        _merged36 = {}
        for _k, _v in {'carried': [DS_ID.SHIELD]}.items():
            _merged36[_k] = _v
        for _k, _v in (sailing._fields if isinstance(sailing, (Record, Fake)) else sailing).items():
            _merged36[_k] = _v
        expect(decide(snapshot(Fake(**_merged36)))).to_match_object(Fake(**{'kind': 'equip'}))
        _merged37 = {}
        for _k, _v in (sailing._fields if isinstance(sailing, (Record, Fake)) else sailing).items():
            _merged37[_k] = _v
        for _k, _v in {'worn_ids': set([DS_ID.SHIELD])}.items():
            _merged37[_k] = _v
        expect(decide(snapshot(Fake(**_merged37)))).to_match_object(Fake(**{'kind': 'custom'}))
        expect(decide(snapshot(sailing))).to_match_object(Fake(**{'kind': 'talk', 'stop': Fake(**{'npc': 'Duke Horacio'})}))
    test('the shield is aboard before the ship sails', _fn34)

    def _fn38():
        step = decide(snapshot(Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.NED_GIVEN_MAP, 'flags': set()}), 'tile': Fake(**{'x': 3047, 'z': 3208, 'level': 1})})))
        expect(step).to_match_object(Fake(**{'kind': 'custom'}))
    test('boarding is not re-gated once the bot is already aboard', _fn38)

    def _fn39():
        step = decide(snapshot(Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.NED_GIVEN_MAP, 'flags': set()}), 'worn_ids': set([DS_ID.SHIELD]), 'inv': {_k: _v for _k, _v in [['trout', 2]]}, 'bank': {_k: _v for _k, _v in [['trout', 100]]}})))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        items = step.items
        expect(items[0]['qty']).to_be_greater_than(10)
    test('a full larder is drawn before the ship sails', _fn39)

    def _fn40():
        step = decide(snapshot(Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.NED_GIVEN_MAP, 'flags': set()}), 'banked': [DS_ID.SHIELD], 'bank': {_k: _v for _k, _v in [['trout', 100]]}})))
        items = step.items
        expect([i['name'] for i in items]).to_equal([DS_ITEM.SHIELD])
    test('the shield is fetched before the larder', _fn40)

    def _fn41():
        landed = Fake(**{'x': 2851, 'z': 3235, 'level': 0})
        shut = decide(snapshot(Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.SAILED_TO_CRANDOR, 'flags': set()}), 'worn_ids': set([DS_ID.SHIELD]), 'tile': landed})))
        expect(shut.name).to_contain('secret passage')
        open = decide(snapshot(Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.SAILED_TO_CRANDOR, 'flags': set(['secret-passage'])}), 'worn_ids': set([DS_ID.SHIELD]), 'tile': landed})))
        expect(open.name).to_contain('Elvarg')
    test('the secret passage is opened before Elvarg is fought', _fn41)

    def _fn42():
        dead = Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.SAILED_TO_CRANDOR, 'flags': set(['secret-passage'])}), 'tile': Fake(**{'x': 3222, 'z': 3218, 'level': 0})})
        expect(decide(snapshot(dead))).to_match_object(Fake(**{'kind': 'talk', 'stop': Fake(**{'npc': 'Duke Horacio'})}))
        _merged43 = {}
        for _k, _v in (dead._fields if isinstance(dead, (Record, Fake)) else dead).items():
            _merged43[_k] = _v
        for _k, _v in {'worn_ids': set([DS_ID.SHIELD])}.items():
            _merged43[_k] = _v
        shielded = decide(snapshot(Fake(**_merged43)))
        expect(shielded).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(shielded.items[0]['name']).to_be('Coins')
        _merged44 = {}
        for _k, _v in (dead._fields if isinstance(dead, (Record, Fake)) else dead).items():
            _merged44[_k] = _v
        for _k, _v in {'worn_ids': set([DS_ID.SHIELD]), 'inv': {_k: _v for _k, _v in [['coins', 5000], ['trout', 18]]}}.items():
            _merged44[_k] = _v
        ready = decide(snapshot(Fake(**_merged44)))
        expect(ready.name).to_contain('Elvarg')
    test('a death on Crandor re-kits at the bank before walking back', _fn42)

    def _fn45():
        expect(decide(snapshot(Fake(**{'journal': 'complete'}))).kind).to_be('done')
    test('a complete journal ends the quest whatever the snapshot says', _fn45)

    def _fn46():
        expect(decide(snapshot(Fake(**{'progress': None})))).to_match_object(Fake(**{'kind': 'wait'}))
    test('an unreadable journal waits rather than guessing', _fn46)
describe('Dragon Slayer decide()', _fn16)

def _fn47():
    CHARMS = [DS_ID.LOBSTER_POT, DS_ID.MIND_BOMB, DS_ID.UNFIRED_BOWL, DS_ID.SILK]
    after_maze = [DS_ID.MAZE_KEY, DS_ID.MAP_MELZAR]
    boat = Fake(**{'progress': Fake(**{'stage': DRAGON_STAGE.BOUGHT_SHIP, 'flags': set()})})

    def _fn48():
        step = decide(snapshot(Fake(**{'carried': after_maze})))
        expect(step).to_match_object(Fake(**{'kind': 'buy', 'item': DS_ITEM.LOBSTER_POT}))
    test("the Oracle's charms are bought only once her piece is next", _fn48)

    def _fn49():
        step = decide(snapshot(Fake(**{'carried': after_maze, 'banked': CHARMS})))
        expect(step.kind).to_be('withdraw')
        ids = [i['id'] for i in step.items]
        expect(ids).to_equal(CHARMS)
    test('charms in the bank are withdrawn before any counter', _fn49)

    def _fn50():
        expect(decide(snapshot(Fake(**{'carried': after_maze, 'bank_known': False})))).to_match_object(Fake(**{'kind': 'scan_bank'}))
    test('an unread bank is scanned before a charm is bought', _fn50)

    def _fn51():
        held = Fake(**{'carried': list(after_maze) + list(CHARMS)})
        expect(decide(snapshot(held))).to_match_object(Fake(**{'kind': 'talk', 'stop': Fake(**{'npc': 'Oracle'})}))
        _merged52 = {}
        for _k, _v in (held._fields if isinstance(held, (Record, Fake)) else held).items():
            _merged52[_k] = _v
        for _k, _v in {'flags': ['asked-oracle']}.items():
            _merged52[_k] = _v
        asked = decide(snapshot(Fake(**_merged52)))
        expect(asked.name).to_contain('chest under Ice Mountain')
    test('holding every charm asks the Oracle, then opens her door', _fn51)

    def _fn53():
        step = decide(snapshot(Fake(**{'carried': after_maze, 'tile': Fake(**{'x': 3057, 'z': 9842, 'level': 0})})))
        expect(step.name).to_contain('chest under Ice Mountain')
    test('past the magic door the chest comes before any shopping', _fn53)

    def _fn55(_arg56):
        held = Fake(**{k: v for k, v in _arg56._fields.items() if k != 'label'})
        _merged57 = {}
        for _k, _v in (held._fields if isinstance(held, (Record, Fake)) else held).items():
            _merged57[_k] = _v
        for _k, _v in {'tile': Fake(**{'x': 3056, 'z': 9841, 'level': 0})}.items():
            _merged57[_k] = _v
        step = decide(snapshot(Fake(**_merged57)))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'leave the oracle chest room'}))
    test_each([Fake(**{'label': 'coins for Wormbrain', 'carried': list(after_maze) + [DS_ID.MAP_ORACLE]}), Fake(**{'label': 'a banked maze key', 'carried': [DS_ID.MAP_MELZAR, DS_ID.MAP_ORACLE], 'banked': [DS_ID.MAZE_KEY]}), Fake(**{'label': 'an unread bank', 'carried': [DS_ID.MAP_ORACLE], 'bank_known': False}), Fake(**{'label': 'the Oziach briefing', 'carried': [DS_ID.MAP_ORACLE], 'flags': ['needs-briefing']}), Fake(**{'label': 'joining the map', 'carried': list(after_maze) + [DS_ID.MAP_ORACLE, DS_ID.MAP_WORMBRAIN]})])('leaves the chest room before $label after looting', _fn55)

    def _fn58():
        step = decide(snapshot(Fake(**{'carried': list(after_maze) + [DS_ID.MAP_ORACLE], 'tile': Fake(**{'x': 3050, 'z': 9840, 'level': 0})})))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw', 'items': [Fake(**{'name': 'Coins'})]}))
    test('withdraws coins once the map piece is west of the magic door', _fn58)

    def _fn59():
        _merged60 = {}
        for _k, _v in {'carried': [DS_ID.MAP]}.items():
            _merged60[_k] = _v
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged60[_k] = _v
        expect(decide(snapshot(Fake(**_merged60)))).to_match_object(Fake(**{'kind': 'buy', 'item': DS_ITEM.HAMMER}))
    test('the hammer is bought before the anvil is visited', _fn59)

    def _fn61():
        _merged62 = {}
        for _k, _v in {'carried': [DS_ID.MAP, DS_ID.HAMMER, NAILS]}.items():
            _merged62[_k] = _v
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged62[_k] = _v
        step = decide(snapshot(Fake(**_merged62)))
        expect(step.name).to_contain('fetch 3 planks')
    test('planks are fetched after the nails and before the patch', _fn61)

    def _fn63():
        graveyard = Fake(**{'x': 3171, 'z': 3680, 'level': 0})
        _merged64 = {}
        for _k, _v in {'carried': [DS_ID.MAP, DS_ID.HAMMER, NAILS, DS_ID.PLANK], 'tile': graveyard}.items():
            _merged64[_k] = _v
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged64[_k] = _v
        step = decide(snapshot(Fake(**_merged64)))
        expect(step.name).to_contain('fetch 2 planks')
        _merged65 = {}
        for _k, _v in {'carried': [DS_ID.MAP, DS_ID.HAMMER, NAILS, [DS_ID.PLANK, 2]], 'tile': graveyard}.items():
            _merged65[_k] = _v
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged65[_k] = _v
        last = decide(snapshot(Fake(**_merged65)))
        expect(last.name).to_be('fetch 1 plank')
    test('a plank trip is finished before the hull is patched', _fn63)

    def _fn66():
        _merged67 = {}
        for _k, _v in {'carried': [DS_ID.MAP], 'bank_known': False}.items():
            _merged67[_k] = _v
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged67[_k] = _v
        expect(decide(snapshot(Fake(**_merged67)))).to_match_object(Fake(**{'kind': 'scan_bank'}))
    test('an unread bank is scanned before a hull supply is bought', _fn66)

    def _fn68():
        _merged69 = {}
        for _k, _v in {'carried': [DS_ID.MAP, NAILS], 'tile': Fake(**{'x': 3047, 'z': 3208, 'level': 1})}.items():
            _merged69[_k] = _v
        for _k, _v in (boat._fields if isinstance(boat, (Record, Fake)) else boat).items():
            _merged69[_k] = _v
        step = decide(snapshot(Fake(**_merged69)))
        expect(step.name).to_be('go ashore')
    test('aboard with a hull supply still to fetch, the bot goes ashore first', _fn68)
describe('Dragon Slayer sources its own shopping at the point of use', _fn47)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/fishingcontest.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.fishingcontest.areas import FC_ID, FC_TILE, in_compound, nearest_dwarf, nearest_spade
from rs2004.quests.defs.fishingcontest import decide, fishingcontest
from rs2004.quests.defs.fishingcontest.journal import FC_STAGE
from rs2004.quests.defs.fishingcontest.supplies import ENTRY_FEE, WORM_TARGET
def id_map(counts):
    return {_k: _v for _k, _v in [[int(id), n] for id, n in list(counts.items())]}


READY = Obj({
    FC_ID.PASS: 1,
    FC_ID.GARLIC: 1,
    FC_ID.FISHING_ROD: 1,
    FC_ID.SPADE: 1,
    FC_ID.RED_VINE_WORM: WORM_TARGET,
    FC_ID.COINS: 500,
})


def snap(options=None):
    if options is None:
        options = Obj({})
    stage = (options.stage if options.stage is not None else FC_STAGE.STARTED)
    return Obj({
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {},
        'inv_ids': id_map((options.inv if options.inv is not None else Obj({}))),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'bank': {},
        'bank_ids': id_map((options.bank if options.bank is not None else Obj({}))),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'free_slots': 26,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def without(id):
    _merged2 = {}
    for _k, _v in (READY._fields if isinstance(READY, Obj) else READY).items():
        _merged2[_k] = _v
    pack = Obj(_merged2)
    pack._fields.pop(id, None)
    return pack


def _fn3():
    def _fn4():
        expect(decide(snap(Obj({'journal': 'unknown'})))).to_equal(Obj({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list is still loading', _fn4)

    def _fn5():
        expect(decide(snap(Obj({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn5)

    def _fn6():
        _merged7 = {}
        for _k, _v in (snap()._fields if isinstance(snap(), Obj) else snap()).items():
            _merged7[_k] = _v
        for _k, _v in {'stage': None}.items():
            _merged7[_k] = _v
        unreadable = Obj(_merged7)
        expect(decide(unreadable).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unreadable', _fn6)

    def _fn8():
        expect(decide(snap(Obj({'stage': FC_STAGE.NOT_STARTED, 'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before believing it has to fetch anything', _fn8)


describe('Fishing Contest decide', _fn3)


def _fn9():
    def _fn10():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.NOT_STARTED}))))).to_be("take garlic from Morgan's cupboard")
    test('fetches the garlic before walking to the dwarf, since Draynor is on the way out', _fn10)

    def _fn11():
        step = decide(snap(Obj({'stage': FC_STAGE.NOT_STARTED, 'bank': Obj({FC_ID.GARLIC: 1})})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['id']).to_be(FC_ID.GARLIC)
    test('takes a banked clove rather than climbing to the cupboard', _fn11)

    def _fn12():
        step = decide(snap(Obj({'stage': FC_STAGE.NOT_STARTED, 'inv': Obj({FC_ID.GARLIC: 1})})))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be('Spade')
    test('picks the spade up on the way past Falador', _fn12)

    def _fn13():
        step = decide(snap(Obj({'stage': FC_STAGE.NOT_STARTED, 'inv': Obj({FC_ID.GARLIC: 1, FC_ID.SPADE: 1})})))
        expect(custom_name(step)).to_be('ask the Mountain Dwarf for the competition pass')
    test('starts the quest once the Draynor and Falador legs are done', _fn13)


describe('Fishing Contest before the pass', _fn9)


def _fn14():
    def _fn15():
        expect(custom_name(decide(snap(Obj({'inv': without(FC_ID.PASS)}))))).to_be('ask the dwarf for another competition pass')
    test('asks the dwarf for a replacement when the pass is in neither pack nor bank', _fn15)

    def _fn16():
        step = decide(snap(Obj({'inv': without(FC_ID.FISHING_ROD)})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Harry')
    test('buys the rod from Harry when none is banked', _fn16)

    def _fn17():
        _merged18 = {}
        for _k, _v in (READY._fields if isinstance(READY, Obj) else READY).items():
            _merged18[_k] = _v
        for _k, _v in {FC_ID.RED_VINE_WORM: 2}.items():
            _merged18[_k] = _v
        expect(custom_name(decide(snap(Obj({'inv': Obj(_merged18)}))))).to_be(f'dig {WORM_TARGET - 2} red vine worm(s)')
    test('digs worms up to the target when the pack is short', _fn17)

    def _fn19():
        _merged20 = {}
        for _k, _v in (without(FC_ID.SPADE)._fields if isinstance(without(FC_ID.SPADE), Obj) else without(FC_ID.SPADE)).items():
            _merged20[_k] = _v
        for _k, _v in {FC_ID.RED_VINE_WORM: 0}.items():
            _merged20[_k] = _v
        pack = Obj(_merged20)
        step = decide(snap(Obj({'inv': pack})))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be('Spade')
    test('fetches a spade before the worms, since the dig needs one', _fn19)

    def _fn21():
        _merged22 = {}
        for _k, _v in (READY._fields if isinstance(READY, Obj) else READY).items():
            _merged22[_k] = _v
        for _k, _v in {FC_ID.COINS: ENTRY_FEE - 1}.items():
            _merged22[_k] = _v
        step = decide(snap(Obj({'inv': Obj(_merged22), 'bank': Obj({FC_ID.COINS: 2000000})})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['id']).to_be(FC_ID.COINS)
    test('withdraws coins when the pack cannot cover the entry fee', _fn21)

    def _fn23():
        expect(custom_name(decide(snap(Obj({'inv': READY}))))).to_be('pay Bonzo the contest entry fee')
    test('pays Bonzo once everything is carried', _fn23)


describe('Fishing Contest supplies', _fn14)


def _fn24():
    def _fn25():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.IN_COMP, 'inv': READY}))))).to_be('stash the garlic in the wall pipe')
    test('never fishes the willow spot — it stashes the garlic instead', _fn25)

    def _fn26():
        _merged27 = {}
        for _k, _v in (without(FC_ID.GARLIC)._fields if isinstance(without(FC_ID.GARLIC), Obj) else without(FC_ID.GARLIC)).items():
            _merged27[_k] = _v
        for _k, _v in {FC_ID.RAW_SARDINE: 2}.items():
            _merged27[_k] = _v
        pack = Obj(_merged27)
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.IN_COMP, 'inv': pack}))))).to_be('hand the sardines to Bonzo and re-enter')
    test('unwinds a round already fished at the willow spot by handing the sardines over', _fn26)

    def _fn28():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.IN_COMP, 'inv': without(FC_ID.GARLIC)}))))).to_be("take garlic from Morgan's cupboard")
    test('re-sources garlic at the willow spot when there is neither clove nor catch', _fn28)

    def _fn29():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.GARLIC_COMP, 'inv': READY}))))).to_be('fish the contest beside the pipes')
    test('fishes the pipes spot once the stranger has moved', _fn29)

    def _fn30():
        _merged31 = {}
        for _k, _v in (READY._fields if isinstance(READY, Obj) else READY).items():
            _merged31[_k] = _v
        for _k, _v in {FC_ID.RED_VINE_WORM: 1, FC_ID.RAW_GIANT_CARP: 2}.items():
            _merged31[_k] = _v
        pack = Obj(_merged31)
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.GARLIC_COMP, 'inv': pack}))))).to_be('fish the contest beside the pipes')
    test('keeps fishing on a half-spent pack rather than walking out to restock', _fn30)

    def _fn32():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.GARLIC_COMP, 'inv': without(FC_ID.PASS)}))))).to_be('ask the dwarf for another competition pass')
    test('gets the pass back before walking into a contest it has already paid for', _fn32)

    def _fn33():
        _merged34 = {}
        for _k, _v in (READY._fields if isinstance(READY, Obj) else READY).items():
            _merged34[_k] = _v
        for _k, _v in {FC_ID.RED_VINE_WORM: 0}.items():
            _merged34[_k] = _v
        pack = Obj(_merged34)
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.GARLIC_COMP, 'inv': pack}))))).to_be(f'dig {WORM_TARGET} red vine worm(s)')
    test('restocks worms mid-contest only once the last one is spent', _fn33)


describe('Fishing Contest inside the contest', _fn24)


def _fn35():
    def _fn36():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.WON_COMP, 'inv': Obj({FC_ID.TROPHY: 1})}))))).to_be('take the trophy to the Mountain Dwarf')
    test('carries the trophy to the dwarf', _fn36)

    def _fn37():
        step = decide(snap(Obj({'stage': FC_STAGE.WON_COMP, 'bank': Obj({FC_ID.TROPHY: 1})})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['id']).to_be(FC_ID.TROPHY)
    test('takes a banked trophy rather than asking Bonzo for a spare', _fn37)

    def _fn38():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.WON_COMP}))))).to_be('ask the dwarf for another competition pass')
    test('needs the pass back before it can walk in for a spare trophy', _fn38)

    def _fn39():
        expect(custom_name(decide(snap(Obj({'stage': FC_STAGE.WON_COMP, 'inv': Obj({FC_ID.PASS: 1})}))))).to_be('ask Bonzo for a spare trophy')
    test('asks Bonzo for a spare trophy once the pass is in hand', _fn39)


describe('Fishing Contest after the win', _fn35)


def _fn40():
    def _fn41():
        expect(in_compound(Obj({'x': 2630, 'z': 3435, 'level': 0}))).to_be(True)
        expect(in_compound(Obj({'x': 2637, 'z': 3444, 'level': 0}))).to_be(True)
        expect(in_compound(FC_TILE.PIPE_STAND)).to_be(True)
        expect(in_compound(FC_TILE.GATE_INSIDE)).to_be(True)
    test('the fenced competition ground holds both fishing spots and the pipes', _fn41)

    def _fn42():
        expect(in_compound(FC_TILE.GATE_OUTSIDE)).to_be(False)
        expect(in_compound(Obj({'x': 2643, 'z': 3440, 'level': 0}))).to_be(False)
        expect(in_compound(None)).to_be(False)
    test('Morris and the gate stand outside it, so the crossing is never skipped', _fn42)

    def _fn43():
        expect(nearest_dwarf(Obj({'x': 2900, 'z': 3480, 'level': 0}))).to_be(FC_TILE.DWARF_EAST)
        expect(nearest_dwarf(Obj({'x': 2800, 'z': 3480, 'level': 0}))).to_be(FC_TILE.DWARF_WEST)
        expect(nearest_dwarf(None)).to_be(FC_TILE.DWARF_EAST)
    test('picks the tunnel mouth on the side the bot is standing', _fn43)

    def _fn44():
        expect(nearest_spade(Obj({'x': 3000, 'z': 3370, 'level': 0}))).to_be(FC_TILE.SPADE_FALADOR)
        expect(nearest_spade(FC_TILE.GATE_OUTSIDE)).to_be(FC_TILE.SPADE_ARDOUGNE)
        # Catherby: Falador is 146 tiles away and Edmond's 261, but only Edmond's avoids the ridge.
        expect(nearest_spade(Obj({'x': 2835, 'z': 3445, 'level': 0}))).to_be(FC_TILE.SPADE_ARDOUGNE)
        expect(nearest_spade(None)).to_be(FC_TILE.SPADE_FALADOR)
    test('takes the spade on its own side of the mountain, not the one that is nearer as the crow flies', _fn44)


describe('Fishing Contest map', _fn40)


def _fn45():
    def _fn46():
        expect(fishingcontest.record.items).to_equal([])
    test('lists no required items, so an empty bank cannot block the start', _fn46)

    def _fn47():
        for tool in ['fishing pass', 'garlic', 'fishing rod', 'spade', 'red vine worm', 'fishing trophy', 'coins']:
            expect(fishingcontest.tools).to_contain(tool)
    test('keeps every quest item off the deposit list', _fn47)

    def _fn48():
        expect(fishingcontest.bank).to_be('nearest')
    test('banks wherever it happens to be, since the quest spans two kingdoms', _fn48)


describe('Fishing Contest module', _fn45)

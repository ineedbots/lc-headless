"""rs2b0t's test/api/ai/quests/defs/tbwt.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs import QUEST_DEFS
from rs2004.quests.defs.tbwt import decide, tbwt
from rs2004.quests.defs.tbwt.areas import TB_ARMOUR, TB_ID, TB_LUBUFU, TB_MAIN, TB_NAME, TB_POTIONS, TB_SPEARS, TB_TAMAYU, TB_TIADECHE, TB_TINSAY
from rs2004.quests.defs.tbwt.journal import TB_FLAG

VILLAGE = Record({'x': 2780, 'z': 3087, 'level': 0})
IRON = TB_SPEARS[0]
STEEL = TB_SPEARS[1]
DOSE4 = TB_POTIONS[0]
DOSE2 = TB_POTIONS[2]
KIT = ['Maple shortbow', 'Adamant arrow'] + list(TB_ARMOUR)
FULL_PACK = [
    [TB_ID.COINS, 500],
    [TB_ID.NET, 1],
    [TB_ID.KNIFE, 1],
    [TB_ID.PESTLE, 1],
    [TB_ID.TINDERBOX, 1],
    [TB_ID.SEAWEED, 1],
    [IRON.id, 1],
    [DOSE4.id, 1],
]


def snap(options=None):
    if options is None:
        options = Record({})
    main = (options.main if options.main is not None else TB_MAIN.STARTED)
    flags = set([
        f'{TB_FLAG.LUBUFU}:{(options.lubufu if options.lubufu is not None else TB_LUBUFU.UNKNOWN)}',
        f'{TB_FLAG.TIADECHE}:{(options.tiadeche if options.tiadeche is not None else TB_TIADECHE.UNKNOWN)}',
        f'{TB_FLAG.TAMAYU}:{(options.tamayu if options.tamayu is not None else TB_TAMAYU.UNKNOWN)}',
        f'{TB_FLAG.TINSAY}:{(options.tinsay if options.tinsay is not None else TB_TINSAY.UNKNOWN)}',
    ])
    if options.agility:
        flags.add(TB_FLAG.AGILITY)
    if options.spear:
        flags.add(TB_FLAG.SPEAR)
    ids = {_k: _v for _k, _v in (((options.inv_ids if options.inv_ids is not None else [])) if options.bare else list(FULL_PACK) + list(((options.inv_ids if options.inv_ids is not None else []))))}
    inv = {_k: _v for _k, _v in ([] if options.bare else [[TB_NAME.COINS.lower(), 500], ['lobster', 6]])}
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if main == TB_MAIN.NOT_STARTED else 'in_progress'))),
        'inv': inv,
        'inv_ids': ids,
        'worn': set(([] if options.bare else [n.lower() for n in KIT])),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': main,
        'progress': QuestProgress(main, flags),
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'tile': (options.tile if options.tile is not None else VILLAGE),
        'free_slots': (options.free_slots if options.free_slots is not None else 12),
        'ranged': 70,
    })


def step(options=None):
    if options is None:
        options = Record({})
    return decide(snap(options))


def named(s):
    return ((s.name if s.kind == 'custom' else f"{s.kind}:{(s.reason if s.kind == 'wait' else '')}"))


PAST_TAMAYU = Record({'lubufu': TB_LUBUFU.COMPLETE, 'tiadeche': TB_TIADECHE.REQUEST_MANUAL})
PAST_TINSAY = Record({
    'lubufu': TB_LUBUFU.COMPLETE,
    'tiadeche': TB_TIADECHE.REQUEST_MANUAL,
    'tamayu': TB_TAMAYU.COMPLETE,
    'agility': True,
    'spear': True,
})


def _fn1():
    def _fn2():
        expect(step(Record({'journal': 'unknown'}))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('an unloaded quest list waits rather than restarting the quest', _fn2)

    def _fn3():
        expect(step(Record({'journal': 'complete', 'main': TB_MAIN.COMPLETE}))).to_equal(Record({'kind': 'done'}))
    test('a green journal is done', _fn3)

    def _fn4():
        for main in [TB_MAIN.NOT_STARTED, TB_MAIN.SPOKE, TB_MAIN.ASKED_FOR_HELP]:
            expect(named(step(Record({'main': main})))).to_be('ask Timfraku for the job')
    test('every pre-start stage goes back to Timfraku', _fn4)

    def _fn5():
        expect(named(step(Record({'main': TB_MAIN.ALL_BROTHERS})))).to_be("claim Timfraku's reward")
        expect(named(step(Record({'main': TB_MAIN.GOLD})))).to_be("claim Timfraku's reward")
    test('the reward is claimed once all four brothers are done', _fn5)

    # Why: the hunt teleports the player into a sealed pocket, and a step that walks from there has no route.
    def _fn6():
        expect(step(Record({'tile': Record({'x': 2520, 'z': 4568, 'level': 0})}))).to_equal(Record({'kind': 'wait', 'reason': 'watching Tamayu hunt the Shaikahan'}))
    test('nothing is attempted from inside the hunt cutscene', _fn6)

    def _fn7():
        expect(step(Record({'bare': True})).kind).not_.to_be('custom')
    test('a bare pack is filled before any brother is walked to', _fn7)

    # Why: Timfraku sits across a 30gp ferry, and a bot that walks first arrives with nothing and no fare home.
    def _fn8():
        expect(step(Record({'main': TB_MAIN.NOT_STARTED, 'bare': True})).kind).not_.to_be('custom')
        expect(named(step(Record({'main': TB_MAIN.NOT_STARTED})))).to_be('ask Timfraku for the job')
    test('the pack is filled before the first crossing, not after it', _fn8)

    def _fn9():
        def _fn10():
            expect(named(step())).to_be('introduce yourself to Lubufu')
        test('an unmet Lubufu is introduced to first', _fn10)

        def _fn11():
            expect(named(step(Record({'lubufu': TB_LUBUFU.FETCH_KARAMBWANJI})))).to_be('net Karambwanji (0/20)')
        test('the bait is netted while he is still owed some', _fn11)

        def _fn12():
            expect(named(step(Record({'lubufu': TB_LUBUFU.FETCH_KARAMBWANJI, 'inv_ids': [[TB_ID.RAW_KARAMBWANJI, 20]]})))).to_be('hand Lubufu 20 of the 20 Karambwanji he still wants')
        test('a full load is handed over rather than topped up', _fn12)

        # Why: he counts them in himself, so a part load is progress and the pack never has to hold all twenty.
        def _fn13():
            expect(named(step(Record({'lubufu': TB_LUBUFU.FETCH_KARAMBWANJI, 'inv_ids': [[TB_ID.RAW_KARAMBWANJI, 11]], 'free_slots': 0})))).to_be('hand Lubufu 11 of the 20 Karambwanji he still wants')
        test('a part load goes over as soon as the pack is out of room', _fn13)

        def _fn14():
            expect(named(step(Record({'lubufu': TB_LUBUFU.FETCH_KARAMBWANJI + 14})))).to_be('net Karambwanji (0/6)')
        test('the count he already holds is deducted from what is owed', _fn14)

        def _fn15():
            expect(named(step(Record({'lubufu': TB_LUBUFU.GIVEN_KARAMBWANJI})))).to_be("take up Lubufu's apprenticeship")
        test('a full hand-in moves on to the apprenticeship', _fn15)
    describe('Lubufu', _fn9)

    def _fn16():
        done = Record({'lubufu': TB_LUBUFU.COMPLETE, 'inv_ids': [[TB_ID.VESSEL, 1]]})

        def _fn17():
            expect(named(step(done))).to_be('bring Tiadeche the news')
        test('the news comes before the vessel', _fn17)

        def _fn18():
            _merged19 = {}
            for _k, _v in (done._fields if isinstance(done, Record) else done).items():
                _merged19[_k] = _v
            for _k, _v in {'tiadeche': TB_TIADECHE.RETURN_WHEN_CAUGHT}.items():
                _merged19[_k] = _v
            expect(named(step(Record(_merged19)))).to_be('net a Karambwanji for bait')
            _merged20 = {}
            for _k, _v in (done._fields if isinstance(done, Record) else done).items():
                _merged20[_k] = _v
            for _k, _v in {'tiadeche': TB_TIADECHE.RETURN_WHEN_CAUGHT, 'inv_ids': [[TB_ID.VESSEL, 1], [TB_ID.RAW_KARAMBWANJI, 1]]}.items():
                _merged20[_k] = _v
            expect(named(step(Record(_merged20)))).to_be('bait the Karambwan vessel')
        test('a vessel with no bait is baited first', _fn18)

        def _fn21():
            expect(named(step(Record({'lubufu': TB_LUBUFU.COMPLETE, 'tiadeche': TB_TIADECHE.RETURN_WHEN_CAUGHT})))).to_be('ask Lubufu for another Karambwan vessel')
        test('a lost vessel is re-issued by Lubufu', _fn21)

        def _fn22():
            expect(named(step(Record({
        'lubufu': TB_LUBUFU.COMPLETE,
        'tiadeche': TB_TIADECHE.RETURN_WHEN_CAUGHT,
        'inv_ids': [[TB_ID.VESSEL_LOADED, 1]],
    })))).to_be('hand Tiadeche the baited vessel')
        test('a baited vessel is handed over', _fn22)

        def _fn23():
            expect(named(step(Record({'lubufu': TB_LUBUFU.COMPLETE, 'tiadeche': TB_TIADECHE.CAUGHT})))).to_be('ask Tiadeche what he needs next')
        test('a catch he has not been asked about yet is picked back up in conversation', _fn23)
    describe("Tiadeche's catch", _fn16)

    def _fn24():
        def _fn25():
            _merged26 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged26[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.SLAY_SHAIKAHAN}.items():
                _merged26[_k] = _v
            expect(named(step(Record(_merged26)))).to_be("watch Tamayu's hunt")
        test('the hunt is watched before anything is handed over', _fn25)

        def _fn27():
            _merged28 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged28[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.WATCHED_CUTSCENE}.items():
                _merged28[_k] = _v
            expect(named(step(Record(_merged28)))).to_be(f'give Tamayu the {DOSE4.name}')
        test('the agility potion goes first', _fn27)

        # Why: he counts doses rather than bottles, and the journal only says so at the fourth.
        def _fn29():
            _merged30 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged30[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.WATCHED_CUTSCENE}.items():
                _merged30[_k] = _v
            base = Record(_merged30)
            _merged31 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged31[_k] = _v
            for _k, _v in {'inv_ids': [[DOSE4.id, 0], [DOSE2.id, 2]]}.items():
                _merged31[_k] = _v
            expect(named(step(Record(_merged31)))).to_be(f'give Tamayu the {DOSE2.name}')
        test('a part-doses pack pours what it has, one bottle per pass', _fn29)

        # Why: Tiadeche's gift is the raw Karambwan the poison is ground from, which is why his leg runs first.
        def _fn32():
            _merged33 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged33[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.WATCHED_CUTSCENE, 'agility': True}.items():
                _merged33[_k] = _v
            base = Record(_merged33)
            _merged34 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged34[_k] = _v
            for _k, _v in {'inv_ids': [[TB_ID.RAW_KARAMBWAN, 1]]}.items():
                _merged34[_k] = _v
            expect(named(step(Record(_merged34)))).to_be('cook the Karambwan on the jungle fire')
            _merged35 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged35[_k] = _v
            for _k, _v in {'inv_ids': [[TB_ID.POORLY_COOKED_KARAMBWAN, 1]]}.items():
                _merged35[_k] = _v
            expect(named(step(Record(_merged35)))).to_be('grind the cooked Karambwan into poison')
            _merged36 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged36[_k] = _v
            for _k, _v in {'inv_ids': [[TB_ID.KARAMBWAN_POISON_PASTE, 1]]}.items():
                _merged36[_k] = _v
            expect(named(step(Record(_merged36)))).to_be('smear the Karambwan paste over the iron spear')
            _merged37 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged37[_k] = _v
            for _k, _v in {'inv_ids': [[IRON.kp_id, 1]]}.items():
                _merged37[_k] = _v
            expect(named(step(Record(_merged37)))).to_be('give Tamayu the Karambwan-poisoned spear')
        test('the poisoned spear is built from the Karambwan he was given', _fn32)

        # Why: any tier above bronze sets both bits Tamayu checks, so whatever the bank had is what he gets.
        def _fn38():
            _merged39 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged39[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.WATCHED_CUTSCENE, 'agility': True}.items():
                _merged39[_k] = _v
            base = Record(_merged39)
            _merged40 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged40[_k] = _v
            for _k, _v in {'inv_ids': [[IRON.id, 0], [STEEL.id, 1], [TB_ID.KARAMBWAN_POISON_PASTE, 1]]}.items():
                _merged40[_k] = _v
            expect(named(step(Record(_merged40)))).to_be('smear the Karambwan paste over the steel spear')
            _merged41 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged41[_k] = _v
            for _k, _v in {'inv_ids': [[IRON.id, 0], [STEEL.kp_id, 1]]}.items():
                _merged41[_k] = _v
            expect(named(step(Record(_merged41)))).to_be('give Tamayu the Karambwan-poisoned spear')
        test('whichever tier the pack carries is the one poisoned and handed over', _fn38)

        # Why: no shop on Karamja sells a spear, and Jogres drop one 4 times in 129.
        def _fn42():
            _merged43 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged43[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.WATCHED_CUTSCENE, 'agility': True}.items():
                _merged43[_k] = _v
            base = Record(_merged43)
            _merged44 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged44[_k] = _v
            for _k, _v in {'inv_ids': [[IRON.id, 0], [TB_ID.KARAMBWAN_POISON_PASTE, 1]]}.items():
                _merged44[_k] = _v
            expect(named(step(Record(_merged44)))).to_be('hunt Jogres for a spear')
        test('a pack with the poison and no shaft hunts Jogres for one', _fn42)

        # Why: the shoal is 160 tiles from the bait, and three Karambwan in ten burn on the fire.
        def _fn45():
            _merged46 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged46[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.WATCHED_CUTSCENE, 'agility': True}.items():
                _merged46[_k] = _v
            base = Record(_merged46)
            expect(named(step(base))).to_be('net bait for the Karambwan shoal')
            _merged47 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged47[_k] = _v
            for _k, _v in {'inv_ids': [[TB_ID.RAW_KARAMBWANJI, 4]]}.items():
                _merged47[_k] = _v
            expect(named(step(Record(_merged47)))).to_be('ask Lubufu for another Karambwan vessel')
            _merged48 = {}
            for _k, _v in (base._fields if isinstance(base, Record) else base).items():
                _merged48[_k] = _v
            for _k, _v in {'inv_ids': [[TB_ID.RAW_KARAMBWANJI, 4], [TB_ID.VESSEL, 1]]}.items():
                _merged48[_k] = _v
            expect(named(step(Record(_merged48)))).to_be('lower the vessel for a Karambwan')
        test('spare bait is carried to the shoal so a burn is re-cooked from the same trip', _fn45)

        def _fn49():
            _merged50 = {}
            for _k, _v in (PAST_TAMAYU._fields if isinstance(PAST_TAMAYU, Record) else PAST_TAMAYU).items():
                _merged50[_k] = _v
            for _k, _v in {'tamayu': TB_TAMAYU.WATCHED_CUTSCENE, 'agility': True, 'spear': True}.items():
                _merged50[_k] = _v
            expect(named(step(Record(_merged50)))).to_be('follow Tamayu on the killing hunt')
        test('with both gifts given the hunt becomes the kill', _fn49)
    describe('Tamayu', _fn24)

    def _fn51():
        def _fn52():
            _merged53 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged53[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_RUM}.items():
                _merged53[_k] = _v
            expect(named(step(Record(_merged53)))).to_be('pick a banana in the plantation')
            _merged54 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged54[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_RUM, 'inv_ids': [[TB_ID.BANANA, 1]]}.items():
                _merged54[_k] = _v
            expect(named(step(Record(_merged54)))).to_be('slice the banana')
            _merged55 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged55[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_RUM, 'inv_ids': [[TB_ID.SLICED_BANANA, 1]]}.items():
                _merged55[_k] = _v
            expect(named(step(Record(_merged55)))).to_be('buy Karamjan rum from Zambo')
            _merged56 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged56[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_RUM, 'inv_ids': [[TB_ID.SLICED_BANANA, 1], [TB_ID.RUM, 1]]}.items():
                _merged56[_k] = _v
            expect(named(step(Record(_merged56)))).to_be('drop the banana slices into the rum')
            _merged57 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged57[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_RUM, 'inv_ids': [[TB_ID.RUM_SLICED, 1]]}.items():
                _merged57[_k] = _v
            expect(named(step(Record(_merged57)))).to_be('give Tinsay the sliced banana in Karamjan rum')
        test('the rum is built banana, slice, bottle', _fn52)

        def _fn58():
            _merged59 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged59[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.GIVEN_RUM}.items():
                _merged59[_k] = _v
            expect(named(step(Record(_merged59)))).to_be('ask Tinsay what he needs next')
            _merged60 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged60[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.GIVEN_SANDWICH}.items():
                _merged60[_k] = _v
            expect(named(step(Record(_merged60)))).to_be('ask Tinsay what he needs next')
        test('a handed-over item is followed by asking what he wants next', _fn58)

        # Why: nobody else on Karamja skins a monkey, and Tamayu only does it once his own hunt is over.
        def _fn61():
            _merged62 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged62[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_SANDWICH}.items():
                _merged62[_k] = _v
            expect(named(step(Record(_merged62)))).to_be('shoot a monkey for its corpse')
            _merged63 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged63[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_SANDWICH, 'inv_ids': [[TB_ID.MONKEY_CORPSE, 1]]}.items():
                _merged63[_k] = _v
            expect(named(step(Record(_merged63)))).to_be('ask Tamayu to skin the monkey')
            _merged64 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged64[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_SANDWICH, 'inv_ids': [[TB_ID.MONKEY_SKIN, 1]]}.items():
                _merged64[_k] = _v
            expect(named(step(Record(_merged64)))).to_be('sandwich the seaweed into the monkey skin')
            _merged65 = {}
            for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                _merged65[_k] = _v
            for _k, _v in {'tinsay': TB_TINSAY.FETCH_SANDWICH, 'inv_ids': [[TB_ID.SANDWICH, 1]]}.items():
                _merged65[_k] = _v
            expect(named(step(Record(_merged65)))).to_be('give Tinsay the seaweed sandwich')
        test('the sandwich runs monkey, Tamayu, seaweed', _fn61)

        def _fn66():
            def at(inv_ids):
                _merged67 = {}
                for _k, _v in (PAST_TINSAY._fields if isinstance(PAST_TINSAY, Record) else PAST_TINSAY).items():
                    _merged67[_k] = _v
                for _k, _v in {'tinsay': TB_TINSAY.FETCH_BONES, 'inv_ids': inv_ids}.items():
                    _merged67[_k] = _v
                return named(step(Record(_merged67)))
            expect(at([])).to_be('kill a Jogre for its bones')
            expect(at([[TB_ID.JOGRE_BONES, 1]])).to_be('burn the Jogre bones')
            expect(at([[TB_ID.BURNT_JOGRE_BONES, 1]])).to_be('net a Karambwanji for the marinade')
            expect(at([[TB_ID.BURNT_JOGRE_BONES, 1], [TB_ID.RAW_KARAMBWANJI, 1]])).to_be('grind the Karambwanji into paste')
            expect(at([[TB_ID.BURNT_JOGRE_BONES, 1], [TB_ID.KARAMBWANJI_PASTE, 1]])).to_be('smother the bones in Karambwanji paste')
            expect(at([[TB_ID.PASTY_JOGRE_BONES, 1]])).to_be('marinate the bones on the jungle fire')
            expect(at([[TB_ID.MARINATED_JOGRE_BONES, 1]])).to_be('give Tinsay the marinated Jogre bones')
        test('the marinade runs Jogre, tinderbox, paste, fire', _fn66)
    describe('Tinsay', _fn51)

    def _fn68():
        past = Record({
        'lubufu': TB_LUBUFU.COMPLETE,
        'tiadeche': TB_TIADECHE.REQUEST_MANUAL,
        'tamayu': TB_TAMAYU.COMPLETE,
        'tinsay': TB_TINSAY.COMPLETE,
        'agility': True,
        'spear': True,
    })

        def _fn69():
            expect(named(step(past))).to_be('ask Lubufu for another Karambwan vessel')
            _merged70 = {}
            for _k, _v in (past._fields if isinstance(past, Record) else past).items():
                _merged70[_k] = _v
            for _k, _v in {'inv_ids': [[TB_ID.VESSEL, 1]]}.items():
                _merged70[_k] = _v
            expect(named(step(Record(_merged70)))).to_be('take a vessel to Tinsay for the crafting instructions')
            _merged71 = {}
            for _k, _v in (past._fields if isinstance(past, Record) else past).items():
                _merged71[_k] = _v
            for _k, _v in {'inv_ids': [[TB_ID.CRAFTING_MANUAL, 1]]}.items():
                _merged71[_k] = _v
            expect(named(step(Record(_merged71)))).to_be('give Tiadeche the crafting manual')
        test('a vessel is fetched, taken to Tinsay, then the manual goes to Tiadeche', _fn69)
    describe("Tiadeche's manual", _fn68)


describe('tai bwo wannai trio decide', _fn1)


def _fn72():
    def _fn73():
        ids = [d.record.id for d in QUEST_DEFS]
        expect(ids).to_contain('tbwt')
        expect((ids.index('tbwt') if 'tbwt' in ids else -1)).to_be_greater_than((ids.index('junglepotion') if 'junglepotion' in ids else -1))
    test('it is registered after Jungle Potion, which it requires', _fn73)

    def _fn74():
        expect(tbwt.owns_inventory).to_be(True)
        expect(tbwt.record.requirements.quests).to_contain('junglepotion')
        expect(tbwt.bank).not_.to_be('nearest')
    test('it owns its own pack and banks in Ardougne', _fn74)


describe('tai bwo wannai trio module', _fn72)

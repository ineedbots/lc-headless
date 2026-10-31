"""Ported from rs2b0t's test/api/ai/quests/defs/trollstronghold.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.loadout import Loadout
from rs2004.catalogs.record import Record
from rs2004.quests.defs.trollstronghold import FOOD_TARGET, ITEM, TROLL_FLAG, TROLL_STAGE, committed, decide, parse_troll_stronghold_journal, troll_zone, trollstronghold
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout

BURTHORPE = Record({'x': 2896, 'z': 3528, 'level': 0})
ARENA = Record({'x': 2912, 'z': 3613, 'level': 0})
STRONGHOLD = Record({'x': 2837, 'z': 10090, 'level': 2})
PRISON = Record({'x': 2833, 'z': 10078, 'level': 0})
SECRET_WAY = Record({'x': 2856, 'z': 3613, 'level': 0})
MOUNTAIN = Record({'x': 2840, 'z': 3690, 'level': 0})
TROLL_PASS = Record({'x': 2907, 'z': 10019, 'level': 0})
FOOD = ['Lobster'] * FOOD_TARGET
COINS = ['Coins'] * 500
WEAPON = 'Rune scimitar'


def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        _v1 = out.get(key)
        out[key] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else TROLL_STAGE.NOT_STARTED)
    bank = counts((options.bank if options.bank is not None else []))
    _v2 = bank.get('coins')
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == TROLL_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': counts((options.inv if options.inv is not None else [])),
        'worn': set([name.lower() for name in ((options.worn if options.worn is not None else []))]),
        'no_progress': 0,
        'bank_coins': (_v2 if _v2 is not None else 0),
        'stage': stage,
        'progress': QuestProgress(stage, set((options.flags if options.flags is not None else []))),
        'bank': bank,
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (BURTHORPE if options.tile is None else options.tile),
        'free_slots': 28,
    })


def ready(options=None):
    """A pack that has already been kitted out: nothing left for prepare() to do."""
    if options is None:
        options = Record({})
    _merged3 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': list(FOOD) + list(COINS), 'worn': [ITEM.CLIMBING_BOOTS, WEAPON]}.items():
        _merged3[_k] = _v
    for _k, _v in (options._fields if isinstance(options, Record) else options).items():
        _merged3[_k] = _v
    return snap(Record(_merged3))


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn4():
    quest_food.name = 'Lobster'
    quest_loadout.current = Loadout('quest', {'righthand': WEAPON}, [Record({'item': 'Lobster', 'qty': 16})])


before_each(_fn4)


def _fn5():
    def _fn6(text, stage):
        expect((parse_troll_stronghold_journal(text).stage if parse_troll_stronghold_journal(text) is not None else None)).to_be(stage)
    test_each([
        [
        '@dbl@I can start this quest by speaking to @dre@Denulth@dbl@ in his tent at the @dre@Imperial Guard Camp@dbl@ in @dre@Burthorpe@dbl@ after completing the @dre@Death Plateau Quest',
        0,
    ],
        [
        '@dbl@I promised @dre@Denulth@dbl@ that I would rescue @dre@Godric@dbl@ from the @dre@Troll Stronghold',
        10,
    ],
        [
        '@dbl@I promised @dre@Denulth@dbl@ that I would rescue @dre@Godric@dbl@ from the @dre@Troll Stronghold||@str@I got some climbing boots from Tenzing.||@dbl@I have to defeat the @dre@Troll Champion@dbl@ to get past the @dre@Arena',
        10,
    ],
        [
        '@dbl@I promised Denulth||@str@I have defeated the Troll Champion.||@dbl@I have to find a way to get into the @dre@Troll Stronghold',
        20,
    ],
        [
        '@str@I have defeated the Troll Champion.||@str@I have found my way into the Troll Stronghold||@str@I have the prison key.|@dbl@I have to get into the @dre@prison',
        20,
    ],
        ['@str@I have found my way into the prison.||@dbl@I have to rescue @dre@Godric', 30],
        [
        "@str@I have found my way into the prison.||@str@I've rescued Mad Eadgar.|@dbl@I have to rescue @dre@Godric",
        30,
    ],
        [
        "@str@I've rescued Godric and Mad Eadgar.|@dbl@I should return and tell @dre@Dunstan@dbl@ his son is safe.",
        40,
    ],
        [
        '@str@I talked to Dunstan and he gave me the Law Talisman|@str@as a token of thanks!||@red@QUEST COMPLETE!',
        50,
    ],
    ])('maps journal text to stage %i', _fn6)

    def _fn7():
        progress = parse_troll_stronghold_journal('@str@I got some climbing boots from Tenzing.||@str@I have defeated the Troll Champion.||@str@I have found my way into the Troll Stronghold||@str@I have the prison key.')
        expect((progress.stage if progress is not None else None)).to_be(TROLL_STAGE.DEFEATED_DAD)
        expect((TROLL_FLAG.BOOTS in (progress.flags if progress is not None else None))).to_be(True)
        expect((TROLL_FLAG.ENTERED_STRONGHOLD in (progress.flags if progress is not None else None))).to_be(True)
        expect((TROLL_FLAG.HAS_PRISON_KEY in (progress.flags if progress is not None else None))).to_be(True)
    test('reads sub-progress flags from journal lines', _fn7)

    def _fn8():
        in_prison = parse_troll_stronghold_journal("@str@I have found my way into the prison.||@str@I've rescued Mad Eadgar.|@dbl@I have to rescue @dre@Godric")
        expect((TROLL_FLAG.FREED_EADGAR in (in_prison.flags if in_prison is not None else None))).to_be(True)
        freed = parse_troll_stronghold_journal("@str@I've rescued Godric and Mad Eadgar.|@dbl@I should return and tell @dre@Dunstan@dbl@ his son is safe.")
        expect((TROLL_FLAG.FREED_EADGAR in (freed.flags if freed is not None else None))).to_be(True)
    test('reads the freed-Eadgar flag from both the stage-30 and stage-40 wording', _fn8)

    def _fn9():
        progress = parse_troll_stronghold_journal("@str@I've rescued Godric.|@dbl@I should return and tell @dre@Dunstan@dbl@ his son is safe.")
        expect((progress.stage if progress is not None else None)).to_be(TROLL_STAGE.FREED_GODRIC)
        expect((TROLL_FLAG.FREED_EADGAR in (progress.flags if progress is not None else None))).to_be(False)
    test('does not read the Eadgar flag when only Godric was freed', _fn9)

    def _fn10():
        expect(parse_troll_stronghold_journal(['Troll Stronghold', 'Loading…'])).to_be_undefined()
    test('fails closed on incomplete journal text', _fn10)


describe('Troll Stronghold journal stage parsing', _fn5)


def _fn11():
    def _fn12():
        expect(troll_zone(BURTHORPE)).to_be('mainland')
        expect(troll_zone(SECRET_WAY)).to_be('secretWay')
        expect(troll_zone(ARENA)).to_be('arena')
        expect(troll_zone(TROLL_PASS)).to_be('trollPass')
        expect(troll_zone(MOUNTAIN)).to_be('mountain')
        expect(troll_zone(STRONGHOLD)).to_be('stronghold')
        expect(troll_zone(PRISON)).to_be('stronghold')
        expect(troll_zone(Record({'x': 3200, 'z': 3200, 'level': 0}))).to_be('mainland')
        expect(troll_zone(None)).to_be('unknown')
    test('classifies every leg of the route', _fn12)

    def _fn13():
        expect(committed(troll_zone(BURTHORPE))).to_be(False)
        expect(committed(troll_zone(None))).to_be(False)
        for tile in [SECRET_WAY, ARENA, TROLL_PASS, MOUNTAIN, STRONGHOLD, PRISON]:
            expect(committed(troll_zone(tile))).to_be(True)
    test('only the mainland is cheap enough to bank from', _fn13)


describe('Troll Stronghold zones', _fn11)


def _fn14():
    def _fn15():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'bank_known': False})))
        expect(step.kind).to_be('scan_bank')
    test('reads the bank before deciding anything about supplies', _fn15)

    def _fn16():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': ['Bones'] + list(FOOD)})))
        expect(step.kind).to_be('deposit')
    test('banks anything that is not part of the loadout', _fn16)

    def _fn17():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'bank': COINS})))
        expect(step.kind == 'withdraw' and (step.items[0]['name'] if step.items[0] is not None else None)).to_be(ITEM.COINS)
    test('withdraws the coin float before the boots it has to buy', _fn17)

    def _fn18():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': COINS, 'bank': [ITEM.CLIMBING_BOOTS]})))
        expect(step.kind == 'withdraw' and (step.items[0]['name'] if step.items[0] is not None else None)).to_be(ITEM.CLIMBING_BOOTS)
    test('withdraws banked climbing boots rather than buying a second pair', _fn18)

    def _fn19():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': [WEAPON] + list(COINS) + list(FOOD)})))
        expect(custom_name(step)).to_be(f'wear {WEAPON}')
    test('wears the gear it just withdrew before walking off to Tenzing', _fn19)

    def _fn20():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': COINS})))
        expect(custom_name(step)).to_contain('Tenzing')
    test('buys boots from Tenzing when the bank has none', _fn20)

    def _fn21():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED})))
        expect(step.kind == 'wait' and step.reason).to_contain('Climbing boots')
    test('waits, naming the shortfall, when it cannot pay for boots', _fn21)

    def _fn22():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': [ITEM.CLIMBING_BOOTS] + list(COINS)})))
        expect(custom_name(step)).to_be(f'wear {ITEM.CLIMBING_BOOTS}')
    test('equips boots it is carrying', _fn22)

    def _fn23():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': COINS, 'worn': [ITEM.CLIMBING_BOOTS], 'bank': [WEAPON]})))
        expect(step.kind == 'withdraw' and (step.items[0]['name'] if step.items[0] is not None else None)).to_be(WEAPON)
    test('withdraws the loadout weapon when nothing is wielded', _fn23)

    def _fn24():
        quest_loadout.current = None
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': COINS,
        'worn': [ITEM.CLIMBING_BOOTS],
        'bank': ['Lobster', 'Rune scimitar', 'Mithril scimitar', 'Rune chainbody'],
    })))
        names = ([i.name for i in as_records(step.items)] if step.kind == 'withdraw' else [])
        expect(names).to_contain('Rune scimitar')
        expect(names).to_contain('Rune chainbody')
        expect(names).not_.to_contain('Mithril scimitar')
    test('with no loadout it scavenges the best the bank holds', _fn24)

    def _fn25():
        quest_loadout.current = None
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': list(COINS) + list(FOOD),
        'worn': [ITEM.CLIMBING_BOOTS],
        'bank': ['Lobster'] * 40,
    })))
        expect(step.kind == 'wait' and step.reason).to_contain('no melee weapon')
    test('with no loadout and an empty bank it says so instead of parking silently', _fn25)

    def _fn26():
        quest_loadout.current = Loadout('quest', {'righthand': WEAPON, 'torso': 'Rune chainbody'}, [Record({'item': 'Lobster', 'qty': 16})])
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': COINS,
        'worn': [ITEM.CLIMBING_BOOTS],
        'bank': [WEAPON, 'Rune chainbody'] + list(['Lobster'] * 40),
    })))
        expect(step.kind == 'withdraw' and sorted([i.name for i in as_records(step.items)])).to_equal(['Lobster', 'Rune chainbody', WEAPON])
    test('withdraws every piece of loadout gear it is not already wearing', _fn26)

    def _fn27():
        quest_loadout.current = Loadout('quest', {'righthand': WEAPON, 'torso': 'Rune chainbody', 'legs': 'Rune platelegs'}, [])
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': list(COINS) + list(FOOD) + [WEAPON, 'Rune chainbody', 'Rune platelegs'],
        'worn': [ITEM.CLIMBING_BOOTS],
        'bank': [],
    })))
        name = custom_name(step)
        expect(name).to_contain(WEAPON)
        expect(name).to_contain('Rune chainbody')
        expect(name).to_contain('Rune platelegs')
    test('wears the whole kit in a single step', _fn27)

    def _fn28():
        quest_loadout.current = Loadout('quest', {'righthand': WEAPON}, [])
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': [],
        'worn': [],
        'bank': [WEAPON] + list(COINS) + list(['Lobster'] * 40),
    })))
        names = ([i.name for i in as_records(step.items)] if step.kind == 'withdraw' else [])
        expect(names).to_contain(ITEM.COINS)
        expect(names).to_contain(WEAPON)
    test('boot money rides the same bank visit as the gear', _fn28)

    def _fn29():
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': COINS,
        'worn': [ITEM.CLIMBING_BOOTS, WEAPON],
        'bank': list(['Lobster'] * 40) + list(['Prayer potion(4)'] * 5),
    })))
        expect(step.kind == 'withdraw' and (([i for i in as_records(step.items) if i.name == 'Prayer potion(4)'] or [None])[0].qty if ([i for i in as_records(step.items) if i.name == 'Prayer potion(4)'] or [None])[0] is not None else None)).to_be(2)
    test('withdraws two prayer potions when the bank has them', _fn29)

    def _fn30():
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': COINS,
        'worn': [ITEM.CLIMBING_BOOTS, WEAPON],
        'bank': list(['Lobster'] * 40) + ['Prayer potion(2)', 'Prayer potion(3)'],
    })))
        expect(step.kind == 'withdraw' and (([i for i in as_records(step.items) if (i.name.startswith('Prayer potion') if i.name is not None else None)] or [None])[0].name if ([i for i in as_records(step.items) if (i.name.startswith('Prayer potion') if i.name is not None else None)] or [None])[0] is not None else None)).to_be('Prayer potion(3)')
    test('prefers the strongest dose the bank holds', _fn30)

    def _fn31():
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': COINS,
        'worn': [ITEM.CLIMBING_BOOTS, WEAPON],
        'bank': list(['Lobster'] * 40) + ['Prayer potion(4)', 'Prayer potion(3)'],
    })))
        potions = ([i for i in as_records(step.items) if i.name.startswith('Prayer potion')] if step.kind == 'withdraw' else [])
        expect(sum([i.qty for i in potions])).to_be(2)
    test('tops up from a weaker dose when the strong one runs short', _fn31)

    def _fn32():
        step = decide(ready(Record({'stage': TROLL_STAGE.STARTED, 'tile': ARENA})))
        expect(custom_name(step)).to_contain('Dad')
    test('carries on without potions when the bank has none', _fn32)

    def _fn33():
        step = decide(ready(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': list(FOOD) + list(COINS) + ['Prayer potion(4)', 'Prayer potion(4)'],
        'tile': ARENA,
    })))
        expect(step.kind).not_.to_be('deposit')
        expect(custom_name(step)).to_contain('Dad')
    test('does not bank the potions it is carrying', _fn33)

    def _fn34():
        step = decide(snap(Record({
        'stage': TROLL_STAGE.STARTED,
        'inv': COINS,
        'worn': [ITEM.CLIMBING_BOOTS, WEAPON],
        'bank': ['Lobster'] * 40,
    })))
        expect(step.kind == 'withdraw' and step.items[0]).to_equal(Record({'name': 'Lobster', 'qty': FOOD_TARGET}))
    test('withdraws food up to the target', _fn34)

    def _fn35():
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': COINS, 'worn': [ITEM.CLIMBING_BOOTS, WEAPON]})))
        expect(step.kind == 'wait' and step.reason).to_contain('no combat food')
    test('waits, naming the shortfall, when the bank holds no food at all', _fn35)

    def _fn36():
        # A rune platebody also wants Dragon Slayer; the server refuses, and
        # a `kind: equip` step re-derived from the same snapshot never stops.
        step = decide(snap(Record({'stage': TROLL_STAGE.STARTED, 'inv': [WEAPON] + list(COINS), 'worn': [ITEM.CLIMBING_BOOTS]})))
        expect(step.kind).to_be('custom')
        expect(custom_name(step)).to_be(f'wear {WEAPON}')
    test('wearing gear is a step that can give up, not a plain equip that retries forever', _fn36)

    def _fn37():
        step = decide(ready(Record({'stage': TROLL_STAGE.STARTED, 'inv': ['Lobster', 'Lobster', 'Lobster', 'Lobster'], 'tile': ARENA})))
        expect(custom_name(step)).to_contain('Dad')
    test('does not walk back down the mountain for a pack that is merely low', _fn37)

    def _fn38():
        step = decide(ready(Record({'stage': TROLL_STAGE.STARTED, 'inv': ['Lobster'], 'tile': ARENA, 'bank': ['Lobster'] * 40})))
        expect(step.kind).to_be('withdraw')
    test('does walk back down when the pack is spent', _fn38)


describe('Troll Stronghold loadout', _fn14)


def _fn39():
    def _fn40():
        expect(trollstronghold.record.id).to_be('troll')
        expect(trollstronghold.owns_inventory).to_be(True)
        expect((trollstronghold.sustain.eat_below_hp if trollstronghold.sustain is not None else None)).to_be(0.6)
        # The spillover deposit banks everything not named here, coins included,
        # and without them every purchase parks on "need N gp".
        expect(trollstronghold.tools).to_contain('coins')
    test('module record id is troll', _fn40)

    def _fn41():
        # Death Plateau's gate reads live quest state; with no client attached
        # that is notStarted, so the honest answer is a wait.
        step = decide(ready(Record({'stage': TROLL_STAGE.NOT_STARTED, 'journal': 'not_started'})))
        expect(step.kind == 'talk' or step.kind == 'wait').to_be(True)
        if step.kind == 'talk':
            expect(step.stop.npc).to_be('Denulth')
    test('starts with Denulth once the loadout is ready', _fn41)

    def _fn42():
        expect(custom_name(decide(ready(Record({'stage': TROLL_STAGE.STARTED, 'tile': ARENA}))))).to_contain('Dad')
    test('fights Dad once started and kitted out', _fn42)

    def _fn43():
        step = decide(ready(Record({'stage': TROLL_STAGE.DEFEATED_DAD, 'tile': STRONGHOLD})))
        expect((custom_name(step).lower() if custom_name(step) is not None else None)).to_contain('prison key')
    test('hunts a Troll General for the prison key after Dad', _fn43)

    def _fn44():
        step = decide(ready(Record({
        'stage': TROLL_STAGE.DEFEATED_DAD,
        'inv': [ITEM.PRISON_KEY] + list(FOOD) + list(COINS),
        'tile': STRONGHOLD,
    })))
        expect((custom_name(step).lower() if custom_name(step) is not None else None)).to_contain('unlock the troll prison')
    test('goes straight to the prison once the key is in the pack', _fn44)

    def _fn45():
        step = decide(ready(Record({'stage': TROLL_STAGE.ENTERED_PRISON, 'tile': PRISON})))
        expect(custom_name(step)).to_contain('Mad Eadgar')
        expect(custom_name(step)).to_contain('Godric')
    test('frees Mad Eadgar alongside Godric while it is standing there', _fn45)

    def _fn46():
        step = decide(ready(Record({'stage': TROLL_STAGE.ENTERED_PRISON, 'flags': [TROLL_FLAG.FREED_EADGAR], 'tile': PRISON})))
        expect(custom_name(step)).not_.to_contain('Eadgar')
        expect(custom_name(step)).to_contain('Godric')
    test('skips Mad Eadgar when the journal says he is already out', _fn46)

    def _fn47():
        step = decide(ready(Record({'stage': TROLL_STAGE.FREED_GODRIC, 'tile': BURTHORPE})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Dunstan')
    test('reports to Dunstan after freeing Godric', _fn47)

    def _fn48():
        expect(decide(snap(Record({'stage': TROLL_STAGE.COMPLETE, 'journal': 'complete'}))).kind).to_be('done')
    test('done when complete', _fn48)


describe('Troll Stronghold decide', _fn39)

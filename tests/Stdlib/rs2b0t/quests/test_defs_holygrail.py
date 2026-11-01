"""Ported from rs2b0t's test/api/ai/quests/defs/holygrail.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.holygrail import GRAIL_STAGE, decide, excalibur_plan, holygrail
from rs2004.quests.defs.holygrail.areas import GRAIL_TILE
from rs2004.quests.defs.holygrail.armour import armour_wanted, reset_unwearable

def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        _v1 = out.get(key)
        out[key] = ((_v1 if _v1 is not None else 0)) + 1
    return out


KIT = ['Rune chainbody', 'Rune platelegs', 'Rune full helm', 'Rune kiteshield']


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else GRAIL_STAGE.NOT_STARTED)
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': counts((options.inv if options.inv is not None else [])),
        'worn': set([n.lower() for n in ((options.worn if options.worn is not None else []))]),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, set()),
        'bank': counts((options.bank if options.bank is not None else ['Excalibur', 'Coins'] + list(KIT))),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (Record({'x': 3222, 'z': 3218, 'level': 0}) if options.tile is None else options.tile),
        'free_slots': 20,
    })


def armed(options=None):
    """Fully armed and on the mainland: the state every mid-quest branch starts from."""
    if options is None:
        options = Record({})
    _merged2 = {}
    for _k, _v in (options._fields if isinstance(options, Record) else options).items():
        _merged2[_k] = _v
    for _k, _v in {'worn': list(KIT) + ['Excalibur'] + list(((options.worn if options.worn is not None else [])))}.items():
        _merged2[_k] = _v
    return snap(Record(_merged2))


def custom(step):
    return ((step.name if step.kind == 'custom' else f'{step.kind}'))


def _fn3():
    reset_unwearable()


before_each(_fn3)


def _fn4():
    def _fn5():
        expect(decide(snap(Record({'journal': 'unknown'})))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('an unloaded quest list waits rather than restarting the quest', _fn5)

    def _fn6():
        expect(decide(snap(Record({'journal': 'complete'})))).to_equal(Record({'kind': 'done'}))
    test('a green quest list is done', _fn6)

    def _fn7():
        step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_CRONE, 'bank_known': False})))
        expect(step.kind).to_be('scan_bank')
    test('an unread bank is scanned before the armour planner runs', _fn7)

    def _fn8():
        step = decide(armed(Record({'stage': GRAIL_STAGE.SPOKEN_CRONE, 'bank_known': False, 'tile': GRAIL_TILE.REALM_ARRIVAL})))
        expect(step.kind).to_be('custom')
    test('inside the realm an unread bank never sends the bot back for one', _fn8)

    def _fn9():
        step = decide(snap(Record({'journal': 'not_started', 'stage': GRAIL_STAGE.NOT_STARTED})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('King Arthur')
    test('not started talks to King Arthur', _fn9)

    def _fn10():
        expect(custom(decide(snap(Record({'stage': GRAIL_STAGE.STARTED}))))).to_contain('Merlin')
    test('started opens the workshop door for Merlin', _fn10)

    def _fn11():
        def _fn12():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_MERLIN, 'inv': ['Excalibur', 'Coins', 'Lobster']})), 'Lobster')
            expect(step.kind).to_be('deposit')
            expect(step.kind == 'deposit' and step.exact_keep).to_be(True)
            expect(step.kind == 'deposit' and step.keep).to_equal(['Coins', 'Lobster'])
        test('banks everything the monk would find, keeping coin and food', _fn12)

        def _fn13():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_MERLIN, 'inv': ['Coins', 'Lobster'], 'worn': ['Rune chainbody']})), 'Lobster')
            expect(custom(step)).to_contain('Entrana')
        test('a pack of coin and food alone is not banked again', _fn13)

        def _fn14():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_MERLIN, 'inv': ['Coins']})), 'Lobster')
            expect(step.kind == 'talk' and step.stop.npc).to_be('High Priest')
        test('a stripped pack and bare shoulders sail on and talk to the High Priest', _fn14)
    describe('the Entrana leg', _fn11)

    def _fn15():
        def _fn16():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_CRONE, 'inv': ['Holy table napkin']})))
            expect(step).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Excalibur', 'qty': 1})]}))
        test('re-arms with Excalibur before anything else', _fn16)

        def _fn17():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_CRONE, 'inv': ['Holy table napkin', 'Excalibur']})))
            expect(step).to_equal(Record({'kind': 'equip', 'item': 'Excalibur'}))
        test('a held Excalibur is wielded, not carried', _fn17)

        def _fn18():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_CRONE})))
            expect(step.kind == 'talk' and step.stop.npc).to_be('Galahad')
        test('no napkin anywhere sends the bot to Galahad first', _fn18)

        def _fn19():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_CRONE, 'bank': ['Holy table napkin', 'Excalibur']})))
            expect(step).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Holy table napkin', 'qty': 1})]}))
        test('a banked napkin is withdrawn rather than begged for again', _fn19)

        def _fn20():
            step = armed_crossing(['Holy table napkin'])
            expect(custom(step)).to_contain('Draynor Manor')
        test('armed and holding the napkin, it fetches two whistles', _fn20)

        def _fn21():
            step = armed_crossing(['Holy table napkin', 'Magic whistle', 'Magic whistle'])
            expect(custom(step)).to_contain('six heads')
        test('two whistles in the pack means blow at the six heads', _fn21)

        def _fn22():
            four = armed_crossing(['Holy table napkin', 'Magic whistle', 'Magic whistle'], GRAIL_STAGE.SPOKEN_CRONE)
            seven = armed_crossing(['Holy table napkin', 'Magic whistle', 'Magic whistle'], GRAIL_STAGE.FAILED_TITAN)
            expect(custom(seven)).to_be(custom(four))
        test('stage 7 is the same errand as stage 4', _fn22)

        def _fn23():
            step = decide(armed(Record({
        'stage': GRAIL_STAGE.SPOKEN_CRONE,
        'inv': ['Holy table napkin', 'Magic whistle'],
        'tile': GRAIL_TILE.REALM_ARRIVAL,
    })))
            expect(custom(step)).to_contain('realm')
        test('in the realm it runs the one realm step', _fn23)

        def _fn24():
            step = decide(snap(Record({
        'stage': GRAIL_STAGE.SPOKEN_CRONE,
        'inv': ['Magic whistle', 'Excalibur'],
        'tile': GRAIL_TILE.REALM_ARRIVAL,
    })))
            expect(step).to_equal(Record({'kind': 'equip', 'item': 'Excalibur'}))
        test('landing on the titan side without Excalibur wields the carried one', _fn24)

        def _fn25():
            step = decide(snap(Record({'stage': GRAIL_STAGE.SPOKEN_CRONE, 'inv': ['Magic whistle'], 'tile': GRAIL_TILE.REALM_ARRIVAL})))
            expect(custom(step)).to_contain('fetch Excalibur')
        test('landing on the titan side with no Excalibur at all leaves to fetch it', _fn25)
    describe('the crossing', _fn15)

    def _fn26():
        def _fn27():
            step = decide(armed(Record({'stage': GRAIL_STAGE.FINDING_PERCIVAL, 'inv': ['Magic whistle'], 'tile': GRAIL_TILE.CASTLE_LANDING})))
            expect(custom(step)).to_contain('leave the realm')
        test('the realm is left before the Goblin Village walk', _fn27)

        def _fn28():
            step = decide(armed(Record({'stage': GRAIL_STAGE.FINDING_PERCIVAL, 'inv': ['Magic whistle']})))
            expect(custom(step)).to_contain('Percival')
        test('a whistle in hand opens the sacks', _fn28)

        def _fn29():
            step = decide(armed(Record({'stage': GRAIL_STAGE.FINDING_PERCIVAL, 'inv': ['Holy table napkin']})))
            expect(custom(step)).to_contain('Draynor Manor')
        test('no whistle means another Draynor Manor trip', _fn29)

        def _fn30():
            step = decide(armed(Record({'stage': GRAIL_STAGE.FINDING_PERCIVAL, 'bank': ['Holy table napkin']})))
            expect(step).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Holy table napkin', 'qty': 1})]}))
        test('a banked napkin is withdrawn before the whistle trip', _fn30)

        def _fn31():
            step = decide(armed(Record({'stage': GRAIL_STAGE.FINDING_PERCIVAL, 'bank': []})))
            expect(step.kind == 'wait' and step.reason).to_contain('Holy table napkin')
        test('no napkin anywhere waits and names why Galahad is no longer an option', _fn31)
    describe('finding Sir Percival', _fn26)

    def _fn32():
        def _fn33():
            step = decide(armed(Record({'stage': GRAIL_STAGE.GIVEN_WHISTLE, 'inv': ['Magic whistle']})))
            expect(custom(step)).to_contain('six heads')
        test('with the whistle spent on Percival it walks back to the six heads', _fn33)

        def _fn34():
            step = decide(armed(Record({'stage': GRAIL_STAGE.GIVEN_WHISTLE, 'inv': ['Magic whistle'], 'tile': GRAIL_TILE.GRAIL_STAND})))
            expect(custom(step)).to_contain('Holy Grail')
        test('inside the renewed realm it lifts the Grail off the table', _fn34)

        def _fn35():
            step = decide(armed(Record({
        'stage': GRAIL_STAGE.GIVEN_WHISTLE,
        'inv': ['Magic whistle', 'Holy grail'],
        'tile': GRAIL_TILE.GRAIL_STAND,
    })))
            expect(custom(step)).to_contain('out of the realm')
        test('holding the Grail in the realm blows the whistle out', _fn35)

        def _fn36():
            step = decide(armed(Record({'stage': GRAIL_STAGE.GIVEN_WHISTLE, 'inv': ['Magic whistle', 'Holy grail']})))
            expect(step.kind == 'talk' and step.stop.npc).to_be('King Arthur')
        test('holding the Grail on the mainland hands it to King Arthur', _fn36)
    describe('claiming the Grail', _fn32)

    def _fn37():
        expect(decide(snap(Record({'stage': 5})))).to_equal(Record({'kind': 'wait', 'reason': 'unmapped Holy Grail stage 5'}))
    test('an unmapped stage waits with the stage in the reason', _fn37)


describe('Holy Grail decide', _fn4)


def armed_crossing(inv, stage=None):
    if stage is None:
        stage = GRAIL_STAGE.SPOKEN_CRONE
    return decide(armed(Record({'stage': stage, 'inv': inv})))


def _fn38():
    def _fn39():
        expect(excalibur_plan(snap())).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Excalibur', 'qty': 1})]}))
    test('the bank is used before the Lady of the Lake', _fn39)

    def _fn40():
        step = excalibur_plan(snap(Record({'bank': ['Coins'], 'inv': ['Coins'] * 500})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('The Lady of the Lake')
    test('with 500 coins held she sells it back', _fn40)

    def _fn41():
        step = excalibur_plan(snap(Record({'bank': ['Coins']})))
        expect(step).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Coins', 'qty': 500})]}))
    test('with the coins banked they are withdrawn first', _fn41)

    def _fn42():
        bare = snap(Record({'bank': []})).with_fields({'bank_coins': 0})
        expect(excalibur_plan(bare)).to_equal(Record({'kind': 'wait', 'reason': 'need 500 gp to buy Excalibur back from the Lady of the Lake'}))
    test('with no coin anywhere it waits and says why', _fn42)


describe('Excalibur sourcing', _fn38)


def _fn44():
    def _fn45():
        expect(armour_wanted(snap())).to_equal(['Rune chainbody', 'Rune platelegs', 'Rune full helm', 'Rune kiteshield'])
    test('picks the best banked piece per slot and never a weapon', _fn45)

    def _fn46():
        expect(armour_wanted(snap(Record({'bank': ['Rune platebody', 'Rune chainbody']})))).to_equal(['Rune chainbody'])
    test('a chainbody outranks a platebody, which rune refuses without Dragon Slayer', _fn46)

    def _fn47():
        expect(armour_wanted(snap(Record({'worn': KIT})))).to_equal([])
    test('worn slots are left alone', _fn47)

    def _fn48():
        expect(armour_wanted(snap(Record({'bank': ['Mithril platelegs']})))).to_equal(['Mithril platelegs'])
    test('a lower tier is taken when the bank has nothing better', _fn48)


describe('the armour planner', _fn44)


def _fn49():
    def _fn50():
        expect(holygrail.record.requirements.quests).to_equal(['arthur'])
    test("Merlin's Crystal is a hard prerequisite", _fn50)

    def _fn51():
        expect(holygrail.record.items).to_equal([Record({'name': 'Excalibur', 'qty': 1, 'kind': 'acquirable'})])
        expect((holygrail.gather.get('excalibur') if holygrail.gather is not None else None)).to_be_defined()
    test('Excalibur is the one declared item, and it is gatherable', _fn51)

    def _fn52():
        for name in [
        'excalibur',
        'holy table napkin',
        'magic whistle',
        'grail bell',
        'holy grail',
        'coins',
        'chainbody',
        'kiteshield',
    ]:
            expect(holygrail.tools).to_contain(name)
    test('every quest item and armour word is kept from the spillover deposit', _fn52)

    def _fn53():
        expect(holygrail.grind).to_contain('Black Knight Titan')
    test('the titan is a declared grind target so random events do not misread the fight', _fn53)


describe('the module record', _fn49)


def _resume_at_covers_the_realm():
    expect(holygrail.resume_at(Record({'x': 2765, 'z': 4686, 'level': 1}))).to_be(True)
    expect(holygrail.resume_at(Record({'x': 2649, 'z': 4683, 'level': 2}))).to_be(True)
    expect(holygrail.resume_at(Record({'x': 2741, 'z': 3235, 'level': 0}))).to_be(False)


test('a restart inside the realm leaves generic banking until outside', _resume_at_covers_the_realm)

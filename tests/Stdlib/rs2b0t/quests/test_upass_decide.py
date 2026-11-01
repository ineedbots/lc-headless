"""Ported from rs2b0t's test/api/ai/quests/upassDecide.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.upass import decide
from rs2004.quests.defs.upass.areas import UP_ITEM
from rs2004.quests.defs.upass.journal import UP_FLAG, UP_STAGE

# `decide()` is pure over a snapshot, so these tests need no client.
def counts(stacks):
    return {_k: _v for _k, _v in [((s if isinstance(s, list) else [s, 1])) for s in stacks]}


ITEM_ID = Record({'OAK_SHORTBOW': 843, 'CROSSBOW': 837})
ARDOUGNE = Record({'x': 2655, 'z': 3283, 'level': 0})
WEST_ARDOUGNE = Record({'x': 2500, 'z': 3300, 'level': 0})
AREA1 = Record({'x': 2450, 'z': 9716, 'level': 0})
KIT = [
    [UP_ITEM.ROPE.id, 3],
    UP_ITEM.SHORTBOW.id,
    [UP_ITEM.BRONZE_ARROW.id, 50],
    UP_ITEM.TINDERBOX.id,
    UP_ITEM.SPADE.id,
    UP_ITEM.BUCKET.id,
    [UP_ITEM.LOBSTER.id, 14],
]
# Why: melee gear matches by name and defaults to worn in these snapshots.
WEAPON = 'rune scimitar'


NAMED = ['stage', 'flags', 'carried', 'banked', 'worn_id_list', 'carried_names', 'worn_names']


def snapshot(over=None):
    if over is None:
        over = Record({})
    stage = over.stage if over.stage is not None else UP_STAGE.NOT_STARTED
    flags = over.flags if over.flags is not None else []
    carried = over.carried if over.carried is not None else []
    banked = over.banked if over.banked is not None else []
    worn_id_list = over.worn_id_list if over.worn_id_list is not None else []
    carried_names = over.carried_names if over.carried_names is not None else []
    worn_names = over.worn_names if over.worn_names is not None else [WEAPON]
    _merged1 = {}
    for _k, _v in {
        'journal': 'in_progress',
        'inv': {_k: _v for _k, _v in [[name, 1] for name in carried_names]},
        'inv_ids': counts(carried),
        'worn': set(worn_names),
        'worn_ids': set(worn_id_list),
        'no_progress': 0,
        'bank_coins': 0,
        'bank': {},
        'bank_ids': counts(banked),
        'bank_known': True,
        'stage': stage,
        'progress': QuestProgress(stage, set(flags)),
        'tile': ARDOUGNE,
    }.items():
        _merged1[_k] = _v
    for _k in over.keys():
        if _k not in NAMED:
            _merged1[_k] = over.get(_k)
    return QuestSnapshot(**_merged1)


def name_of(step):
    return ((step).name if (step).name is not None else '')


def kind_of(step):
    return (step).kind


def reason_of(step):
    return ((step).reason if (step).reason is not None else '')


def _fn2():
    def _fn3():
        expect(kind_of(decide(snapshot(Record({'journal': 'unknown'}))))).to_be('wait')
    test('an unloaded journal waits rather than guessing a stage', _fn3)

    def _fn4():
        expect(kind_of(decide(snapshot(Record({'journal': 'complete'}))))).to_be('done')
    test('a complete journal is done', _fn4)

    # Why: there is no bank past the cave mouth before the level 62 paladins.
    def _fn5():
        step = decide(snapshot(Record({'carried': KIT, 'worn_names': [], 'flags': [UP_FLAG.STARTED]})))
        expect(kind_of(step)).to_be('wait')
        expect(reason_of(step)).to_contain('melee weapon')
    test('without a melee weapon the cave mouth is a stop, not a descent', _fn5)

    # Why: the journal cannot distinguish these stages; the horn marks the leg complete.
    def _fn6():
        in_area2 = Record({'x': 2396, 'z': 9600, 'level': 0})
        for stage in [UP_STAGE.ENTERED_SECOND_AREA, UP_STAGE.KILLED_UNICORN]:
            before = decide(snapshot(Record({'stage': stage, 'tile': in_area2, 'carried': [UP_ITEM.RAILING.id]})))
            expect(name_of(before)).to_contain('crush the unicorn')
            after = decide(snapshot(Record({'stage': stage, 'tile': in_area2, 'carried': [UP_ITEM.UNICORN_HORN.id]})))
            expect(name_of(after)).to_contain('crests')
    test('the unicorn leg is keyed on the horn, not on the stage', _fn6)

    # Why: firing the arrow swaps the bow in and leaves the scimitar packed.
    def _fn7():
        step = decide(snapshot(Record({
        'stage': UP_STAGE.KILLED_UNICORN,
        'tile': Record({'x': 2424, 'z': 9719, 'level': 0}),
        'worn_names': [],
        'carried_names': [WEAPON],
    })))
        expect(name_of(step)).to_be(f'wear {WEAPON}')
    test('the weapon goes back on before the paladins', _fn7)

    def _fn8():
        step = decide(snapshot(Record({'banked': KIT})))
        expect(kind_of(step)).to_be('withdraw')
    test('the kit is drawn before the quest is started', _fn8)

    def _fn9():
        step = decide(snapshot(Record({'carried': KIT})))
        expect(name_of(step)).to_contain('King Lathas')
    test('with the kit in the pack, an unstarted quest goes to King Lathas', _fn9)

    # Why: treating the started bit as a stage loops back to Lathas.
    def _fn10():
        step = decide(snapshot(Record({'carried': KIT, 'flags': [UP_FLAG.STARTED]})))
        expect(name_of(step)).not_.to_contain('King Lathas')
    test('started is a flag on stage zero and routes to Koftik, not back to Lathas', _fn10)

    # Why: West Ardougne needs an explicit wall crossing before Koftik is reachable.
    def _fn11():
        step = decide(snapshot(Record({'carried': KIT, 'flags': [UP_FLAG.STARTED]})))
        expect(name_of(step)).to_contain('West Ardougne')
    test('Koftik is behind the wall, so the crossing comes first', _fn11)

    def _fn12():
        step = decide(snapshot(Record({'carried': KIT, 'flags': [UP_FLAG.STARTED], 'tile': WEST_ARDOUGNE})))
        expect(name_of(step)).to_contain('Koftik')
    test('inside West Ardougne it goes to Koftik instead of crossing again', _fn12)

    # Why: the one-way pass has no bank after the entrance.
    def _fn13():
        step = decide(snapshot(Record({'stage': UP_STAGE.SPOKEN_KOFTIK, 'tile': WEST_ARDOUGNE, 'carried': [UP_ITEM.TINDERBOX.id], 'banked': []})))
        expect(kind_of(step)).to_be('wait')
        expect(reason_of(step)).to_contain('a bow')
    test('a pack short of the kit refuses to descend and names what is missing', _fn13)

    # Why: `upass_bridge.rs2` accepts the full `weapon_bow` category.
    def _fn14():
        no_plain_bow = [s for s in KIT if s != UP_ITEM.SHORTBOW.id]
        step = decide(snapshot(Record({
        'stage': UP_STAGE.SPOKEN_KOFTIK,
        'tile': WEST_ARDOUGNE,
        'carried': list(no_plain_bow) + [ITEM_ID.OAK_SHORTBOW],
    })))
        expect(kind_of(step)).not_.to_be('wait')
    test('any bow satisfies the bridge shot, not only the plain shortbow', _fn14)

    # Why: crossbows use `weapon_crossbow`, not the required `weapon_bow` category.
    def _fn15():
        no_plain_bow = [s for s in KIT if s != UP_ITEM.SHORTBOW.id]
        step = decide(snapshot(Record({
        'stage': UP_STAGE.SPOKEN_KOFTIK,
        'tile': WEST_ARDOUGNE,
        'carried': list(no_plain_bow) + [ITEM_ID.CROSSBOW],
        'banked': [],
    })))
        expect(kind_of(step)).to_be('wait')
        expect(reason_of(step)).to_contain('bow')
    test('a crossbow is not a bow', _fn15)

    # Why: tier-name matching previously missed dragon and poisoned daggers.
    def _fn16():
        for weapon in ['dragon dagger', 'dragon dagger(p)', 'poisoned dagger(p)']:
            step = decide(snapshot(Record({'carried': KIT, 'worn_names': [weapon], 'flags': [UP_FLAG.STARTED]})))
            expect(reason_of(step)).not_.to_contain('melee weapon')
    test('a dragon dagger counts as a melee weapon, poisoned or not', _fn16)

    # Why: Aemad sells rope near the bank this quest already uses.
    def _fn17():
        no_rope = [s for s in KIT if not isinstance(s, list) or s[0] != UP_ITEM.ROPE.id]
        step = decide(snapshot(Record({'carried': list(no_rope) + [[UP_ITEM.COINS.id, 5000]]})))
        expect(kind_of(step)).to_be('buy')
        expect((step).item).to_be(UP_ITEM.ROPE.name)
        expect((step).shop.npc).to_be('Aemad')
    test('rope the bank does not have is bought at Aemad', _fn17)

    # Why: Lowe is the supported fallback when the bank has no bow.
    def _fn18():
        no_bow = [s for s in KIT if s != UP_ITEM.SHORTBOW.id]
        step = decide(snapshot(Record({'carried': list(no_bow) + [[UP_ITEM.COINS.id, 5000]]})))
        expect(kind_of(step)).to_be('buy')
        expect((step).shop.npc).to_be('Lowe')
    test('a bow the bank does not have is bought at Lowe', _fn18)

    # Why: sending a broke account to Aemad would retry the failed purchase forever.
    def _fn19():
        no_rope = [s for s in KIT if not isinstance(s, list) or s[0] != UP_ITEM.ROPE.id]
        expect(kind_of(decide(snapshot(Record({'carried': no_rope, 'banked': []}))))).not_.to_be('buy')
        at_the_mouth = decide(snapshot(Record({'stage': UP_STAGE.SPOKEN_KOFTIK, 'tile': WEST_ARDOUGNE, 'carried': no_rope, 'banked': []})))
        expect(kind_of(at_the_mouth)).to_be('wait')
        expect(reason_of(at_the_mouth)).to_contain('Rope')
    test('with no coins anywhere it never walks to a counter it cannot pay', _fn19)

    # Why: without coins, report the shortfall before walking to a shop.
    def _fn20():
        step = decide(snapshot(Record({'stage': UP_STAGE.SPOKEN_KOFTIK, 'tile': WEST_ARDOUGNE, 'carried': [UP_ITEM.TINDERBOX.id], 'banked': []})))
        expect(kind_of(step)).to_be('wait')
        expect(reason_of(step)).to_contain('Rope')
    test('short of kit and coins alike, it stops and names the shortfall', _fn20)

    def _fn21():
        step = decide(snapshot(Record({'stage': UP_STAGE.SPOKEN_KOFTIK, 'tile': AREA1, 'carried': KIT})))
        expect(name_of(step)).to_contain('damp cloth')
    test('in the first cavern with no cloth, it asks Koftik for one', _fn21)

    def _fn22():
        step = decide(snapshot(Record({'stage': UP_STAGE.SPOKEN_KOFTIK, 'tile': AREA1, 'carried': list(KIT) + [UP_ITEM.DAMP_CLOTH.id]})))
        expect(name_of(step)).to_contain('fire arrow')
    test('with the cloth it builds the fire arrow', _fn22)

    def _fn23():
        step = decide(snapshot(Record({'stage': UP_STAGE.SPOKEN_KOFTIK, 'tile': AREA1, 'carried': list(KIT) + [UP_ITEM.LIT_ARROW.id]})))
        expect(name_of(step)).to_contain('wield')
    test('a lit arrow in the pack is wielded before the shot', _fn23)

    def _fn24():
        step = decide(snapshot(Record({
        'stage': UP_STAGE.SPOKEN_KOFTIK,
        'tile': AREA1,
        'carried': KIT,
        'worn_id_list': [UP_ITEM.LIT_ARROW.id, UP_ITEM.SHORTBOW.id],
    })))
        expect(name_of(step)).to_contain('stay rope')
    test('a lit arrow already worn fires at the stay rope', _fn24)

    # Why: which orbs are already dark is not answerable from a snapshot, a burned orb has left the pack, and neither the trap nor the ground spawns hand over a second one. A per-site decide cycle therefore picks the same site forever, so the sweep is one step from end to end that keeps its own tally.
    def _fn25():
        inside = Record({'x': 2460, 'z': 9678, 'level': 0})
        for carried in [[], [UP_ITEM.ORB1.id], [UP_ITEM.ORB1.id, UP_ITEM.ORB2.id, UP_ITEM.ORB3.id]]:
            step = decide(snapshot(Record({'stage': UP_STAGE.PASSED_BRIDGE, 'tile': inside, 'carried': carried})))
            expect(name_of(step)).to_contain('orbs')
    test('past the grid, the orb phase is a single step whatever the pack holds', _fn25)

    def _fn26():
        step = decide(snapshot(Record({'stage': UP_STAGE.PASSED_BRIDGE, 'tile': Record({'x': 2479, 'z': 9679, 'level': 0})})))
        expect(name_of(step)).to_contain('grid')
    test('east of the grid it crosses before sweeping orbs', _fn26)

    # Why: the bridge-and-rope shelf overlaps the orb corridor's bounding box on x 2431-2464 / z 9686-9731, and a plain box read the shelf as the corridor. One run drifted onto the rope shelf, declared the grid crossed and spent six minutes clicking at stepping stones on the far side of a seam.
    def _fn27():
        for tile in [
        Record({'x': 2442, 'z': 9716, 'level': 0}),
        Record({'x': 2460, 'z': 9693, 'level': 0}),
        Record({'x': 2446, 'z': 9697, 'level': 0}),
    ]:
            expect(name_of(decide(snapshot(Record({'stage': UP_STAGE.PASSED_BRIDGE, 'tile': tile}))))).to_contain('grid')
    test('the bridge and rope shelf is not mistaken for the corridor past the grid', _fn27)

    def _fn28():
        for tile in [
        Record({'x': 2416, 'z': 9698, 'level': 0}),
        Record({'x': 2382, 'z': 9668, 'level': 0}),
        Record({'x': 2464, 'z': 9677, 'level': 0}),
    ]:
            expect(name_of(decide(snapshot(Record({'stage': UP_STAGE.PASSED_BRIDGE, 'tile': tile}))))).to_contain('orbs')
    test('the far west of the corridor still reads as past the grid', _fn28)

    def _fn29():
        step = decide(snapshot(Record({
        'stage': UP_STAGE.CONFRONTED_IBAN,
        'tile': Record({'x': 2140, 'z': 4647, 'level': 1}),
        'carried': [UP_ITEM.DOLL.id],
        'flags': [UP_FLAG.DOLL_COMPLETE],
    })))
        expect(name_of(step)).to_contain('pit of the damned')
    test('a finished doll at the confronted stage is thrown into the pit', _fn29)

    # Why: the temple throws the player into the second cavern, which has no walkable way back up, Koftik's
    # dialogue is the transport. Each step of the walk out is keyed on where the last one landed.
    def _fn30():
        legs = [
        [Record({'x': 2482, 'z': 9607, 'level': 0}), 'Koftik'],
        [AREA1, 'leave the underground pass'],
        [WEST_ARDOUGNE, 'East Ardougne'],
        [ARDOUGNE, 'King Lathas'],
    ]
        for tile, expected in legs:
            expect(name_of(decide(snapshot(Record({'stage': UP_STAGE.DEFEATED_IBAN, 'tile': tile}))))).to_contain(expected)
    test('the walk out is keyed on where the last step landed', _fn30)

    # Why: the doll comes out of a chest in a fifteen-tile pocket whose only exit is a door the collision pack calls blocked, so a leg that lifts it ends shut in and every later step answers "unreachable". A live run spent fifty-five minutes there. The way out has to come before anything else, at any stage.
    def _fn31():
        inside = [
        Record({'x': 2156, 'z': 4566, 'level': 1}),
        Record({'x': 2151, 'z': 4566, 'level': 1}),
        Record({'x': 2157, 'z': 4565, 'level': 1}),
    ]
        for tile in inside:
            step = decide(snapshot(Record({'stage': UP_STAGE.FOUND_DOLL, 'carried': [UP_ITEM.DOLL.id], 'tile': tile})))
            expect(name_of(step)).to_contain("out of Kardia's house")
    test("being shut in Kardia's house outranks every other step", _fn31)

    # Why: the door tile and the platform outside it are one tile apart from the pocket and must not be
    # read as inside it, or the module lets itself out of a house it is already standing outside, forever.
    def _fn32():
        for tile in [Record({'x': 2158, 'z': 4566, 'level': 1}), Record({'x': 2158, 'z': 4567, 'level': 1})]:
            step = decide(snapshot(Record({'stage': UP_STAGE.FOUND_DOLL, 'carried': [UP_ITEM.DOLL.id], 'tile': tile})))
            expect(name_of(step)).not_.to_contain("out of Kardia's house")
    test('the door tile and the platform outside it are not the house', _fn32)

    # Why: taking the blood leaves the character on Kalrag's own tile, one pocket with the dwarf camp but a different area name. A live run read that as "on the platforms" and spent seven attempts walking at a level-1 cage from level 0. Every step below has to accept both names.
    def _fn33():
        KALRAG = Record({'x': 2356, 'z': 9911, 'level': 0})
        doll = [UP_ITEM.DOLL.id, UP_ITEM.GAUNTLETS.id]
        with_blood = decide(snapshot(Record({
        'stage': UP_STAGE.FOUND_DOLL,
        'carried': doll,
        'tile': KALRAG,
        'flags': [UP_FLAG.ASHES_ON_DOLL, UP_FLAG.BLOOD_ON_DOLL],
    })))
        expect(name_of(with_blood)).to_contain('climb back up')
        no_ashes = decide(snapshot(Record({'stage': UP_STAGE.FOUND_DOLL, 'carried': doll, 'tile': KALRAG})))
        expect(name_of(no_ashes)).not_.to_contain('climb down')
    test("Kalrag's side of the cave is below, not on the platforms", _fn33)

    # Why: every value the journal can report is now routed, so this guards the shape of the fallback,
    # a stage the module does not know has to name itself and stop, not retry the last step it did know.
    def _fn34():
        step = decide(snapshot(Record({'stage': -1, 'tile': AREA1})))
        expect(kind_of(step)).to_be('wait')
        expect(reason_of(step)).to_contain('-1')
    test('a stage the module does not know waits with the stage named', _fn34)


describe('Underground Pass decide()', _fn2)


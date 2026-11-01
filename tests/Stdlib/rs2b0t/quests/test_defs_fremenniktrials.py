"""Ported from rs2b0t's test/api/ai/quests/defs/fremenniktrials.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.fremenniktrials import FT_ID, decide, fremenniktrials, riddle_answer
from rs2004.quests.defs.fremenniktrials.areas import MAZE_ROUTE
from rs2004.quests.defs.fremenniktrials.bard import reset_bard_latch
from rs2004.quests.defs.fremenniktrials.hunter import around, middle, narrow
from rs2004.quests.defs.fremenniktrials.journal import FT_STAGE
from rs2004.quests.defs.fremenniktrials.navigator import maze_leg_at

ALL_TRIALS = ['navigator', 'merchant', 'hunter', 'seer', 'warrior', 'reveller', 'bard']


def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        _v1 = out.get(key)
        out[key] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def id_counts(ids):
    out = {}
    for id in ids:
        _v2 = out.get(id)
        out[id] = ((_v2 if _v2 is not None else 0)) + 1
    return out


def snap(options=None):
    if options is None:
        options = Record({})
    flags = set((options.flags if options.flags is not None else []))
    inv = counts((options.inv if options.inv is not None else []))
    bank = counts((options.bank if options.bank is not None else []))
    if options.coins is not None:
        inv['coins'] = options.coins
    if options.banked_coins is not None:
        bank['coins'] = options.banked_coins
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': inv,
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set([n.lower() for n in ((options.worn if options.worn is not None else []))]),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (options.votes if options.votes is not None else 0),
        'progress': Record({'stage': (options.votes if options.votes is not None else 0), 'flags': flags}),
        'bank': bank,
        'bank_ids': id_counts((options.bank_ids if options.bank_ids is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (options.tile if options.tile is not None else None),
        'free_slots': 28,
    })


def only(trial, extra=None):
    """Every trial won but the one named, so `decide` has to fall through to it."""
    if extra is None:
        extra = []
    return list([f'{t}-done' for t in [t for t in ALL_TRIALS if t != trial]]) + list(extra)


def talk_to(step):
    return ((step.stop.npc if step.kind == 'talk' else None))


def seer(extra=None):
    if extra is None:
        extra = []
    return only('seer', ['warrior-started', 'seer-started'] + list(extra))


def custom_name(step):
    return ((step.name if step.kind == 'custom' else None))


def _fn3():
    def _fn4():
        expect(decide(snap(Record({'journal': 'unknown'})))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list has not loaded', _fn4)

    def _fn5():
        expect(decide(snap(Record({'journal': 'complete'})))).to_equal(Record({'kind': 'done'}))
    test('is done when the list is green', _fn5)

    def _fn6():
        expect(decide(snap(Record({'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before deciding anything else', _fn6)

    def _fn7():
        step = decide(snap(Record({'votes': FT_STAGE.NOT_STARTED, 'journal': 'not_started'})))
        expect(talk_to(step)).to_be('Brundt the Chieftain')
    test('starts by asking Brundt for a quest', _fn7)

    def _fn8():
        step = decide(snap(Record({'votes': 7, 'flags': [f'{t}-done' for t in ALL_TRIALS]})))
        expect(talk_to(step)).to_be('Brundt the Chieftain')
    test('returns to Brundt once seven votes are in', _fn8)

    def _fn9():
        expect(talk_to(decide(snap()))).to_be('Manni the Reveller')
    test('opens the reveller trial before any other', _fn9)


describe('The Fremennik Trials decide', _fn3)


def _fn10():
    def _fn11():
        step = decide(snap(Record({'flags': only('reveller', ['reveller-started']), 'coins': 1000})))
        expect(custom_name(step)).to_be('buy a low alcohol keg (250gp)')
    test('buys the low alcohol keg first', _fn11)

    def _fn12():
        step = decide(snap(Record({'flags': only('reveller', ['reveller-started']), 'banked_coins': 5000})))
        expect(step.kind).to_be('withdraw')
    test('withdraws coins when the pack cannot cover the keg', _fn12)

    def _fn13():
        step = decide(snap(Record({
        'flags': only('reveller', ['reveller-started']),
        'inv': ['Tinderbox'],
        'inv_ids': [FT_ID.LOW_ALCOHOL_KEG],
        'coins': 1000,
    })))
        expect(custom_name(step)).to_be("buy a beer at the Forester's Arms")
    test('buys a beer for the workman once the keg is carried', _fn13)

    def _fn14():
        step = decide(snap(Record({
        'flags': only('reveller', ['reveller-started']),
        'inv': ['Tinderbox', 'Beer'],
        'inv_ids': [FT_ID.LOW_ALCOHOL_KEG],
    })))
        expect(step).to_match_object(Record({'kind': 'use_on', 'item': 'Beer', 'target': 'Council workman'}))
    test('turns the beer into a firecracker at the bridge workman', _fn14)

    def _fn15():
        step = decide(snap(Record({
        'flags': only('reveller', ['reveller-started']),
        'inv': ['Tinderbox'],
        'inv_ids': [FT_ID.LOW_ALCOHOL_KEG, FT_ID.FIRECRACKER],
    })))
        expect(step).to_match_object(Record({'kind': 'grab_ground', 'item': 'Keg of beer'}))
    test('takes the keg off the table once the firecracker is in hand', _fn15)

    def _fn16():
        step = decide(snap(Record({'flags': only('reveller', ['reveller-started']), 'inv_ids': [FT_ID.BEER_KEG]})))
        expect(custom_name(step)).to_be('drink Manni under the table')
    test('drinks only after the swap has spent the low alcohol keg', _fn16)


describe("Manni's drinking contest", _fn10)


def _fn17():
    def bard(extra=None):
        if extra is None:
            extra = []
        return only('bard', ['bard-started'] + list(extra))

    def _fn18():
        step = decide(snap(Record({'flags': bard()})))
        expect(step).to_match_object(Record({'kind': 'grab_ground', 'item': 'Bronze axe'}))
    test('picks up the Rellekka axe spawn when the bank has none', _fn18)

    def _fn19():
        step = decide(snap(Record({'flags': bard(), 'inv': ['Bronze axe']})))
        expect(step).to_match_object(Record({'kind': 'pick_loc', 'loc': 'Swaying tree'}))
    test('cuts the musical tree once an axe is carried', _fn19)

    def _fn20():
        step = decide(snap(Record({'flags': bard(), 'inv': ['Bronze axe', 'Knife'], 'inv_ids': [FT_ID.BRANCH]})))
        expect(custom_name(step)).to_be('carve the branch into an unstrung lyre')
    test('carves the branch with a knife', _fn20)

    def _fn21():
        reset_bard_latch()
        step = decide(snap(Record({'flags': bard(), 'inv_ids': [FT_ID.UNSTRUNG_LYRE]})))
        expect(custom_name(step)).to_be('ask Lalli who traded him the wool')
    test('asks Lalli before Askeladden for the pet rock', _fn21)

    def _fn22():
        step = decide(snap(Record({'flags': bard(), 'inv_ids': [FT_ID.UNSTRUNG_LYRE, FT_ID.PET_ROCK]})))
        expect(step).to_match_object(Record({'kind': 'pick_loc', 'loc': 'Cabbage'}))
    test('picks the stew vegetables once the rock is carried', _fn22)

    def _fn23():
        step = decide(snap(Record({'flags': bard(), 'inv_ids': [FT_ID.UNSTRUNG_LYRE, FT_ID.GOLDEN_FLEECE]})))
        expect(custom_name(step)).to_be('spin the fleece at the Seers spinning wheel')
    test('spins the fleece before stringing the lyre', _fn23)

    def _fn24():
        step = decide(snap(Record({'flags': bard(), 'inv_ids': [FT_ID.UNSTRUNG_LYRE, FT_ID.GOLDEN_WOOL]})))
        expect(custom_name(step)).to_be('string the lyre with golden wool')
    test('strings the lyre with the spun wool', _fn24)

    def _fn25():
        step = decide(snap(Record({'flags': bard(), 'inv_ids': [FT_ID.LYRE]})))
        expect(step).to_match_object(Record({'kind': 'buy', 'item': 'Raw shark'}))
    test('buys the shark from Rufus when neither pack nor bank has one', _fn25)

    def _fn26():
        step = decide(snap(Record({'flags': bard(), 'inv_ids': [FT_ID.LYRE], 'bank_ids': [FT_ID.RAW_SHARK]})))
        expect(step.kind).to_be('withdraw')
    test('withdraws a banked shark rather than walking to Canifis', _fn26)

    def _fn27():
        step = decide(snap(Record({'flags': bard(), 'inv_ids': [FT_ID.ENCHANTED_LYRE]})))
        expect(custom_name(step)).to_be('play the lyre on the longhall stage')
    test('plays the enchanted lyre on the stage', _fn27)


describe("Olaf's lyre", _fn17)


def _fn28():
    def merchant(extra=None):
        if extra is None:
            extra = []
        return only('merchant', ['merchant-started'] + list(extra))

    def _fn29():
        expect(custom_name(decide(snap(Record({'flags': merchant()}))))).to_be('ask the Sailor and then Olaf about the flower')
    test('opens the chain with the Sailor and Olaf', _fn29)

    def _fn30():
        asks = {
        'olaf': 'Yrsa',
        'yrsa': 'Brundt the Chieftain',
        'chief': 'Sigli the Huntsman',
        'sigli': 'Skulgrimen',
        'skul': 'Fisherman',
        'fisherman': 'Swensen the Navigator',
        'swensen': 'Peer the Seer',
        'seer': 'Thorvald the Warrior',
        'thorvald': 'Manni the Reveller',
        'manni': 'Thora the Barkeep',
    }
        for at, npc in asks.items():
            expect(talk_to(decide(snap(Record({'flags': merchant([f'merchant-at:{at}'])}))))).to_be(npc)
    test('walks the ask chain by the step the journal names', _fn30)

    def _fn31():
        expect(talk_to(decide(snap(Record({'flags': merchant(['merchant-at:thora']), 'coins': 5000}))))).to_be('Askeladden')
        expect(decide(snap(Record({'flags': merchant(['merchant-at:thora']), 'banked_coins': 20000}))).kind).to_be('withdraw')
    test('pays Askeladden his five thousand', _fn31)

    def _fn32():
        handovers = [
        [FT_ID.PROMISSORY_NOTE, 'Thora the Barkeep'],
        [FT_ID.COCKTAIL, 'Manni the Reveller'],
        [FT_ID.CHAMPIONS_TOKEN, 'Thorvald the Warrior'],
        [FT_ID.WARRIORS_CONTRACT, 'Peer the Seer'],
        [FT_ID.FORECAST, 'Swensen the Navigator'],
        [FT_ID.SEA_MAP, 'Fisherman'],
        [FT_ID.UNUSUAL_FISH, 'Skulgrimen'],
        [FT_ID.BOWSTRING, 'Sigli the Huntsman'],
        [FT_ID.HUNTERS_MAP, 'Brundt the Chieftain'],
        [FT_ID.FISCAL_STATEMENT, 'Yrsa'],
        [FT_ID.STURDY_BOOTS, 'Olaf the Bard'],
        [FT_ID.BALLAD, 'Sailor'],
        [FT_ID.FLOWER, 'Sigmund The Merchant'],
    ]
        for id, npc in handovers:
            expect(talk_to(decide(snap(Record({'flags': merchant(), 'inv_ids': [id]}))))).to_be(npc)
    test('hands each traded good to the councillor who wants it', _fn32)


describe("Sigmund's flower chain", _fn28)


def _fn33():
    def _fn34():
        expect(talk_to(decide(snap(Record({'flags': seer(), 'inv': ['Coins']}))))).to_be('Peer the Seer')
    test('has Peer bank everything before the door', _fn34)

    def _fn35():
        expect(custom_name(decide(snap(Record({'flags': seer()}))))).to_be("solve the lock on Peer's door")
    test('solves the lock once the pack is empty', _fn35)

    def _fn36():
        step = decide(snap(Record({'flags': seer(), 'tile': Record({'x': 2631, 'z': 3665, 'level': 0})})))
        expect(custom_name(step)).to_be('climb to the puzzle floor')
    test('climbs to the puzzle floor from the west room', _fn36)

    def _fn37():
        step = decide(snap(Record({'flags': seer(), 'tile': Record({'x': 2632, 'z': 3662, 'level': 2})})))
        expect(custom_name(step)).to_be('take the red disk from the unicorn head')
    test('collects the unicorn disk first on the puzzle floor', _fn37)

    def _fn38():
        step = decide(snap(Record({
        'flags': seer(),
        'tile': Record({'x': 2632, 'z': 3662, 'level': 2}),
        'inv_ids': [FT_ID.RED_DISK, FT_ID.WOODEN_DISK, FT_ID.RED_HERRING],
    })))
        expect(custom_name(step)).to_be('cook the red herring for its dye')
    test('cooks the herring for its dye', _fn38)

    def _fn39():
        floor = Record({'x': 2632, 'z': 3662, 'level': 2})
        two = [FT_ID.RED_DISK, FT_ID.RED_DISK]

        def at(ids):
            return custom_name(decide(snap(Record({'flags': seer(), 'tile': floor, 'inv_ids': list(two) + list(ids)}))))
        expect(at([])).to_be('open the chest and take the jug')
        expect(at([FT_ID.JUG_EMPTY])).to_be('open the cupboard and take the bucket')
        expect(at([FT_ID.JUG_EMPTY, FT_ID.BUCKET_EMPTY])).to_be('fill the jug from the tap')
        expect(at([FT_ID.JUG_3, FT_ID.BUCKET_EMPTY])).to_be('pour the jug into the bucket')
        expect(at([FT_ID.JUG_3, FT_ID.BUCKET_3])).to_be('pour the jug into the bucket')
        expect(at([FT_ID.JUG_1, FT_ID.BUCKET_5])).to_be('empty the bucket down the drain')
        expect(at([FT_ID.JUG_1, FT_ID.BUCKET_EMPTY])).to_be('pour the jug into the bucket')
        expect(at([FT_ID.JUG_EMPTY, FT_ID.BUCKET_1])).to_be('fill the jug from the tap')
        expect(at([FT_ID.JUG_3, FT_ID.BUCKET_1])).to_be('pour the jug into the bucket')
        expect(at([FT_ID.JUG_EMPTY, FT_ID.BUCKET_4])).to_be('balance the scales with a four-fifths bucket')
    test('measures four fifths with the three-jug and the five-bucket', _fn39)

    def _fn40():
        step = decide(snap(Record({'flags': seer(), 'tile': Record({'x': 2632, 'z': 3662, 'level': 2}), 'inv_ids': [FT_ID.VASE]})))
        expect(custom_name(step)).to_be('take the trapdoor down to the mural')
    test('takes the vase down to the mural for its lid', _fn40)

    def _fn41():
        step = decide(snap(Record({
        'flags': seer(),
        'tile': Record({'x': 2636, 'z': 3665, 'level': 0}),
        'inv_ids': [FT_ID.VASE, FT_ID.RED_DISK],
    })))
        expect(custom_name(step)).to_be('press a red disk into the mural')
    test('presses the disks into the mural downstairs', _fn41)

    def _fn42():
        floor = Record({'x': 2632, 'z': 3662, 'level': 2})
        expect(custom_name(decide(snap(Record({'flags': seer(), 'tile': floor, 'inv_ids': [FT_ID.VASE, FT_ID.VASE_LID]}))))).to_be('fill the vase from the tap')
        expect(custom_name(decide(snap(Record({'flags': seer(), 'tile': floor, 'inv_ids': [FT_ID.VASE_WATER, FT_ID.VASE_LID]}))))).to_be('screw the lid onto the full vase')
        expect(custom_name(decide(snap(Record({'flags': seer(), 'tile': floor, 'inv_ids': [FT_ID.SEALED_VASE_WATER]}))))).to_be('freeze the sealed vase until it shatters')
        expect(custom_name(decide(snap(Record({'flags': seer(), 'tile': floor, 'inv_ids': [FT_ID.FROZEN_KEY]}))))).to_be('melt the ice off the key')
        expect(custom_name(decide(snap(Record({'flags': seer(), 'tile': floor, 'inv_ids': [FT_ID.SEERS_KEY]}))))).to_be('take the trapdoor down to the locked door')
        expect(custom_name(decide(snap(Record({'flags': seer(), 'tile': Record({'x': 2636, 'z': 3665, 'level': 0}), 'inv_ids': [FT_ID.SEERS_KEY]}))))).to_be('unlock the far door')
    test('freezes the sealed vase and melts the key out', _fn42)


describe("Peer's puzzle house", _fn33)


def _fn43():
    def warrior(extra=None):
        if extra is None:
            extra = []
        return only('warrior', ['warrior-started'] + list(extra))

    def _fn44():
        expect(custom_name(decide(snap(Record({'flags': warrior()}))))).to_be("climb down to Thorvald's battleground")
    test('climbs down with an empty pack', _fn44)

    def _fn45():
        expect(talk_to(decide(snap(Record({'flags': warrior(), 'worn': ['Rune chainbody']}))))).to_be('Peer the Seer')
    test('banks through Peer while anything is still worn', _fn45)

    def _fn46():
        step = decide(snap(Record({'flags': warrior(), 'tile': Record({'x': 2671, 'z': 10098, 'level': 2})})))
        expect(custom_name(step)).to_be('fight Koschei to the death')
    test('fights once it is down there', _fn46)

    def _fn47():
        step = decide(snap(Record({'flags': warrior(), 'tile': Record({'x': 2667, 'z': 3692, 'level': 1})})))
        expect(custom_name(step)).to_be('climb down from the loft')
    test('climbs out of the loft the honourable death drops it in', _fn47)

    def _fn48():
        won = [f'{t}-done' for t in ALL_TRIALS]
        step = decide(snap(Record({'votes': 7, 'flags': won, 'tile': Record({'x': 2667, 'z': 3692, 'level': 1})})))
        expect(custom_name(step)).to_be('climb down from the loft')
    test('climbs out of the loft before walking to Brundt for the seventh vote', _fn48)


describe("Thorvald's battleground", _fn43)


def _fn49():
    def _fn50():
        answers = [
        ['My first is in mage, but not in wizard.', 'MIND'],
        ['My first is in tar, but not in a swamp.', 'TREE'],
        ['My first is in the well, but not at sea.', 'LIFE'],
        ['My first is in fish, but not in the sea.', 'FIRE'],
        ['My first is in water, and also in tea.', 'TIME'],
        ['My first is in wizard, but not in a mage.', 'WIND'],
    ]
        for plaque, word in answers:
            expect(riddle_answer(plaque)).to_be(word)
    test('answers every riddle the door can roll', _fn50)

    def _fn51():
        expect(riddle_answer('My whole wears more rings the older I get.')).to_be('TREE')
        expect(riddle_answer('My whole cannot die as long as it has food.')).to_be('FIRE')
    test('answers from the second plaque alone', _fn51)

    def _fn52():
        expect(riddle_answer('My first is in nothing at all.')).to_be_null()
    test('does not guess at an unknown plaque', _fn52)


describe('the combination lock', _fn49)


def _fn53():
    def _fn54():
        expect(fremenniktrials.record.requirements.skills).to_equal([
        Record({'skill': 'woodcutting', 'level': 40}),
        Record({'skill': 'crafting', 'level': 40}),
        Record({'skill': 'fletching', 'level': 25}),
    ])
    test('names the three skill floors the trials gate on', _fn54)

    def _fn55():
        expect(fremenniktrials.owns_inventory).to_be(True)
        expect(fremenniktrials.bank).to_match_object(Record({'x': 2725, 'z': 3491}))
    test('owns its own inventory and banks in Seers Village', _fn55)


describe('the quest record', _fn53)


def _fn56():
    full = Record({'xlo': 2600, 'xhi': 2760, 'zlo': 3540, 'zhi': 3720})

    def _fn57():
        expect(middle(full)).to_match_object(Record({'x': 2680, 'z': 3630}))
    test('starts aiming at the middle of the province', _fn57)

    def _fn58():
        expect(narrow(full, Record({'x': 2680, 'z': 3630}), 'north-east')).to_equal(Record({'xlo': 2681, 'xhi': 2760, 'zlo': 3631, 'zhi': 3720}))
    test('a diagonal bearing cuts both axes to the named side', _fn58)

    def _fn59():
        expect(narrow(full, Record({'x': 2680, 'z': 3630}), 'west')).to_equal(Record({'xlo': 2600, 'xhi': 2679, 'zlo': 3630, 'zhi': 3630}))
    test('a straight bearing pins the axis it says nothing about', _fn59)

    def _fn60():
        pinched = Record({'xlo': 2700, 'xhi': 2760, 'zlo': 3540, 'zhi': 3720})
        expect(narrow(pinched, Record({'x': 2690, 'z': 3600}), 'west')).to_be_null()
    test('halves that cross over give the search nothing to aim at', _fn60)

    def _fn61():
        expect(around(Record({'x': 2604, 'z': 3716}))).to_equal(Record({'xlo': 2600, 'xhi': 2616, 'zlo': 3704, 'zhi': 3720}))
    test('reopening around the character stays inside the province', _fn61)

    def _fn62():
        expect(narrow(full, Record({'x': 2688, 'z': 3626}), 'nowhere')).to_be(full)
    test('an unreadable bearing leaves the box alone', _fn62)

    def _fn63():
        north = narrow(full, Record({'x': 2688, 'z': 3626}), 'north')
        closing = narrow(north, Record({'x': 2688, 'z': 3660}), 'south')
        expect(middle(closing)).to_match_object(Record({'x': 2688, 'z': 3643}))
    test('the box closes between two readings that bracket the Draugen', _fn63)


describe("the Draugen's search box", _fn56)


def _fn64():
    def tile(x, z):
        return (Record({'x': x, 'z': z, 'level': 0}))

    def _fn65():
        expect(maze_leg_at(tile(2631, 10004))).to_be(0)
    test('the ladder entry reads as the start of the route', _fn65)

    def _fn66():
        for i, hop in enumerate(MAZE_ROUTE):
            expect(maze_leg_at(tile(hop.land.x, hop.land.z))).to_be(i + 1)
    test('each landing reads as the leg that portal just finished', _fn66)

    def _fn67():
        for i, hop in enumerate(MAZE_ROUTE):
            expect(maze_leg_at(tile(hop.stand.x, hop.stand.z))).to_be(i)
    test('each stand reads as the leg whose portal is still to come', _fn67)

    def _fn68():
        expect(maze_leg_at(tile(2645, 10045))).to_be(-1)
    test('a tile in neither set is scattered', _fn68)

    def _fn69():
        expect(maze_leg_at(None)).to_be(-1)
    test('no tile is read at all when the scene has no player', _fn69)


describe("Swensen's maze — where the route thinks we are", _fn64)


def resumes_in_the_trials():
    room = Record({'x': 2632, 'z': 3662, 'level': 2})
    expect(fremenniktrials.resume_at(room)).to_be(True)
    expect(fremenniktrials.resume_at(Record({'x': 2726, 'z': 3491, 'level': 0}))).to_be(False)
    step = decide(snap(Record({'flags': seer(), 'tile': room, 'bank_known': False})))
    expect(step.kind).not_.to_be('scan_bank')


test('a restart on the puzzle floor carries on with the trial, without a bank scan', resumes_in_the_trials)


def warns_below_the_proven_prayer():
    levels = {'woodcutting': 40, 'crafting': 40, 'fletching': 25, 'prayer': 43}
    spy_on(skills, 'level', impl=lambda skill: levels[skill])
    expect(fremenniktrials.warn_readiness()).to_contain('wants Prayer 70')


test('Prayer 43 unlocks the protection but is warned about, since it runs dry against Koschei', warns_below_the_proven_prayer)

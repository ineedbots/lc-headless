"""Ported from rs2b0t's src/bot/../../test/scripts/RoguesPurse/RoguesPurseLogic.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from bots.roguespurse.logic import COINS, FARE, FARE_FLOAT, IDENTIFY_LEVEL, WALL_STAGE, check_gates, detour_cost, is_level_refusal, is_stage_refusal, plan_cycle, rank_banks_by_detour
from rs2004.quests.defs.junglepotion import JP_STAGE
def _fn1():
    def _fn2():
        expect(plan_cycle(Record({'continue_pending': False, 'unids': 0, 'identified': 0, 'free_slots': 28}))).to_equal(['search'])
    test('an empty pack only searches', _fn2)

    def _fn3():
        expect(plan_cycle(Record({'continue_pending': False, 'unids': 1, 'identified': 0, 'free_slots': 27}))).to_equal(['identify', 'search'])
    test('a carried unid identifies before the next search', _fn3)

    def _fn4():
        expect(plan_cycle(Record({'continue_pending': True, 'unids': 1, 'identified': 1, 'free_slots': 26}))).to_equal(['continue', 'identify', 'drop', 'search'])
    test('steady state is identify, drop, search — three user events plus a continue', _fn4)

    def _fn5():
        worst = plan_cycle(Record({'continue_pending': True, 'unids': 5, 'identified': 5, 'free_slots': 10}))
        expect(len(worst)).to_be_less_than_or_equal(4)
    test('four events at most, so the engine never defers part of the burst to the next tick', _fn5)

    def _fn6():
        expect((plan_cycle(Record({'continue_pending': True, 'unids': 0, 'identified': 0, 'free_slots': 28})) or [None])[0]).to_be('continue')
    test('the continue always leads — the objbox is what suspended the last search', _fn6)

    def _fn7():
        expect(plan_cycle(Record({'continue_pending': False, 'unids': 2, 'identified': 1, 'free_slots': 0}))).to_equal(['identify', 'drop'])
    test('a full pack stops searching (the engine would find a herb and bin it)', _fn7)

    def _fn8():
        expect(plan_cycle(Record({'continue_pending': False, 'unids': 0, 'identified': 28, 'free_slots': 0}))).to_equal(['drop'])
    test('a full pack of identified herbs still drains itself', _fn8)


describe('planCycle (one tick of packets)', _fn1)


def _fn9():
    def _fn10():
        expect(check_gates(Record({'herblore_level': 8, 'stage': JP_STAGE.COMPLETE}))).to_equal(Record({'ok': True}))
    test('a completed quest with the quest xp behind it passes', _fn10)

    def _fn11():
        expect(WALL_STAGE).to_be(JP_STAGE.GET_ROGUES_PURSE)
        expect(check_gates(Record({'herblore_level': 3, 'stage': WALL_STAGE})).ok).to_be(True)
        expect(check_gates(Record({'herblore_level': 3, 'stage': JP_STAGE.FOUND_ROGUES_PURSE})).ok).to_be(True)
        expect(check_gates(Record({'herblore_level': 3, 'stage': WALL_STAGE - 1})).ok).to_be(False)
        expect(check_gates(Record({'herblore_level': 3, 'stage': JP_STAGE.GET_SNAKE_WEED})).ok).to_be(False)
    test('the stage the wall actually wants is get_rogues_purse, not started', _fn11)

    def _fn12():
        for level in [0, 1, 2]:
            gate = check_gates(Record({'herblore_level': level, 'stage': JP_STAGE.COMPLETE}))
            expect(gate.ok).to_be(False)
            expect(gate.ok == False and gate.reason).to_contain(f'Herblore {IDENTIFY_LEVEL}')
        expect(check_gates(Record({'herblore_level': IDENTIFY_LEVEL, 'stage': JP_STAGE.COMPLETE})).ok).to_be(True)
    test('Herblore below 3 fails first, whatever the quest says', _fn12)

    def _fn13():
        gate = check_gates(Record({'herblore_level': 8, 'stage': JP_STAGE.NOT_STARTED}))
        expect(gate.ok).to_be(False)
        expect(gate.ok == False and gate.reason).to_contain('AIOQuester')
    test('an unstarted quest names the fix', _fn13)

    def _fn14():
        gate = check_gates(Record({'herblore_level': 8, 'stage': JP_STAGE.FOUND_SITO_FOIL}))
        expect(gate.ok).to_be(False)
        expect(gate.ok == False and gate.reason).to_contain(f'stage {JP_STAGE.FOUND_SITO_FOIL}')
    test('a mid-quest stage says which stage it saw', _fn14)

    def _fn15():
        expect(check_gates(Record({'herblore_level': 8, 'stage': None})).ok).to_be(False)
    test('an unreadable journal is not treated as eligible', _fn15)


describe('checkGates (both engine gates, before the walk to Karamja)', _fn9)


def _fn16():
    def _fn17():
        # The four ferry labels end in " ship"; anchoring keeps the Karamja shipyard gate out.
        ships = [sc for sc in SPECIAL_CROSSINGS if ((sc.label if sc.label is not None else '').lower().endswith(' ship'))]
        expect(len(ships)).to_be_greater_than(0)
        for ship in ships:
            expect((ship.requires.item if ship.requires is not None else None)).to_be(COINS)
            expect((ship.requires.count if ship.requires is not None else None)).to_be(FARE)
    test('FARE matches what the Karamja ship crossings actually charge', _fn17)

    def _fn18():
        gate = ([sc for sc in SPECIAL_CROSSINGS if ('al kharid' in (sc.label if sc.label is not None else '').lower())] or [None])[0]
        _v19 = ((gate.requires if gate is not None else None).count if (gate.requires if gate is not None else None) is not None else None)
        expect(FARE_FLOAT).to_be_greater_than_or_equal(FARE + ((_v19 if _v19 is not None else 0)))
    test('the float covers the fare and leaves change for the Al Kharid gate', _fn18)





def _fn20():
    # `p_teleport(map_findsquare(0_50_50_21_18, ...))` in player_death.
    LUMBRIDGE_DEATH = Record({'x': 3221, 'z': 3218, 'level': 0})
    POTHOLE = Record({'x': 2823, 'z': 3119, 'level': 0})

    def named(name):
        return ([b for b in BANK_LOCATIONS if b.name == name] or [None])[0]

    def _fn21():
        al_kharid = named('Al Kharid')
        draynor = named('Draynor')
        # Al Kharid is closer to the corpse. That is the trap.
        expect(bank_distance(LUMBRIDGE_DEATH, al_kharid.tile)).to_be_less_than(bank_distance(LUMBRIDGE_DEATH, draynor.tile))
        # ...but it is backwards, so it loses once the walk to Karamja is counted.
        expect(detour_cost(LUMBRIDGE_DEATH, draynor.tile, POTHOLE)).to_be_less_than(detour_cost(LUMBRIDGE_DEATH, al_kharid.tile, POTHOLE))
        ranked = rank_banks_by_detour(LUMBRIDGE_DEATH, POTHOLE, BANK_LOCATIONS)
        expect(([_i for _i, b in enumerate(ranked) if b.name == 'Draynor'] or [-1])[0]).to_be_less_than(([_i for _i, b in enumerate(ranked) if b.name == 'Al Kharid'] or [-1])[0])
    test('the Lumbridge death spawn banks at Draynor, not the nearer Al Kharid', _fn21)

    def _fn22():
        bank = Record({'x': 3093, 'z': 3243})
        expect(detour_cost(bank, bank, POTHOLE)).to_be_close_to(((POTHOLE.x - bank.x) ** 2 + (POTHOLE.z - bank.z) ** 2) ** 0.5)
    test('a bank we are standing on costs only the onward leg', _fn22)

    def _fn23():
        ranked = rank_banks_by_detour(LUMBRIDGE_DEATH, POTHOLE, BANK_LOCATIONS)
        expect(len(ranked)).to_be(len(BANK_LOCATIONS))
        for i in range(1, len(ranked)):
            expect(detour_cost(LUMBRIDGE_DEATH, ranked[i - 1].tile, POTHOLE)).to_be_less_than_or_equal(detour_cost(LUMBRIDGE_DEATH, ranked[i].tile, POTHOLE))
    test('ranking is stable and keeps every candidate', _fn23)





def _fn24():
    def _fn25():
        expect(is_stage_refusal('Unfortunately, you find nothing of interest.')).to_be(True)
        expect(is_stage_refusal('unfortunately you find nothing of interest')).to_be(True)
    test('the wall refusal is recognised as written by the engine', _fn25)

    def _fn26():
        expect(is_level_refusal('You cannot identify this herb.')).to_be(True)
    test('the identify refusal is recognised', _fn26)

    def _fn27():
        for line in [
        'You search the wall...',
        'You find a herb.',
        'You identify the herb. It is Rogues Purse.',
        'You need a higher Herblore level.',
    ]:
            expect(is_stage_refusal(line)).to_be(False)
            expect(is_level_refusal(line)).to_be(False)
    test('a successful search or identify is not a refusal', _fn27)


describe('refusal messages (the authoritative gate check at runtime)', _fn24)

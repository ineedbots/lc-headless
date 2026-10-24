"""rs2b0t's test/scripts/RangingGuild/ranging-guild-logic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe,
test and expect. runtime.test.ts stubs the client's facades, which pocketpy can't."""

from bots.rangingguild.logic import ARROW_RESTOCK_FEE, BOWS, ENTRY_FEE, JUDGE_PREFS, JUDGE_SPAWN, STAND, TARGETS, TICKETS_PER_RUNE_ARROWS
from bots.rangingguild.logic import WorldView, best_bow, classify_shot, decide, hit_label, hit_points, is_bow, pick_option, round_phase
from bots.rangingguild.logic import tickets_for_score


def idle(target_count=0, tickets=0, coins=1000, bow_worn=True, bow_held=False, bronze_worn=0, bronze_held=0):
    return WorldView(target_count, tickets, coins, bow_worn, bow_held, bronze_worn, bronze_held)


describe('round_phase', lambda: [
    test('0 is idle', lambda: expect(round_phase(0)).to_be('idle')),
    test('1 through 10 are shooting', lambda: [expect(round_phase(1)).to_be('shooting'), expect(round_phase(10)).to_be('shooting')]),
    test('11 is finished', lambda: expect(round_phase(11)).to_be('finished')),
    test('anything else reads as idle', lambda: expect(round_phase(99)).to_be('idle')),
])

describe('decide', lambda: [
    test('enters a round when idle with the fee', lambda: expect(decide(idle())).to_be('enter')),
    test('banks when idle without the fee', lambda: expect(decide(idle(coins=ENTRY_FEE - 1))).to_be('bank')),
    test('redeems once the tickets cover rune arrows, even mid-round', lambda: expect(decide(idle(tickets=TICKETS_PER_RUNE_ARROWS, target_count=4, bronze_worn=6))).to_be('redeem')),
    test('collects the reward before anything else once the round is over', lambda: expect(decide(idle(target_count=11, bow_worn=False, coins=0))).to_be('collect')),
    test('wields a held bow before shooting', lambda: expect(decide(idle(bow_worn=False, bow_held=True, target_count=3, bronze_worn=7))).to_be('wield-bow')),
    test('banks for a bow when none is held or worn', lambda: expect(decide(idle(bow_worn=False))).to_be('bank')),
    test('shoots while arrows are in the quiver', lambda: expect(decide(idle(target_count=1, bronze_worn=10))).to_be('shoot')),
    test('wields arrows that sit in the pack', lambda: expect(decide(idle(target_count=1, bronze_held=10))).to_be('wield-arrows')),
    test('buys more arrows from the judge when the quiver and pack are empty mid-round', lambda: expect(decide(idle(target_count=5, coins=ARROW_RESTOCK_FEE))).to_be('restock-arrows')),
    test('banks when arrows are gone mid-round and the restock fee is not held', lambda: expect(decide(idle(target_count=5, coins=ARROW_RESTOCK_FEE - 1))).to_be('bank')),
])

describe('classify_shot', lambda: [
    test('standing inside five tiles', lambda: expect(classify_shot(['You should probably be behind the haystack.'])).to_be('too-close')),
    test('no bow worn', lambda: [
        expect(classify_shot(['A bow might help here...'])).to_be('no-bow'),
        expect(classify_shot(['You need a bow to take part in the competition.'])).to_be('no-bow'),
    ]),
    test('no bronze arrows in the quiver', lambda: [
        expect(classify_shot(["You'll be needing those bronze arrows..."])).to_be('no-arrows'),
        expect(classify_shot(['I suggest you use the 10 bronze arrows I gave you.'])).to_be('no-arrows'),
    ]),
    test('all ten fired', lambda: expect(classify_shot(["You've fired all your arrows, maybe you should talk to the Judge."])).to_be('round-over')),
    test('not entered', lambda: [
        expect(classify_shot(['Maybe you should ask before using those.'])).to_be('not-entered'),
        expect(classify_shot(['Sorry, you may only use the targets for the competition, not for practicing.'])).to_be('not-entered'),
    ]),
    test('cannot reach', lambda: expect(classify_shot(["I can't reach that!"])).to_be('unreachable')),
    test('the aim line is not a refusal', lambda: expect(classify_shot(['You carefully aim at the target...'])).to_be_null()),
    test('empty window', lambda: expect(classify_shot([])).to_be_null()),
])

describe('hit table', lambda: [
    test('labels match the content script', lambda: [
        expect(hit_label(0)).to_be('Bulls-Eye!'),
        expect(hit_label(1)).to_be('Hit Yellow!'),
        expect(hit_label(3)).to_be('Hit Red!'),
        expect(hit_label(7)).to_be('Hit Blue!'),
        expect(hit_label(10)).to_be('Hit Black!'),
        expect(hit_label(11)).to_be('Missed!'),
    ]),
    test('points match the content script', lambda: [
        expect(hit_points(0)).to_be(100),
        expect(hit_points(1)).to_be(50),
        expect(hit_points(4)).to_be(30),
        expect(hit_points(5)).to_be(20),
        expect(hit_points(9)).to_be(10),
        expect(hit_points(11)).to_be(0),
    ]),
    test('a perfect round is 100 tickets and a score rounds down', lambda: [
        expect(tickets_for_score(1000)).to_be(100),
        expect(tickets_for_score(345)).to_be(34),
        expect(tickets_for_score(0)).to_be(0),
    ]),
])

describe('pick_option', lambda: [
    test('takes the entry offer', lambda: expect(pick_option(["Sure, I'll give it a go.", 'What are the rules?', 'No thanks.'], JUDGE_PREFS)).to_be(0)),
    test('buys arrows when offered mid-round', lambda: expect(pick_option(["Sure, i'll take some.", 'No thanks.'], JUDGE_PREFS)).to_be(0)),
    test('declines the rules reminder', lambda: expect(pick_option(['Yes please.', "No thanks, I've got it.", 'How am I doing so far?'], JUDGE_PREFS)).to_be(1)),
    test('a bare "No thanks." is never the pick', lambda: expect(pick_option(['No thanks.'], JUDGE_PREFS)).to_be(-1)),
    test('matching ignores case', lambda: expect(pick_option(["SURE, I'LL GIVE IT A GO."], JUDGE_PREFS)).to_be(0)),
])

describe('bows', lambda: [
    test('best first, gated on the ranged level', lambda: [
        expect(best_bow(70, lambda name: True)).to_be('Magic shortbow'),
        expect(best_bow(45, lambda name: True)).to_be('Yew shortbow'),
        expect(best_bow(40, lambda name: name == 'Shortbow')).to_be('Shortbow'),
    ]),
    test('nothing available is null', lambda: expect(best_bow(99, lambda name: False)).to_be_null()),
    test('is_bow matches the category by name, case-insensitive', lambda: [
        expect(is_bow('magic shortbow')).to_be(True),
        expect(is_bow('Longbow')).to_be(True),
        expect(is_bow('Crossbow')).to_be(False),
        expect(is_bow(None)).to_be(False),
    ]),
    test('every bow is at most level 50 so a guild entrant can wield the top tier soon', lambda: expect(max([b.level for b in BOWS])).to_be_less_than_or_equal(50)),
])


def cheb(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def targets_in_band():
    for t in TARGETS:
        d = cheb(STAND, t)
        expect(d).to_be_greater_than_or_equal(5)
        expect(d).to_be_less_than_or_equal(10)


describe('stand geometry', lambda: [
    test('every target is outside the five-tile refusal and inside the ten-tile approach range', targets_in_band),
    test('the judge stays within five tiles of the stand across his one-tile wander', lambda: expect(cheb(STAND, JUDGE_SPAWN) + 1).to_be_less_than_or_equal(5)),
])

"""Pure death and party cases from rs2b0t jivekq-recovery.test.ts (MIT, see thirdparty/rs2b0t)."""

from bots.jivekq.party import Party
from bots.jivekq.recovery import death_report, recovery_drops
from rs2004.geometry import Tile

POINT = {'x': 3473, 'z': 9498, 'level': 0}
DEATH = {'at': 1000, 'tile': POINT, 'items': [{'id': 861, 'count': 1}, {'id': 892, 'count': 250}],
         'ground': [{'id': 892, 'count': 30}]}


def report_validation():
    expect(death_report(DEATH, 1000).to_message()).to_equal(DEATH)
    for change in [{'at': 3000}, {'at': -200000}, {'tile': {'x': 3473, 'z': 9498, 'level': 9}},
                   {'items': [{'id': 861, 'count': -1}]}, {'items': [{'id': 861, 'count': 1}] * 60}]:
        value = {key: val for key, val in DEATH.items()}
        value.update(change)
        expect(death_report(value, 1000)).to_be_null()


test('death reports validate position, age and bounded item counts', report_validation)


def exact_pile():
    death = death_report(DEATH, 1000)
    bow = Fake(id=861, count=1, tile=death.tile)
    arrow = Fake(id=892, count=30, tile=death.tile)
    drops = [bow, arrow, Fake(id=995, count=5000, tile=death.tile), Fake(id=861, count=1, tile=Tile(3474, 9498))]
    expect(recovery_drops(death, drops)).to_equal([bow])
    arrow._fields['count'] = 280
    expect(recovery_drops(death, drops)).to_equal([bow, arrow])
    death.ground = [Fake(id=861, count=1)]
    expect(recovery_drops(death, [bow])).to_equal([])
    expect(recovery_drops(death, [bow, bow])).to_equal([bow, bow])


test('recovery excludes preexisting piles, nearby loot and unrelated items, counting separate drops', exact_pile)


def party_death(paused):
    party = Party(['one', 'two', 'three', 'four'], 'one', 'one')
    for name in party.roster:
        party.receive({'name': name, 'session': name, 'trip': 1, 'stage': 'fight', 'ready': True, 'tile': POINT}, 1000)
    party.receive({'name': 'two', 'session': 'two', 'trip': 1, 'stage': 'retreat', 'ready': False,
                   'restocking': True, 'reason': 'paused' if paused else '', 'tile': POINT, 'death': DEATH}, 1000)
    expect(party.unsafe(1, 1000)).to_be(paused)
    expect(len(party.deaths(1))).to_be(1)
    expect(party.deaths(1)[0].name).to_be('two')
    if not paused:
        for name in ['one', 'three', 'four']:
            party.receive({'name': name, 'session': name, 'trip': 1, 'stage': 'fight', 'ready': True, 'tile': POINT}, 8000)
        expect(party.unsafe(1, 8000)).to_be(False)


test_each([False, True])('a teammate death permits recovery but cannot excuse an explicit pause: %s', party_death)


def invalid_casualty():
    party = Party(['one', 'two', 'three', 'four'], 'one', 'one')
    for name in ['one', 'three', 'four']:
        party.receive({'name': name, 'session': name, 'trip': 2, 'stage': 'fight', 'ready': True, 'tile': POINT}, 8000)
    party.receive({'name': 'visitor', 'session': 'visitor', 'trip': 2, 'stage': 'retreat', 'ready': False,
                   'restocking': True, 'tile': POINT, 'death': DEATH}, 8000)
    party.receive({'name': 'two', 'session': 'two', 'trip': 1, 'stage': 'retreat', 'ready': False,
                   'restocking': True, 'tile': POINT, 'death': DEATH}, 1000)
    expect(party.unsafe(2, 8000)).to_be(True)
    expect(party.deaths(2)).to_equal([])


test('foreign and previous-trip deaths cannot excuse a missing fighter', invalid_casualty)

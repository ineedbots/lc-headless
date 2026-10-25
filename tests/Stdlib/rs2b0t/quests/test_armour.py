"""rs2b0t's test/api/ai/quests/armour.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.game import skills
from rs2004.quests.armour import armour_choice
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.tabs import quests


def snap(overrides=None):
    base = QuestSnapshot(journal='in_progress', inv={}, worn=set(), bank_known=True, no_progress=0, bank_coins=0)
    return base.with_fields(overrides or {})


def id_of(choice):
    return choice.id if choice is not None else None


def levels(defence, ranged):
    return lambda skill: defence if skill == 'defence' else ranged


def body_at(defence, expected):
    def body():
        spy_on(skills, 'level', returns=defence)
        choice = armour_choice(snap({'bank_ids': {1111: 1, 1113: 1}}), 'torso')
        expect(id_of(choice)).to_be(expected)
    return body


for _defence, _expected in [[39, 1111], [40, 1113]]:
    test(f'selects the wearable body at Defence {_defence}', body_at(_defence, _expected))


def _fn4():
    choice = armour_choice(snap({'worn': set(['studded body']), 'bank_ids': {1113: 1}}), 'torso')
    expect(choice.name if choice is not None else None).to_be('Studded body')


test('preserves already worn ranged armor', _fn4)


def _fn5():
    spy_on(skills, 'level', returns=40)
    choice = armour_choice(snap({'bank_known': False, 'bank_ids': {1113: 1}}), 'torso')
    expect(choice).to_be_null()


test('ignores a stale bank when its contents are unknown', _fn5)


def _fn6():
    spy_on(skills, 'level', returns=40)
    choice = armour_choice(snap({'inv_ids': {1111: 1}, 'bank_ids': {1113: 1}}), 'torso')
    expect(id_of(choice)).to_be(1111)


test('prefers carried usable armor over higher banked armor', _fn6)


def rune_gate(status):
    def body():
        spy_on(skills, 'level', returns=40)
        spy_on(quests, 'status', returns=status)
        choice = armour_choice(snap({'bank_ids': {1127: 1}}), 'torso')
        expect(id_of(choice)).to_be(1127 if status == 'complete' else None)
    return body


for _status in ['not_started', 'complete']:
    test(f'respects the Rune platebody quest gate when Dragon Slayer is {_status}', rune_gate(_status))


def selects(id, slot, defence, ranged, location):
    def body():
        spy_on(skills, 'level', impl=levels(defence, ranged))
        expect(id_of(armour_choice(snap({location: {id: 1}}), slot))).to_be(id)
    return body


for _id, _slot, _defence, _ranged in [
    [1129, 'torso', 1, 1],
    [1095, 'legs', 1, 1],
    [1167, 'hat', 1, 1],
    [1131, 'torso', 10, 1],
    [1133, 'torso', 20, 20],
    [1097, 'legs', 1, 20],
    [1169, 'hat', 1, 20],
]:
    for _location in ['inv_ids', 'bank_ids']:
        test(f'selects ranged armor {_id} from {_location} at its exact gates', selects(_id, _slot, _defence, _ranged, _location))


def rejects(id, slot, defence, ranged):
    def body():
        spy_on(skills, 'level', impl=levels(defence, ranged))
        expect(armour_choice(snap({'bank_ids': {id: 1}}), slot)).to_be_null()
    return body


for _id, _slot, _defence, _ranged in [
    [1131, 'torso', 9, 70],
    [1133, 'torso', 19, 20],
    [1133, 'torso', 20, 19],
    [1097, 'legs', 70, 19],
    [1169, 'hat', 70, 19],
    [1129, 'torso', 70, 0],
]:
    test(f'rejects ranged armor {_id} at Defence {_defence}, Ranged {_ranged}', rejects(_id, _slot, _defence, _ranged))


def _fn11():
    spy_on(skills, 'level', returns=70)
    expect(id_of(armour_choice(snap({'ranged': 19, 'bank_ids': {1169: 1, 1167: 1}}), 'hat'))).to_be(1167)


test('uses snapshot Ranged to avoid selecting an unwearable coif', _fn11)

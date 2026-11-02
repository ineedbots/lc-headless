"""Ported from rs2b0t's test/api/ai/quests/defs/legends-armour.test.ts and legends-bank-choice.test.ts (MIT, see
thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.defs.legends.areas import LQ_ID, LQ_ITEM
from rs2004.quests.defs.legends.supplies import dress_for_combat, from_bank, junk_ids
from rs2004.quests.engine.types import QuestSnapshot

WORN = set([1333, 1079, 1163, 1201, 1704])


def snap(bank_ids=None, inv_ids=None, worn_ids=None, bank_known=True):
    return QuestSnapshot(
        journal='in_progress',
        inv={},
        inv_ids=inv_ids if inv_ids is not None else {},
        worn=set(),
        worn_ids=worn_ids if worn_ids is not None else WORN,
        attack=70,
        bank_known=bank_known,
        bank={},
        bank_ids=bank_ids if bank_ids is not None else {},
    )


def lower_armour_withdrawn():
    spy_on(skills, 'level', returns=70)
    step = dress_for_combat(snap({1111: 1}))
    expect(step).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'id': 1111, 'name': 'Adamant chainbody', 'qty': 1})]}))


def rune_skipped():
    spy_on(skills, 'level', returns=30)
    step = dress_for_combat(snap({1113: 1, 1111: 1}))
    expect(step).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'id': 1111, 'qty': 1})]}))


def worn_lower_kept():
    spy_on(skills, 'level', returns=70)
    expect(dress_for_combat(snap({1113: 1}, None, set([1333, 1111, 1073, 1161, 1199])))).to_be_null()


def carried_lower_equipped():
    spy_on(skills, 'level', returns=30)
    step = dress_for_combat(snap(None, {1111: 1, 1113: 1}, None, False))
    expect(step.kind).to_be('equip')
    expect(step.item).to_be('Adamant chainbody')


def lower_armour_not_junk():
    expect(junk_ids(snap(None, {1111: 1, 1073: 1, 1161: 1, 1199: 1}))).to_equal([])


def no_body_waits():
    spy_on(skills, 'level', returns=70)
    expect(dress_for_combat(snap()).kind).to_be('wait')


def lost_helm_is_no_stop():
    spy_on(skills, 'level', returns=70)
    expect(dress_for_combat(snap(None, None, set([1333, 1113, 1079, 1201])))).to_be_null()


def wearable_rune_withdrawn():
    spy_on(skills, 'level', returns=40)
    expect(dress_for_combat(snap({1113: 1}))).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'id': 1113, 'qty': 1})]}))


def weapon_first():
    spy_on(skills, 'level', returns=30)
    step = dress_for_combat(snap(None, {1331: 1}, set()))
    expect(step.kind).to_be('equip')
    expect(step.item).to_be('Adamant scimitar')


def worn_amulet_kept():
    expect(dress_for_combat(snap({1704: 1}, None, set([1333, 1111, 1073, 1161, 1199, 1725])))).to_be_null()


def leather_not_junk():
    pack = {}
    for id in [1129, 1095, 1167, 1131, 1133, 1097, 1169]:
        pack[id] = 1
    expect(junk_ids(snap(None, pack))).to_equal([])


# Why: withdrawals use the nearest booth because every booth exposes the same bank contents.
def names_no_bank():
    step = from_bank(snap({LQ_ID.LAW_RUNE: 20}), Record({'id': LQ_ID.LAW_RUNE, 'name': LQ_ITEM.LAW_RUNE}), 5)
    expect(step.kind).to_be('withdraw')
    expect(step.bank).to_be_null()


test('withdraws lower armor when Rune is not owned', lower_armour_withdrawn)
test('skips banked Rune when Defence is insufficient', rune_skipped)
test('keeps already worn lower armor rather than withdrawing Rune', worn_lower_kept)
test('equips carried lower armor without scanning the bank', carried_lower_equipped)
test('keeps withdrawn lower armor through the junk deposit', lower_armour_not_junk)
test('waits when no protective body is owned', no_body_waits)
test('a helm lost to a death does not park the quest', lost_helm_is_no_stop)
test('still withdraws wearable Rune', wearable_rune_withdrawn)
test('still equips the required usable melee weapon first', weapon_first)
test('preserves a worn amulet rather than replacing it with banked glory', worn_amulet_kept)
test('keeps selected leather and studded armor through the junk deposit', leather_not_junk)
test('a withdrawal names no bank, so the walker picks the nearest', names_no_bank)

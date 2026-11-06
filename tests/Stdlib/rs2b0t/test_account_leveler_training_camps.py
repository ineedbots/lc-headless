"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerTrainingCamps.test.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

from bots.account_leveler.combat import COMBAT_CAMPS




additions = [
    Record({'id': 'varrock-west-guards', 'npc_ids': [9], 'max_threat': 28}),
    Record({'id': 'varrock-east-guards', 'npc_ids': [9], 'max_threat': 28}),
    Record({'id': 'falador-north-guards', 'npc_ids': [9], 'max_threat': 28}),
    Record({'id': 'falador-south-guards', 'npc_ids': [9], 'max_threat': 28}),
    Record({'id': 'lumbridge-bears', 'npc_ids': [105], 'max_threat': 28}),
    Record({'id': 'varrock-east-bears', 'npc_ids': [106], 'max_threat': 28}),
    Record({'id': 'ice-mountain-bears', 'npc_ids': [106], 'max_threat': 28}),
    Record({'id': 'varrock-sewer-zombies', 'npc_ids': [73], 'max_threat': 28}),
    Record({'id': 'edgeville-dungeon-skeletons', 'npc_ids': [91], 'max_threat': 28}),
    Record({'id': 'rimmington-hobgoblins', 'npc_ids': [122], 'max_threat': 28}),
    Record({'id': 'yanille-giants', 'npc_ids': [117], 'max_threat': 28}),
    Record({'id': 'varrock-warrior-women', 'npc_ids': [15], 'max_threat': 28}),
    Record({'id': 'burthorpe-guards', 'npc_ids': [1076, 1077], 'max_threat': 37}),
    Record({'id': 'varrock-palace-guards', 'npc_ids': [9], 'max_threat': 28}),
    Record({'id': 'edgeville-dungeon-giants', 'npc_ids': [117], 'max_threat': 28}),
    Record({'id': 'wilderness-east-giants', 'npc_ids': [117], 'max_threat': 28}),
    Record({'id': 'ardougne-moss-giants', 'npc_ids': [112], 'max_threat': 42}),
    Record({'id': 'wilderness-hobgoblins', 'npc_ids': [122], 'max_threat': 28}),
]
def _fn8(_arg9, *_args):
    id = _arg9.id
    expect(([camp for camp in COMBAT_CAMPS if camp.id == id] or [None])[0], id).to_be_defined()


test_each(additions)('training camp $id is registered', _fn8)

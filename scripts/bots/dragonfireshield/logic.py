"""Ported from rs2b0t's src/bot/scripts/DragonfireShield/DragonfireShieldLogic.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile

__all__ = ['SHIELD_ID', 'SHIELD', 'DUKE', 'DUKE_STAND', 'STAND_REACH', 'BANK_STAND', 'BANK_REACH', 'BOOTH', 'BOOTH_OP', 'MAX_TALK_GUARD', 'COINS_ID', 'PRINCE_ALI_QUEST', 'GATE_FEE', 'decide']

# Why: `%dragon_shield = 1` (set when Oziach names the shield) makes Duke Horacio hand out a free shield each conversation.
SHIELD_ID = 1540
SHIELD = 'Dragonfire shield'
DUKE = 'Duke Horacio'
DUKE_STAND = Tile(3212, 3220, 1)
STAND_REACH = 4
BANK_STAND = Tile(3269, 3167, 0)
BANK_REACH = 5
BOOTH = 'Bank booth'
BOOTH_OP = 'Use-quickly'
MAX_TALK_GUARD = 100
# Why: the Al Kharid gate charges 20 gp per crossing until Prince Ali Rescue is complete; the walk planner pays it.
COINS_ID = 995
PRINCE_ALI_QUEST = 'Prince Ali Rescue'
GATE_FEE = 20


def decide(p):
    if p.trip_active and p.at_stand and not p.full:
        return 'farm'
    if p.full:
        return 'bank'
    if p.at_stand and not p.trip_active and p.ground > 0:
        return 'loot'
    if p.at_stand and not p.trip_active and p.ground == 0 and (p.un_noted > 0 or p.notes > 0 or p.junk > 0):
        return 'bank'
    if p.at_bank and (p.un_noted > 0 or p.junk > 0 or (p.want_notes and p.has_banked_shields and p.notes == 0 and p.free > 0)):
        return 'bank'
    if not p.at_stand:
        return 'duke'
    if p.at_stand and not p.trip_active and p.ground == 0 and not p.full:
        return 'farm'
    return 'wait'

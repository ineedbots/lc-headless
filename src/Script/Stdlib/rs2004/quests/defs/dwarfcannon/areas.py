"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dwarfcannon/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import LadderHop, NpcStop

__all__ = ['FALADOR_WEST_BANK', 'MC_TILE', 'MC_LOC', 'MC_OBJ', 'RAILINGS', 'CANNON_PARTS', 'COMMANDER', 'COMMANDER_INSPECT', 'NULODION', 'DWARF_CHILD', 'CAVE_HOPS', 'MC_FOOD_TARGET']

FALADOR_WEST_BANK = Tile(2946, 3369, 0)
MC_TILE = Record({
    'COMMANDER': Tile(2571, 3463, 0),
    'TOWER_LADDER': Tile(2570, 3441, 0),
    'TOWER_L1_LADDER': Tile(2570, 3443, 1),
    'TOWER_L2_DOWN': Tile(2570, 3443, 2),
    'TOWER_L1_DOWN': Tile(2570, 3441, 1),
    'REMAINS': Tile(2567, 3444, 2),
    'CAVE_ENTRANCE': Tile(2622, 3392, 0),
    'CAVE_ARRIVE': Tile(2620, 9797, 0),
    'CRATE': Tile(2571, 9850, 0),
    'MUD_PILE': Tile(2621, 9796, 0),
    'MUD_EXIT': Tile(2623, 3391, 0),
    'CANNON': Tile(2577, 3461, 0),
    'NULODION': Tile(3011, 3453, 0),
})
MC_LOC = Record({'CRATE': 1, 'CAVE': 2, 'BROKEN_CANNON': 5, 'MUD_PILE': 13, 'RAILING_FIRST': 15, 'RAILING_LAST': 20})
MC_OBJ = Record({
    'REMAINS': Record({'id': 0, 'name': 'Dwarf remains'}),
    'TOOLKIT': Record({'id': 1, 'name': 'Tool kit'}),
    'NOTES': Record({'id': 3, 'name': "Nulodion's notes."}),
    'MOULD': Record({'id': 4, 'name': 'Ammo mould'}),
    'RAILING': Record({'id': 14, 'name': 'Railing'}),
})
RAILINGS = [
    Record({'id': 15, 'at': Tile(2556, 3475, 0)}),
    Record({'id': 16, 'at': Tile(2558, 3472, 0)}),
    Record({'id': 17, 'at': Tile(2557, 3464, 0)}),
    Record({'id': 18, 'at': Tile(2559, 3462, 0)}),
    Record({'id': 19, 'at': Tile(2564, 3460, 0)}),
    Record({'id': 20, 'at': Tile(2572, 3460, 0)}),
]
CANNON_PARTS = ['Pipe', 'Barrel', 'Axle', 'Shaft']
# Why: one stop covers every Commander conversation, as the 3 accept lines never share a page and `driveDialog` otherwise takes the last option, which at stage 5 is the refusal.
COMMANDER = NpcStop('Dwarf Commander', MC_TILE.COMMANDER, 8, ["Yeah, I'd love to help.", "Ok, I'll see what I can do.", 'Ok then, just for you!'])
# Why: told the cannon is fixed, the Commander walks over and inspects it before the next page, and the default lull tolerance ended the drive in that gap.
COMMANDER_INSPECT = NpcStop(COMMANDER.npc, COMMANDER.anchor, COMMANDER.leash, COMMANDER.prefer, None, 20000)
NULODION = NpcStop('Nulodion', MC_TILE.NULODION, 8, [])
DWARF_CHILD = NpcStop('Dwarf youngster', MC_TILE.CRATE, 8, [])
# Why: the cave is entered and left by scripted telejumps that no transports edge carries, so findPath reports the interior unreachable from anywhere outside it.
CAVE_HOPS = [
    LadderHop(MC_TILE.CAVE_ENTRANCE, 'Cave Entrance', 'Enter', MC_TILE.CAVE_ARRIVE),
    LadderHop(MC_TILE.MUD_PILE, 'Mud pile', 'Climb-over', MC_TILE.MUD_EXIT),
]
MC_FOOD_TARGET = 8

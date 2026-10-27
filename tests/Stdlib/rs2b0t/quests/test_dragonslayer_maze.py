"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/dragonslayerMaze.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.dragonslayer.areas import DS_ID, DS_LOC
from rs2004.quests.defs.dragonslayer.maze import MAZE_LEGS, MAZE_NPC, door_crossed, in_maze, leg_from_position
from rs2004.quests.defs.dragonslayer import OZIACH_GOALS

def _fn1():

    def _fn2():
        spent = set()
        for leg in MAZE_LEGS:
            if leg.kind != 'door' or leg.key_id == DS_ID.MAZE_KEY:
                continue
            dropped = ([_i for _i, l in enumerate(MAZE_LEGS) if l.kind == 'kill' and l.key_id == leg.key_id] or [-1])[0]
            door = MAZE_LEGS.index(leg) if leg in MAZE_LEGS else -1
            expect(dropped).to_be_greater_than_or_equal(0)
            expect(dropped).to_be_less_than(door)
            spent.add(leg.key_id)
        expect(len(spent)).to_be(6)
    test('every key a kill drops is spent by a later door', _fn2)

    def _fn3():
        ids = [l.npc_id for l in [l for l in MAZE_LEGS if l.kind == 'kill']]
        expect(ids).to_equal([MAZE_NPC.GIANT_RAT, MAZE_NPC.GHOST, MAZE_NPC.SKELETON, MAZE_NPC.ZOMBIE, MAZE_NPC.MELZAR, MAZE_NPC.DEMON])
    test('the key droppers are the quest ids, not the decoys sharing their names', _fn3)

    def _fn4():
        for leg in MAZE_LEGS:
            if leg.kind != 'door':
                continue
            expect(leg.land.distance_to(leg.door)).to_be_less_than_or_equal(1)
            expect(leg.land.distance_to(leg.stand)).to_be_less_than_or_equal(1)
    test('each door lands on the far side of its own tile', _fn4)

    def _fn5():
        last = MAZE_LEGS[len(MAZE_LEGS) - 1]
        expect(last.kind).to_be('chest')
        if last.kind == 'chest':
            expect(last.stand.z).to_be_greater_than(9600)
    test('the route ends in the basement at the chest', _fn5)

    def _fn6():
        front = MAZE_LEGS[0]
        expect(front.kind).to_be('door')
        if front.kind != 'door':
            return
        expect(front.key_id).to_be(DS_ID.MAZE_KEY)
        expect(door_crossed(front, Fake(**{'x': 2940, 'z': 3248, 'level': 0}), True)).to_be(True)
        expect(door_crossed(front, Fake(**{'x': 2941, 'z': 3248, 'level': 0}), True)).to_be(False)
        expect(door_crossed(front, Fake(**{'x': 2960, 'z': 3248, 'level': 0}), False)).to_be(False)
    test('the front door is crossed while the maze key is still in the pack', _fn6)

    def _fn7():
        red = ([l for l in MAZE_LEGS if l.kind == 'door' and l.key_id == DS_ID.RED_KEY] or [None])[0]
        expect(red).to_be_defined()
        if (red.kind if red is not None else None) != 'door':
            return
        expect(door_crossed(red, Fake(**{'x': 2925, 'z': 3253, 'level': 0}), True)).to_be(False)
        expect(door_crossed(red, Fake(**{'x': 2925, 'z': 3253, 'level': 0}), False)).to_be(True)
    test('a coloured door is crossed exactly when its key is gone', _fn7)

    def _fn8():
        expect(in_maze(Fake(**{'x': 2935, 'z': 3250, 'level': 0}))).to_be(True)
        expect(in_maze(Fake(**{'x': 2930, 'z': 3250, 'level': 2}))).to_be(True)
        expect(in_maze(Fake(**{'x': 2932, 'z': 9645, 'level': 0}))).to_be(True)
        expect(in_maze(Fake(**{'x': 2960, 'z': 3250, 'level': 0}))).to_be(False)
        expect(in_maze(Fake(**{'x': 2941, 'z': 3248, 'level': 0}))).to_be(False)
        expect(in_maze(Fake(**{'x': 2940, 'z': 3248, 'level': 0}))).to_be(True)
        expect(in_maze(None)).to_be(False)
    test('inMaze covers all four floors and nothing outside', _fn8)

    def _fn9():
        expect(leg_from_position(Fake(**{'x': 3013, 'z': 3355, 'level': 0}))).to_be(0)
        expect(leg_from_position(Fake(**{'x': 2935, 'z': 3250, 'level': 0}))).to_be(1)
        expect(MAZE_LEGS[leg_from_position(Fake(**{'x': 2929, 'z': 3250, 'level': 1}))]).to_match_object(Fake(**{'kind': 'kill', 'npc_id': MAZE_NPC.GHOST}))
        expect(MAZE_LEGS[leg_from_position(Fake(**{'x': 2925, 'z': 3251, 'level': 2}))]).to_match_object(Fake(**{'kind': 'kill', 'npc_id': MAZE_NPC.SKELETON}))
        expect(MAZE_LEGS[leg_from_position(Fake(**{'x': 2932, 'z': 9641, 'level': 0}))]).to_match_object(Fake(**{'kind': 'kill', 'npc_id': MAZE_NPC.ZOMBIE}))
        expect(leg_from_position(Fake(**{'x': 3012, 'z': 9813, 'level': 0}))).to_be(0)
        expect(leg_from_position(Fake(**{'x': 3212, 'z': 3220, 'level': 1}))).to_be(0)
        expect(leg_from_position(Fake(**{'x': 2911, 'z': 4832, 'level': 0}))).to_be(0)
        expect(MAZE_LEGS[leg_from_position(Fake(**{'x': 2936, 'z': 3240, 'level': 0}))]).to_match_object(Fake(**{'kind': 'climb', 'op': 'Climb-down'}))
    test('a cold start resumes on the floor the bot is standing on', _fn9)
describe("Melzar's Maze route", _fn1)

def _fn10():

    def _fn11():
        expect(DS_LOC.CRANDOR_SECRET_DOOR).to_match_object(Fake(**{'x': 2836, 'z': 9600, 'level': 0}))
        expect(DS_LOC.SECRET_WALL_KARAMJA_STAND.x).to_be(DS_LOC.CRANDOR_SECRET_DOOR.x)
        expect(DS_LOC.SECRET_WALL_KARAMJA_STAND.level).to_be(DS_LOC.CRANDOR_SECRET_DOOR.level)
        expect(DS_LOC.CRANDOR_SECRET_DOOR.z - DS_LOC.SECRET_WALL_KARAMJA_STAND.z).to_be(1)
    test('is one loc, on the Crandor row, reached from a stand one tile south', _fn11)

    def _fn12():
        expect(DS_LOC.ELVARG_GATE_INSIDE.x).to_be(DS_LOC.ELVARG_GATE.x)
        expect(DS_LOC.ELVARG_GATE_STAND.x).to_be(DS_LOC.ELVARG_GATE.x - 1)
    test('the lair gate is taken from the lair column, which is the side that opens', _fn12)
describe('the Crandor secret wall', _fn10)

def _fn13():

    def _fn14():
        REPLIES = Fake(**{'Where is the first piece of the map?': "Deep in a strange building known as Melzar's maze|located north west of Rimmington.", 'Where is the second piece of the map?': 'You will need to talk to the oracle on the ice mountain.', 'Where is the third piece of the map?': 'That was stolen by one of the goblins from the goblin village.', 'Where can I get an antidragon shield?': 'I believe the Duke of Lumbridge Castle may have one in his armoury.'})
        expect(OZIACH_GOALS).to_have_length(4)
        for goal in OZIACH_GOALS:
            reply = REPLIES._fields.get(goal.ask)
            expect(reply).to_be_defined()
            expect(reply.lower()).to_contain(goal.heard)
    test('every goal is judged on a phrase his reply actually contains', _fn14)

    def _fn15():
        for goal in OZIACH_GOALS:
            others = [g for g in OZIACH_GOALS if g != goal]
            for other in others:
                expect(other.heard).not_.to_contain(goal.heard)
    test('no goal phrase matches another goal reply', _fn15)
describe('Oziach', _fn13)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

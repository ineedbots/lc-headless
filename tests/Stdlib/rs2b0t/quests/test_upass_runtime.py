"""Underground Pass's game legs, against what phase 17h's live run found."""

import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.navigation import navigator
from rs2004.quests.defs.upass import area2, bridge, cross, doll, pass_, supplies
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_NPC
from rs2004.quests.defs.upass.route import UPASS_CROSSINGS


class FakeLoc:
    def __init__(self, x, z):
        self.at = Tile(x, z, 0)
        self.id = 3238
        self.sent = []

    def tile(self):
        return self.at

    def distance(self):
        return 1

    def interact(self, op):
        self.sent.append(op)
        return True


def ledge_goes_to_the_cardinal_loc():
    diagonal = FakeLoc(2374, 9643)
    cardinal = FakeLoc(2374, 9644)
    spy_on(locs, 'query', impl=lambda: FakeQuery([diagonal, cardinal]))
    edge = [e for e in UPASS_CROSSINGS if e.loc == 3238 and e.stand.z == 9644][0]
    expect(cross.operate(edge, lambda line: None)).to_be(True)
    expect(cardinal.sent).to_equal(['Cross'])
    expect(diagonal.sent).to_equal([])


test("a row of ledges sends the op to the cardinal one, not the diagonal that refuses it", ledge_goes_to_the_cardinal_loc)


def no_baked_route_is_only_false():
    spy_on(navigator, 'find_path', impl=lambda *args, **kw: Fake(ok=False))
    lines = []
    crossed = run_wait(pass_.cross_by_route(Tile(2374, 9604, 0), Tile(2424, 9719, 0), lambda line: lines.append(line)))
    expect(crossed).to_be(False)
    expect(len([line for line in lines if 'no baked route' in line])).to_be(1)


test('a tile the bridge graph does not name falls through to the free search', no_baked_route_is_only_false)


class Paladin:
    def __init__(self, attacks, clock):
        self.attacks = attacks
        self.clock = clock

    def interact(self, op):
        self.attacks.append(self.clock[0])
        return True


def lapsed_attack_is_renewed():
    clock = [0]
    attacks = []

    paladin = Paladin(attacks, clock)

    def advance(n=1):
        clock[0] += 600
        return None
        yield

    def nothing(*args):
        return None
        yield

    patch(_core, 'step_time', lambda: clock[0])
    spy_on(execution, 'delay_ticks', impl=advance)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(sustain, 'run', impl=nothing)
    patch(bridge, 'prayer_upkeep', nothing)
    # The target lives for 13 seconds of a fight whose first attack lapsed.
    gone = run_wait(bridge.fight_until_gone(lambda: paladin if clock[0] < 13000 else None, lambda line: None))
    expect(gone).to_be(True)
    expect(len(attacks)).to_be_greater_than(1)


test('a fight renews an attack that lapsed, rather than waiting out the kill', lapsed_attack_is_renewed)


def forced_move_is_waited_out():
    tiles = [Tile(2416, 9605, 0)]

    ticks = [0]

    # The pipe holds the player still for 5 ticks before moving them.
    def land(n=1):
        ticks[0] += 1
        if ticks[0] > 5:
            tiles[0] = Tile(2412, 9605, 0)
        return None
        yield

    spy_on(game, 'tile', impl=lambda: tiles[0])
    spy_on(execution, 'delay_ticks', impl=land)
    spy_on(navigator, 'find_path', impl=lambda *args, **kw: Fake(ok=False))
    walked = []

    def no_walk(*args, **kw):
        walked.append(args)
        return False
        yield

    patch(cross.traversal, 'walk_resilient', Spy(no_walk))
    took = run_wait(cross.cross_once(Tile(2376, 9610, 0), lambda line: None))
    expect(took).to_be('crossed')
    expect(walked).to_equal([])
    expect(tiles[0].x).to_be(2412)


test('a crossing still landing is waited out, not walked away from', forced_move_is_waited_out)


def drop_gets_ticks_to_land():
    landed = []
    ticks = [0]

    def tick(n=1):
        ticks[0] += 1
        if ticks[0] == 3:
            landed.append(Fake(id=UP_ITEM.BADGE_JERRO.id, distance=lambda: 1))
        return None
        yield

    spy_on(execution, 'delay_ticks', impl=tick)
    spy_on(ground_items, 'query', impl=lambda: FakeQuery(landed))
    drop = run_wait(bridge.await_drop(UP_ITEM.BADGE_JERRO.id))
    expect(drop is not None).to_be(True)
    expect(ticks[0]).to_be(3)


test('a drop gets a few ticks to land after its NPC leaves the scene', drop_gets_ticks_to_land)


def run_nothing():
    return False
    yield


def a_kill_without_a_crest_is_still_owed():
    def arrived(*args):
        return True
        yield

    def nothing(*args):
        return None
        yield

    patch(area2, 'walk_to', arrived)
    patch(area2, 'settle_scene', nothing)
    patch(area2, 'fight_until_gone', arrived)
    patch(area2, 'take_drop', lambda id, log: run_nothing())
    jerro = Fake(id=UP_NPC.PALADIN_JERRO, actions=lambda: ['Attack'], distance=lambda: 1)
    spy_on(area2.npcs, 'query', impl=lambda: FakeQuery([jerro]))
    killed = set()
    expect(run_wait(area2.kill_paladin(lambda line: None, killed))).to_be(False)
    expect(UP_NPC.PALADIN_JERRO in killed).to_be(False)


test('a paladin who left no crest is still owed one', a_kill_without_a_crest_is_still_owed)


def spade_is_dropped_last():
    expect(doll.SPENT[-1].id).to_be(UP_ITEM.SPADE.id)
    expect(doll.SPENT[0].id).to_be(UP_ITEM.HISTORY.id)


test("making room for the robes loses the spade last, which Regicide can't rebuy", spade_is_dropped_last)


def one_unanswered_equip_is_not_a_refusal():
    supplies.unwearable.clear()
    supplies.refusals.clear()
    supplies.note_refused('Rune scimitar', lambda line: None)
    expect('rune scimitar' in supplies.unwearable).to_be(False)
    supplies.note_refused('Rune scimitar', lambda line: None)
    supplies.note_refused('Rune scimitar', lambda line: None)
    expect('rune scimitar' in supplies.unwearable).to_be(True)
    supplies.unwearable.clear()
    supplies.refusals.clear()


test('a piece is written off only after it has failed repeatedly', one_unanswered_equip_is_not_a_refusal)


class Doll:
    id = UP_ITEM.DOLL.id
    count = 1

    def __init__(self, heard, pack):
        self.heard = heard
        self.pack = pack
        self.uses = 0

    def use_on(self, target):
        self.uses += 1
        if self.uses == 1:
            self.heard.append("I can't reach that!")
        else:
            self.pack.clear()
        return True


def refused_throw_goes_again():
    heard = []
    pack = []
    thrown = Doll(heard, pack)
    pack.append(thrown)
    spy_on(game_messages, 'mark', impl=lambda: len(heard))
    spy_on(game_messages, 'since', impl=lambda mark: [Fake(text=text) for text in heard[mark:]])
    spy_on(game, 'tile', returns=Tile(2142, 4647, 1))
    spy_on(inventory, 'items', impl=lambda: pack)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    clock = [0]

    def now():
        clock[0] += 100
        return clock[0]

    patch(_core, 'step_time', now)
    patch(doll, 'loc_by_id', lambda id, op, within=12: Fake(id=id))
    expect(run_wait(doll.throw_doll(lambda line: None))).to_be(True)
    expect(thrown.uses).to_be(2)


test("a throw the server couldn't reach goes again at once, since Iban won't wait", refused_throw_goes_again)

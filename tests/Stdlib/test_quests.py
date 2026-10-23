"""The quest engine's steps, with rs2b0t's test/api/ai/quests exec/primitives, questPrayer, driveDialogGap and
exec/gotoNpc tests ported."""

import rs2004.quests.exec.primitives as primitives
from rs2004.quests.exec import LadderHop, LineRule, NpcStop, goto_npc, drive_dialog, is_underground, needs_hop
from rs2004.quests.exec import pick_by_line, pick_preferred, talk_op
from rs2004.quests.prayer import PRAYER_FLOOR, PROTECTION_NAME, prayer_upkeep_action

TICK_MS = 600


def drive(generator):
    while True:
        try:
            next(generator)
        except StopIteration as e:
            return e.value


class FakeExecution:
    """Polls a wait's condition once a simulated tick, so a longer wait gets more chances."""

    def delay_ticks(self, n):
        if False:
            yield

    def delay_until(self, cond, ms=6000):
        if False:
            yield
        for _ in range(max(1, ms // TICK_MS)):
            if cond():
                return True
        return cond()


class Patched:
    """Stands fakes in for the primitives module's names, and puts the real ones back."""

    def __init__(self, **fakes):
        self.saved = {name: getattr(primitives, name) for name in fakes}
        for name, fake in fakes.items():
            setattr(primitives, name, fake)

    def restore(self):
        for name, real in self.saved.items():
            setattr(primitives, name, real)


SEDRIDOR_OPTIONS = ["Nothing thanks, I'm just looking around.", 'What are you doing down here?', "I'm looking for the head wizard."]


def test_the_first_preferred_option_is_picked_by_part_whatever_the_case():
    assert pick_preferred(SEDRIDOR_OPTIONS, ["I'm looking for the head wizard."]) == "I'm looking for the head wizard."
    # The preference order wins over the options' order.
    assert pick_preferred(['No, I am busy.', 'Yes, certainly.'], ['Yes, certainly.', 'No, I am busy.']) == 'Yes, certainly.'
    assert pick_preferred(['Have you any quests for me?'], ['have you any quests']) == 'Have you any quests for me?'
    assert pick_preferred(['Yes please!', "Oh, it's a rune shop. No thank you, then."], ['I have been sent here with a package']) is None


SKAVID = [LineRule('ar cur', 'Gor.'), LineRule('bidith ig', 'Cur.'), LineRule('cur tanath', 'Bidith.'), LineRule('gor nod', 'Tanath.')]
SKAVID_OPTIONS = ['Cur.', 'Ar.', 'Bidith.', 'Tanath.', 'Gor.']


def test_the_option_is_picked_by_what_the_npc_said():
    assert pick_by_line(['Ar cur...'], SKAVID_OPTIONS, SKAVID) == 'Gor.'
    assert pick_by_line(['Bidith ig...'], SKAVID_OPTIONS, SKAVID) == 'Cur.'
    assert pick_by_line(['Gor nod...'], SKAVID_OPTIONS, SKAVID) == 'Tanath.'
    # The longest matching rule wins, so the overlapping "ar cur" can't take "Cur tanath".
    assert pick_by_line(['Cur tanath...'], SKAVID_OPTIONS, SKAVID) == 'Bidith.'
    # Colour tags and pipes in the line are ignored.
    assert pick_by_line(['@dbl@Gor|nod...'], SKAVID_OPTIONS, SKAVID) == 'Tanath.'


def test_no_option_is_guessed_by_line():
    assert pick_by_line(['Tanath gor ar bidith?'], SKAVID_OPTIONS, SKAVID) is None
    # The rule's reply isn't on offer.
    assert pick_by_line(['Ar cur...'], ['Cur.', 'Ar.'], SKAVID) is None
    assert pick_by_line([], SKAVID_OPTIONS, SKAVID) is None
    # The option labels alone match no rule, so a line captured from the option page yields nothing.
    assert pick_by_line(SKAVID_OPTIONS, SKAVID_OPTIONS, [LineRule('ar cur', 'Gor.')]) is None


def test_underground_is_past_z_5000_and_a_hop_is_needed_across_it():
    assert is_underground(Tile(3104, 9571))
    assert not is_underground(Tile(3104, 3162))
    assert needs_hop(Tile(0, 3218), Tile(0, 9572))
    assert needs_hop(Tile(0, 9576), Tile(0, 3402))
    assert not needs_hop(Tile(0, 3218), Tile(0, 3402))
    assert not needs_hop(Tile(0, 9571), Tile(0, 9576))


def test_talking_takes_talk_to_or_a_bare_talk():
    assert talk_op(['Talk-to', 'Trade']) == 'Talk-to'
    assert talk_op(['Talk']) == 'Talk'
    assert talk_op(['Attack', 'Pickpocket']) is None


def test_the_protection_prayers_are_named_as_prayer_takes_them():
    assert PROTECTION_NAME['melee'] == 'Protect from Melee'
    assert PROTECTION_NAME['magic'] == 'Protect from Magic'
    assert PROTECTION_NAME['missiles'] == 'Protect from Missiles'


def upkeep(in_combat=True, protect_active=False, protect_available=True, points=70, doses=2):
    return prayer_upkeep_action(in_combat, protect_active, protect_available, points, doses)


def test_prayer_upkeep_raises_protection_in_a_fight_and_drops_it_after():
    assert upkeep() == 'protect'
    assert upkeep(protect_active=True) == 'none'
    assert upkeep(in_combat=False, protect_active=True) == 'drop'
    assert upkeep(in_combat=False) == 'none'
    assert upkeep(in_combat=False, points=0) == 'none'


def test_prayer_upkeep_drinks_at_the_floor_while_it_has_doses():
    assert upkeep(protect_active=True, points=PRAYER_FLOOR) == 'drink'
    assert upkeep(points=PRAYER_FLOOR) == 'drink'
    # With no doses left it holds what protection it can.
    assert upkeep(points=PRAYER_FLOOR, doses=0) == 'protect'
    assert upkeep(points=PRAYER_FLOOR, doses=0, protect_active=True) == 'none'
    # A prayer that can't be raised is never toggled.
    assert upkeep(protect_available=False) == 'none'
    assert upkeep(protect_available=False, points=0) == 'drink'


class QuietThenPage:
    """A conversation that goes quiet for gap polls, then offers pages."""

    def __init__(self, gap):
        self.gap = gap
        self.polls = 0
        self.pages = 0

    def is_open(self):
        return False

    def can_continue(self):
        self.polls += 1
        return self.polls > self.gap

    def continue_(self):
        if False:
            yield
        self.pages += 1
        return True

    def options(self):
        return []


def test_a_talk_waits_out_a_scripted_pause_only_when_its_stop_asks():
    # Lawgof walks to the cannon and inspects it before his next page.
    dialog = QuietThenPage(8)
    patched = Patched(execution=FakeExecution(), chat_dialog=dialog)
    drive(drive_dialog([], lambda m: None))
    assert dialog.pages == 0
    dialog = QuietThenPage(8)
    primitives.chat_dialog = dialog
    drive(drive_dialog([], lambda m: None, 12000))
    assert dialog.pages > 0
    patched.restore()


class World:
    """Where you stand, the walks asked for, and the ladder ops sent."""

    def __init__(self, here, walk_script):
        self.here = here
        self.walks = []
        self.ops = []
        self.walk_script = walk_script


class FakeGame:
    def __init__(self, world):
        self.world = world

    def tile(self):
        return self.world.here


class FakeTraversal:
    def __init__(self, world):
        self.world = world

    def walk_resilient(self, dest, radius=2, attempts=None, timeout_ms=None, log=None):
        if False:
            yield
        self.world.walks.append(dest)
        landed = self.world.walk_script(dest)
        if landed is False:
            return False
        self.world.here = landed
        return True


class FakeLadder:
    def __init__(self, world):
        self.world = world

    def tile(self):
        return self.world.here

    def interact(self, op):
        self.world.ops.append(op)
        self.world.here = Tile(3105, 3162, 0)
        return True


class Chain:
    """A query whose filters are ignored and whose nearest is one thing."""

    def __init__(self, found):
        self.found = found

    def name(self, *_):
        return self

    def action(self, *_):
        return self

    def where(self, *_):
        return self

    def within(self, *_):
        return self

    def nearest(self):
        return self.found


class FakeQueries:
    def __init__(self, found):
        self.found = found

    def query(self):
        return Chain(self.found)


def walk_anywhere(dest):
    return Tile(dest.x, dest.z, dest.level)


def in_world(world):
    return Patched(execution=FakeExecution(), game=FakeGame(world), traversal=FakeTraversal(world),
                   locs=FakeQueries(FakeLadder(world)), npcs=FakeQueries(None))


HOPS = [
    LadderHop(Tile(3105, 3162, 0), 'Ladder', 'Climb-down', Tile(3104, 9576, 0)),
    LadderHop(Tile(3104, 9576, 0), 'Ladder', 'Climb-up', Tile(3105, 3162, 0)),
]
WIZARD_HOPS = [
    LadderHop(Tile(3105, 3162, 0), 'Ladder', 'Climb-down', Tile(3104, 9576, 0), walk=Tile(3108, 3162, 0)),
    LadderHop(Tile(3104, 9576, 0), 'Ladder', 'Climb-up', Tile(3105, 3162, 0)),
]
SEDRIDOR = NpcStop('Sedridor', Tile(3103, 9572, 0), 8, [], approach=[Tile(3108, 9572, 0)])


def test_with_no_hop_toward_an_underground_anchor_the_walk_goes_straight_there():
    world = World(Tile(2387, 3435, 0), walk_anywhere)
    patched = in_world(world)
    drive(goto_npc(NpcStop('Brimstail', Tile(2390, 9810, 0), 8, []), [], lambda m: None))
    patched.restore()
    assert len([t for t in world.walks if t.x == 2390 and t.z == 9810]) > 0


def test_a_failed_leg_underground_climbs_back_up_to_re_roll_the_landing():
    def approach_fails(dest):
        return False if dest.x == 3108 and dest.z == 9572 else walk_anywhere(dest)

    world = World(Tile(3107, 9575, 0), approach_fails)
    patched = in_world(world)
    assert not drive(goto_npc(SEDRIDOR, HOPS, lambda m: None))
    patched.restore()
    assert world.ops == ['Climb-up']

    def anchor_fails(dest):
        return False if dest.x == 3103 and dest.z == 9572 else walk_anywhere(dest)

    world = World(Tile(3108, 9572, 0), anchor_fails)
    patched = in_world(world)
    assert not drive(goto_npc(SEDRIDOR, HOPS, lambda m: None))
    patched.restore()
    assert world.ops == ['Climb-up']


def test_a_failed_leg_on_the_surface_never_climbs():
    world = World(Tile(3210, 3220, 0), lambda dest: False)
    patched = in_world(world)
    aubury = NpcStop('Aubury', Tile(3253, 3402, 0), 8, [], approach=[Tile(3230, 3300, 0)])
    assert not drive(goto_npc(aubury, HOPS, lambda m: None))
    patched.restore()
    assert world.ops == []


def test_a_hop_behind_a_door_walks_its_long_walk_tile_then_its_stand_then_climbs():
    world = World(Tile(3251, 3420, 0), walk_anywhere)
    patched = in_world(world)
    drive(goto_npc(SEDRIDOR, WIZARD_HOPS, lambda m: None))
    patched.restore()
    assert (world.walks[0].x, world.walks[0].z) == (3108, 3162)
    assert (world.walks[1].x, world.walks[1].z) == (3105, 3162)
    assert world.ops[0] == 'Climb-down'


def test_a_failed_walk_to_the_hop_never_climbs():
    for failed_x in [3108, 3105]:
        world = World(Tile(3251, 3420, 0), lambda dest: False if dest.x == failed_x else walk_anywhere(dest))
        patched = in_world(world)
        assert not drive(goto_npc(SEDRIDOR, WIZARD_HOPS, lambda m: None))
        patched.restore()
        assert world.ops == []

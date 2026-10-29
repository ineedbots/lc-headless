"""A server-update boundary for quest and clue workflow tests."""

from coverage_world import PatchWorld
from helpers import FakeModule
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
import rs2004.quests.exec.prompts as prompts


class QuestObject:
    def __init__(self, world, name, id=1, ops=None, at=None, effect=None):
        self.world = world
        self.name = name
        self.id = id
        self.count = 1
        self.index = id
        self.size = 1
        self.ops = ops if ops is not None else ['Take']
        self.at = at if at is not None else world.position
        self.effect = effect
        self.accept = True
        self.alive = True
        self.contested = False
        self.attacking_me = False
        self.in_combat = False
        self.health = 10
        self.max_health = 10
        self.noted = False
        self.slot = 3

    def actions(self):
        return self.ops

    def tile(self):
        return self.at

    def network_tile(self):
        return self.at

    def distance(self):
        return self.at.distance_to(self.world.position) if self.world.position is not None else 100

    def interact(self, op):
        self.world.actions.append((self.name, op))
        if self.accept and self.effect is not None:
            self.world.effects.append(self.effect)
        return self.accept

    def use_on(self, other):
        return self.interact('Use on ' + other.name)

    def targets_me(self):
        return self.attacking_me

    def targets_another_player(self):
        return self.contested

    def valid(self):
        return self.alive


class QuestWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.position = Tile(3000, 3000)
        self.pack = []
        self.scene = []
        self.worn = []
        self.effects = []
        self.actions = []
        self.walks = []
        self.can_walk = True
        self.on_walk = None
        self.on_update = None
        self.interrupted = False
        self.fighting = False
        self.level = 50
        self.messages = []
        self.inventory = FakeModule(items=lambda: self.pack, count=self.count,
                                    count_by_id=self.count_by_id, contains=lambda n: self.count(n) > 0,
                                    first=self.first, is_full=lambda: len(self.pack) >= 28,
                                    free=lambda: 28 - len(self.pack), used=lambda: len(self.pack))
        self.entities = FakeModule(query=self.query, all=lambda: self.scene)
        self.game = FakeModule(tile=lambda: self.position, in_combat=lambda: self.fighting)
        self.traversal = FakeModule(walk_resilient=self.walk)

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(prompts, '_core', self)
        self.patch(prompts, 'sustain', FakeModule(run=lambda: self.reply()))
        self.patch(prompts, 'prayer_upkeep', lambda: self.reply(False))
        self.install(prompts)
        return self

    def saw_since(self, mark, pattern):
        return any([pattern(text) if callable(pattern) else pattern.lower() in text.lower()
                    for text in self.messages[mark:]])

    def install(self, module):
        for name, value in [('inventory', self.inventory), ('game', self.game),
                            ('traversal', self.traversal), ('npcs', self.entities),
                            ('locs', self.entities), ('ground_items', self.entities),
                            ('event_signal', FakeModule(pending=lambda: self.interrupted)),
                            ('skills', FakeModule(level=lambda n: self.level, effective=lambda n: self.level,
                                                  xp=lambda n: 1000)),
                            ('equipment', FakeModule(items=lambda: self.worn)),
                            ('game_messages', FakeModule(mark=lambda: len(self.messages), saw_since=self.saw_since,
                                since=lambda mark: [FakeModule(text=m) for m in self.messages[mark:]])),
                            ('reachability', FakeModule(can_reach=lambda *a, **kw: True))]:
            if hasattr(module, name):
                self.patch(module, name, value)

    def first(self, name):
        return ([i for i in self.pack if i.name.lower() == name.lower()] or [None])[0]

    def count(self, name):
        return sum([i.count for i in self.pack if i.name.lower() == name.lower()])

    def count_by_id(self, id):
        return sum([i.count for i in self.pack if i.id == id])

    def hold(self, name, count=1, id=1, effect=None):
        item = QuestObject(self, name, id, effect=effect)
        item.count = count
        self.pack.append(item)
        return item

    def query(self):
        def supply(ids, names, radius, layer):
            return [e for e in self.scene if (ids is None or e.id in ids)
                    and (names is None or e.name in names)
                    and (radius is None or e.distance() <= radius)]
        return EntityQuery(supply, lambda e: True)

    def walk(self, tile, **kwargs):
        self.walks.append(tile)
        yield execution.Ticks(1)
        if self.can_walk:
            self.position = tile
            if self.on_walk is not None:
                self.on_walk()
        return self.can_walk

    def reply(self, value=True, effect=None):
        yield execution.Ticks(1)
        if effect is not None:
            effect()
        return value

    def advance(self):
        PatchWorld.advance(self)
        effects = self.effects
        self.effects = []
        if self.respond:
            for effect in effects:
                effect()
        if self.on_update is not None:
            self.on_update()

    def run(self, task):
        for guard in range(2000):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            assert isinstance(wait, (execution.Update, execution.Ticks))
            self.waits.append(wait)
            self.now += 500
            self.advance()
        assert False, 'quest exceeded its simulated update budget'

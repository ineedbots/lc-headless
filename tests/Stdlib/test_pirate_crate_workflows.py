"""The smuggling crate reports its own contents before rum or bananas are spent."""

import rs2004.quests.defs.piratestreasure.crate as crate
import rs2004.quests.defs.piratestreasure.karamja as island
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class Cargo(QuestObject):
    def use_on(self, target):
        world = self.world
        if self.id == island.PT_ID.RUM:
            def packed():
                world.rum = True
                world.pack.remove(self)
        else:
            def packed():
                world.bananas += 1
                world.pack.remove(self)
        self.world.effects.append(packed)
        return True


class CrateWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.rum = False
        self.bananas = 0
        self.can_ship = True
        self.position = island.PT_TILE.BANANA_CRATE

    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(crate)
        self.install(island)
        self.patch(island, 'sustain', FakeModule(run=lambda: self.reply()))
        self.patch(island, 'talk_strict', self.talk)
        box = QuestObject(self, 'Crate', crate.PT_LOC.BANANA_CRATE, ['Search'],
                          at=island.PT_TILE.BANANA_CRATE, effect=self.report)
        tree = QuestObject(self, 'Banana Tree', list(island.BANANA_TREE_IDS)[0], ['Search'],
                           at=island.PT_TILE.BANANA_GROVE, effect=self.pick)
        self.scene = [box, tree]
        return self

    def pick(self):
        self.pack.append(Cargo(self, 'Banana', island.PT_ID.BANANA))

    def report(self):
        self.messages.append(f'The crate has {self.bananas} bananas inside.')
        if self.rum:
            self.messages.append('There is some rum in here.')

    def talk(self, *args):
        yield from self.reply()
        if self.can_ship:
            self.rum = False
            self.bananas = 0
        return self.can_ship


def test_pirate_crate_search_distinguishes_missing_refused_silent_and_readable():
    for mode in ['walk_failed', 'missing', 'refused', 'silent', 'read']:
        with CrateWorld() as w:
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            if mode == 'missing':
                w.scene = []
            elif mode == 'refused':
                w.scene[0].accept = False
            state = w.run(crate.search_banana_crate(w.logs.append))
            assert (state is not None) == (mode == 'read')
            if state is not None:
                assert state.bananas == 0 and not state.rum


def test_pirate_smuggling_stashes_rum_fills_ten_bananas_and_returns_to_mainland():
    with CrateWorld() as w:
        w.pack = [Cargo(w, 'Karamjan rum', island.PT_ID.RUM)]
        assert w.run(island.ship_crate(w.logs.append))
        assert w.position == island.PT_TILE.WYDIN
        assert not w.rum and w.bananas == 0 and not w.pack


def test_pirate_smuggling_recovers_missing_rum_and_failed_shipment():
    with CrateWorld() as w:
        assert not w.run(island.ship_crate(w.logs.append))
        assert w.position == island.PT_TILE.WYDIN
        w.rum = True
        w.bananas = 10
        w.can_ship = False
        assert not w.run(island.ship_crate(w.logs.append))
    with CrateWorld() as w:
        w.can_walk = False
        assert not w.run(island.stash_rum(w.logs.append))
        assert not w.run(island.fill_crate(w.logs.append))
        assert w.run(island.pick_bananas(1, w.logs.append)) == 0
    with CrateWorld() as w:
        w.scene = [w.scene[0]]
        assert not w.run(island.fill_crate(w.logs.append))
        w.hold('Banana', id=island.PT_ID.BANANA)
        assert w.run(island.pick_bananas(1, w.logs.append)) == 1


def test_pirate_resmuggling_rehires_after_crate_refusal_and_verifies_shipment():
    for mode in ['rehired', 'walk_failed', 'talk_failed', 'stash_failed', 'rum_missing', 'unshipped']:
        with CrateWorld() as w:
            w.pack = [Cargo(w, 'Karamjan rum', island.PT_ID.RUM)]
            w.bananas = 10
            state = FakeModule(attempts=0)
            def stash(log):
                state.attempts += 1
                yield from w.reply()
                if state.attempts == 1:
                    if mode == 'walk_failed':
                        w.can_walk = False
                    return False
                w.rum = mode != 'rum_missing'
                return mode != 'stash_failed'
            def talk(*args):
                yield from w.reply()
                if state.attempts >= 2 and mode != 'unshipped':
                    w.rum = False
                return mode != 'talk_failed'
            w.patch(island, 'stash_rum', stash)
            w.patch(island, 'talk_strict', talk)
            assert w.run(island.ship_crate(w.logs.append)) == (mode == 'rehired')


def test_pirate_stash_reads_existing_rum_before_spending_another_bottle():
    with CrateWorld() as w:
        w.rum = True
        w.pack = [Cargo(w, 'Karamjan rum', island.PT_ID.RUM)]
        assert w.run(island.stash_rum(w.logs.append))
        assert w.count_by_id(island.PT_ID.RUM) == 1

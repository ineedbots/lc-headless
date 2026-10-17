# Account settings: script.settings["Chicken Killer"].
SETTINGS = {
    'combat_style': SettingDef('string', 'strength', label='Combat style', options=COMBAT_STYLE_OPTIONS),
    'start_location': SettingDef('tile', [3230, 3298, 0], label='Start location (Lumbridge east chicken pen by default)'),
    'radius': SettingDef('number', 8, min=0, label='Fight and loot radius (tiles)'),
    'bury_bones': SettingDef('boolean', False, label='Pick up and bury bones'),
    'kill_over_loot': SettingDef('boolean', False, label='Only loots when theres no targets'),
}

GIVE_UP_TICKS = 15
SKIP_TICKS = 50
POLL_TICKS = 1
CHICKEN_NAME = 'Chicken'
LOOT_EXTRA_DIST = 3

class ChickenKiller(TaskBot):
    def on_start(self):
        self.kills = 0
        self.buried = 0
        self.target = None
        self.attack_tick = 0
        self.loot_skip = {}
        self.npc_skip = {}
        self.npc_spawns = {}
        self.npc_despawn_times = {}
        self.dying_targets = set()
        log('Killing', CHICKEN_NAME, 'around', self.settings.start_location, ', starting at', game.tile(), ', pid', players.local().index)

        self.add(
            Task(self.is_fighting_target, lambda: execution.delay_ticks(POLL_TICKS), label='fight'),
            Task(lambda: not game.has_combat_style(self.settings.combat_style), self.set_style, label='style'),
            Task(self.away_from_start, self.walk_to_start, label='return'),
            Task(lambda: self.next_loot(True) is not None, lambda: self.pick_up(True), label='loot'), # prio feathers
            Task(lambda: self.settings.bury_bones and inventory.contains('Bones') and inventory.is_full(), self.bury, label='bury'),
            Task(lambda: self.next_loot() is not None and (not self.settings.kill_over_loot or self.next_target() is None), self.pick_up, label='loot'),
            Task(lambda: True, self.attack, label='attack'),
        )

    def ensure_reachable(self, tile, force=False):
        if not force and direct_navigator.reachable(tile):
            return True

        yield from traversal.walk_resilient(
            tile, radius=1, timeout_ms=120000,
            use_teleport_catalog=False, log=lambda msg: log(msg))

        return direct_navigator.reachable(tile)

    def key_for_npc(self, npc):
        return npc.index

    def is_fighting_target(self):
        if self.target is None:
            return False

        targetting = players.local().target
        if targetting is None or targetting[0] != 'npc' or targetting[1] != self.target:
            self.target = None
            return False

        npc = npcs.get(self.target)
        if npc is None:
            self.target = None
            return False

        if npc.in_combat:
            if npc.health == 0:
                self.dying_targets.add(self.target)

                self.target = None
                return False

            if npc.targets_another_player():
                self.target = None
                return False

        if game.in_combat():
            self.attack_tick = game.tick()
        elif game.tick() - self.attack_tick >= GIVE_UP_TICKS:
            self.npc_skip[self.key_for_npc(npc)] = game.tick() + SKIP_TICKS
            log('Could not attack', npc, '- leaving it for a while')

            self.target = None
            return False

        return True

    def away_from_start(self):
        here = game.tile()
        if here is None:
            return True

        start = self.settings.start_location
        if here.level != start.level or here.distance_to(start) > self.settings.radius:
            return True

        return False

    def walk_to_start(self):
        self.target = None
        log('Walking to', self.settings.start_location)

        reachable = yield from self.ensure_reachable(self.settings.start_location, True)
        if not reachable:
            log('Could not reach the start location; retrying shortly')
            yield from execution.delay(5000)

    def set_style(self):
        self.target = None
        log('Setting combat style', self.settings.combat_style)

        game.set_combat_style(self.settings.combat_style)
        yield from execution.delay_until(lambda: game.has_combat_style(self.settings.combat_style), 3000)

    def key_for_item(self, item):
        tile = item.tile()
        return (item.id, tile.x, tile.z, tile.level)

    def next_loot(self, feather_only=False):
        names = []
        if not inventory.is_full() or inventory.contains('Feather'):
            names.append('Feather')

        if self.settings.bury_bones and not inventory.is_full() and not feather_only:
            names.append('Bones')

        if not names:
            return None

        now = game.tick()
        self.loot_skip = {key: until for key, until in self.loot_skip.items() if until > now}
        return (ground_items.query()
                .name(names)
                .within_of(self.settings.start_location, self.settings.radius + LOOT_EXTRA_DIST)
                .where(lambda item: self.key_for_item(item) not in self.loot_skip)
                .reachable()
                .nearest())

    def pick_up(self, feather_only=False):
        loot = self.next_loot(feather_only)
        if loot is None:
            return

        name = loot.name
        if name is None:
            return

        reachable = yield from self.ensure_reachable(loot.tile())
        if not reachable:
            return

        self.target = None
        log('Picking up', name)

        going_to_move = loot.tile().distance_to(game.tile()) > 0
        before = inventory.count(name)
        if loot.interact('Take'):
            if going_to_move:
                yield from execution.delay_ticks(POLL_TICKS * 2)
                yield from execution.delay_until(lambda: inventory.count(name) != before or not game.moving(), 10000)
            else:
                yield from execution.delay_until(lambda: inventory.count(name) != before, 10000)

        if inventory.count(name) == before:
            self.loot_skip[self.key_for_item(loot)] = game.tick() + SKIP_TICKS
            log('Could not pick up', loot, '- leaving it for a while')

    def bury(self):
        while inventory.contains('Bones'):
            bones = inventory.first('Bones')
            if bones is None:
                return

            self.target = None
            log('Burying bone')

            before = inventory.count('Bones')
            if not bones.interact('Bury'):
                return

            buried = yield from execution.delay_until(lambda: inventory.count('Bones') < before, 3000)
            if buried:
                self.buried += 1

    def next_target(self):
        if game.in_combat():
            npc = npcs.query().where(lambda npc: npc.targets_me()).nearest()
            if not npc is None:
                return npc

        now = game.tick()
        self.npc_skip = {key: until for key, until in self.npc_skip.items() if until > now}
        return (npcs.query()
                       .name(CHICKEN_NAME).action('Attack')
                       .within_of(self.settings.start_location, self.settings.radius)
                       .where(lambda npc: self.key_for_npc(npc) not in self.npc_skip)
                       .where(lambda npc: not npc.in_combat or npc.targets_me())
                       .nearest())

    def finish_waiting_for_attack(self):
        if self.target is None:
            return True

        npc = npcs.get(self.target)
        if npc is None or npc.in_combat:
            return True

        return False

    def attack(self):
        self.target = None
        npc = self.next_target()

        if npc is None:
            next_spawn = None
            for key, despawn_tick in self.npc_despawn_times.items():
                if key not in self.npc_spawns:
                    continue

                spawn = self.npc_spawns[key]
                if spawn.distance_to(self.settings.start_location) <= self.settings.radius and (next_spawn is None or despawn_tick < next_spawn[1]):
                    next_spawn = (spawn, despawn_tick)

            if next_spawn is not None and next_spawn[0].distance_to(game.tile()) > 1:
                reachable = yield from self.ensure_reachable(next_spawn[0])
                if not reachable:
                    yield from execution.delay_ticks(POLL_TICKS)
                    return

                yield from traversal.walk_to(next_spawn[0], radius=1, timeout_ms=20000)

            yield from execution.delay_ticks(POLL_TICKS)
            return

        reachable = yield from self.ensure_reachable(npc.tile())
        if not reachable:
            yield from execution.delay_ticks(POLL_TICKS)
            return

        log('Attacking', npc)
        if not npc.interact('Attack'):
            yield from execution.delay_ticks(POLL_TICKS)
            return

        self.target = npc.index
        self.attack_tick = game.tick()
        yield from execution.delay_until(self.finish_waiting_for_attack, 5000)

    def on_npc_spawned(self, npc):
        if npc.name == CHICKEN_NAME:
            key = self.key_for_npc(npc)
            self.npc_despawn_times.pop(key, None)
            self.npc_spawns[key] = npc.tile()

    def on_npc_despawned(self, npc):
        if npc.name == CHICKEN_NAME:
            self.npc_despawn_times[self.key_for_npc(npc)] = game.tick()

        if npc.index == self.target:
            self.target = None

        if npc.index in self.dying_targets:
            self.dying_targets.remove(npc.index)
            self.kills += 1
            log('Killed', npc, ', total:', self.kills)

    def on_server_message(self, msg):
        if msg.startswith("I can't reach"):
            self.target = None
            log('Unreachable')

            self.walk_to_start()
        elif msg.startswith("Oh dear"):
            log('You have died')

    def on_progress_report(self):
        return {'Kills': self.kills, 'Feathers held': inventory.count('Feather'), 'Bones buried': self.buried}


BOT = define_bot(
    name='Chicken Killer',
    create=ChickenKiller,
    description='Kills chickens, collects feathers and optionally buries bones near a chosen start location',
    category='Combat',
    settings_schema=SETTINGS,
)

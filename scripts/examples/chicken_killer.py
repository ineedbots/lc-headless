# Kills chickens and picks up their bones, then logs out: a TaskBot that fights, loots and waits on
# what it did. The settings are in SETTINGS below; an account file overrides any of them in its
# script.settings["Chicken killer"], which the client fills in with these defaults when the script loads.

SETTINGS = {
    'npcs': SettingDef('string[]', ['Chicken'], label='NPCs to attack'),
    'loot': SettingDef('string[]', ['Bones'], label='Items to pick up'),
    'loot_goal': SettingDef('number', 3, min=1, label='Log out once the backpack holds this much loot'),
    'centre': SettingDef('tile', [3230, 3298], label='Where to fight: the chicken pen east of Lumbridge'),
    'radius': SettingDef('number', 8, min=1, max=30, label='How far from the centre to fight'),
    'teleport': SettingDef('string', '', help='A ::tele argument for staff accounts, used on start when the centre is far away, such as "0,50,51,30,34"'),
}

# A target that neither side has hit for this many ticks after the attack is given up on.
GIVE_UP_TICKS = 15
# An item that hasn't been picked up after this many tries is left, as it's probably behind a fence.
MAX_PICKUP_TRIES = 3


class ChickenKiller(TaskBot):
    def on_start(self):
        self.kills = 0
        self.target = None
        self.attack_tick = 0
        self.pickup_tries = {}
        log('Starting at', game.tile())
        if self.settings.teleport and game.tile().distance_to(self.settings.centre) > 50:
            log('Teleporting to', self.settings.teleport)
            chat.command('tele ' + self.settings.teleport)

        # Highest priority first: each loop runs the first task whose check passes.
        self.add(
            Task(self.is_fighting, lambda: None, label='fight'),
            Task(self.has_enough_loot, self.finish, label='finish'),
            Task(lambda: self.next_loot() is not None, self.pick_up, label='loot'),
            Task(lambda: True, self.attack, label='attack'),
        )

    def count_loot(self):
        return sum([inventory.count(name) for name in self.settings.loot])

    def is_fighting(self):
        if self.target is None:
            return False
        npc = npcs.get(self.target)
        if npc is not None and (game.in_combat() or npc.in_combat or game.tick() - self.attack_tick < GIVE_UP_TICKS):
            return True
        self.target = None
        return False

    def has_enough_loot(self):
        return self.count_loot() >= self.settings.loot_goal or inventory.is_full()

    def finish(self):
        if game.in_combat():
            return
        log('Holding', self.count_loot(), 'loot after', self.kills, 'kills; done')
        stop_account()

    def next_loot(self):
        if game.in_combat():
            return None
        return (ground_items.query()
                .name(self.settings.loot)
                .within_of(self.settings.centre, self.settings.radius)
                .where(lambda item: self.pickup_tries.get(self.key(item), 0) < MAX_PICKUP_TRIES)
                .nearest())

    def key(self, item):
        tile = item.tile()
        return (item.id, tile.x, tile.z)

    def pick_up(self):
        loot = self.next_loot()
        key = self.key(loot)
        self.pickup_tries[key] = self.pickup_tries.get(key, 0) + 1
        before = self.count_loot()
        log('Picking up', loot)
        loot.interact('Take')
        # Waits for the backpack to change, or gives the item up for this try after 5 seconds.
        picked = yield from execution.delay_until(lambda: self.count_loot() > before, 5000)
        if not picked and self.pickup_tries[key] >= MAX_PICKUP_TRIES:
            log("Can't reach", loot, '- leaving it')

    def attack(self):
        centre = self.settings.centre
        npc = (npcs.query()
               .name(self.settings.npcs)
               .within_of(centre, self.settings.radius)
               .where(lambda npc: not npc.in_combat)
               .nearest())
        if npc is None:
            if game.tile().distance_to(centre) > 2:
                direct_navigator.walk(centre)
            yield from execution.delay(1200)
            return

        if npc.interact('Attack'):
            self.target = npc.index
            self.attack_tick = game.tick()
            log('Attacking', npc)
        yield from execution.delay_ticks(2)

    def on_npc_despawned(self, npc):
        if npc.index == self.target and npc.health == 0:
            self.kills += 1
            log('Killed', npc, '- kills so far:', self.kills)
            self.target = None

    def on_server_message(self, msg):
        if msg.startswith("I can't reach"):
            log('Unreachable; picking another target')
            self.target = None

    def on_progress_report(self):
        return {'Kills': self.kills, 'Loot held': self.count_loot(), 'Loot goal': self.settings.loot_goal}


BOT = define_bot(
    name='Chicken killer',
    create=ChickenKiller,
    description='Kills chickens, picks up their bones and logs out at a goal',
    category='Combat',
    settings_schema=SETTINGS,
)

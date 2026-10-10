# Mines rocks and drops the ore when the backpack is full: a LoopingBot whose loop waits on each swing.
# Needs a pickaxe in the backpack or wielded. Every rock in 2004 is named "Rocks", so they're found by id.

ROCK_IDS = {
    'Copper': [2090, 2091],
    'Tin': [2094, 2095],
    'Iron': [2092, 2093],
}
ORES = ['Copper ore', 'Tin ore', 'Iron ore']

SETTINGS = {
    'rocks': SettingDef('string[]', ['Copper', 'Tin'], options=['Copper', 'Tin', 'Iron'], label='Rocks to mine'),
    'centre': SettingDef('tile', [3286, 3366], label='The mine: south-east of Varrock'),
    'radius': SettingDef('number', 10, min=1, max=30),
    'teleport': SettingDef('string', '', help='A ::tele argument for staff accounts, such as "0,51,52,22,38"'),
    'ore_goal': SettingDef('number', 0, min=0, label='Log out after mining this many ores; 0 for never'),
}

# A swing that gets no ore in this long, and leaves the rock standing, is tried again.
SWING_TIMEOUT_MS = 8000


class PowerMiner(LoopingBot):
    def on_start(self):
        self.ores_mined = 0
        self.rock_ids = []
        for rock in self.settings.rocks:
            self.rock_ids.extend(ROCK_IDS[rock])
        if self.settings.teleport and game.tile().distance_to(self.settings.centre) > 50:
            chat.command('tele ' + self.settings.teleport)

    def has_pickaxe(self):
        held = inventory.items() + equipment.items()
        return any([item.name is not None and item.name.endswith('pickaxe') for item in held])

    def loop(self):
        if not self.has_pickaxe():
            # The server says so in a message box, which phase 4's chat_dialog reads; checking first is simpler.
            log('No pickaxe; stopping')
            stop_script()
            return
        if self.settings.ore_goal and self.ores_mined >= self.settings.ore_goal:
            log('Mined', self.ores_mined, 'ores; done')
            stop_account()
            return
        if inventory.is_full():
            yield from self.drop_ore()
            return 0

        rock = (locs.query()
                .id(self.rock_ids)
                .within_of(self.settings.centre, self.settings.radius)
                .nearest())
        if rock is None:
            direct_navigator.walk(self.settings.centre)
            return 1200

        before = inventory.used()
        if not rock.interact('Mine'):
            return 600
        # Done when the ore lands, or the rock is mined out by someone else.
        yield from execution.delay_until(lambda: inventory.used() > before or not rock.valid(), SWING_TIMEOUT_MS)

    def drop_ore(self):
        for item in inventory.items():
            if item.name in ORES:
                item.interact('Drop')
                yield from execution.delay(100)

    def on_skill_xp(self, e):
        if e.name == 'mining':
            self.ores_mined += 1

    def on_progress_report(self):
        return {'Ores mined': self.ores_mined, 'Mining level': skills.level('mining')}


BOT = define_bot(
    name='Power miner',
    create=PowerMiner,
    description='Mines rocks and drops the ore',
    category='Mining',
    settings_schema=SETTINGS,
)

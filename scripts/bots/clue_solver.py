# Solves the clue scroll or opens the casket in the pack, and idles until it's handed another: rs2b0t's ClueSolver
# (MIT, see thirdparty/rs2b0t). It banks everything but the trail's kit at the nearest bank, walks the trail, takes the
# reward, and banks the reward after.

from rs2004.catalogs import LOADOUT_SETTING, ContinueDialog, food_heal_amount, script_food, should_eat_to_use_food, sustain
from rs2004.clues import SPADE_NAME, TRIO, SolveClue, held_clue_like_id, open_clue_bank, tiles_to, walk_to_bank

SETTINGS = {
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 8, 'Food to withdraw', 1, 27),
    'restore_prayer': SettingDef('boolean', True, 'Top up prayer between trails',
                                 help='prays at the nearest altar after the bank stop; hard dig guardians are fought under Protect from Magic'),
    'use_teleports': SettingDef('boolean', True, 'Use teleports',
                                help='routes long legs through spell teleports and the ring of dueling, and stocks the runes at the bank stop'),
}


class BankReturn(Task):
    """After a trail, back to the nearest bank to put the reward away."""

    def __init__(self, bot):
        Task.__init__(self, label='bank return')
        self.bot = bot

    def validate(self):
        return self.bot.return_to_bank and held_clue_like_id() is None and game.tile() is not None

    def execute(self):
        bot = self.bot
        here = game.tile()
        near = nearest_bank(here)
        if near is None:
            bot.log('[clue] no known bank on this level to return to: idling here')
            bot.idle()
            return
        tile = Tile(near['tile']['x'], near['tile']['z'], near['tile']['level'])
        if max(abs(tile.x - here.x), abs(tile.z - here.z)) > 3:
            bot.set_status(f"returning to the {near['name']} bank")
            bot.log(f"[clue] trail done: returning to the {near['name']} bank ({tile})")
            walked = yield from walk_to_bank(tile, lambda m: bot.log(f'  {m}'))
            if not walked:
                bot.log('[clue] walk to the bank failed: idling here')
                bot.idle()
                return
        # Why: the reward has to go in, or the bot stands on the booth holding the trail's loot until the next trail's
        # prep deposits it.
        yield from bot.deposit_trail_loot()
        bot.idle()


class ClueSolver(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'waiting for a clue'
        self.solved = 0
        self.return_to_bank = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.food = script_food(self.settings, '')
        self.food_pattern = self.food.lower()
        self.solve_clue = SolveClue(self)

        def eat():
            if self.food_pattern == '':
                return
            held = [i for i in inventory.items() if self.is_food(i.name)]
            if not held or not should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food), len(held)):
                return
            self.log(f'eating {held[0].name} ({round(skills.hp_fraction() * 100)}% hp)')
            before = skills.effective('hitpoints')
            held[0].interact('Eat')
            yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)

        sustain.set(eat)
        foodless = f", food '{self.food}'" if self.food else ', foodless'
        self.log(f'ClueSolver: watching the pack for clue scrolls and caskets{foodless}')
        self.add(ContinueDialog(), self.solve_clue, BankReturn(self))

    # SolveClue's host

    def set_status(self, text):
        if text == 'clue solved':
            self.solved += 1
            self.return_to_bank = True
        self.status = text

    def is_food(self, name):
        return self.food_pattern != '' and self.food_pattern in (name or '').lower()

    def food_name(self):
        return self.food

    def food_withdraw(self):
        return self.settings.num('food_withdraw', 8)

    def weapon_name(self):
        return self.settings.str('weapon', '')

    def restore_prayer(self):
        return self.settings.bool('restore_prayer', True)

    def use_teleports(self):
        return self.settings.bool('use_teleports', True)

    def idle(self):
        self.return_to_bank = False
        self.set_status('waiting for a clue')

    def deposit_trail_loot(self):
        """Banks the casket's reward, keeping what the next trail runs on."""
        opened = yield from open_clue_bank(lambda m: self.log(f'  {m}'))
        if not opened:
            self.log('[clue] could not open the bank to store the reward')
            return
        keep = [n for n in [self.food, self.weapon_name(), SPADE_NAME] + TRIO + ['Coins', 'Air rune', 'Water rune', 'Earth rune', 'Fire rune', 'Law rune'] if n != '']
        before = inventory.used()
        yield from bank.deposit_all_matching(deposit_all_except(keep))
        self.log(f'[clue] banked the reward ({before} to {inventory.used()} slots used)')
        yield from bank.close()

    def on_progress_report(self):
        held = held_clue_like_id()
        current = self.solve_clue.executor.current
        report = {
            'Status': 'waiting for a clue' if held is None and not self.return_to_bank else self.status,
            'Solved': self.solved,
            'Held clue': held if held is not None else 'none',
            'Clue': self.solve_clue.clue_status(),
        }
        if current is not None:
            report['Leg'] = f'{current.leg}: {current.step} (attempt {current.attempt})'
            # Why: a long walk logs little, so the distance left is what tells a walk from a stall.
            left = tiles_to(current.target)
            if left is not None:
                report['To go'] = f'{left} of {current.start_dist} tiles'
        report['At'] = str(game.tile())
        return report


BOT = define_bot(
    name='ClueSolver',
    create=ClueSolver,
    description='Solves the easy clue scroll (or opens the casket) in your pack: banks everything except clue/food/spade at the nearest bank, walks the trail, opens the reward. Idles until you hand it a clue.',
    category='Treasure Trails',
    tags=['clues', 'banking', 'utility'],
    settings_schema=SETTINGS,
)

"""Funding a quest's coins against spied facades: reaching a Man, pickpocketing him, clearing what he says, buying and
eating a Kebab below the safe health, and which town the coins come from, each through its success and its failures."""

import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.exec import fund_coins
from rs2004.quests.exec.fund_coins import AL_KHARID_ENTRY_CASH, AL_KHARID_FUNDING_MAN, FUNDING_STALL_MS, KEBAB_SELLER, SAFE_PICKPOCKET_HP, VARROCK_FUNDING_MAN
from rs2004.traversal import traversal

after_each(lambda: event_signal.set_interrupt(None))


class Town:
    """The player in a town with a Man and a Kebab seller. A pickpocket pays pay coins, or hurts when hurts is set."""

    def __init__(self, at=None, coins=0, hp=10):
        self.at = at if at is not None else AL_KHARID_FUNDING_MAN
        self.coins = coins
        self.hp = hp
        self.xp = 0
        self.kebabs = 0
        self.pay = 30
        self.hurts = 0
        self.man_at = self.at
        self.has_man = True
        self.has_seller = True
        self.man_ok = True
        self.seller_ok = True
        self.eat_ok = True
        self.walk_ok = True
        self.moves = True
        self.walks = []
        self.ticks = []
        self.lines = []
        self.clock = 0
        self.tick_ms = 0
        self.chat = FakeChat([]).install(chat_dialog)
        self.chat_on_talk = []
        self.on_pick = None
        self.regen_to = None
        self.upkeep_hp = None
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(inventory, 'count', impl=self.count)
        spy_on(inventory, 'items', impl=self.items)
        spy_on(skills, 'xp', impl=lambda name: self.xp)
        spy_on(skills, 'effective', impl=lambda name: self.hp)
        spy_on(npcs, 'query', impl=querying(self.rows))
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        spy_on(execution, 'delay_ticks', impl=self.delay_ticks)
        spy_on(execution, 'delay_until', impl=self.delay_until)
        spy_on(sustain, 'run', impl=self.upkeep)
        spy_on(_core, 'step_time', impl=lambda: self.clock)

    def log(self, line):
        self.lines.append(line)

    def logged(self, text):
        return len([line for line in self.lines if text in line]) > 0

    def count(self, name):
        if name == 'Coins':
            return self.coins
        return self.kebabs if name == 'Kebab' else 0

    def items(self):
        if self.kebabs > 0:
            return [Fake(name='Kebab', interact=self.eat)]
        return []

    def eat(self, op):
        if not self.eat_ok:
            return False
        self.kebabs -= 1
        self.hp += 5
        return True

    def rows(self):
        rows = []
        if self.has_man:
            rows.append(Fake(name='Man', tile=lambda: self.man_at, distance=lambda: 2, actions=lambda: ['Pickpocket'], interact=self.pick))
        if self.has_seller:
            rows.append(Fake(name='Kebab seller', tile=lambda: self.at, distance=lambda: 2, actions=lambda: ['Talk-to'], interact=self.talk))
        return rows

    def pick(self, op):
        if not self.man_ok:
            return False
        if self.on_pick is not None:
            self.on_pick()
        if self.hurts > 0:
            self.hp -= self.hurts
        else:
            self.coins += self.pay
            self.xp += self.pay
        return True

    def talk(self, op):
        if self.seller_ok:
            self.chat.pages = list(self.chat_on_talk)
        return self.seller_ok

    def walk(self, dest, radius=0, attempts=0, timeout_ms=0, log=None):
        self.walks.append(dest)
        if self.walk_ok and self.moves:
            self.at = dest
            self.man_at = dest
        return self.walk_ok
        yield

    def delay_ticks(self, n=1):
        self.ticks.append(n)
        self.clock += self.tick_ms
        return None
        yield

    def delay_until(self, cond, timeout_ms=6000):
        self.clock += self.tick_ms
        if self.regen_to is not None:
            self.hp = self.regen_to
        return cond()
        yield

    def upkeep(self):
        if self.upkeep_hp is not None:
            self.hp = self.upkeep_hp
        return None
        yield

    def interrupt_after(self, calls):
        state = {'left': calls}

        def pending():
            state['left'] -= 1
            return state['left'] < 0

        event_signal.set_interrupt(pending)


def nothing_owed():
    town = Town()
    expect(run_wait(fund_coins.fund_quest_coins(0, town.log))).to_be(True)
    town.coins = 50
    expect(run_wait(fund_coins.fund_quest_coins(50, town.log))).to_be(True)
    expect(town.walks).to_have_length(0)


test('nothing is earned when no coins are owed or the pack already holds them', nothing_owed)


def farms_in_al_kharid():
    town = Town(coins=80)
    expect(run_wait(fund_coins.fund_quest_coins(130, town.log, label='waterfall'))).to_be(True)
    expect(town.coins).to_be(140)
    expect(town.logged('waterfall funding: 110/130 gp')).to_be(True)
    expect(town.walks).to_equal([AL_KHARID_FUNDING_MAN])


test('inside Al Kharid the Man there is farmed to the target and each hundred is reported', farms_in_al_kharid)


def varrock_pays_the_toll():
    town = Town(at=VARROCK_FUNDING_MAN)
    expect(run_wait(fund_coins.fund_quest_coins(50, town.log))).to_be(True)
    expect(town.walks).to_equal([VARROCK_FUNDING_MAN, AL_KHARID_FUNDING_MAN, AL_KHARID_FUNDING_MAN])
    expect(town.logged(f'earning {AL_KHARID_ENTRY_CASH} gp')).to_be(True)


test('west of the toll gate a Varrock Man pays the toll, then Al Kharid finishes the sum', varrock_pays_the_toll)


def varrock_covers_small_sums():
    town = Town(at=VARROCK_FUNDING_MAN)
    expect(run_wait(fund_coins.fund_quest_coins(10, town.log))).to_be(True)
    expect(town.walks).to_equal([VARROCK_FUNDING_MAN])


test('a target below the toll money ends in Varrock, with no walk through the gate', varrock_covers_small_sums)


def varrock_failure_stops():
    town = Town(at=VARROCK_FUNDING_MAN)
    town.walk_ok = False
    expect(run_wait(fund_coins.fund_quest_coins(50, town.log))).to_be(False)
    expect(town.walks).to_equal([VARROCK_FUNDING_MAN])


test('failing to reach the Varrock Man stops the funding', varrock_failure_stops)


def toll_holder_skips_varrock():
    town = Town(at=VARROCK_FUNDING_MAN, coins=AL_KHARID_ENTRY_CASH)
    expect(run_wait(fund_coins.fund_quest_coins(30, town.log))).to_be(True)
    expect(town.walks[0]).to_equal(AL_KHARID_FUNDING_MAN)


test('holding the toll money already goes straight to Al Kharid', toll_holder_skips_varrock)


def shantay_skips_varrock():
    town = Town(at=Tile(3303, 3129, 0))
    expect(run_wait(fund_coins.fund_quest_coins(30, town.log))).to_be(True)
    expect(town.walks[0]).to_equal(AL_KHARID_FUNDING_MAN)
    expect(town.logged('Varrock')).to_be(False)


test('Shantay Pass is already past the toll, so it skips Varrock with no money', shantay_skips_varrock)


def walk_to_town_fails():
    town = Town(at=Tile(3303, 3129, 0))
    town.walk_ok = False
    expect(run_wait(fund_coins.fund_quest_coins(30, town.log))).to_be(False)


test('failing the walk to Al Kharid stops the funding', walk_to_town_fails)


def walk_lands_elsewhere():
    town = Town(at=Tile(3303, 3129, 0))
    town.moves = False
    expect(run_wait(fund_coins.fund_quest_coins(30, town.log))).to_be(False)
    expect(town.logged('did not reach the Al Kharid')).to_be(True)


test('a walk that reports success outside the town is refused', walk_lands_elsewhere)


def interrupted_after_walk():
    town = Town(at=Tile(3303, 3129, 0))
    town.interrupt_after(1)
    expect(run_wait(fund_coins.fund_quest_coins(30, town.log))).to_be(False)
    expect(town.walks).to_have_length(1)
    expect(town.coins).to_be(0)


test('a runtime event during the walk to town yields before farming', interrupted_after_walk)


def reach_refusals():
    town = Town()
    town.interrupt_after(0)
    expect(run_wait(fund_coins.reach_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(False)
    expect(town.walks).to_have_length(0)

    event_signal.set_interrupt(None)
    town.interrupt_after(1)
    expect(run_wait(fund_coins.reach_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(False)
    expect(town.walks).to_have_length(1)

    event_signal.set_interrupt(None)
    town.walk_ok = False
    expect(run_wait(fund_coins.reach_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(False)


test('reaching the Man gives up on an event before or after the walk, and on a failed walk', reach_refusals)


def no_man_named():
    town = Town()
    town.has_man = False
    expect(run_wait(fund_coins.reach_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(False)
    expect(town.logged('no pickpocketable Man')).to_be(True)


test('a town with no Man is logged and fails', no_man_named)


def far_man_is_out_of_leash():
    town = Town()
    town.man_at = Tile(AL_KHARID_FUNDING_MAN.x + fund_coins.FUNDING_MAN_LEASH + 1, AL_KHARID_FUNDING_MAN.z, 0)
    expect(fund_coins.funding_man(AL_KHARID_FUNDING_MAN)).to_be_null()
    town.man_at = Tile(AL_KHARID_FUNDING_MAN.x + fund_coins.FUNDING_MAN_LEASH, AL_KHARID_FUNDING_MAN.z, 0)
    expect(fund_coins.funding_man(AL_KHARID_FUNDING_MAN)).to_be_defined()


test('a Man past the leash is not the funding Man', far_man_is_out_of_leash)


def man_turns_up_during_the_wait():
    town = Town()
    town.has_man = False

    def appears(cond, timeout_ms=6000):
        town.has_man = True
        return cond()
        yield

    spy_on(execution, 'delay_until', impl=appears)
    expect(run_wait(fund_coins.reach_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(True)


test('a Man walking in during the wait is accepted', man_turns_up_during_the_wait)


def dialog_cleared():
    town = Town()
    town.chat.pages = ['continue', 'continue']
    expect(run_wait(fund_coins.clear_funding_dialog())).to_be(True)
    expect(town.chat.pages).to_have_length(0)
    expect(town.ticks).to_equal([1, 1])


test('what the Man says is continued through a page a tick', dialog_cleared)


def dialog_interrupted():
    town = Town()
    town.chat.pages = ['continue', 'continue']
    town.interrupt_after(0)
    expect(run_wait(fund_coins.clear_funding_dialog())).to_be(False)
    expect(town.chat.pages).to_have_length(2)


test('a runtime event leaves the rest of his dialog alone', dialog_interrupted)


def pick_refused_by_interact():
    town = Town()
    town.man_ok = False
    expect(run_wait(fund_coins.pickpocket_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(True)
    expect(town.ticks).to_equal([2])
    expect(town.coins).to_be(0)


test('a refused pickpocket click waits and lets the loop try again', pick_refused_by_interact)


def pick_with_no_change():
    town = Town()
    town.pay = 0
    expect(run_wait(fund_coins.pickpocket_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(True)
    expect(town.logged('produced no coin, XP, health, or dialogue change')).to_be(True)
    expect(town.ticks).to_equal([2])


test('a pickpocket that changes nothing is logged and retried', pick_with_no_change)


def pick_failed_stuns():
    town = Town()
    town.hurts = 1
    expect(run_wait(fund_coins.pickpocket_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(True)
    expect(town.ticks).to_equal([8])


test("a failed pickpocket waits out the Man's eight-tick stun", pick_failed_stuns)


def pick_finds_the_man_again():
    town = Town()
    town.man_at = Tile(3000, 3000, 0)
    expect(run_wait(fund_coins.pickpocket_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(True)
    expect(town.walks).to_equal([AL_KHARID_FUNDING_MAN])
    expect(town.coins).to_be(town.pay)


test('a Man who wandered off is walked back to first', pick_finds_the_man_again)


def pick_gives_up():
    town = Town()
    town.interrupt_after(0)
    expect(run_wait(fund_coins.pickpocket_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(False)

    event_signal.set_interrupt(None)
    town = Town()
    town.man_at = Tile(3000, 3000, 0)
    town.walk_ok = False
    expect(run_wait(fund_coins.pickpocket_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(False)
    expect(town.coins).to_be(0)


test('pickpocketing gives up on a pending event or an unreachable Man', pick_gives_up)


def pick_interrupted_while_waiting():
    town = Town()
    town.on_pick = lambda: event_signal.set_interrupt(lambda: True)
    expect(run_wait(fund_coins.pickpocket_funding_man(AL_KHARID_FUNDING_MAN, town.log))).to_be(False)


test('a runtime event while the pickpocket resolves yields at once', pick_interrupted_while_waiting)


def seller_pages():
    return ['continue', ['No thank you.', 'Yes please.'], 'continue']


def kebab_town():
    town = Town(at=KEBAB_SELLER, coins=5)
    town.chat_on_talk = seller_pages()

    def buys(text):
        town.kebabs += 1

    town.chat.on_choose = buys
    return town


def kebab_bought():
    town = kebab_town()
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(True)
    expect(town.kebabs).to_be(1)
    expect(town.chat.chosen).to_equal(['Yes please.'])


test('a Kebab is bought with the exact "Yes please."', kebab_bought)


def kebab_refusals():
    town = kebab_town()
    town.interrupt_after(0)
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)
    event_signal.set_interrupt(None)

    town = kebab_town()
    town.walk_ok = False
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)

    town = kebab_town()
    town.has_seller = False
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)
    expect(town.logged('no talkable Kebab seller')).to_be(True)

    town = kebab_town()
    town.seller_ok = False
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)


test('a Kebab fails on an event, a failed walk, no seller or a refused talk', kebab_refusals)


def kebab_odd_options():
    town = kebab_town()
    town.chat_on_talk = [['Maybe later.']]
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)
    expect(town.logged('unexpected options: [Maybe later.]')).to_be(True)
    expect(town.chat.chosen).to_have_length(0)


test('options without the exact wording are logged, and none is picked', kebab_odd_options)


def kebab_choice_refused():
    town = kebab_town()

    def refused(text):
        return False
        yield

    spy_on(chat_dialog, 'choose_option', impl=refused)
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)


test('a choice the dialog refuses fails the purchase', kebab_choice_refused)


def kebab_interrupted_mid_dialog():
    town = kebab_town()
    town.interrupt_after(1)
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)
    expect(town.kebabs).to_be(0)


test('a runtime event in the dialog fails the purchase', kebab_interrupted_mid_dialog)


def kebab_never_arrives():
    town = kebab_town()
    town.chat_on_talk = []
    expect(run_wait(fund_coins.buy_kebab(town.log))).to_be(False)
    expect(town.logged('within 40 dialogue steps')).to_be(True)
    expect(town.ticks).to_have_length(40)


test('a seller who never completes a sale gives up after forty steps', kebab_never_arrives)


def eating():
    town = Town(hp=1)
    expect(run_wait(fund_coins.eat_funding_kebab())).to_be(False)
    town.kebabs = 1
    town.eat_ok = False
    expect(run_wait(fund_coins.eat_funding_kebab())).to_be(False)
    town.eat_ok = True
    expect(run_wait(fund_coins.eat_funding_kebab())).to_be(True)
    expect(town.hp).to_be(6)


test('eating needs a Kebab and an accepted click, and succeeds once it leaves the pack', eating)


def health_already_safe():
    town = Town(hp=SAFE_PICKPOCKET_HP)
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(True)
    expect(town.walks).to_have_length(0)


test('safe health needs no food', health_already_safe)


def health_from_sustain():
    town = Town(hp=1)
    town.upkeep_hp = SAFE_PICKPOCKET_HP
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(True)
    expect(town.kebabs).to_be(0)


test('the food the sustain eats is enough without a purchase', health_from_sustain)


def health_from_kebab():
    town = kebab_town()
    town.hp = 1
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(True)
    expect(town.hp).to_be(6)
    expect(town.kebabs).to_be(0)


test('low health with coins buys and eats a Kebab', health_from_kebab)


def health_kebab_failures():
    town = kebab_town()
    town.hp = 1
    town.has_seller = False
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(False)

    town = kebab_town()
    town.hp = 1
    town.eat_ok = False
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(False)


test('a Kebab that cannot be bought or eaten stops the funding', health_kebab_failures)


def health_regen():
    town = Town(hp=1, coins=0)
    town.regen_to = SAFE_PICKPOCKET_HP
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(True)
    expect(town.logged('waiting up to')).to_be(True)
    expect(town.walks).to_have_length(0)


test('no coins for a Kebab waits for health to regenerate', health_regen)


def health_regen_skips_kebabs_in_varrock():
    town = Town(hp=1, coins=50)
    town.regen_to = SAFE_PICKPOCKET_HP
    expect(run_wait(fund_coins.restore_funding_health(False, town.log))).to_be(True)
    expect(town.walks).to_have_length(0)


test('where no Kebabs are to be had, health regenerates even with coins', health_regen_skips_kebabs_in_varrock)


def health_never_regens():
    town = Town(hp=1)
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(False)
    expect(town.logged('funding paused')).to_be(True)


test('health that never returns pauses the funding', health_never_regens)


def health_interrupts():
    town = Town(hp=1)
    town.interrupt_after(0)
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(False)
    event_signal.set_interrupt(None)

    town = Town(hp=1)
    town.interrupt_after(1)
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(False)
    event_signal.set_interrupt(None)

    # The regeneration wait ends because of the event, not the health.
    town = Town(hp=1)
    town.interrupt_after(2)
    expect(run_wait(fund_coins.restore_funding_health(True, town.log))).to_be(False)
    expect(town.logged('funding paused')).to_be(False)


test('a runtime event stops the health wait at each of its steps', health_interrupts)


def farm_stalls():
    town = Town()
    town.pay = 0
    town.tick_ms = FUNDING_STALL_MS
    expect(run_wait(fund_coins.farm_funding_coins(AL_KHARID_FUNDING_MAN, 50, True, town.log, 'quest'))).to_be(False)
    expect(town.logged('no cash, Thieving XP, or Hitpoints change')).to_be(True)


test('two minutes with no cash, XP or health change gives up', farm_stalls)


def farm_keeps_going_on_evidence():
    town = Town()
    town.pay = 10
    town.tick_ms = FUNDING_STALL_MS
    expect(run_wait(fund_coins.farm_funding_coins(AL_KHARID_FUNDING_MAN, 30, True, town.log, 'quest'))).to_be(True)
    expect(town.coins).to_be(30)


test('coins arriving reset the stall clock, however slowly they come', farm_keeps_going_on_evidence)


def farm_refusals():
    town = Town()
    town.walk_ok = False
    expect(run_wait(fund_coins.farm_funding_coins(AL_KHARID_FUNDING_MAN, 30, True, town.log, 'quest'))).to_be(False)

    town = Town(hp=1)
    expect(run_wait(fund_coins.farm_funding_coins(AL_KHARID_FUNDING_MAN, 30, False, town.log, 'quest'))).to_be(False)
    expect(town.coins).to_be(0)


test('farming stops when the Man cannot be reached or health stays low', farm_refusals)


def farm_loses_the_man():
    town = Town()
    state = {'walks': 0}

    def first_only(dest, radius=0, attempts=0, timeout_ms=0, log=None):
        state['walks'] += 1
        return state['walks'] == 1
        yield

    def gone_after_first_look():
        state['looks'] = state.get('looks', 0) + 1
        return town.rows() if state['looks'] == 1 else []

    spy_on(traversal, 'walk_resilient', impl=first_only)
    spy_on(npcs, 'query', impl=querying(gone_after_first_look))
    expect(run_wait(fund_coins.farm_funding_coins(AL_KHARID_FUNDING_MAN, 30, False, town.log, 'quest'))).to_be(False)
    expect(state['walks']).to_be(2)
    expect(town.coins).to_be(0)


test('farming stops when the Man vanishes and cannot be walked back to', farm_loses_the_man)


def farm_interrupts():
    town = Town()
    town.interrupt_after(2)
    expect(run_wait(fund_coins.farm_funding_coins(AL_KHARID_FUNDING_MAN, 30, True, town.log, 'quest'))).to_be(False)
    expect(town.coins).to_be(0)
    event_signal.set_interrupt(None)

    town = Town()
    town.on_pick = lambda: event_signal.set_interrupt(lambda: True)
    expect(run_wait(fund_coins.farm_funding_coins(AL_KHARID_FUNDING_MAN, 30, True, town.log, 'quest'))).to_be(False)


test('a runtime event stops the farm before and after a pickpocket', farm_interrupts)


def step_runs_the_funding():
    town = Town(coins=40)
    step = fund_coins.earn_quest_coins_step(40, 'trap')
    expect(run_wait(step.run(town.log))).to_be(True)
    expect(step.name).to_contain('40')


test('the decide-time step runs the funding', step_runs_the_funding)

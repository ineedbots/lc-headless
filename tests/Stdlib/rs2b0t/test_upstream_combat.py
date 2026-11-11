"""Regressions for rs2b0t 27e57fa3's combat progression and recurring supplies."""

from bots.account_leveler.record import Record
from bots.account_leveler.combat import COMBAT_CAMPS, combat_plan
from bots.account_leveler.advanced_camps import ADVANCED_CAMPS
from bots.account_leveler.planner import empty_memory, enabled_skills
from bots.account_leveler.ranging_guild import ranging_guild_plan
from bots.account_leveler.methods import method_for
from bots.account_leveler.session import uses_activity_cooldown
from bots.account_leveler.shopping import SHOPPING_RESERVE
from bots.account_leveler.loot import SECONDARY_LOOT
from bots.account_leveler.equipment import bows
from bots.account_leveler.manifests import manifest_for
from bots.auto_fighter import AutoFighter, should_keep_bank_item
from bots.autofighter.data import is_burial_bone, wants_auto_fighter_loot
from bots.ranging_guild import RangingGuild
from rs2004.settings import SettingsBag
from rs2004.tabs import special
from rs2004.items import inventory, equipment
from rs2004.bank import bank
from rs2004.game import reader


def snapshot(level=80):
    return Record({'levels': {skill: level for skill in enabled_skills},
                   'stock': {'coins': 100000, 'lobster': 100, 'trout': 100, 'bronze arrow': 300},
                   'quests': {}, 'bank_ready': True, 'wilderness': True, 'now': 1000, 'target': 99})


def only(id):
    memory = empty_memory()
    memory.cooldowns = Record({camp.id: 2000 for camp in COMBAT_CAMPS if camp.id != id})
    return memory


def requirements_and_access():
    s = snapshot()
    for camp in ADVANCED_CAMPS:
        for quest in camp.quests or []:
            s.quests[quest] = True
        for need in camp.supplies or []:
            s.stock[need.item.lower()] = need.count
        plan = combat_plan(s, 'attack', only(camp.id), lambda: 0)
        expect(plan.id).to_be(camp.id)
        expect(plan.travel.level).to_be(camp.level or 0)
        expect(plan.settings.leash_radius).to_be(camp.leash_radius or 12)
        expect(plan.settings.use_special).to_be(True)
        for quest in camp.quests or []:
            s.quests[quest] = False
            expect(combat_plan(s, 'attack', only(camp.id), lambda: 0)).to_be(None)
            s.quests[quest] = True
        for skill, level in (camp.skills or Record({})).items():
            s.levels[skill] = level - 1
            expect(combat_plan(s, 'attack', only(camp.id), lambda: 0)).to_be(None)
            s.levels[skill] = 80
        if camp.wilderness:
            s.wilderness = False
            expect(combat_plan(s, 'attack', only(camp.id), lambda: 0)).to_be(None)
            s.wilderness = True
        if camp.prayer == False:
            expect(combat_plan(s, 'prayer', only(camp.id), lambda: 0)).to_be(None)
    dragon = combat_plan(s, 'attack', only('taverley-baby-blue-dragons'), lambda: 0)
    expect(dragon.settings.bury_baby_dragon_bones).to_be(True)
    expect(dragon.settings.travel_items).to_equal(['Dusty key'])
    s.stock['dusty key'] = 0
    expect(combat_plan(s, 'attack', only(dragon.id), lambda: 0)).to_be(None)
    s.stock['bronze axe'] = 0
    s.unavailable_items = ['bronze axe']
    expect(combat_plan(s, 'attack', only('brimhaven-dungeon-moss-giants'), lambda: 0)).to_be(None)
    s.stock['coins'] = 874
    expect(combat_plan(s, 'attack', only('brimhaven-dungeon-fire-giants'), lambda: 0)).to_be(None)


test('advanced camps enforce quests, skills, tools, fares and wilderness consent', requirements_and_access)


def ranged_progression():
    s = snapshot()
    plan = method_for(s, 'ranged', empty_memory(), lambda: 0)
    expect(plan.script).to_be('RangingGuild')
    expect(manifest_for(plan.script).name).to_be('RangingGuild')
    expect(plan.settings.coins_reserve).to_be(SHOPPING_RESERVE)
    expect(uses_activity_cooldown(plan)).to_be(True)
    for camp in ADVANCED_CAMPS:
        if camp.training_tier > 2:
            expect(combat_plan(s, 'ranged', only(camp.id), lambda: 0)).to_be(None)
    memory = empty_memory()
    memory.cooldowns['ranging-guild'] = 2000
    expect(ranging_guild_plan(s, memory)).to_be(None)
    s.levels['ranged'] = 39
    expect(ranging_guild_plan(s, empty_memory())).to_be(None)
    s.levels['ranged'] = 40
    s.stock['coins'] = 0
    expect(ranging_guild_plan(s, empty_memory())).to_be(None)
    s.stock['coins'] = 100000
    s.unavailable_items = [bow.item.lower() for bow in bows]
    expect(ranging_guild_plan(s, empty_memory())).to_be(None)
    for name in ['Herb', 'Unicorn horn', 'Red spiders\' eggs', 'Nature rune', 'Limpwurt root']:
        expect(name in SECONDARY_LOOT).to_be(True)


test('ranged training prefers affordable guild sessions and avoids advanced fights', ranged_progression)


def result(value):
    yield from ()
    return value


def combat_supplies():
    Scene()
    expect(is_burial_bone('Babydragon bones', False, False, True)).to_be(True)
    expect(wants_auto_fighter_loot('Babydragon bones', [], False, False, True)).to_be(True)
    expect(should_keep_bank_item('Babydragon bones', 534, 'Trout', True, [], [], False, False, True)).to_be(True)
    expect(should_keep_bank_item('Babydragon bones', 535, 'Trout', True, [], [], False, False, True)).to_be(False)
    bot = AutoFighter()
    bot.travel_supplies = [('Coins', 1200), ('Bronze axe', 1)]
    counts = {'Coins': 1200, 'Bronze axe': 1}
    spy_on(inventory, 'count', impl=lambda name: counts.get(name, 0))
    expect(run_wait(bot.restock_travel())).to_be(True)
    counts['Coins'] = 100
    counts['Bronze axe'] = 0
    withdrawals = []
    def withdraw_x(name, count):
        withdrawals.append((name, count))
        counts[name] = counts.get(name, 0) + count
        return result(True)
    def withdraw(name, op):
        withdrawals.append((name, op))
        counts[name] = counts.get(name, 0) + 1
        return True
    spy_on(inventory, 'is_full', returns=False)
    spy_on(bank, 'withdraw_x', impl=withdraw_x)
    spy_on(bank, 'withdraw', impl=withdraw)
    expect(run_wait(bot.restock_travel())).to_be(True)
    expect(withdrawals).to_equal([('Coins', 1100), ('Bronze axe', 'Withdraw-1')])
    closed = []
    spy_on(bank, 'close', impl=lambda: result(closed.append(True)))
    spy_on(bank, 'withdraw', returns=False)
    spy_on(bank, 'withdraw_x', impl=lambda name, count: result(False))
    spy_on(inventory, 'is_full', returns=True)
    spy_on(bot, 'request_finish', impl=lambda message: closed.append(message))
    counts['Bronze axe'] = 0
    expect(run_wait(bot.restock_travel())).to_be(False)
    expect(closed).to_equal([True, 'Missing travel supply: Bronze axe'])
    spy_on(special, 'wielded', returns='Magic shortbow')
    spy_on(equipment, 'items', returns=[])
    spy_on(special, 'armed', returns=True)
    spy_on(special, 'disarm', impl=lambda: result(True))
    expect(bot.special_due()).to_be(True)
    expect(run_wait(bot.arm_special())).to_be(True)
    expect(bot.resume_attack).to_be(True)


test('travel supply failures finish safely and an arrow-starved shortbow disarms', combat_supplies)


def guild_reserve():
    Scene()
    bot = RangingGuild()
    bot.settings = SettingsBag({'coins_reserve': 1000})
    bot.banked_coins = 800
    spy_on(inventory, 'count_by_id', impl=lambda id: 300 if id == 995 else 0)
    spy_on(equipment, 'items', returns=[])
    spy_on(inventory, 'items', returns=[])
    expect(bot.view().coins).to_be(100)
    bot.banked_coins = 1000
    expect(bot.view().coins).to_be(300)
    bot.bind_finish(lambda message: None)
    failed = False
    try:
        bot.stop('no bow held, worn or banked', True)
    except RuntimeError:
        failed = True
    expect(failed).to_be(True)


test('guild reserve includes banked coins and delegated failures reach the parent', guild_reserve)


def guild_banking():
    Scene()
    bot = RangingGuild()
    bot.settings = SettingsBag({'coins_reserve': 1000, 'coins_per_trip': 10000})
    bot.banked_coins = 0
    bot.arrows_bought = 0
    bot.bind_log(lambda message: None)
    finishes = []
    bot.bind_finish(finishes.append)
    coins = {'pack': 0, 'bank': 2000}
    spy_on(equipment, 'items', returns=[Record({'name': 'Shortbow', 'slot': 3, 'count': 1, 'id': 841})])
    spy_on(inventory, 'items', returns=[])
    spy_on(inventory, 'count_by_id', impl=lambda id: coins['pack'] if id == 995 else 0)
    spy_on(bank, 'count_by_id', impl=lambda id: coins['bank'] if id == 995 else 0)
    spy_on(bank, 'deposit_all_matching', impl=lambda predicate: result(True))
    spy_on(reader, 'varp', returns=0)
    withdrawals = []
    def withdraw(id, count):
        withdrawals.append(count)
        coins['bank'] -= count
        coins['pack'] += count
        return result(True)
    spy_on(bank, 'withdraw_x_by_id', impl=withdraw)
    run_wait(bot.restock())
    expect(withdrawals).to_equal([1000])
    expect(coins).to_equal({'pack': 1000, 'bank': 1000})
    expect(bot.view().coins).to_be(1000)
    coins['pack'] = 100
    coins['bank'] = 500
    run_wait(bot.restock())
    expect(withdrawals).to_equal([1000])
    expect(len(finishes)).to_be(1)
    bank_trips = []
    spy_on(bot, 'bank_trip', impl=lambda: result(bank_trips.append(True)))
    run_wait(bot.enter())
    run_wait(bot.restock_arrows())
    expect(bank_trips).to_equal([True, True])


test('guild banking preserves the reserve and avoids judge fees when spendable coins run out', guild_banking)

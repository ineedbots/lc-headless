"""Goblin Diplomacy funds supplies without pickpocketing at unsafe health."""

import rs2004.quests.defs.goblindiplomacy as gd
from rs2004 import execution
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class FundingWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.hp = 20
        self.xp = 0
        self.coins = QuestObject(self, 'Coins', 995)
        self.coins.count = 0
        self.pack = [self.coins]

    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(gd)
        self.patch(gd, '_core', self)
        self.patch(gd, 'skills', FakeModule(effective=lambda n: self.hp, xp=lambda n: self.xp))
        return self


def test_funding_man_requires_arrival_and_waits_for_spawn_then_resolves_theft():
    for mode in ['walk_failed', 'missing', 'respawn', 'refused', 'silent', 'coins', 'stunned']:
        with FundingWorld() as w:
            w.can_walk = mode != 'walk_failed'
            w.position = gd.AL_KHARID_FUNDING_MAN
            man = QuestObject(w, 'Man', ops=['Pickpocket'])
            man.accept = mode != 'refused'
            man.effect = lambda: setattr(w.coins, 'count', 100)
            if mode == 'stunned':
                def stun():
                    w.hp -= 1
                    w.pages = [('continue', ['You have been stunned!'])]
                man.effect = stun
            w.scene = [] if mode in ['walk_failed', 'missing', 'respawn'] else [man]
            if mode == 'respawn':
                w.on_update = lambda: setattr(w, 'scene', [man]) if w.now >= 2000 else None
            w.respond = mode != 'silent'
            assert w.run(gd.pickpocket_funding_man(gd.AL_KHARID_FUNDING_MAN, w.logs.append)) == (mode not in ['walk_failed', 'missing'])
            if mode == 'coins':
                assert w.coins.count == 100
            if mode == 'stunned':
                assert w.hp == 19 and not w.pages


def test_funding_kebab_purchase_handles_dialogue_refusal_and_missing_food():
    for mode in ['walk_failed', 'missing', 'refused', 'wrong_options', 'silent', 'done']:
        with FundingWorld() as w:
            w.can_walk = mode != 'walk_failed'
            food = QuestObject(w, gd.FALLBACK_FOOD, ops=['Eat'])
            seller = QuestObject(w, 'Kebab seller', ops=['Talk-to'], at=gd.KEBAB_SELLER)
            seller.accept = mode != 'refused'
            if mode == 'wrong_options':
                seller.effect = lambda: setattr(w, 'pages', [('options', ['Leave'])])
            elif mode == 'done':
                seller.effect = lambda: setattr(w, 'pages', [('continue', ['Fresh kebabs!']), ('options', ['Yes please.', 'No thanks.'])])
                w.on_update = lambda: w.pack.append(food) if w.clicks and w.clicks[-1] == 110 and food not in w.pack else None
            w.scene = [] if mode == 'missing' else [seller]
            assert w.run(gd.buy_one_kebab(w.logs.append)) == (mode == 'done')


def test_funding_eating_requires_food_consumption_and_regenerates_when_broke():
    for mode in ['missing', 'refused', 'silent', 'eaten']:
        with FundingWorld() as w:
            food = QuestObject(w, gd.FALLBACK_FOOD, ops=['Eat'], effect=lambda: setattr(w, 'pack', []))
            food.accept = mode != 'refused'
            w.pack = [] if mode == 'missing' else [food]
            w.respond = mode != 'silent'
            assert w.run(gd.eat_carried_combat_food()) == (mode == 'eaten')
            w.pack = [] if mode == 'missing' else [food]
            assert w.run(gd.eat_funding_kebab()) == (mode == 'eaten')
    for recovers in [True, False]:
        with FundingWorld() as w:
            w.hp = 1
            if recovers:
                w.on_update = lambda: setattr(w, 'hp', gd.SAFE_PICKPOCKET_HP) if w.now >= 2000 else None
            assert w.run(gd.restore_funding_health(False, w.logs.append)) == recovers


def test_funding_farm_stops_stalled_theft_and_logs_each_hundred_coins():
    for mode in ['unreachable', 'stalled', 'funded', 'unsafe']:
        with FundingWorld() as w:
            w.position = gd.AL_KHARID_FUNDING_MAN
            w.can_walk = mode != 'unreachable'
            man = QuestObject(w, 'Man', ops=['Pickpocket'], effect=lambda: setattr(w.coins, 'count', w.coins.count + 100))
            w.scene = [man]
            w.respond = mode != 'stalled'
            if mode == 'unsafe':
                w.hp = 1
            assert w.run(gd.farm_funding_coins(gd.AL_KHARID_FUNDING_MAN, 200, False, w.logs.append)) == (mode == 'funded')
            if mode == 'funded':
                assert w.coins.count == 200 and '200/200' in w.logs[-1]


def test_funding_route_earns_toll_then_crosses_into_the_verified_area():
    for mode in ['already_funded', 'first_failed', 'walk_failed', 'funded']:
        with FundingWorld() as w:
            if mode == 'already_funded':
                w.coins.count = gd.GOBLIN_DIPLOMACY_FUNDING_TARGET
            calls = []
            def farm(anchor, target, kebabs, log):
                calls.append((anchor, target, kebabs))
                yield from w.reply()
                if mode == 'first_failed':
                    return False
                w.coins.count = target
                return True
            w.patch(gd, 'farm_funding_coins', farm)
            w.can_walk = mode != 'walk_failed'
            assert w.run(gd.earn_goblin_diplomacy_coins(w.logs.append)) == (mode in ['already_funded', 'funded'])
            if mode == 'funded':
                assert calls[0][2] is False and calls[1][2] is True


def test_goblin_dyes_source_each_ingredient_and_reject_missing_cash_or_arrival():
    for color in ['Blue', 'Orange']:
        for mode in ['held', 'no_cash', 'leaves', 'unreachable', 'ingredients', 'combine', 'red', 'yellow', 'yellow_no_cash']:
            with FundingWorld() as w:
                w.patch(gd, 'goto_npc', lambda *a: w.reply(mode != 'unreachable'))
                def talk(name, prefer, log):
                    yield from w.reply()
                    if mode == 'ingredients':
                        w.pack.append(QuestObject(w, color + ' dye'))
                    return True
                w.patch(gd, 'talk_through', talk)
                steps = []
                def execute(step, hops, log):
                    steps.append(step)
                    yield from w.reply()
                    return True
                w.patch(gd, 'execute_step', execute)
                w.coins.count = 0 if mode in ['no_cash', 'yellow_no_cash'] else 100
                if mode == 'held':
                    w.pack.append(QuestObject(w, color + ' dye'))
                if mode in ['ingredients', 'unreachable', 'yellow', 'yellow_no_cash']:
                    leaf = QuestObject(w, 'Woad leaf' if color == 'Blue' else 'Redberries')
                    leaf.count = 3
                    w.pack.append(leaf)
                if mode in ['combine', 'red', 'yellow', 'yellow_no_cash']:
                    w.pack.append(QuestObject(w, 'Red dye'))
                if mode == 'combine':
                    w.pack.append(QuestObject(w, 'Yellow dye'))
                if mode in ['yellow', 'yellow_no_cash']:
                    onion = QuestObject(w, 'Onion')
                    onion.count = 2
                    w.pack.append(onion)
                result = w.run((gd.make_blue_dye if color == 'Blue' else gd.make_orange_dye)(w.logs.append))
                expected = mode in ['held', 'ingredients'] if color == 'Blue' else mode in ['held', 'no_cash', 'leaves', 'combine', 'red']
                assert result == expected, (color, mode, w.logs)
                if color == 'Orange' and mode == 'combine':
                    assert steps[-1].product == 'Orange dye'

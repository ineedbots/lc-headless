"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/bones.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.bank import bank, banking
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.hunting.combat import Fight, Retreat
from rs2004.hunting.sites import TAVERLEY_BLUE
from rs2004.hunting.supply import SHIELD, acquire_key, bank_routine, enter_lair, in_cell, leave_cell, leave_lair
from rs2004.items import equipment, inventory
from rs2004.quests.defs.watchtower.areas import WT_ITEM
from rs2004.quests.food import quest_food
from rs2004.quests.weapons import quest_done, wieldable
from rs2004.traversal import traversal

__all__ = ['dragon_bank_pending', 'refresh_dragon_bank', 'in_dragon_lair', 'leave_dragon_lair', 'hunt_dragon_bones']

FOOD = 12


def bones_held():
    return inventory.count_by_id(WT_ITEM.DRAGON_BONES.id) > 0


bank_pending = False


def dragon_bank_pending():
    return bank_pending


def refresh_dragon_bank(log):
    global bank_pending
    if event_signal.pending() or skills.effective('hitpoints') <= 0:
        return False
    _w1 = yield from banking.open(stand=TAVERLEY_BLUE.bank, log=log)
    if not (_w1):
        return False
    yield from bank.deposit_all_matching(lambda _name, id: id != WT_ITEM.DRAGON_BONES.id, log)
    if any([item.id != WT_ITEM.DRAGON_BONES.id for item in inventory.items()]):
        return False
    bank_pending = False
    return True


def in_dragon_lair(tile):
    return TAVERLEY_BLUE.in_area((tile if tile is not None else None)) or not not tile and tile.level == 0 and tile.x >= 2928 and tile.x <= 2934 and tile.z >= 9683 and tile.z <= 9689


class DragonHost:
    def __init__(self, food, log):
        self.food = food
        self.log = log
        self.weapon = ''
        self.spot = 0
        self.target_idx = None

    @property
    def died(self):
        return skills.effective('hitpoints') <= 0

    def set_status(self, status):
        pass

    def park_for(self, reason):
        self.log(reason)

    def vlog(self, message):
        pass

    def count_bank_trip(self):
        pass

    def style(self):
        return 'melee'

    def food_name(self):
        return self.food

    def food_withdraw(self):
        return FOOD

    def weapon_name(self):
        return self.weapon

    def ammo_name(self):
        return ''

    def spell_name(self):
        return ''

    def keep_extra(self):
        return [WT_ITEM.DRAGON_BONES.name]

    def leave_by_walk(self):
        return True

    def pick_weapon(self, available):
        names = set([name.lower() for name in available])
        options = [item.name for item in wieldable(skills.level('attack'), quest_done) if item.name.lower() in names]
        self.weapon = options[0] if options else ''

    def count_kill(self):
        execution.note_progress()

    def count_burial(self):
        pass

    def hp_fraction(self):
        return skills.effective('hitpoints') / max(1, skills.level('hitpoints'))

    def panic_hp(self):
        return 0.35

    def retreat_hp(self):
        return 0.5

    def has_food(self):
        return inventory.count(self.food) > 0

    def need_eat(self):
        return self.hp_fraction() < 0.65 and self.has_food()

    def eat_once(self):
        item = inventory.first(self.food)
        before = inventory.count(self.food)
        if item is None or not item.interact('Eat'):
            return False
        ate = yield from execution.delay_until(lambda: inventory.count(self.food) < before, 3000)
        return ate

    def shield_ready(self):
        return equipment.contains(SHIELD)

    def bury_bones(self):
        return False

    def bone_name(self):
        return WT_ITEM.DRAGON_BONES.name

    def safespot_index(self):
        return self.spot

    def set_safespot_index(self, index):
        self.spot = index


def dragon_host(food, log):
    return DragonHost(food, log)


def leave_dragon_lair(log):
    host = dragon_host(quest_food.name or 'Lobster', log)
    if event_signal.pending() or host.died:
        return False
    _c9 = in_cell()
    if _c9:
        _w10 = yield from leave_cell(host)
        _c9 = not (_w10)
    if _c9:
        return False
    _result11 = yield from leave_lair(host, TAVERLEY_BLUE)
    return _result11


def hunt_dragon_bones(food, log):
    global bank_pending
    host = dragon_host(food, log)
    if event_signal.pending() or host.died:
        return False
    if bones_held():
        _result12 = yield from leave_dragon_lair(log)
        return _result12
    _c13 = in_cell()
    if _c13:
        _w14 = yield from leave_cell(host)
        _c13 = not (_w14)
    if _c13:
        return False
    bank_pending = True
    try:
        yield from fight_for_bones(host, food, log)
    except Exception:
        yield from finish_hunt(host, log)
        raise
    yield from finish_hunt(host, log)
    return bones_held() and not bank_pending and not in_dragon_lair(game.tile())


def finish_hunt(host, log):
    if event_signal.pending() or host.died:
        return
    left = yield from leave_dragon_lair(log)
    if left:
        yield from refresh_dragon_bank(log)


def fight_for_bones(host, food, log):
    yield from bank_routine(host, TAVERLEY_BLUE, Record({'withdraw_food': True, 'deposit_inventory': True, 'heal_to': 0.9}))
    if event_signal.pending() or host.died:
        return False
    _fn15 = getattr(host, 'shield_ready', None)
    if not (_fn15() if _fn15 is not None else None) or not host.weapon_name() or not equipment.contains(host.weapon_name()):
        log('need a Dragonfire shield and a usable one-handed weapon for the dragon-bone hunt')
        return False
    if inventory.count(food) < FOOD:
        log(f'need {FOOD} {food} for the dragon-bone hunt')
        return False
    _w16 = yield from acquire_key(host, TAVERLEY_BLUE)
    if _w16 != 'held' or event_signal.pending() or host.died:
        return False
    _fn17 = getattr(host, 'shield_ready', None)
    if not (_fn17() if _fn17 is not None else None) or not host.has_food():
        return False
    game.set_auto_retaliate(False)
    if not game.set_combat_style('strength'):
        return False
    _w18 = yield from enter_lair(host, TAVERLEY_BLUE)
    if not (_w18):
        return False
    fight = Fight(host, TAVERLEY_BLUE)
    retreat = Retreat(host, TAVERLEY_BLUE)
    deadline = _core.step_time() + 300000
    pass_ = 0
    _first19 = True
    while True:
        if not _first19:
            pass_ += 1
        _first19 = False
        if not (pass_ < 500 and _core.step_time() < deadline and not bones_held()):
            break
        if event_signal.pending() or host.died:
            return False
        yield from sustain.run()
        if event_signal.pending() or host.died:
            return False
        if retreat.validate():
            yield from retreat.execute()
        _c20 = host.need_eat()
        if _c20:
            _w21 = yield from host.eat_once()
            _c20 = not (_w21)
        if _c20:
            break
        _fn22 = getattr(host, 'shield_ready', None)
        if not (_fn22() if _fn22 is not None else None) or inventory.count(food) < 3 or host.hp_fraction() < host.panic_hp():
            break
        if not fight.blocks_loot():
            drop = ground_items.query().where(lambda item: item.id == WT_ITEM.DRAGON_BONES.id).within(12).nearest()
            if drop:
                _c23 = inventory.is_full()
                if _c23:
                    _w24 = yield from host.eat_once()
                    _c23 = not (_w24)
                if _c23:
                    break
                _c25 = not (drop.interact('Take'))
                if not _c25:
                    _w26 = yield from execution.delay_until(bones_held, 6000)
                    _c25 = not (_w26)
                if _c25:
                    break
                continue
        if fight.validate():
            yield from fight.execute()
        else:
            _w28 = yield from traversal.walk_resilient(TAVERLEY_BLUE.melee_anchor, radius=2, attempts=2, timeout_ms=30000, log=log)
            if not (_w28):
                break
        yield from execution.delay_ticks(1)

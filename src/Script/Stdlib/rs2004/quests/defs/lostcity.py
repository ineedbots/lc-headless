"""Ported from rs2b0t's src/bot/api/ai/quests/defs/lostcity.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.lostcity_combat import defeat_tree_spirit
from rs2004.quests.exec.primitives import NpcStop, talk_through
from rs2004.quests.food import FOOD_FLOAT, quest_food
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.strike import STRIKE_CASTS, prepare_strikes
from rs2004.tabs import quests
from rs2004.traversal import traversal
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['LOST_CITY_STAGE', 'parse_lost_city_journal', 'LOST_CITY_FOOD_TARGET', 'LOST_CITY_STAFF_TARGET', 'LOST_CITY_CAST_TARGET', 'lost_city_area', 'decide', 'lostcity']

LOST_CITY_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'SPOKEN_TO_SHAMUS': 2,
    'SPIRIT_DEFEATED': 3,
    'BRANCH_CUT': 4,
    'STAFF_MADE': 5,
    'COMPLETE': 6,
})


def parse_lost_city_journal(lines):
    text = normalize_journal(lines)
    # Why: later journal entries repeat earlier history, so check the newest first.
    if ('quest complete!' in text):
        return LOST_CITY_STAGE.COMPLETE
    if ('crafted a dramen staff' in text):
        return LOST_CITY_STAGE.STAFF_MADE
    if ('i should craft the branch from the tree into a staff' in text):
        return LOST_CITY_STAGE.BRANCH_CUT
    if ('with the spirit defeated i can cut a branch' in text):
        return LOST_CITY_STAGE.SPIRIT_DEFEATED
    if ('i can find a dramen tree' in text):
        return LOST_CITY_STAGE.SPOKEN_TO_SHAMUS
    if ('apparently there is a leprechaun' in text):
        return LOST_CITY_STAGE.STARTED
    if ('i can start this quest' in text):
        return LOST_CITY_STAGE.NOT_STARTED
    return None


def read_lost_city_stage():
    status = quests.status('Lost City')
    if status == 'complete':
        return LOST_CITY_STAGE.COMPLETE
    if status == 'not_started':
        return LOST_CITY_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    lines = yield from quests.journal('Lost City')
    stage = parse_lost_city_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage


KNIFE = 'Knife'
BRANCH = 'Dramen branch'
STAFF = 'Dramen staff'
LOST_CITY_FOOD_TARGET = FOOD_FLOAT
LOST_CITY_STAFF_TARGET = 5
LOST_CITY_CAST_TARGET = STRIKE_CASTS
STRIKE_RUNES = ['air rune', 'mind rune', 'water rune', 'earth rune', 'fire rune']
AXES = ['Rune axe', 'Adamant axe', 'Mithril axe', 'Black axe', 'Steel axe', 'Iron axe', 'Bronze axe']
DUNGEON_AXES = ['Iron axe', 'Bronze axe']
SHAMUS_TREE_ID = 2409
DRAMEN_TREE_ID = 1292
MAGIC_DOOR_ID = 2407
SHAMUS_ID = 654
ENTRANA_ZOMBIE_ID = 76
DRAYNOR_BANK = Tile(3093, 3243, 0)
KNIFE_SPAWN = Tile(3224, 3202, 0)
BOB_AXES = Record({'npc': 'Bob', 'anchor': Tile(3232, 3203, 0)})
SHAMUS_TREE = Tile(3138, 3212, 0)
PORT_SARIM_MONK = Tile(3046, 3235, 0)
ENTRANA_LANDING = Tile(2834, 3334, 0)
ENTRANA_LADDER = Tile(2820, 3374, 0)
DUNGEON_ARRIVAL = Tile(2822, 9774, 0)
ZOMBIES = Tile(2846, 9761, 0)
DRAMEN_TREE = Tile(2860, 9734, 0)
MAGIC_DOOR_APPROACH = Tile(2873, 9750, 0)
SHED_OUTSIDE = Tile(3201, 3169, 0)
WARRIOR = NpcStop('Warrior', Tile(3145, 3202, 0), 7, [
    'What are you camped here for?',
    "Who's Zanaris?",
    "If it's hidden how are you planning to find it?",
    "Looks like you don't know either.",
])
PORT_MONK = NpcStop('Monk of Entrana', PORT_SARIM_MONK, 8, ["Yes, okay, I'm ready to go."])


def lost_city_area(tile):
    if not tile:
        return 'unknown'
    if tile.x >= 3150 and tile.x <= 3300 and tile.z >= 9450 and tile.z <= 9700:
        return 'zanaris'
    if tile.x >= 2790 and tile.x <= 2900 and tile.z >= 9650 and tile.z <= 9850:
        return 'dungeon'
    if tile.x >= 2790 and tile.x <= 2880 and tile.z >= 3290 and tile.z <= 3440:
        return ('entranaShip' if tile.level > 0 else 'entrana')
    return 'mainland'


def held(snap, name):
    return ((snap.inv.get(name.lower()) if snap.inv.get(name.lower()) is not None else 0)) > 0


def held_count(snap, name):
    return (snap.inv.get(name.lower()) if snap.inv.get(name.lower()) is not None else 0)


def worn(snap, name):
    return (name.lower() in snap.worn)


def banked(snap, name):
    return ((snap.bank.get(name.lower()) if snap.bank is not None else None) if (snap.bank.get(name.lower()) if snap.bank is not None else None) is not None else 0)


def has_axe(snap):
    return any([held(snap, name) or worn(snap, name) for name in AXES])


def worn_axe(snap):
    return any([worn(snap, name) for name in AXES])


def held_axe(snap):
    return ([name for name in AXES if held(snap, name)] or [None])[0]


def bank_axe(snap):
    return ([name for name in AXES if banked(snap, name) > 0] or [None])[0]


def selected_food():
    food = (quest_food.name.strip() if quest_food.name is not None else None)
    return (food if food else None)


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': DRAYNOR_BANK})


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': DRAYNOR_BANK})


def mainland_keep():
    food = (selected_food().lower() if selected_food() is not None else None)
    return list(STRIKE_RUNES) + ['knife'] + list([name.lower() for name in AXES]) + ['dramen branch', 'dramen staff', 'coins'] + list((([food] if food else [])))


def make_acquisition_space(snap, slots):
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    keep = mainland_keep()
    disposable = any([not (name in keep) for name in list(list(snap.inv.keys()))])
    return (Record({'kind': 'deposit', 'keep': keep, 'bank': DRAYNOR_BANK, 'exact_keep': True}) if disposable else Record({
        'kind': 'wait',
        'reason': f"need {slots} free inventory slot{('' if slots == 1 else 's')} for Lost City items",
    }))


def source_knife(snap):
    if held(snap, KNIFE):
        return None
    space = make_acquisition_space(snap, 1)
    if space:
        return space
    if not snap.bank_known:
        return scan_bank()
    if banked(snap, KNIFE) > 0:
        return withdraw([{'name': KNIFE, 'qty': 1}])
    return Record({'kind': 'grab_ground', 'item': KNIFE, 'anchor': KNIFE_SPAWN, 'wait_if_missing': True})


def source_mainland_axe(snap):
    if has_axe(snap):
        return None
    space = make_acquisition_space(snap, 1)
    if space:
        return space
    if not snap.bank_known:
        return scan_bank()
    axe = bank_axe(snap)
    if axe:
        return withdraw([{'name': axe, 'qty': 1}])
    _v3 = snap.inv.get('coins')
    if ((_v3 if _v3 is not None else 0)) < 100:
        if banked(snap, 'Coins') > 0:
            return withdraw([{'name': 'Coins', 'qty': min(1000, banked(snap, 'Coins'))}])
        return Record({'kind': 'wait', 'reason': 'need coins for an axe from Bob'})
    return Record({'kind': 'buy', 'item': 'Bronze axe', 'qty': 1, 'shop': BOB_AXES, 'est_gp': 100})


def entrana_keep():
    food = (selected_food().lower() if selected_food() is not None else None)
    return list(STRIKE_RUNES) + ['knife', 'coins'] + list((([food] if food else [])))


def has_entrana_spillover(snap):
    keep = entrana_keep()
    return any([not (name in keep) for name in list(list(snap.inv.keys()))])


def unequip_all(_log):
    for item in equipment.items():
        _c4 = item.name
        if _c4:
            _w5 = yield from equipment.unequip(item.name)
            _c4 = not (_w5)
        if _c4:
            return False
    return len(equipment.items()) == 0


def source_combat_food(snap):
    food = selected_food()
    if not food:
        return Record({'kind': 'wait', 'reason': 'select a food item for the Lost City fights'})
    missing = LOST_CITY_FOOD_TARGET - held_count(snap, food)
    if missing <= 0:
        return None
    if not snap.bank_known:
        return scan_bank()
    in_bank = banked(snap, food)
    if in_bank < missing:
        return Record({
            'kind': 'wait',
            'reason': f'need {missing} more {food} in the bank ({LOST_CITY_FOOD_TARGET} combat food total)',
        })
    space = make_acquisition_space(snap, missing)
    if space:
        return space
    return withdraw([{'name': food, 'qty': missing}])


def restore_with_selected_food(target):
    """Top up toward `target` HP fraction before a fight. Keep it under 1.0; the old 0.9 burned food on tiny heals (#393)."""
    for i in range(LOST_CITY_FOOD_TARGET):
        if not (skills.hp_fraction() < target):
            break
        before_hp = skills.effective('hitpoints')
        yield from sustain.run()
        if skills.effective('hitpoints') <= before_hp:
            return


def wait_out_combat(timeout_ms):
    deadline = _core.step_time() + timeout_ms
    while game.in_combat() and _core.step_time() < deadline:
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    return not game.in_combat()


def reveal_and_talk_shamus(log):
    shamus = npcs.query().where(lambda n: n.id == SHAMUS_ID).within(30).nearest()
    if not shamus:
        _w6 = yield from traversal.walk_resilient(SHAMUS_TREE, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w6):
            return False
        tree = locs.query().where(lambda l: l.id == SHAMUS_TREE_ID).action('Chop').within(8).nearest()
        if not tree:
            log('no Lost City tree to Chop at the adventurer camp')
            return False
        if not (tree.interact('Chop')):
            return False
        yield from execution.delay_until(lambda: npcs.query().where(lambda n: n.id == SHAMUS_ID).within(30).nearest() is not None, 8000)
        shamus = npcs.query().where(lambda n: n.id == SHAMUS_ID).within(30).nearest()
    if not shamus:
        return False
    _result7 = yield from talk_through('Shamus', ['How does it fit in a shed then?'], log)
    return _result7


def disembark_entrana(log):
    plank = locs.query().name('Gangplank').action('Cross').within(10).nearest()
    if not plank:
        log('no Entrana Gangplank to Cross from the ship')
        return False
    if not (plank.interact('Cross')):
        return False

    def _fn9():
        tile = game.tile()
        return tile is not None and tile.level == 0 and ENTRANA_LANDING.distance_to(tile) <= 8
    _result8 = yield from execution.delay_until(_fn9, 10000)
    return _result8


def descend_entrana(log):
    _w10 = yield from traversal.walk_resilient(ENTRANA_LADDER, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w10):
        return False
    _w11 = yield from talk_through('Cave monk', ['Well that is a risk I will have to take.'], log)
    if not (_w11):
        return False

    def _fn13():
        tile = game.tile()
        return tile is not None and DUNGEON_ARRIVAL.distance_to(tile) <= 8
    _result12 = yield from execution.delay_until(_fn13, 12000)
    return _result12


def live_has_dungeon_axe():
    return any([inventory.contains(name) or equipment.contains(name) for name in DUNGEON_AXES])


def take_dungeon_axe():
    if inventory.is_full():
        keep = mainland_keep()
        junk = ([item for item in inventory.items() if item.name is not None and not (item.name.lower() in keep) and any([op.lower() == 'drop' for op in item.actions()])] or [None])[0]
        if junk:
            junk.interact('Drop')
            yield from execution.delay_until(lambda: not inventory.is_full(), 3000)
    drop = ground_items.query().name(*DUNGEON_AXES).within(20).nearest()
    if not drop:
        return False
    if not (drop.interact('Take')):
        return False
    _result14 = yield from execution.delay_until(live_has_dungeon_axe, 8000)
    return _result14


def acquire_dungeon_axe(log):
    _c15 = live_has_dungeon_axe()
    if not _c15:
        _w16 = yield from take_dungeon_axe()
        _c15 = (_w16)
    if _c15:
        return True
    if game.in_combat():
        yield from wait_out_combat(120000)
        _result17 = yield from take_dungeon_axe()
        return _result17
    _w18 = yield from traversal.walk_resilient(ZOMBIES, radius=7, attempts=3, timeout_ms=90000, log=log)
    if not (_w18):
        return False
    _w19 = yield from take_dungeon_axe()
    if _w19:
        return True
    zombie = npcs.query().where(lambda n: n.id == ENTRANA_ZOMBIE_ID and not n.in_combat and not n.targets_another_player()).action('Attack').within(15).nearest()
    if not zombie:
        log('waiting for an available Entrana Zombie')
        yield from execution.delay_ticks(2)
        return False
    yield from restore_with_selected_food(0.7)
    if not (zombie.interact('Attack')):
        return False
    yield from execution.delay_until(lambda: game.in_combat() or not zombie.valid(), 5000)
    yield from wait_out_combat(120000)
    _result20 = yield from take_dungeon_axe()
    return _result20


def chop_branch(log):
    if inventory.is_full():
        keep = mainland_keep()
        junk = ([item for item in inventory.items() if item.name is not None and not (item.name.lower() in keep) and any([op.lower() == 'drop' for op in item.actions()])] or [None])[0]
        food = (selected_food().lower() if selected_food() is not None else None)
        item = (junk if junk is not None else ((([item for item in inventory.items() if (item.name.lower() if item.name is not None else None) == food and any([op.lower() == 'eat' for op in item.actions()])] or [None])[0] if food else None)))
        if not item or not (item.interact(('Drop' if junk else 'Eat'))):
            log('inventory is full and has no disposable item or food for the Dramen branch')
            return False
        _w21 = yield from execution.delay_until(lambda: not inventory.is_full(), 3000)
        if not (_w21):
            return False
    _w22 = yield from traversal.walk_resilient(DRAMEN_TREE, radius=3, attempts=3, timeout_ms=120000, log=log)
    if not (_w22):
        return False
    before = inventory.count(BRANCH)
    tree = locs.query().where(lambda l: l.id == DRAMEN_TREE_ID).action('Chop down').within(8).nearest()
    if not tree:
        log('no Dramen tree to cut a branch from')
        return False
    if not (tree.interact('Chop down')):
        return False
    _result23 = yield from execution.delay_until(lambda: inventory.count(BRANCH) > before, 10000)
    return _result23


def leave_dungeon(log):
    if game.in_combat():
        yield from execution.delay_until(lambda: not game.in_combat(), 120000)
        return False
    # Walk to the tile west of the portal then interact; targeting the portal tile makes the navigator treat its one-way teleport as a door edge.
    _w24 = yield from traversal.walk_resilient(MAGIC_DOOR_APPROACH, radius=0, attempts=3, timeout_ms=120000, log=log)
    if not (_w24):
        return False
    door = locs.query().where(lambda l: l.id == MAGIC_DOOR_ID).action('Open').within(3).nearest()
    if not door:
        log('no Magic door to leave the Entrana dungeon')
        return False
    if not (door.interact('Open')):
        return False

    def _fn26():
        tile = game.tile()
        return tile is not None and lost_city_area(tile) != 'dungeon'
    _result25 = yield from execution.delay_until(_fn26, 12000)
    return _result25


def enter_zanaris(log):
    _w27 = yield from traversal.walk_resilient(SHED_OUTSIDE, radius=1, attempts=4, timeout_ms=300000, log=log)
    if not (_w27):
        return False
    door = locs.query().where(lambda l: l.id == 2406).action('Open').within(5).nearest()
    if not door:
        log('no Lost City shed Door to Open')
        return False
    if not (door.interact('Open')):
        return False
    _result28 = yield from execution.delay_until(lambda: lost_city_area(game.tile()) == 'zanaris', 15000)
    return _result28


def sail_to_entrana(log):
    _w29 = yield from traversal.walk_resilient(PORT_SARIM_MONK, radius=3, attempts=3, timeout_ms=120000, log=log)
    if not (_w29):
        return False
    _w30 = yield from talk_through(PORT_MONK.npc, PORT_MONK.prefer, log)
    if not (_w30):
        return False

    def _fn32():
        tile = game.tile()
        return tile is not None and tile.x >= 2790 and tile.x <= 2880 and tile.z >= 3290 and tile.z <= 3440
    _result31 = yield from execution.delay_until(_fn32, 30000)
    return _result31


def mainland_tools(snap):
    _v33 = source_knife(snap)
    return (_v33 if _v33 is not None else source_mainland_axe(snap))


def source_strike_runes(snap):
    return prepare_strikes(snap, entrana_keep())


def travel_to_dungeon(snap):
    area = lost_city_area(snap.tile)
    if area == 'entranaShip':
        return Record({'kind': 'custom', 'name': 'disembark on Entrana', 'run': disembark_entrana})
    if area == 'entrana':
        return Record({'kind': 'custom', 'name': 'descend the one-way Entrana ladder', 'run': descend_entrana})
    if area == 'mainland':
        knife = source_knife(snap)
        if knife:
            return knife
        if has_entrana_spillover(snap):
            return Record({'kind': 'deposit', 'keep': entrana_keep(), 'bank': DRAYNOR_BANK, 'exact_keep': True})
        if len(snap.worn) > 0:
            return Record({'kind': 'custom', 'name': 'remove Entrana-restricted equipment', 'run': unequip_all})
        food = source_combat_food(snap)
        if food:
            return food
        if snap.stage == LOST_CITY_STAGE.SPOKEN_TO_SHAMUS:
            runes = source_strike_runes(snap)
            if runes:
                return runes
        return Record({'kind': 'custom', 'name': 'sail from Port Sarim to Entrana', 'run': sail_to_entrana})
    return Record({'kind': 'wait', 'reason': 'locating the Entrana route'})


def dungeon_work(snap, stage):
    if not has_axe(snap):
        return Record({'kind': 'custom', 'name': 'get an axe from Entrana Zombies', 'run': acquire_dungeon_axe})
    if not worn_axe(snap):
        return Record({'kind': 'equip', 'item': held_axe(snap)})
    if stage == LOST_CITY_STAGE.SPOKEN_TO_SHAMUS:
        def _fn36(log):
            def _fn37():
                _w38 = yield from read_lost_city_stage()
                return ((_w38 if _w38 is not None else 0)) >= LOST_CITY_STAGE.SPIRIT_DEFEATED
            return defeat_tree_spirit(log, _fn37)
        return Record({'kind': 'custom', 'name': 'defeat the Tree Spirit', 'run': _fn36})
    return Record({'kind': 'custom', 'name': 'cut a Dramen branch', 'run': chop_branch})


def local_staff_count(snap):
    return held_count(snap, STAFF) + ((1 if worn(snap, STAFF) else 0))


def local_staff_materials(snap):
    return local_staff_count(snap) + held_count(snap, BRANCH)


def known_staff_materials(snap):
    return local_staff_materials(snap) + banked(snap, STAFF) + banked(snap, BRANCH)


def craft_held_branch(snap, area):
    knife = source_knife(snap)
    if knife:
        return (Record({'kind': 'custom', 'name': 'leave the dungeon to replace the Knife', 'run': leave_dungeon}) if area == 'dungeon' else knife)
    return Record({
        'kind': 'use_on',
        'item': KNIFE,
        'target_kind': 'item',
        'target': BRANCH,
        'anchor': DRAMEN_TREE,
        'product': STAFF,
    })


def banked_staff_materials_to_withdraw(snap):
    missing = LOST_CITY_STAFF_TARGET - local_staff_materials(snap)
    if missing <= 0:
        return []
    staffs = min(missing, banked(snap, STAFF))
    missing -= staffs
    branches = min(missing, banked(snap, BRANCH))
    missing -= branches
    if missing > 0:
        return None
    return list((([{'name': STAFF, 'qty': staffs}] if staffs > 0 else []))) + list((([{'name': BRANCH, 'qty': branches}] if branches > 0 else [])))


def finish_five_staves(snap, stage, area):
    if area == 'zanaris':
        return Record({'kind': 'wait', 'reason': 'waiting for Lost City completion'})
    if area == 'dungeon':
        if known_staff_materials(snap) < LOST_CITY_STAFF_TARGET:
            return dungeon_work(snap, stage)
        if held(snap, BRANCH):
            return craft_held_branch(snap, area)
        return Record({'kind': 'custom', 'name': 'exit through the Wilderness portal', 'run': leave_dungeon})
    if area != 'mainland':
        return travel_to_dungeon(snap)
    # A normal run leaves the dungeon with all 5 local, so skip the bank detour that would only confirm nothing is needed.
    if local_staff_materials(snap) >= LOST_CITY_STAFF_TARGET:
        if held(snap, BRANCH):
            return craft_held_branch(snap, area)
        if not worn(snap, STAFF):
            return Record({'kind': 'equip', 'item': STAFF})
        return Record({'kind': 'custom', 'name': 'enter Zanaris through the swamp shed', 'run': enter_zanaris})
    if not snap.bank_known:
        return scan_bank()
    if known_staff_materials(snap) < LOST_CITY_STAFF_TARGET:
        return travel_to_dungeon(snap)
    if held(snap, BRANCH):
        return craft_held_branch(snap, area)
    materials = banked_staff_materials_to_withdraw(snap)
    if materials and len(materials) > 0:
        if any([item['name'] == BRANCH for item in materials]) and not held(snap, KNIFE):
            knife = source_knife(snap)
            if knife:
                return knife
        slots = sum([item['qty'] for item in materials])
        space = make_acquisition_space(snap, slots)
        if space:
            return space
        return withdraw(materials)
    if local_staff_count(snap) < LOST_CITY_STAFF_TARGET:
        return Record({'kind': 'wait', 'reason': f'recovering {LOST_CITY_STAFF_TARGET} Dramen staves'})
    if not worn(snap, STAFF):
        return Record({'kind': 'equip', 'item': STAFF})
    return Record({'kind': 'custom', 'name': 'enter Zanaris through the swamp shed', 'run': enter_zanaris})


def decide(snap):
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else 0)) >= LOST_CITY_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Lost City journal stage unavailable'})
    area = lost_city_area(snap.tile)
    if stage == LOST_CITY_STAGE.NOT_STARTED:
        tool = mainland_tools(snap)
        return (tool if tool is not None else Record({'kind': 'talk', 'stop': WARRIOR}))
    if stage == LOST_CITY_STAGE.STARTED:
        tool = mainland_tools(snap)
        return (tool if tool is not None else Record({'kind': 'custom', 'name': 'reveal Shamus and learn about the staff', 'run': reveal_and_talk_shamus}))
    if stage == LOST_CITY_STAGE.SPOKEN_TO_SHAMUS or stage == LOST_CITY_STAGE.SPIRIT_DEFEATED:
        if area == 'dungeon':
            return dungeon_work(snap, stage)
        return travel_to_dungeon(snap)
    if stage == LOST_CITY_STAGE.BRANCH_CUT or stage == LOST_CITY_STAGE.STAFF_MADE:
        return finish_five_staves(snap, stage, area)
    return Record({'kind': 'wait', 'reason': f'unrecognized Lost City stage {stage}'})


lostcity = QuestModule(**{
    'record': quest_record('zanaris'),
    'bank': DRAYNOR_BANK,
    'grind': ['Zombie', 'Tree spirit'],
    'tools': ['knife', 'axe', 'dramen branch', 'dramen staff'],
    'owns_inventory': True,
    'sustain': Record({'foods': [], 'eat_below_hp': 0.5}),
    'read_stage': read_lost_city_stage,
    'decide': decide,
})

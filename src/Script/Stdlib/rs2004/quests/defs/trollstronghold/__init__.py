"""Ported from rs2b0t's src/bot/api/ai/quests/defs/trollstronghold/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.loadout import gear_of, weapon_of
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.trollstronghold.areas import BOOT_COST, COIN_FLOAT, COMBAT_FOODS, DENULTH_START, DUNSTAN_FINISH, FALADOR_WEST_BANK, FOOD_FLOOR, FOOD_TARGET, ITEM, PRAYER_POTIONS, PRAYER_POTION_TARGET, TENZING_BOOTS, TENZING_DONE_RULES, TILE, committed, troll_zone
from rs2004.quests.defs.trollstronghold.combat import attackable, fight, protected_walk
from rs2004.quests.defs.trollstronghold.journal import TROLL_FLAG, TROLL_QUEST, TROLL_STAGE, parse_troll_stronghold_journal, read_troll_stronghold_progress
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import talk_choosing_by
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['parse_troll_stronghold_journal', 'read_troll_stronghold_progress', 'TROLL_FLAG', 'TROLL_QUEST', 'TROLL_STAGE', 'troll_zone', 'committed', 'ITEM', 'COMBAT_FOODS', 'FOOD_TARGET', 'FALADOR_WEST_BANK', 'planned_gear', 'wear_all', 'prepare', 'steal_cell_key', 'unlock_cell', 'decide', 'trollstronghold']


# Snapshot helpers
def held_count(snap, name):
    count = snap.inv.get(name.lower())
    return count if count is not None else 0


def held(snap, name):
    return held_count(snap, name) > 0


def worn(snap, name):
    return (name.lower() in snap.worn)


def banked(snap, name):
    count = snap.bank.get(name.lower()) if snap.bank is not None else None
    return count if count is not None else 0


def food_names():
    configured = (quest_food.name.strip() if quest_food.name is not None else None)
    names = [n for n in [configured] + list(COMBAT_FOODS) if bool(n)]
    by_lower = {}
    for n in names:
        by_lower[n.lower()] = n
    return list(by_lower.values())


def food_held(snap):
    return sum([held_count(snap, name) for name in food_names()])


# Loadout
unwearable = set()
TIERS = ['rune', 'adamant', 'mithril', 'black', 'steel', 'iron', 'bronze']
GEAR_SLOTS = [
    Record({'slot': 'weapon', 'kinds': ['2h sword', 'longsword', 'scimitar', 'battleaxe', 'warhammer', 'mace', 'sword']}),
    Record({'slot': 'body', 'kinds': ['platebody', 'chainbody']}),
    Record({'slot': 'legs', 'kinds': ['platelegs', 'plateskirt']}),
    Record({'slot': 'helm', 'kinds': ['full helm', 'med helm']}),
    Record({'slot': 'shield', 'kinds': ['kiteshield', 'sq shield']}),
]


def best_in_bank(snap, kinds):
    for tier in TIERS:
        for kind in kinds:
            name = f'{tier} {kind}'
            if (name in unwearable):
                continue
            if banked(snap, name) > 0 or held(snap, name):
                # Display casing: every log line and step label carries this name.
                return name[0].upper() + name[1:]
    return None


def wearing_slot(snap, kinds):
    for name in snap.worn:
        if any([name.endswith(kind) for kind in kinds]):
            return True
    return False


def scavenged_gear(snap):
    """What ran before loadouts existed."""
    out = []
    for _item1 in GEAR_SLOTS:
        slot = _item1.slot
        kinds = _item1.kinds
        if wearing_slot(snap, kinds) or (slot == 'shield' and any([n.endswith('2h sword') for n in out])):
            continue
        pick = best_in_bank(snap, kinds)
        if pick:
            out.append(pick)
    return out


def planned_gear(snap):
    """A declared loadout is taken literally; declaring nothing falls back to scavenging."""
    declared = gear_of(quest_loadout.current)
    names = (declared if len(declared) > 0 else scavenged_gear(snap))
    return [name for name in names if not (name.lower() in unwearable) and not worn(snap, name)]


def potions_held(snap):
    return sum([held_count(snap, name) for name in PRAYER_POTIONS])


def keep_set(snap):
    return [n.lower() for n in list(PRAYER_POTIONS) + [ITEM.COINS, ITEM.CLIMBING_BOOTS, ITEM.PRISON_KEY, ITEM.CELL_KEY_1, ITEM.CELL_KEY_2] + list(food_names()) + list(planned_gear(snap))]


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': FALADOR_WEST_BANK})


def wear_all(names):
    """The kit in one step; a step per piece pays a task hand-off each, and `equip` already waits for the item to land. Refusals are shed."""

    def _fn2(log):
        for name in names:
            _c3 = equipment.contains(name)
            if not _c3:
                _w4 = yield from equipment.equip(name)
                _c3 = (_w4)
            if _c3:
                continue
            log(f'cannot wear {name} — level or quest requirement; banking it and moving on')
            unwearable.add(name.lower())
        return True
    return Record({'kind': 'custom', 'name': f"wear {', '.join(names)}", 'run': _fn2})


def wear_or_shed(name):
    return wear_all([name])


# Why: the boots are required, so a refusal is a dead end.
# Why: `opheld2,death_climbingboots` only lets them on once Death Plateau is complete, so the step says so and parks.
def wear_boots():
    """Wear the climbing boots."""
    if (ITEM.CLIMBING_BOOTS.lower() in unwearable):
        return Record({
            'kind': 'wait',
            'reason': 'the server will not let these Climbing boots on — Death Plateau is not actually complete',
        })
    return wear_or_shed(ITEM.CLIMBING_BOOTS)


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': FALADOR_WEST_BANK})


# Why: this runs on every decide() tick while you're still on the mainland, so each branch has to be idempotent.
# Why: a step that does not change the snapshot spins here forever.
def prepare(snap, zone='mainland'):
    """The loadout, in one pure pass; null when the pack is ready."""
    boots_ready = held(snap, ITEM.CLIMBING_BOOTS) or worn(snap, ITEM.CLIMBING_BOOTS)
    # Past the stile a bank trip means climbing back down the secret way; only a spent pack or missing boots is worth that.
    if committed(zone) and boots_ready and food_held(snap) >= FOOD_FLOOR:
        if not worn(snap, ITEM.CLIMBING_BOOTS):
            return wear_boots()
        # Only the bank is out of reach up here.
        carried = [name for name in planned_gear(snap) if held(snap, name)]
        if len(carried) > 0:
            return wear_all(carried)
        return None
    if not snap.bank_known:
        return scan_bank()
    keep = keep_set(snap)
    if any([not (name in keep) for name in list(list(snap.inv.keys()))]):
        return Record({'kind': 'deposit', 'keep': keep, 'bank': FALADOR_WEST_BANK, 'exact_keep': True})
    # One visit: Tenzing is 40 tiles west and the bank is east.
    from_bank = []
    # One purchase, a standing float would mean a bank trip for 12gp of change.
    needs_boot_money = not boots_ready and banked(snap, ITEM.CLIMBING_BOOTS) == 0
    if needs_boot_money and held_count(snap, ITEM.COINS) < COIN_FLOAT and banked(snap, ITEM.COINS) > 0:
        from_bank.append({'name': ITEM.COINS, 'qty': min(COIN_FLOAT - held_count(snap, ITEM.COINS), banked(snap, ITEM.COINS))})
    if not boots_ready and banked(snap, ITEM.CLIMBING_BOOTS) > 0:
        from_bank.append({'name': ITEM.CLIMBING_BOOTS, 'qty': 1})
    # A loadout names what you want; the bank may not have it.
    missing = []
    for name in planned_gear(snap):
        if held(snap, name):
            continue
        if banked(snap, name) > 0:
            from_bank.append({'name': name, 'qty': 1})
        else:
            missing.append(name)
    # Optional. The quest is winnable on food alone.
    want_potions = PRAYER_POTION_TARGET - potions_held(snap)
    for name in PRAYER_POTIONS:
        if want_potions <= 0:
            break
        available = banked(snap, name)
        if available > 0:
            take = min(want_potions, available)
            from_bank.append({'name': name, 'qty': take})
            want_potions -= take
    have = food_held(snap)
    if have < FOOD_TARGET:
        for name in food_names():
            available = banked(snap, name)
            if available > 0:
                from_bank.append({'name': name, 'qty': min(FOOD_TARGET - have, available)})
                break
    if len(from_bank) > 0:
        return withdraw(from_bank)
    # Wear it here; the detour to Tenzing is 40 tiles of carrying it.
    to_wear = [name for name in planned_gear(snap) if held(snap, name)]
    if len(to_wear) > 0:
        return wear_all(to_wear)
    if not boots_ready:
        if held_count(snap, ITEM.COINS) < BOOT_COST:
            return Record({'kind': 'wait', 'reason': f'need {BOOT_COST} gp for Climbing boots — bank has none'})
        return Record({'kind': 'custom', 'name': 'buy Climbing boots from Tenzing (12gp)', 'run': buy_boots})
    if not worn(snap, ITEM.CLIMBING_BOOTS):
        return wear_boots()
    if food_held(snap) == 0:
        return Record({'kind': 'wait', 'reason': f"no combat food in the bank (tried {', '.join(food_names())})"})
    # Missing armour is survivable; a missing weapon is not worth walking up for.
    weapon = weapon_of(quest_loadout.current)
    if weapon is not None and any([name.lower() == weapon.lower() for name in missing]):
        return Record({'kind': 'wait', 'reason': f'loadout weapon \'{weapon}\' is not in the bank'})
    if not wearing_slot(snap, GEAR_SLOTS[0].kinds):
        return Record({'kind': 'wait', 'reason': 'no melee weapon — put one in your loadout, or bank one'})
    return None


# Custom steps
WALK = Record({'radius': 4, 'attempts': 4, 'timeout_ms': 300000})


def walk_to(tile, radius, log):
    here = game.tile()
    if here and here.level == tile.level and tile.distance_to(here) <= radius:
        return True
    _result5 = yield from traversal.walk_resilient(tile, radius=radius, attempts=WALK.attempts, timeout_ms=WALK.timeout_ms, log=log)
    return _result5


CAVE_MOUTH = Tile(2908, 3654, 0)
THROWER_RANGE = 11


# Why: 5 thrower trolls between the cave exit and the stronghold door open on sight at 8 tiles, and a walk never fights back, so the crossing is pure damage Protect from Missiles blocks outright.
# Why: prayer drains per tick, and held from Falador it empties the bar before the level-113 general is in sight.
# Why: the crossing is its own leg with the prayer following the throwers: up while one is in range, down once the last is behind us, about 40 tiles before the door.
def walk_to_stronghold(tile, radius, log):
    """Walk to the stronghold under a threat-tracking protection prayer."""
    zone = troll_zone(game.tile())
    if zone == 'stronghold':
        _result7 = yield from walk_to(tile, radius, log)
        return _result7
    _c8 = zone != 'mountain'
    if _c8:
        _w9 = yield from walk_to(CAVE_MOUTH, 3, log)
        _c8 = not (_w9)
    if _c8:
        return False

    def thrower_near():
        return npcs.query().name('Thrower Troll').within(THROWER_RANGE).nearest() is not None

    _result10 = yield from protected_walk('missiles', thrower_near, lambda: walk_to(tile, radius, log), log)
    return _result10


def buy_boots(log):
    if inventory.contains(ITEM.CLIMBING_BOOTS) or equipment.contains(ITEM.CLIMBING_BOOTS):
        return True
    if inventory.count(ITEM.COINS) < BOOT_COST:
        log(f'need {BOOT_COST} coins for Climbing boots')
        return False
    # Radius 1: Tenzing is inside his hut, and any wider radius is satisfied on the doorstep with the shut door in the way.
    _w11 = yield from walk_to(TILE.TENZING, 1, log)
    if not (_w11):
        return False
    before = inventory.count(ITEM.CLIMBING_BOOTS)
    # Why: judge by the boots; Tenzing's shop loop often leaves an objbox up, so `talkChoosingBy` reports failure for a talk that already handed them over and the retry walks the leg twice.
    yield from talk_choosing_by(TENZING_BOOTS.npc, TENZING_DONE_RULES, TENZING_BOOTS.prefer, log)
    _result12 = yield from execution.delay_until(lambda: inventory.count(ITEM.CLIMBING_BOOTS) > before, 8000)
    return _result12


# Why: below 20 hitpoints `defeat_dad` fires, setting the quest stage, healing Dad to full and offering a forfeit dialogue.
# Why: draining that dialogue is the win condition; leaving it up loses the win.
def fight_dad(log):
    """Fight Dad to his forfeit and drain the dialogue."""
    _w13 = yield from walk_to(TILE.DAD, 6, log)
    if not (_w13):
        return False
    # Why: the callbacks below record what they see here; pocketpy closures can't rebind the function's locals.
    state = {'forfeited': False, 'seen': False}

    def find():
        npc = attackable('Dad', 20)
        if npc:
            state['seen'] = True
        return npc

    def _fn15():
        log('Dad is not in the arena — poking the Arena Exit to bring him back')
        _w16 = yield from walk_to(Tile(2916, 3628, 0), 1, log)
        if not (_w16):
            return False
        exit = locs.query().name('Arena Exit').action('Open').within(6).nearest()
        if exit:
            exit.interact('Open')
            yield from execution.delay_ticks(3)
        return True

    def _fn17(pick):
        state['forfeited'] = True
    _result14 = yield from fight(Record({
        'what': 'Dad',
        'target': find,
        'on_missing': _fn15,
        'won': lambda: state['forfeited'] or (state['seen'] and attackable('Dad', 24) is None and not game.in_combat()),
        'on_dialogue': _fn17,
        'dialogue': ["I'll be going now."],
        'protect': 'melee',
        'guard': 600,
    }), log)
    return _result14


def take_ground(name, log):
    if inventory.contains(name):
        return True
    drop = ground_items.query().name(name).within(12).nearest()
    if not drop:
        return False
    log(f'taking {name}')
    if not (drop.interact('Take')):
        return False
    _result18 = yield from execution.delay_until(lambda: inventory.contains(name), 8000)
    return _result18


def hunt_general(log):
    _c19 = inventory.contains(ITEM.PRISON_KEY)
    if not _c19:
        _w20 = yield from take_ground(ITEM.PRISON_KEY, log)
        _c19 = (_w20)
    if _c19:
        return True
    _w21 = yield from walk_to_stronghold(TILE.GENERAL, 5, log)
    if not (_w21):
        return False

    def key_is_ours():
        return inventory.contains(ITEM.PRISON_KEY) or ground_items.query().name(ITEM.PRISON_KEY).within(12).nearest() is not None

    def _fn22():
        _result23 = yield from walk_to_stronghold(TILE.GENERAL, 5, log)
        return _result23
    ok = yield from fight(Record({
        'what': 'Troll General',
        'target': lambda: attackable('Troll General', 12),
        'won': key_is_ours,
        'on_missing': _fn22,
        'protect': 'melee',
        'guard': 900,
    }), log)
    if not ok:
        return False
    _result24 = yield from take_ground(ITEM.PRISON_KEY, log)
    return _result24


def enter_prison(log):
    """The prison door is a baked crossing: walking to the cells unlocks it."""
    _result25 = yield from walk_to_stronghold(TILE.PRISON_LANDING, 3, log)
    return _result25


# Why: cell keys sit on the belts of 2 sleeping guards, and pickpocketing is the quiet way.
# Why: a failed steal wakes the guard and killing the woken guard drops the same key, so neither outcome is a dead end.
def steal_cell_key(guard, key, stand, log):
    """Take a cell key off a sleeping guard."""
    for attempt in range(25):
        _c26 = inventory.contains(key)
        if not _c26:
            _w27 = yield from take_ground(key, log)
            _c26 = (_w27)
        if _c26:
            return True
        _w28 = yield from walk_to(stand, 2, log)
        if not (_w28):
            return False
        sleeping = npcs.query().name(guard).action('Pickpocket').within(6).nearest()
        if sleeping and skills.effective('thieving') >= 30:
            before = inventory.count(key)
            if sleeping.interact('Pickpocket'):
                _w29 = yield from execution.delay_until(lambda: inventory.count(key) > before, 5000)
                if _w29:
                    log(f'pickpocketed {guard} for {key}')
                    return True
            yield from execution.delay_ticks(2)
            continue
        # Awake (or Thieving too low): put it down and take the key off the floor.
        woken = attackable(guard, 8)
        if not woken:
            yield from execution.delay_ticks(2)
            continue
        yield from fight(Record({
            'what': guard,
            'target': lambda: attackable(guard, 8),
            'won': lambda: inventory.contains(key) or ground_items.query().name(key).within(8).nearest() is not None,
            'protect': 'melee',
            'guard': 400,
        }), log)
    log(f'could not get {key} from {guard}')
    return False


def unlock_cell(key, door, stand, log):
    _w30 = yield from walk_to(stand, 1, log)
    if not (_w30):
        return False
    cell = locs.query().name('Cell Door').action('Unlock').where(lambda l: l.tile().x == door.x and l.tile().z == door.z).nearest()
    if not cell:
        log(f'no Cell Door to Unlock at ({door.x},{door.z})')
        return False
    before = inventory.count(key)
    if not (cell.interact('Unlock')):
        return False
    _result31 = yield from execution.delay_until(lambda: inventory.count(key) < before, 8000)
    return _result31


GODRIC_DOOR = Tile(2832, 10078, 0)
EADGAR_DOOR = Tile(2832, 10082, 0)


# Why: freeing Godric advances the stage and `decide()` then walks out to Dunstan, so anything optional happens first.
# Why: Eadgar is optional here and required for Eadgar's Ruse, which is worth one pickpocket while standing here.
def free_prisoners(freed_eadgar, log):
    """Free both prisoners, Eadgar before Godric."""
    _w32 = yield from walk_to_stronghold(TILE.PRISON_LANDING, 4, log)
    if not (_w32):
        return False
    if not freed_eadgar:
        _w33 = yield from steal_cell_key('Berry', ITEM.CELL_KEY_2, TILE.EADGAR_CELL, log)
        if _w33:
            _w34 = yield from unlock_cell(ITEM.CELL_KEY_2, EADGAR_DOOR, TILE.EADGAR_CELL, log)
            if not (_w34):
                log("could not open Mad Eadgar's cell — carrying on to Godric")
        else:
            log('could not free Mad Eadgar — carrying on to Godric')
    _w35 = yield from steal_cell_key('Twig', ITEM.CELL_KEY_1, TILE.GODRIC_CELL, log)
    if not (_w35):
        return False
    _result36 = yield from unlock_cell(ITEM.CELL_KEY_1, GODRIC_DOOR, TILE.GODRIC_CELL, log)
    return _result36


# decide
def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def decide(snap):
    _v37 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v37 if _v37 is not None else snap.stage)
    if snap.journal == 'complete' or ((stage if stage is not None else 0)) >= TROLL_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Troll Stronghold journal stage unavailable'})
    if stage == TROLL_STAGE.NOT_STARTED and quests.status('Death Plateau') != 'complete':
        return Record({'kind': 'wait', 'reason': 'Death Plateau must be complete before Troll Stronghold'})
    zone = troll_zone(snap.tile)
    if stage == TROLL_STAGE.NOT_STARTED:
        _v38 = prepare(snap)
        return (_v38 if _v38 is not None else Record({'kind': 'talk', 'stop': DENULTH_START}))
    if stage == TROLL_STAGE.STARTED:
        _v39 = prepare(snap, zone)
        return (_v39 if _v39 is not None else custom('defeat Dad in the troll arena', fight_dad))
    if stage == TROLL_STAGE.DEFEATED_DAD:
        prep = prepare(snap, zone)
        if prep:
            return prep
        return (custom('unlock the troll prison', enter_prison) if held(snap, ITEM.PRISON_KEY) else custom('kill a Troll General for the Prison key', hunt_general))
    if stage == TROLL_STAGE.ENTERED_PRISON:
        # A resume can land here from anywhere, a death sends you to Lumbridge, and the prison needs the boots on.
        prep = prepare(snap, zone)
        if prep:
            return prep
        freed_eadgar = has_flag(snap.progress, TROLL_FLAG.FREED_EADGAR)
        return custom(('free Godric from his cell' if freed_eadgar else 'free Mad Eadgar and Godric from their cells'), lambda log: free_prisoners(freed_eadgar, log))
    if stage == TROLL_STAGE.FREED_GODRIC:
        return Record({'kind': 'talk', 'stop': DUNSTAN_FINISH})
    return Record({'kind': 'wait', 'reason': f'unrecognized Troll Stronghold stage {stage}'})


def warn_troll_stronghold_readiness():
    bits = []
    combat = min(skills.level('attack'), skills.level('strength'), skills.level('defence'))
    if skills.level('agility') < 15:
        bits.append('Agility 15 is required for the secret-way rocks')
    if skills.level('prayer') < 43:
        bits.append('Protect from Melee (Prayer 43) turns Dad and the level-113 generals into a formality')
    if skills.level('thieving') < 30:
        bits.append('Thieving 30 steals the cell keys; below it both guards have to be killed')
    if combat < 50 or skills.level('hitpoints') < 50:
        bits.append(f"combat looks light for a level-113 general (att/str/def≈{combat}, hp={skills.level('hitpoints')})")
    return (f"Troll Stronghold: {'; '.join(bits)}" if len(bits) > 0 else None)


trollstronghold = QuestModule(**{
    'record': quest_record('troll'),
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': FALADOR_WEST_BANK,
    'grind': ['Dad', 'Troll General', 'Twig', 'Berry'],
    'tools': ['coins', 'climbing boots', 'prison key', 'cell key 1', 'cell key 2'] + list([f.lower() for f in COMBAT_FOODS]),
    'owns_inventory': True,
    'read_progress': read_troll_stronghold_progress,
    'sustain': Record({'foods': food_names(), 'eat_below_hp': 0.6}),
    'coin_float': COIN_FLOAT,
    'warn_readiness': warn_troll_stronghold_readiness,
    'decide': decide,
})

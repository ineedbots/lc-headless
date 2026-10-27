"""Ported from rs2b0t's src/bot/api/ai/quests/defs/vampireslayer.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs, npcs
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.interfaces import interfaces
from rs2004.items import inventory
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.garlic import GARLIC, MORGAN_STAIRS_TOP, take_garlic
from rs2004.quests.exec.primitives import talk_through
from rs2004.quests.food import quest_food
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.prayer import prayer_upkeep
from rs2004.tabs import quests
from rs2004.traversal import traversal


__all__ = ['VAMPIRE_SLAYER_STAGE', 'parse_vampire_slayer_journal', 'vampire_slayer_area', 'decide', 'vampireslayer']

VAMPIRE_SLAYER_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'SPOKEN_TO_HARLOW': 2, 'COMPLETE': 3})


def parse_vampire_slayer_journal(lines):


    text = normalize_journal(lines)
    if ('quest complete!' in text):
        return VAMPIRE_SLAYER_STAGE.COMPLETE
    if ('i have spoken to dr harlow' in text) or ('dr harlow gave me a stake' in text):
        return VAMPIRE_SLAYER_STAGE.SPOKEN_TO_HARLOW
    if ('i need to speak to dr harlow' in text):
        return VAMPIRE_SLAYER_STAGE.STARTED
    if ('i can start this quest' in text):
        return VAMPIRE_SLAYER_STAGE.NOT_STARTED
    return None


def read_vampire_slayer_stage():
    status = quests.status('Vampire Slayer')
    if status == 'complete':
        return VAMPIRE_SLAYER_STAGE.COMPLETE
    if status == 'not_started':
        return VAMPIRE_SLAYER_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    lines = yield from quests.journal('Vampire Slayer')
    stage = parse_vampire_slayer_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage


ITEM = Record({
    'BEER': 'Beer',
    'GARLIC': GARLIC,
    'HAMMER': 'Hammer',
    'STAKE': 'Stake',
    'SWORD': 'Black sword',
    'KEBAB': 'Kebab',
})
COUNT_DRAYNOR_ID = 757
COFFIN_CLOSED_ID = 2614
COIN_FLOAT = 5000
COIN_RESERVE = 2000
DRAYNOR_BANK = Tile(3093, 3243, 0)
JOLLY_BOAR = Tile(3277, 3490, 0)
VARROCK_GENERAL = Record({'npc': 'Shop keeper', 'anchor': Tile(3218, 3415, 0)})
VARROCK_SWORDS = Record({'npc': 'Shop keeper', 'anchor': Tile(3203, 3397, 0)})
MANOR_STAIRS_DOWN = Tile(3115, 3357, 0)
CRYPT_ARRIVAL = Tile(3077, 9771, 0)
CRYPT_STAIRS_UP = Tile(3077, 9768, 0)
COFFIN = Tile(3077, 9775, 0)
MORGAN = Record({'npc': 'Morgan', 'anchor': Tile(3098, 3268, 0), 'leash': 5, 'prefer': ["Ok, I'm up for an adventure."]})
HARLOW_FIRST = Record({'npc': 'Dr Harlow', 'anchor': Tile(3277, 3492, 0), 'leash': 5, 'prefer': ['Morgan needs your help']})
_merged1 = {}
for _k, _v in (HARLOW_FIRST._fields if isinstance(HARLOW_FIRST, Record) else HARLOW_FIRST).items():
    _merged1[_k] = _v


for _k, _v in {'prefer': ['Ok mate.']}.items():
    _merged1[_k] = _v


HARLOW_STAKE = Record(_merged1)
SAFE_WEAPONS = ['Black sword', 'Steel sword', 'Iron sword', 'Bronze sword']
BANK_FOODS = [
    'Shark',
    'Lobster',
    'Swordfish',
    'Tuna',
    'Salmon',
    'Trout',
    'Bread',
    'Cooked meat',
    'Cooked chicken',
    'Cake',
    ITEM.KEBAB,
]


def vampire_slayer_area(tile):
    if not tile:
        return 'unknown'
    if tile.level == 1 and tile.x >= 3088 and tile.x <= 3110 and tile.z >= 3255 and tile.z <= 3280:
        return 'morganUpper'
    if tile.level == 0 and tile.x >= 3040 and tile.x <= 3140 and tile.z >= 9700 and tile.z <= 9850:
        return 'crypt'
    if tile.level == 0 and tile.z < 5000:
        return 'mainland'
    return 'unknown'


def held_count(snap, name):
    return (snap.inv.get(name.lower()) if snap.inv.get(name.lower()) is not None else 0)


def held(snap, name):
    return held_count(snap, name) > 0


def banked(snap, name):
    return ((snap.bank or {}).get(name.lower()) if (snap.bank or {}).get(name.lower()) is not None else 0)


def worn(snap, name):
    return (name.lower() in snap.worn)


def food_names():
    configured = quest_food.name.strip()
    names = [name for name in [configured] + list(BANK_FOODS) if bool(name)]
    return list(list({_k: _v for _k, _v in [[name.lower(), name] for name in names]}.values()))


def exact_keep():
    return ['coins', ITEM.BEER.lower(), ITEM.GARLIC.lower(), ITEM.HAMMER.lower(), ITEM.STAKE.lower()] + list([name.lower() for name in SAFE_WEAPONS]) + list([name.lower() for name in food_names()])


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': DRAYNOR_BANK})


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': DRAYNOR_BANK})


def make_space(snap, slots):
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    keep = exact_keep()
    if any([not (name in keep) for name in list(list(snap.inv.keys()))]):
        return Record({'kind': 'deposit', 'keep': keep, 'bank': DRAYNOR_BANK, 'exact_keep': True})
    # Why: a restart can hold nothing but an oversized pile of valid supplies or food and the generic deposit can't keep quantities, so bank everything but coins and withdraw 1 clean loadout.
    return Record({'kind': 'deposit', 'keep': ['coins'], 'bank': DRAYNOR_BANK, 'exact_keep': True})


def normalize_pack(snap):
    keep = exact_keep()
    return (Record({'kind': 'deposit', 'keep': keep, 'bank': DRAYNOR_BANK, 'exact_keep': True}) if any([not (name in keep) for name in list(list(snap.inv.keys()))]) else None)


def source_coins(snap):
    in_pack = held_count(snap, 'Coins')
    # One 5k withdrawal covers the beer, hammer, sword and kebabs; don't cross the map to refill a couple of coins.
    if in_pack >= COIN_RESERVE:
        return None
    in_bank = banked(snap, 'Coins')
    if in_bank <= 0:
        return Record({'kind': 'wait', 'reason': 'need coins for Vampire Slayer supplies'})
    space = (make_space(snap, 1) if in_pack == 0 else None)
    return (space if space is not None else withdraw([{'name': 'Coins', 'qty': min(COIN_FLOAT - in_pack, in_bank)}]))


def source_banked_or(snap, name, fallback):
    if held(snap, name):
        return None
    if banked(snap, name) > 0:
        _v2 = make_space(snap, 1)
        return (_v2 if _v2 is not None else withdraw([{'name': name, 'qty': 1}]))
    return fallback()


def held_safe_weapon(snap):
    _v3 = ([name for name in SAFE_WEAPONS if held(snap, name)] or [None])[0]
    return (_v3 if _v3 is not None else None)


def worn_weapon(snap):
    if any([worn(snap, name) for name in SAFE_WEAPONS]):
        return True


    return any([(name.endswith('sword') or name.endswith('scimitar') or name.endswith('dagger') or name.endswith('mace') or name.endswith('battleaxe') or name.endswith('warhammer') or name.endswith('spear') or name.endswith('halberd') or name.endswith('whip') or name.endswith('axe')) for name in list(snap.worn)])


def bank_weapon(snap):
    _v4 = ([name for name in SAFE_WEAPONS if banked(snap, name) > 0] or [None])[0]
    return (_v4 if _v4 is not None else None)


def leave_morgan_upper(log):
    if (game.tile().level if game.tile() is not None else None) != 1:
        return True
    # Why: the upper staircase's map tile is blocked by its own collision shape, so on a restart the loaded staircase is clicked before navigation is asked for an impossible route.
    visible = locs.query().name('Staircase').action('Climb-down').within(8).nearest()
    if visible:
        if not (visible.interact('Climb-down')):
            return False
        _result5 = yield from execution.delay_until(lambda: (game.tile().level if game.tile() is not None else None) == 0, 8000)
        return _result5
    _w6 = yield from traversal.walk_resilient(MORGAN_STAIRS_TOP, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w6):
        return False
    stairs = locs.query().name('Staircase').action('Climb-down').within(6).nearest()
    if not stairs or not (stairs.interact('Climb-down')):
        log("Morgan's Staircase did not offer Climb-down")
        return False
    _result7 = yield from execution.delay_until(lambda: (game.tile().level if game.tile() is not None else None) == 0, 8000)
    return _result7


def buy_beer(log):
    if inventory.contains(ITEM.BEER):
        return True
    _w8 = yield from traversal.walk_resilient(JOLLY_BOAR, radius=3, attempts=3, timeout_ms=180000, log=log)
    if not (_w8):
        return False
    before = inventory.count(ITEM.BEER)
    _w9 = yield from talk_through('Bartender', ["I'll have a beer please."], log)
    if not (_w9):
        return False
    _result10 = yield from execution.delay_until(lambda: inventory.count(ITEM.BEER) > before, 6000)
    return _result10


def eat_food():
    allowed = set([name.lower() for name in food_names()])


    food = ([item for item in inventory.items() if item.name is not None and (item.name.lower() in allowed) and any([(action.lower() == 'eat' or action.lower() == 'drink') for action in item.actions()])] or [None])[0]
    if not food:
        return False


    action = ([op for op in food.actions() if (op.lower() == 'eat' or op.lower() == 'drink')] or [None])[0]
    if not action:
        return False
    before_count = len(inventory.items())
    before_hp = skills.effective('hitpoints')
    if not (food.interact(action)):
        return False
    _result11 = yield from execution.delay_until(lambda: len(inventory.items()) < before_count or skills.effective('hitpoints') != before_hp, 4000)
    return _result11


def leave_crypt(log):
    if vampire_slayer_area(game.tile()) != 'crypt':
        return True
    _w12 = yield from traversal.walk_resilient(CRYPT_STAIRS_UP, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w12):
        return False
    stairs = locs.query().name('Stairs').action('Walk-Up').within(6).nearest()
    if not stairs or not (stairs.interact('Walk-Up')):
        log('the crypt Stairs did not offer Walk-Up')
        return False
    _result13 = yield from execution.delay_until(lambda: vampire_slayer_area(game.tile()) != 'crypt', 8000)
    return _result13


def enter_crypt(log):
    if vampire_slayer_area(game.tile()) == 'crypt':
        return True
    _w14 = yield from traversal.walk_resilient(MANOR_STAIRS_DOWN, radius=2, attempts=5, timeout_ms=240000, log=log)
    if not (_w14):
        return False
    stairs = locs.query().name('Stairs').action('Walk-Down').within(7).nearest()
    if not stairs or not (stairs.interact('Walk-Down')):
        log('the manor Stairs did not offer Walk-Down')
        return False

    def _fn16():
        tile = game.tile()
        return vampire_slayer_area(tile) == 'crypt' and CRYPT_ARRIVAL.distance_to(tile) <= 8
    _result15 = yield from execution.delay_until(_fn16, 10000)
    return _result15


def live_count():
    return npcs.query().where(lambda npc: npc.id == COUNT_DRAYNOR_ID and not npc.targets_another_player()).within(12).nearest()


def fight_count(log):
    if vampire_slayer_area(game.tile()) != 'crypt':
        yield from enter_crypt(log)
        return False


    while skills.hp_fraction() < 0.9 and any([any([(op.lower() == 'eat' or op.lower() == 'drink') for op in item.actions()]) for item in inventory.items()]):
        _w17 = yield from eat_food()
        if not (_w17):
            break
    _w18 = yield from traversal.walk_resilient(COFFIN, radius=3, attempts=3, timeout_ms=60000, log=log)
    if not (_w18):
        return False
    count = live_count()
    if not count:
        coffin = locs.query().where(lambda loc: loc.id == COFFIN_CLOSED_ID).action('Open').within(7).nearest()
        if not coffin:
            log("waiting for Count Draynor's Coffin to close")
            yield from execution.delay_ticks(2)
            return False
        if not (coffin.interact('Open')):
            return False
        yield from execution.delay_until(lambda: live_count() is not None, 10000)
        count = live_count()
    if not count:
        log('Count Draynor did not emerge from the Coffin')
        return False
    deadline = _core.step_time() + 180000
    while _core.step_time() < deadline:
        if quests.status('Vampire Slayer') == 'complete':
            return True
        if skills.hp_fraction() < 0.6:
            yield from eat_food()
        else:
            yield from prayer_upkeep()
        count = live_count()
        if not count:
            _result19 = yield from execution.delay_until(lambda: quests.status('Vampire Slayer') == 'complete', 12000)
            return _result19
        if not game.in_combat():
            if not (count.interact('Attack')):
                return False
            yield from execution.delay_until(lambda: game.in_combat() or live_count() is None, 5000)
        yield from execution.delay_ticks(1)
    log('Count Draynor fight exceeded three minutes')
    return False


# Why: a free quest is fought at low level against low-level things, so food is not what makes the loadout complete; the run still eats whatever it happens to carry.
def complete_combat_loadout(snap):
    return held(snap, ITEM.STAKE) and held(snap, ITEM.GARLIC) and held(snap, ITEM.HAMMER) and worn_weapon(snap)


def stage_two(snap, area):
    if area == 'crypt' and not complete_combat_loadout(snap):
        return Record({'kind': 'custom', 'name': 'leave the crypt to recover supplies', 'run': leave_crypt})
    if area == 'morganUpper':
        return (Record({'kind': 'custom', 'name': "leave Morgan's upper floor", 'run': leave_morgan_upper}) if held(snap, ITEM.GARLIC) else Record({'kind': 'custom', 'name': "take garlic from Morgan's cupboard", 'run': take_garlic}))
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'return to the mainland to resume Vampire Slayer'})
    if not snap.bank_known:
        return scan_bank()
    normalize = normalize_pack(snap)
    if normalize:
        return normalize
    if not held(snap, ITEM.STAKE):
        if banked(snap, ITEM.STAKE) > 0:
            _v20 = make_space(snap, 1)
            return (_v20 if _v20 is not None else withdraw([{'name': ITEM.STAKE, 'qty': 1}]))
        if held(snap, ITEM.BEER):
            return Record({'kind': 'talk', 'stop': HARLOW_STAKE})
        if banked(snap, ITEM.BEER) > 0:
            _v21 = make_space(snap, 1)
            return (_v21 if _v21 is not None else withdraw([{'name': ITEM.BEER, 'qty': 1}]))
        coins = source_coins(snap)
        return (coins if coins is not None else Record({'kind': 'custom', 'name': 'buy Dr Harlow a Beer', 'run': buy_beer}))
    garlic = source_banked_or(snap, ITEM.GARLIC, lambda: (Record({'kind': 'custom', 'name': "take garlic from Morgan's cupboard", 'run': take_garlic})))
    if garlic:
        return garlic

    def _fn22():
        coins = source_coins(snap)
        return (coins if coins is not None else Record({'kind': 'buy', 'item': ITEM.HAMMER, 'qty': 1, 'shop': VARROCK_GENERAL, 'est_gp': 100}))
    hammer = source_banked_or(snap, ITEM.HAMMER, _fn22)
    if hammer:
        return hammer
    if not worn_weapon(snap):
        weapon = held_safe_weapon(snap)
        if weapon:
            return Record({'kind': 'equip', 'item': weapon})
        in_bank = bank_weapon(snap)
        if in_bank:
            _v23 = make_space(snap, 1)
            return (_v23 if _v23 is not None else withdraw([{'name': in_bank, 'qty': 1}]))
        coins = source_coins(snap)
        if coins:
            return coins
        return Record({'kind': 'buy', 'item': ITEM.SWORD, 'qty': 1, 'shop': VARROCK_SWORDS, 'est_gp': 1000})
    return Record({'kind': 'custom', 'name': 'enter the crypt and defeat Count Draynor', 'run': fight_count})


def decide(snap):
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else 0)) >= VAMPIRE_SLAYER_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Vampire Slayer journal stage unavailable'})
    area = vampire_slayer_area(snap.tile)
    if area == 'crypt':
        return (stage_two(snap, area) if snap.stage == VAMPIRE_SLAYER_STAGE.SPOKEN_TO_HARLOW else Record({'kind': 'custom', 'name': 'leave the crypt before continuing the quest', 'run': leave_crypt}))
    if area == 'morganUpper':
        if snap.stage == VAMPIRE_SLAYER_STAGE.STARTED and not held(snap, ITEM.GARLIC):
            return Record({'kind': 'custom', 'name': "take garlic from Morgan's cupboard", 'run': take_garlic})
        return Record({'kind': 'custom', 'name': "leave Morgan's upper floor", 'run': leave_morgan_upper})
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'return to the mainland to resume Vampire Slayer'})
    if not snap.bank_known:
        return scan_bank()
    normalize = normalize_pack(snap)
    if normalize:
        return normalize
    if snap.stage == VAMPIRE_SLAYER_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': MORGAN})
    if snap.stage == VAMPIRE_SLAYER_STAGE.STARTED:
        garlic = source_banked_or(snap, ITEM.GARLIC, lambda: (Record({'kind': 'custom', 'name': "take garlic from Morgan's cupboard", 'run': take_garlic})))
        return (garlic if garlic is not None else Record({'kind': 'talk', 'stop': HARLOW_FIRST}))
    if snap.stage == VAMPIRE_SLAYER_STAGE.SPOKEN_TO_HARLOW:
        return stage_two(snap, area)
    return Record({'kind': 'wait', 'reason': f'unrecognized Vampire Slayer stage {snap.stage}'})


vampireslayer = QuestModule(**{
    'record': ([record for record in QUESTS if record.id == 'vampire'] or [None])[0],
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': DRAYNOR_BANK,
    'grind': ['Count Draynor'],
    'tools': ['beer', 'garlic', 'hammer', 'stake', 'sword', 'kebab', 'coins'],
    'owns_inventory': True,
    'read_stage': read_vampire_slayer_stage,
    'sustain': Record({'foods': food_names(), 'eat_below_hp': 0.6}),
    'decide': decide,
})

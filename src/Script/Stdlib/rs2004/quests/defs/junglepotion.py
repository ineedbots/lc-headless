"""Ported from rs2b0t's src/bot/api/ai/quests/defs/junglepotion.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.engine.provisioning import COIN_FLOAT, float_withdraw
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import held_id, prompt_loc, settle_scene
from rs2004.quests.food import quest_food
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['JUNGLE_POTION_QUEST', 'TRUFITUS', 'JUNGLE_HERBS', 'POTHOLE_ENTRANCE', 'in_caves', 'JP_STAGE', 'herb_for_stage', 'parse_jungle_journal', 'read_jungle_progress', 'enter_pothole', 'decide', 'junglepotion']

JUNGLE_POTION_QUEST = 'Jungle Potion'
TRUFITUS = Tile(2809, 3086, 0)
ARDOUGNE_BANK = Tile(2616, 3332, 0)
JUNGLE_HERBS = [
    Record({
        'key': 'snake weed',
        'name': 'Snake weed',
        'id': 1526,
        'unid_id': 1525,
        'loc': 'Marshy jungle vine',
        'op': 'Search',
        'at': Tile(2760, 3014, 0),
        'stand': Tile(2761, 3015, 0),
    }),
    Record({
        'key': 'ardrigal',
        'name': 'Ardrigal',
        'id': 1528,
        'unid_id': 1527,
        'loc': 'Palm tree',
        'op': 'Search',
        'at': Tile(2870, 3115, 0),
        'stand': Tile(2869, 3115, 0),
    }),
    Record({
        'key': 'sito foil',
        'name': 'Sito foil',
        'id': 1530,
        'unid_id': 1529,
        'loc': 'Scorched earth',
        'op': 'Search',
        'at': Tile(2784, 3067, 0),
        'stand': Tile(2785, 3068, 0),
    }),
    Record({
        'key': 'volencia moss',
        'name': 'Volencia moss',
        'id': 1532,
        'unid_id': 1531,
        'loc': 'Rock',
        'op': 'Search',
        'at': Tile(2850, 3035, 0),
        'stand': Tile(2851, 3034, 0),
    }),
    Record({
        'key': 'rogues purse',
        'name': 'Rogues purse',
        'id': 1534,
        'unid_id': 1533,
        'loc': 'Fungus covered Cavern wall',
        'op': 'Search',
        'at': Tile(2850, 9476, 0),
        'stand': Tile(2850, 9477, 0),
        'underground': True,
    }),
]
# The cave mouth is 2x2 over (2824-2825, 3118-3119), so the stand is its west neighbour.
POTHOLE_ENTRANCE = Record({'loc': 'Rocks', 'op': 'Search', 'stand': Tile(2823, 3119, 0)})
POTHOLE_EXIT = Record({'loc': 'Hand holds', 'op': 'Climb', 'stand': Tile(2830, 9521, 0)})
START_DIALOGUE = [
    "It's a nice village, where is everyone?",
    'Me? How can I help?',
    'It sounds like just the challenge for me.',
]
HAND_IN_DIALOGUE = ['Of course!']


def in_caves(tile):
    return tile is not None and tile.z >= 9400


# Why: `get_*` means Trufitus has named the herb and `found_*` means it's picked, the only state he accepts it in.
# Journal stages, in the order the engine walks them.
JP_STAGE = Record({
    'NOT_STARTED': 0,
    'GET_SNAKE_WEED': 1,
    'FOUND_SNAKE_WEED': 2,
    'GET_ARDRIGAL': 3,
    'FOUND_ARDRIGAL': 4,
    'GET_SITO_FOIL': 5,
    'FOUND_SITO_FOIL': 6,
    'GET_VOLENCIA_MOSS': 7,
    'FOUND_VOLENCIA_MOSS': 8,
    'GET_ROGUES_PURSE': 9,
    'FOUND_ROGUES_PURSE': 10,
    'FOUND_ALL_HERBS': 11,
    'COMPLETE': 12,
})


def herb_for_stage(stage):
    """Herb index by stage: both the `get_` and `found_` stage point at the same herb."""
    if stage < JP_STAGE.GET_SNAKE_WEED or stage > JP_STAGE.FOUND_ROGUES_PURSE:
        return None
    _v1 = JUNGLE_HERBS[((stage - 1) // 2)]
    return (_v1 if _v1 is not None else None)


def parse_jungle_journal(lines):
    """The journal names the herb it wants and, once picked, says so in the past tense, which separates every `get_`/`found_` stage without a varp."""
    text = normalize_journal(lines)
    if ('quest complete!' in text):
        return QuestProgress(JP_STAGE.COMPLETE)
    if ('i can start this quest' in text):
        return QuestProgress(JP_STAGE.NOT_STARTED)
    if ('trufitus needs to commune with the gods' in text):
        return QuestProgress(JP_STAGE.FOUND_ALL_HERBS)
    # Newest first: the "picked" line only ever appears alongside its own "need to give".
    asked = [
        ['rogues purse', JP_STAGE.GET_ROGUES_PURSE, JP_STAGE.FOUND_ROGUES_PURSE],
        ['volencia moss', JP_STAGE.GET_VOLENCIA_MOSS, JP_STAGE.FOUND_VOLENCIA_MOSS],
        ['sito foil', JP_STAGE.GET_SITO_FOIL, JP_STAGE.FOUND_SITO_FOIL],
        ['ardrigal', JP_STAGE.GET_ARDRIGAL, JP_STAGE.FOUND_ARDRIGAL],
        ['snakeweed', JP_STAGE.GET_SNAKE_WEED, JP_STAGE.FOUND_SNAKE_WEED],
    ]
    for herb, get_stage, found_stage in asked:
        if (f'i need to give the {herb}' in text) or (f'i picked some fresh {herb}' in text):
            return QuestProgress(found_stage)
        if (f'i need to pick some fresh {herb}' in text):
            return QuestProgress(get_stage)
    # Rogues purse renders singular in the "give" line only.
    if ('i need to give the rogue purse' in text):
        return QuestProgress(JP_STAGE.FOUND_ROGUES_PURSE)
    return None


def read_jungle_progress():
    status = quests.status(JUNGLE_POTION_QUEST)
    if status == 'complete':
        return QuestProgress(JP_STAGE.COMPLETE)
    if status == 'not_started':
        return QuestProgress(JP_STAGE.NOT_STARTED)
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(JUNGLE_POTION_QUEST)
    progress = parse_jungle_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress


def enter_pothole(log):
    """The cave mouth raises a message box first, then the yes/no prompt."""
    if in_caves(game.tile()):
        return True
    ok = yield from prompt_loc(Record({
        'name': POTHOLE_ENTRANCE.loc,
        'op': POTHOLE_ENTRANCE.op,
        'near': POTHOLE_ENTRANCE.stand,
        'prefer': ["Yes, I'll enter the cave."],
        'expect': lambda: in_caves(game.tile()),
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def leave_pothole(log):
    if not in_caves(game.tile()):
        return True
    ok = yield from prompt_loc(Record({
        'name': POTHOLE_EXIT.loc,
        'op': POTHOLE_EXIT.op,
        'near': POTHOLE_EXIT.stand,
        'expect': lambda: not in_caves(game.tile()),
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def pick_herb(herb):
    def pick(log):
        target = herb
        # Only the unid proves a fresh pick; a clean herb from an earlier run doesn't advance the stage and Trufitus refuses it.
        if held_id(target.unid_id) > 0:
            return True
        _c4 = target.underground
        if _c4:
            _w5 = yield from enter_pothole(log)
            _c4 = not (_w5)
        if _c4:
            return False
        _c6 = not target.underground and in_caves(game.tile())
        if _c6:
            _w7 = yield from leave_pothole(log)
            _c6 = not (_w7)
        if _c6:
            return False
        _result8 = yield from prompt_loc(Record({'name': target.loc, 'op': target.op, 'near': target.stand, 'expect': lambda: held_id(target.unid_id) > 0}), log)
        return _result8
    return pick


def identify_herb(herb):
    def identify(log):
        target = herb
        if held_id(target.id) > 0:
            return True
        unid = ([item for item in inventory.items() if item.id == target.unid_id] or [None])[0]
        if not unid:
            log(f'no unidentified {target.name} in the pack')
            return False
        if not (unid.interact('Identify')):
            return False
        _result10 = yield from execution.delay_until(lambda: held_id(target.id) > 0, 6000)
        return _result10
    return identify


def talk_to_trufitus(prefer, log):
    _c11 = in_caves(game.tile())
    if _c11:
        _w12 = yield from leave_pothole(log)
        _c11 = not (_w12)
    if _c11:
        return False
    _w13 = yield from traversal.walk_resilient(TRUFITUS, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w13):
        return False
    _result14 = yield from talk_strict('Trufitus', prefer, log)
    return _result14


def start_quest(log):
    result = yield from talk_to_trufitus(START_DIALOGUE, log)
    return result


def hand_in_herb(log):
    result = yield from talk_to_trufitus(HAND_IN_DIALOGUE, log)
    return result


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    # Why: a carried unid outranks the journal since it only exists once picked, which the journal can't render.
    # Why: at `found_snake_weed` with the unid held the journal writes no line, and every other `found_` stage writes the previous "go and pick it" line.
    carried = ([h for h in JUNGLE_HERBS if (((snap.inv_ids or {}).get(h.unid_id) if (snap.inv_ids or {}).get(h.unid_id) is not None else 0)) > 0] or [None])[0]
    if carried:
        return Record({'kind': 'custom', 'name': f'identify the {carried.name}', 'run': identify_herb(carried)})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Jungle Potion journal stage unavailable'})
    tile = snap.tile
    on_island = tile and tile.x >= 2700 and tile.x <= 3010 and tile.z >= 2870 and tile.z <= 3260 and (tile.x < 2850 or tile.z <= 3180) and (tile.x < 2970 or tile.z <= 3070)
    if tile and not on_island and not in_caves(tile):
        if not snap.bank_known:
            return Record({'kind': 'scan_bank', 'bank': ARDOUGNE_BANK})
        bank = (snap.bank if snap.bank is not None else {})
        coins = float_withdraw(snap.inv, bank, 'Coins', COIN_FLOAT)
        food = (float_withdraw(snap.inv, bank, quest_food.name, 8) if quest_food.name else None)
        items = [item for item in [coins, food] if item is not None]
        if len(items) > 0:
            _v15 = (food['qty'] if food is not None else None)
            slots = ((_v15 if _v15 is not None else 0)) + ((1 if coins and not snap.inv.get('coins') else 0))
            if ((snap.free_slots if snap.free_slots is not None else 28)) < slots:
                _flat16 = []
                for herb in JUNGLE_HERBS:
                    _flat16.extend([herb.id, herb.unid_id])
                return Record({
                    'kind': 'deposit',
                    'bank': ARDOUGNE_BANK,
                    'keep': ['coins'] + list((([quest_food.name.lower()] if quest_food.name else []))),
                    'keep_ids': _flat16,
                    'exact_keep': True,
                })
            return Record({'kind': 'withdraw', 'items': items, 'bank': ARDOUGNE_BANK})
        _v17 = snap.inv.get('coins')
        if ((_v17 if _v17 is not None else 0)) < 60:
            return Record({'kind': 'wait', 'reason': 'need 60 Coins for the outbound and return boat fares'})
    if stage == JP_STAGE.NOT_STARTED:
        return Record({'kind': 'custom', 'name': 'ask Trufitus for the herb-gathering job', 'run': start_quest})
    if stage >= JP_STAGE.FOUND_ALL_HERBS:
        return Record({'kind': 'custom', 'name': 'let Trufitus commune with the gods', 'run': hand_in_herb})
    herb = herb_for_stage(stage)
    if not herb:
        return Record({'kind': 'wait', 'reason': f'Jungle Potion stage {stage} is not implemented'})
    # Picking advances `get_` to `found_` and only `found_` accepts a hand-in, so a clean herb at a `get_` stage still gets re-picked.
    _v18 = (snap.inv_ids or {}).get(herb.id)
    held = (_v18 if _v18 is not None else 0)
    if stage % 2 == 1 or held == 0:
        return Record({'kind': 'custom', 'name': f'pick {herb.name}', 'run': pick_herb(herb)})
    return Record({'kind': 'custom', 'name': f'give the {herb.name} to Trufitus', 'run': hand_in_herb})


junglepotion = QuestModule(
    record=quest_record('junglepotion'),
    bank=ARDOUGNE_BANK,
    owns_inventory=True,
    read_progress=read_jungle_progress,
    decide=decide,
)

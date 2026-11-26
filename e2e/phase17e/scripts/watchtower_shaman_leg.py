"""Local-289 diagnostic: seed only the shaman leg, never report a full quest pass."""

import json
import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.game import game, skills
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.watchtower import watchtower
from rs2004.quests.defs.watchtower.areas import WT_ITEM
from rs2004.quests.defs.watchtower.enclave import dissolve_shamans, held_id, leave_enclave
from rs2004.quests.prayer import prayer_upkeep, set_quest_prayer
from seed_helpers import send

started = False
deaths = 0


def on_death():
    global deaths
    deaths += 1


def upkeep():
    yield from prayer_upkeep()
    while skills.effective('hitpoints') < skills.level('hitpoints') * 0.85:
        food = inventory.first('Lobster')
        if food is None or not food.interact('Eat'):
            return
        yield from execution.delay_ticks(1)


def loop():
    global started
    if started:
        return 600
    started = True
    yield from execution.delay_ticks(5)
    assert inventory.used() == 0, 'use a newly prepared, seeded scratch account'
    # This is explicitly a seeded leg diagnostic, not full-quest acceptance.
    yield from send('setvar itwatchtower 10')
    yield from send('setvar itwatchtower_bits 0')
    for item in ['rune_chainbody 1', 'rune_platelegs 1', 'rune_longsword 1',
                 'antidragonbreathshield 1', 'lobster 8', 'bronze_pickaxe 1',
                 'magic_ogre_potion 1', 'nightshade 1', '3doseprayerrestore 2']:
        yield from send('give ' + item)
    for name in ['Rune chainbody', 'Rune platelegs', 'Rune longsword', 'Dragonfire shield']:
        worn = yield from equipment.equip(name)
        assert worn, 'could not equip ' + name
    assert held_id(WT_ITEM.NIGHTSHADE.id) == 1, 'exactly one nightshade required'
    assert held_id(WT_ITEM.MAGIC_OGRE_POTION.id) == 1, 'enchanted potion required'
    assert held_id(WT_ITEM.CRYSTAL3.id) == 0 and held_id(WT_ITEM.CRYSTAL4.id) == 0
    yield from send('infiniterun')
    yield from send('tele 0,39,47,11,29')
    sustain.set(upkeep)
    set_quest_prayer(watchtower.pray, log)
    mark = game_messages.mark()
    start = _core.step_time()
    log('SHAMAN_LEG_START', game.my_name(), game.tile())
    ok = yield from dissolve_shamans(log)
    elapsed = _core.step_time() - start
    messages = [message.text.lower() for message in game_messages.since(mark)]
    entries = len([text for text in messages if 'you run past the guard' in text])
    dissolves = len([text for text in messages if 'the ogre dissolves into spirit form' in text])
    passed = ok and entries == 1 and dissolves == 6 and deaths == 0 and held_id(WT_ITEM.CRYSTAL3.id) == 1 and held_id(WT_ITEM.CRYSTAL4.id) == 1
    log('SHAMAN_LEG_RESULT ' + json.dumps({'name': game.my_name(), 'passed': passed,
        'seeded_target_stage': 10, 'quest_complete': False, 'entries': entries,
        'dissolves': dissolves, 'deaths': deaths, 'elapsed_ms': elapsed,
        'shaman_crystal': held_id(WT_ITEM.CRYSTAL3.id), 'rock_crystal': held_id(WT_ITEM.CRYSTAL4.id)}))
    if ok:
        yield from leave_enclave(log)
    stop_account()
    return 600

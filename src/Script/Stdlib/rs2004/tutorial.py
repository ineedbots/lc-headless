"""Playable Tutorial Island, resumed from the server's instruction panel before on_start.
complete() follows every instructor; skip() remains an explicit alternative for test tools.
"""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import npcs, locs
from rs2004.game import game, direct_navigator
from rs2004.items import inventory, equipment
from rs2004.reach import reach

__all__ = ['on_tutorial_island', 'complete', 'skip']

GUIDE = 'RuneScape Guide'
SKIP_OPTION = 'Yes please'
# A design the server allows: a male with the first of each body kit, in the first colours.
DESIGN_KITS = [0, 10, 18, 26, 33, 36, 42]
DESIGN_COLOURS = [0, 0, 0, 0, 0]
# The design screen opens as the player is placed, sometimes a tick or two after.
DESIGN_WAIT_MS = 1800
DESIGN_CLOSE_MS = 5000
TALK_ATTEMPTS = 3
# Walking to the guide comes first.
TALK_OPEN_MS = 10000
DIALOGUE_STEPS = 25
LEAVE_MS = 10000


def in_tutorial_area(x, z):
    """Whether the tile is on the island or in its mine and dungeon below, as the server's in_tutorial_island
    has them, on any level."""
    if 3053 <= x and x <= 3156 and 3056 <= z and z <= 3136:
        return True
    return 3072 <= x and x <= 3118 and 9492 <= z and z <= 9535


def on_tutorial_island():
    return _core.is_placed() and in_tutorial_area(_core.get_x(), _core.get_z())


def offers_skip(options):
    """Whether the guide's options include skipping, matched by part without regard to case, as
    choose_option matches."""
    wanted = SKIP_OPTION.lower()
    for option in options:
        if wanted in option.lower():
            return True
    return False


# Stage numbers follow the server's tutorial constants; the varp itself is server-only.
STAGE_TIMEOUT_MS = 180000
ACTION_WAIT_MS = 15000
TABS = {2: 11, 20: 3, 50: 1, 170: 13, 230: 2,
        370: 4, 410: 0, 550: 5, 570: 8, 580: 9, 620: 6}
INSTRUCTORS = {
    1: ('RuneScape Guide', (3094, 3107)),
    3: ('RuneScape Guide', (3094, 3107)),
    10: ('Survival Expert', (3104, 3096)),
    60: ('Survival Expert', (3104, 3096)),
    140: ('Master Chef', (3076, 3085)),
    220: ('Quest Guide', (3086, 3123)),
    240: ('Quest Guide', (3086, 3123)),
    260: ('Mining Instructor', (3081, 9504)),
    279: ('Mining Instructor', (3081, 9504)),
    280: ('Mining Instructor', (3081, 9504)),
    330: ('Mining Instructor', (3081, 9504)),
    360: ('Combat Instructor', (3106, 9508)),
    390: ('Combat Instructor', (3106, 9508)),
    450: ('Combat Instructor', (3106, 9508)),
    520: ('Financial Advisor', (3127, 3124)),
    540: ('Brother Brace', (3131, 3114)),
    560: ('Brother Brace', (3124, 3106)),
    590: ('Brother Brace', (3124, 3106)),
    610: ('Magic Instructor', (3140, 3087)),
    630: ('Magic Instructor', (3140, 3087)),
    660: ('Magic Instructor', (3140, 3087)),
    670: ('Magic Instructor', (3140, 3087)),
}
# id, approach tile, operation. Doors and gates themselves advance the server stage.
PASSAGES = {
    4: (3014, (3098, 3107), 'Open'),
    120: (3015, (3090, 3092), 'Open'),
    130: (3017, (3079, 3084), 'Open'),
    180: (3018, (3073, 3090), 'Open'),
    200: (3019, (3086, 3126), 'Open'),
    250: (3029, (3088, 3120), 'Climb-down'),
    350: (3020, (3094, 9503), 'Open'),
    420: (3022, (3111, 9518), 'Open'),
    470: (3030, (3111, 9525), 'Climb-up'),
    510: (3024, (3124, 3124), 'Open'),
    530: (3025, (3129, 3124), 'Open'),
    600: (3026, (3122, 3102), 'Open'),
}


INSTRUCTIONS = [
    ('getting started', 1),
    ('interacting with scenery', 4),
    ('moving around', 10),
    ('viewing the items', 20),
    ('cut down a tree', 30),
    ('building a fire', 40),
    ('you gained some experience', 50),
    ('these are your stats', 60),
    ('catch some shrimp.', 70),
    ('cooking your shrimp', 80),
    ('burning your shrimp', 90),
    ("you've just cooked your first", 120),
    ('follow the path until you get to the door', 130),
    ('talk to the chef indicated', 140),
    ('making dough', 150),
    ('cooking dough', 160),
    ('your first loaf of bread', 170),
    ('the music player.', 180),
    ("it's only a short distance", 190),
    ('in this menu you will see many options', 195),
    ('run to the next guide', 200),
    ('talk with the quest guide', 220),
    ('open the quest journal', 230),
    ('this is your quest journal', 240),
    ("it's time to enter some caves", 250),
    ('mining and smithing', 260),
    ('to prospect a mineable rock', 270),
    ('try prospecting the grey', 274),
    ('try prospecting the brown', 275),
    ('talk to the mining instructor to find out', 280),
    ('first mine one tin ore', 290),
    ('now you have some copper ore', 294),
    ('now you have some tin ore', 295),
    ("so let's smelt", 320),
    ("you've made a bronze bar", 330),
    ('smithing a dagger', 340),
    ("you've finished this area", 350),
    ('both melee and ranged', 360),
    ('wielding weapons', 370),
    ('this is your worn inventory', 380),
    ("you're now holding your dagger", 390),
    ('unequipping items', 400),
    ('click on the flashing crossed swords', 410),
    ('this is your combat interface', 420),
    ('to attack the rat right click', 430),
    ('sit back and watch', 440),
    ("you've made your first kill", 450),
    ('rat ranging', 460),
    ('you have completed the tasks here', 470),
    ("this is the 'bank of runescape'", 500),
    ('this is your bank box', 510),
    ('financial advice', 520),
    ('continue through the next door', 530),
    ('follow the path to the chapel', 540),
    ('click on the flashing icon to open the prayer', 550),
    ("talk with brother brace and he'll tell", 560),
    ('click on flashing smily', 570),
    ('this is your friends list', 580),
    ('this is your ignore list', 590),
    ('pass through the door to find the path', 600),
    ('just follow the path to the wizards', 610),
    ('open up your final menu', 620),
    ("sadly it didn't have any effect", 650),
    ('cast wind strike at a chicken', 640),
    ('you have almost completed the tutorial', 660),
]
_last_stage = 0


def progress():
    """Read server instructions; transient 'Please wait' panels retain the preceding stage."""
    global _last_stage
    root = _core.get_tutorial_modal()
    text = ' '.join(_core.get_texts(root)).lower() if root >= 0 else ''
    text = ' '.join(text.replace('|', ' ').split())
    for phrase, stage in INSTRUCTIONS:
        if phrase in text:
            _last_stage = max(_last_stage, stage)
            break
    return _last_stage


def _drain_dialogue():
    """Only answer known progression options; never guess at an unfamiliar choice."""
    for step in range(80):
        if not chat_dialog.is_open():
            yield from execution.delay_ticks(2)
            if not chat_dialog.is_open():
                return True
        options = chat_dialog.options()
        if options:
            wanted = ['No, thank you', 'No thanks', "I'm ready to move on"]
            if progress() == 500 or progress() >= 660:
                wanted = ['Yes.']
            choice = None
            for part in wanted:
                for option in options:
                    if part.lower() in option.lower():
                        choice = option
                        break
                if choice is not None:
                    break
            if choice is None:
                return False
            yield from chat_dialog.choose_option(choice)
        elif chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        else:
            yield from execution.delay_ticks(1)
    return False


def _instructor(name, tile):
    npc = npcs.query().name(name).nearest()
    if npc is None or npc.distance() > 12:
        yield from direct_navigator.walk_to(tile, radius=3, timeout_ms=20000)
        npc = npcs.query().name(name).nearest()
    if npc is None:
        return False
    def find():
        return npcs.query().name(name).nearest()
    status = yield from reach.entity_op(find, 'Talk-to', lambda: chat_dialog.is_open(),
                                       open_when_unreachable=True, expect_ms=TALK_OPEN_MS)
    if status != 'done':
        return False
    result = yield from _drain_dialogue()
    return result


def _scenery(ids, tile=None):
    if tile is not None:
        yield from direct_navigator.walk_to(tile, radius=2, timeout_ms=20000)
    return locs.query().id(ids).nearest()


def _operate(ids, tile, action):
    loc = yield from _scenery(ids, tile)
    return loc is not None and loc.interact(action)


def _use(name, target):
    item = inventory.first(name)
    return item is not None and target is not None and item.use_on(target)


def _light_fire():
    if not inventory.contains('Logs'):
        tree = locs.query().id(3033, 3034, 3036).reachable().nearest()
        if tree is None or not tree.interact('Chop down'):
            return False
        yield from execution.delay_until(lambda: inventory.contains('Logs'), ACTION_WAIT_MS)
    return _use('Tinderbox', inventory.first('Logs'))


def _shrimp():
    if not inventory.contains('Raw shrimps'):
        spot = npcs.query().name('Fishing spot').nearest()
        if spot is None or not spot.interact('Net'):
            return False
        yield from execution.delay_until(lambda: inventory.contains('Raw shrimps'), ACTION_WAIT_MS)
        # Stop fishing before lighting a replacement fire or cooking.
    fire = locs.query().name('Fire').nearest()
    if fire is None:
        yield from _light_fire()
        yield from execution.delay_until(lambda: locs.query().name('Fire').nearest() is not None, ACTION_WAIT_MS)
        fire = locs.query().name('Fire').nearest()
    return _use('Raw shrimps', fire)


def _fight(ranged):
    if ranged:
        yield from equipment.unequip('Wooden shield')
        yield from equipment.equip('Shortbow')
        yield from equipment.equip('Bronze arrow')
    rat = npcs.query().name('Giant rat').where(lambda n: n.targets_me()).nearest()
    if rat is None:
        query = npcs.query().name('Giant rat').where(lambda n: not n.targets_another_player())
        if not ranged:
            query.reachable()
        rat = query.nearest()
    if rat is None or not rat.interact('Attack'):
        return False
    finished = 470 if ranged else 450
    yield from execution.delay_until(lambda: progress() >= finished or not rat.valid(), 90000)
    return True


def _perform_stage(stage):
    if chat_dialog.is_open():
        result = yield from _drain_dialogue()
        return result
    if stage in TABS:
        result = yield from game.open_side_tab(TABS[stage])
        return result
    if stage in INSTRUCTORS:
        name, tile = INSTRUCTORS[stage]
        if stage == 450 and _core.get_x() <= 3110 and _core.get_z() >= 9511:
            result = yield from _operate(3022, (3112, 9518), 'Open')
            return result
        result = yield from _instructor(name, tile)
        return result
    if stage in PASSAGES:
        if stage == 510:
            yield from modals.close_if_open()
        id, tile, action = PASSAGES[stage]
        result = yield from _operate(id, tile, action)
        return result
    if stage in (190, 195):
        if stage == 190:
            yield from game.open_side_tab(12)
            yield from execution.delay_ticks(1)
        game.set_run(True)
        return True
    if stage == 30:
        result = yield from _operate([3033, 3034, 3036], None, 'Chop down')
        return result
    if stage == 40:
        result = yield from _light_fire()
        return result
    if stage == 70:
        spot = npcs.query().name('Fishing spot').nearest()
        return spot is not None and spot.interact('Net')
    if stage in (80, 90):
        result = yield from _shrimp()
        return result
    if stage == 150:
        return _use('Bucket of water', inventory.first('Pot of flour'))
    if stage == 160:
        target = yield from _scenery(3039)
        return _use('Bread dough', target)
    if stage in (270, 274, 275):
        id = 3043 if stage == 274 else 3042
        result = yield from _operate(id, None, 'Prospect')
        return result
    if stage in (290, 294, 295):
        id = 3042 if stage == 295 else 3043
        result = yield from _operate(id, None, 'Mine')
        return result
    if stage == 320:
        target = yield from _scenery(3044)
        return _use('Copper ore', target)
    if stage == 340:
        if chat_dialog.is_main_make_panel():
            result = yield from chat_dialog.make_from_panel('Bronze dagger')
            return result
        return _use('Bronze bar', locs.query().name('Anvil').nearest())
    if stage == 380:
        result = yield from equipment.equip('Bronze dagger')
        return result
    if stage == 400:
        yield from equipment.unequip('Bronze dagger')
        yield from equipment.equip('Bronze sword')
        result = yield from equipment.equip('Wooden shield')
        return result
    if stage in (430, 440, 460):
        result = yield from _fight(stage == 460)
        return result
    if stage == 500:
        result = yield from _operate(3045, (3122, 3124), 1)
        return result
    if stage in (640, 650):
        if not inventory.contains('Air rune') or not inventory.contains('Mind rune'):
            result = yield from _instructor('Magic Instructor', (3140, 3087))
            return result
        chicken = npcs.query().name('Chicken').nearest()
        if chicken is None:
            return False
        return game.cast_on_npc('Wind Strike', chicken)
    return False


def complete(say):
    """Complete all tasks through ordinary player actions. False leaves startup stopped on the island."""
    say('tutorial: completing Tutorial Island')
    yield from _finish_design(say)
    stage = -1
    deadline = _core.step_time() + STAGE_TIMEOUT_MS
    while on_tutorial_island():
        current = progress()
        if current != stage:
            stage = current
            deadline = _core.step_time() + STAGE_TIMEOUT_MS
            say(f'tutorial: stage {stage}')
            execution.note_progress()
        if _core.step_time() >= deadline:
            say(f'tutorial: stalled at stage {stage}; stopping before script startup')
            return False
        performed = yield from _perform_stage(stage)
        if not performed:
            say(f'tutorial: stage {stage} action unavailable; retrying')
        yield from execution.delay_ticks(1)
        yield from execution.delay_until(lambda: progress() != stage or chat_dialog.is_open() or not on_tutorial_island(), 5000)
    if not _core.is_placed():
        say('tutorial: disconnected before mainland arrival')
        return False
    say('tutorial: completed; arrived on the mainland')
    return True


def _finish_design(say):
    """Saves a design when the design screen is open; the server lets the guide offer the skip after one."""
    yield from execution.delay_until(lambda: game.appearance_screen_open(), DESIGN_WAIT_MS)
    if not game.appearance_screen_open():
        return
    say('tutorial: saving a character design')
    game.set_appearance(False, DESIGN_KITS, DESIGN_COLOURS)
    yield from execution.delay_until(lambda: not game.appearance_screen_open(), DESIGN_CLOSE_MS)


def _talk(say):
    """Talks to the guide and answers him. 'skipped', 'refused' when he talked without offering the skip,
    or 'failed'."""
    guide = npcs.query().name(GUIDE).nearest()
    if guide is None:
        say(f"tutorial: can't see the {GUIDE}")
        return 'failed'
    if not guide.interact('Talk-to'):
        return 'failed'
    opened = yield from execution.delay_until(lambda: chat_dialog.is_open(), TALK_OPEN_MS)
    if not opened:
        return 'failed'
    for i in range(DIALOGUE_STEPS):
        if not chat_dialog.is_open():
            break
        options = chat_dialog.options()
        if options:
            if not offers_skip(options):
                return 'refused'
            yield from chat_dialog.choose_option(SKIP_OPTION)
            return 'skipped'
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        else:
            yield from execution.delay_ticks(1)
    return 'refused'


def skip(say):
    """Gets off the island by the guide's skip. Use with yield from; True once the player has left."""
    say('tutorial: on Tutorial Island; asking the RuneScape Guide to skip it')
    yield from _finish_design(say)
    for attempt in range(TALK_ATTEMPTS):
        outcome = yield from _talk(say)
        if outcome == 'refused':
            break
        if outcome != 'skipped':
            continue
        left = yield from execution.delay_until(lambda: not on_tutorial_island(), LEAVE_MS)
        if left:
            say('tutorial: skipped')
            return True
    say(f"tutorial: the {GUIDE} didn't offer to skip the tutorial; still on the island")
    return False

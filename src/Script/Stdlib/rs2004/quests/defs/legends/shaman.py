"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/shaman.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs, npcs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.legends.areas import LQ_ID, LQ_LOC, LQ_LOC_ID, LQ_NPC, LQ_TILE, in_octagram
from rs2004.quests.defs.legends.fight import drink_prayer
from rs2004.quests.defs.legends.jungle import enter_jungle, leave_jungle, summon_gujuo, talk_gujuo_status
from rs2004.quests.defs.legends.scene import drive_boxes, drive_to_end, drive_until, held_id, here, loc_near, modal_text, offer_to, prompt_loc, settle_scene, use_on_loc
from rs2004.quests.defs.legends.trials import climb_out_of_trials, leave_octagram
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['enter_shaman_cave', 'speak_to_ungadulu', 'water_talk_answer', 'ask_gujuo_for_water', 'bless_bowl', 'needs_dose', 'bless_prayer_floor', 'make_golden_bowl', 'cut_reed', 'fill_bowl_from_pool', 'find_pool_dried', 'enter_octagram', 'summon_demon', 'ask_for_seeds', 'germinate_seeds']

CRAWL_ATTEMPTS = 6
ROCK_IDS = [LQ_LOC_ID.MOSSY_ROCK_1, LQ_LOC_ID.MOSSY_ROCK_2, LQ_LOC_ID.MOSSY_ROCK_3]


# Why: The crawl has a level-50 gate, then an Agility roll; failure costs 5 HP without moving the player.
def enter_shaman_cave(log):
    """Squeeze through the rocks in the north-west jungle into Ungadulu's cave."""
    if here() == 'shaman_caves':
        return True
    _w1 = yield from enter_jungle(log)
    if not (_w1):
        return False
    _w2 = yield from traversal.walk_resilient(LQ_TILE.MOSSY_ROCKS, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w2):
        return False
    yield from settle_scene()
    for i in range(CRAWL_ATTEMPTS):
        if here() == 'shaman_caves':
            yield from settle_scene()
            return True
        # Why: Jungle ore veins share these names, so match the three cave-mouth ids.
        rock = locs.query().where(lambda l: (l.id in ROCK_IDS)).action('Search').within(8).nearest()
        if not rock:
            log('no mossy rock offering Search near the cave mouth')
            return False
        if not (rock.interact('Search')):
            continue
        yield from drive_until(lambda: here() == 'shaman_caves', ["Yes, I'll crawl through"], log, 25000)
    log('six crawls and still outside the shaman cave')
    return False


# Why: "Who are you?" unlocks Gujuo's pure-water branch and must be asked before the water question.
UNGADULU_PREFER = ['Who are you?', 'Where do I get pure water from?']


def speak_to_ungadulu(log):
    """Talk to Ungadulu through the flames until he has named the sacred water."""
    # Why: From inside the ring, Investigate opens a different menu outside this driver's preference list.
    _c3 = in_octagram(game.tile())
    if _c3:
        _w4 = yield from leave_octagram(log)
        _c3 = not (_w4)
    if _c3:
        log('cannot get out of the octagram to talk to Ungadulu through the flames')
        return False
    _w5 = yield from enter_shaman_cave(log)
    if not (_w5):
        return False
    _w6 = yield from traversal.walk_resilient(LQ_TILE.FIRE_WALL_WEST, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w6):
        return False
    yield from settle_scene()
    wall = loc_near(LQ_LOC.FIRE_WALL, 'Investigate', 6)
    if not wall:
        log('no fire wall offering Investigate beside the octagram')
        return False
    if not (wall.interact('Investigate')):
        return False
    # The message box appears before the option list.
    _w7 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w7):
        log('the fire wall raised nothing — is Ungadulu still in the octagram?')
        return False
    # Why: Require "Who are you?" because a missing Ungadulu produces two boxes and no menu, which otherwise looks successful.
    _result8 = yield from drive_to_end(UNGADULU_PREFER, log, 60000, 'Who are you?')
    return _result8


# Why: The last two choices finish the dialogue after Gujuo gives the sketch.
GUJUO_WATER_PREFER = [
    'I need some pure water to douse some magic flames.',
    'Where is the pool of sacred water?',
    'What kind of a vessel?',
    'Ungadulu looks a little strange.',
    'How do I bless the vessel?',
    'Ok thanks for your help.',
]
# Why: Receiving the sketch also advances the stage, so the item proves success without reading the journal.
gujuo_water_talk = talk_gujuo_status(GUJUO_WATER_PREFER, lambda: held_id(LQ_ID.GOLD_BOWL_SKETCH) > 0, 120000)


# Why: A menu without the water topic means the invisible Ungadulu bit still needs setting; no dialogue is retried locally.
def water_talk_answer(talk):
    """Next action after trying Gujuo's water dialogue."""
    if talk == 'goal':
        return 'done'
    return ('retry' if talk == 'nodialog' else 'caves')


def ask_gujuo_for_water(log):
    """Ask Gujuo where the pure water comes from, going back to Ungadulu if he cannot say."""
    first = yield from gujuo_water_talk(log)
    if water_talk_answer(first) == 'done':
        return True
    if water_talk_answer(first) == 'retry':
        log('Gujuo would not open a dialogue — trying him again rather than walking the caves for a bit he never spoke about')
        _w9 = yield from gujuo_water_talk(log)
        return (_w9) == 'goal'
    log('Gujuo has no pure-water topic — Ungadulu has not been asked who he is')
    _w10 = yield from speak_to_ungadulu(log)
    if not (_w10):
        return False
    after = yield from gujuo_water_talk(log)
    if after != 'goal':
        log(f"back from Ungadulu and the sketch still did not come — {('no conversation happened' if after == 'nodialog' else 'no topic on his menu')}")
    return after == 'goal'


# Why: These paths reach the blessing offer; goodbye options leave the bowl unchanged.
BLESS_PREFER = [
    "Yes, I'd like you to bless my gold bowl.",
    "Yes, I'd like to bless my gold bowl.",
    'How do I bless the vessel?',
    'What kind of a vessel?',
    'I need some pure water to douse some magic flames.',
]


# Why: Using the bowl on Gujuo opens the blessing menu directly.
def bless_bowl(log):
    """Gujuo blesses the bowl; the trance rolls against prayer and re-offers on a miss."""

    def blessed():
        return held_id(LQ_ID.GOLD_BOWL_BLESSED) > 0 or held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0 or held_id(LQ_ID.GOLD_BOWL_BLESSED_WATER) > 0

    if blessed():
        return True
    _w11 = yield from summon_gujuo(log)
    if not (_w11):
        return False
    # Why: The use-on sometimes produces no dialogue, so retry the offer after a short wait.
    for i in range(BLESS_ATTEMPTS):
        gujuo = npcs.query().name(LQ_NPC.GUJUO).within(12).nearest()
        if not gujuo:
            log('no Gujuo in range for the bowl')
            return False
        _w12 = yield from top_up_prayer(log)
        if not (_w12):
            log(f"prayer at {skills.effective('prayer')} with nothing left to drink, and the trance refuses below {BLESS_FLOOR}")
            return False
        offered = yield from offer_to(LQ_ID.GOLD_BOWL, gujuo, log)
        outcome = 'quiet'
        if offered:
            outcome = yield from drive_blessing(blessed)
        if outcome == 'blessed':
            return True
        if needs_dose(outcome, skills.effective('prayer')):
            yield from drink_prayer(log)
        log(f"bowl on Gujuo {('sent' if offered else 'refused')} at {gujuo.tile().x},{gujuo.tile().z}, prayer {skills.effective('prayer')}/{skills.level('prayer')}, trance {outcome}")
        yield from settle_scene()
    log(f'Gujuo took the bowl {BLESS_ATTEMPTS} times and never blessed it')
    return blessed()


# Why: Starting at 99 Prayer can take 11 misses to reach the optimal 42; 20 attempts leave margin beyond that worst case.
BLESS_ATTEMPTS = 20
# Why: A miss drains 5 Prayer and closes the dialogue when that drops below Gujuo's level-42 gate.
BLESS_MS = 40000
# Why: The trance has 12 ticks of overhead dialogue with no widget, so shorter waits would retry before it resolves.
BLESS_IDLE_TICKS = 20
BLESS_MISSED = 'deep enough trance'
BLESS_REFUSED = 'too inexperienced'


def drive_blessing(blessed):
    """Drive Gujuo's trance, ending once it blesses the bowl or the conversation closes without it."""
    seen = {'opened': False, 'idle': 0, 'missed': False, 'refused': False}

    def ended():
        if blessed():
            return True
        said = modal_text()
        seen['missed'] = seen['missed'] or BLESS_MISSED in said
        seen['refused'] = seen['refused'] or BLESS_REFUSED in said
        if chat_dialog.is_open() or chat_dialog.can_continue() or modals.is_open():
            seen['opened'] = True
            seen['idle'] = 0
            return False
        seen['idle'] += 1
        return seen['opened'] and seen['idle'] >= BLESS_IDLE_TICKS

    # Why: `driveBoxes` checks between clicks, preserving the failure text that `driveChoice` would dismiss.
    yield from drive_boxes(ended, BLESS_MS, BLESS_PREFER)
    if blessed():
        return 'blessed'
    if seen['refused']:
        return 'refused'
    return 'missed' if seen['missed'] else 'quiet'


# Why: The stat block can lag by two ticks, so account for the 5-point miss and trust a server refusal immediately.
BLESS_MISS_COST = 5


def needs_dose(outcome, points):
    """Whether another attempt needs a Prayer dose."""
    if outcome == 'refused':
        return True
    return outcome == 'missed' and points - BLESS_MISS_COST < BLESS_FLOOR


BLESS_FLOOR = 42


# Why: The miss roll rises about 1.73 per Prayer point, from 3 in 5 at level 42 to 98 in 100 at level 99, so hold at the minimum.
def bless_prayer_floor():
    """Prayer target for each attempt."""
    return BLESS_FLOOR


def top_up_prayer(log):
    """Restore Prayer to Gujuo's minimum."""
    if skills.effective('prayer') >= bless_prayer_floor():
        return True
    drank = yield from drink_prayer(log)
    return drank


BOWL_ATTEMPTS = 6


# Why: The anvil has no ops, and failed forging can consume one or both bars, so retry while two remain.
def make_golden_bowl(log):
    """Hammer 2 gold bars into a golden bowl at the Tai Bwo Wannai anvil."""
    if held_id(LQ_ID.GOLD_BOWL) > 0:
        return True
    _w15 = yield from leave_jungle(log)
    if not (_w15):
        return False
    for i in range(BOWL_ATTEMPTS):
        if held_id(LQ_ID.GOLD_BOWL) > 0:
            return True
        if held_id(LQ_ID.GOLD_BAR) < 2:
            log('fewer than two gold bars left for the bowl')
            return False
        yield from use_on_loc(LQ_ID.GOLD_BAR, Record({'name': LQ_LOC.ANVIL, 'near': LQ_TILE.ANVIL}), ['Yes'], lambda: held_id(LQ_ID.GOLD_BOWL) > 0, log)
    return held_id(LQ_ID.GOLD_BOWL) > 0


def cut_reed(log):
    """Cut a hollow reed at the sacred pool; the knife and the machete both work."""
    if held_id(LQ_ID.HOLLOW_REED) > 0:
        return True
    _w16 = yield from enter_jungle(log)
    if not (_w16):
        return False
    tool = (LQ_ID.KNIFE if held_id(LQ_ID.KNIFE) > 0 else LQ_ID.MACHETE)
    _result17 = yield from use_on_loc(tool, Record({'name': LQ_LOC.TALL_REEDS, 'near': LQ_TILE.TALL_REEDS}), [], lambda: held_id(LQ_ID.HOLLOW_REED) > 0, log)
    return _result17


# Why: Only the reed reaches the water through the rocks, and siphoning consumes it.
def fill_bowl_from_pool(log):
    """Syphon the jungle pool into the blessed bowl."""
    if held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
        return True
    _w18 = yield from cut_reed(log)
    if not (_w18):
        return False
    _result19 = yield from use_on_loc(LQ_ID.HOLLOW_REED, Record({'name': LQ_LOC.SACRED_WATER, 'near': LQ_TILE.SACRED_POOL, 'id': LQ_LOC_ID.SACRED_WATER}), [], lambda: held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0, log)
    return _result19


# Why: Using the reed after germination advances the quest to `water_pool_dried_up`.
def find_pool_dried(log):
    """Touch the dried pool, which is what starts the hunt for the source."""
    _w20 = yield from cut_reed(log)
    if not (_w20):
        return False

    def dry():
        return loc_near(LQ_LOC.POLLUTED_WATER, 'Look', 8) is not None

    used = yield from use_on_loc(LQ_ID.HOLLOW_REED, Record({'name': LQ_LOC.SACRED_WATER, 'near': LQ_TILE.SACRED_POOL, 'id': LQ_LOC_ID.SACRED_WATER}), [], dry, log)
    return used or dry()


# Why: Use the west wall from its own tile; a nearby diagonal section crosses on the wrong axis.
def enter_octagram(log):
    """Douse the flames with pure water and step into the octagram."""
    if in_octagram(game.tile()):
        return True
    # Why: Trials pockets also report `shamanCaves`, so leave them before approaching the fire wall.
    _w21 = yield from climb_out_of_trials(log)
    if not (_w21):
        return False
    _w22 = yield from enter_shaman_cave(log)
    if not (_w22):
        return False
    _w23 = yield from traversal.walk_resilient(LQ_TILE.FIRE_WALL_WEST, radius=0, attempts=4, timeout_ms=120000, log=log)
    if not (_w23):
        return False
    yield from settle_scene()
    if held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
        splashed = yield from use_on_loc(LQ_ID.GOLD_BOWL_BLESSED_PURE, Record({'name': LQ_LOC.FIRE_WALL, 'near': LQ_TILE.FIRE_WALL_WEST, 'within': 2}), [], lambda: in_octagram(game.tile()), log)
        if splashed:
            yield from settle_scene()
            return True
    # Why: Chopping through the dense jungle empties the bowl, so fill it after the last crossing.
    if held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) == 0:
        log('no pure water in the bowl at the flames — the fill has to be the last thing before the cave, as crossing the band boils it off')
    # Why: After the demon dies, Touch crosses the flames without water; keep the attempt bounded because it cannot work earlier.
    touched = yield from prompt_loc(Record({
        'name': LQ_LOC.FIRE_WALL,
        'op': 'Touch',
        'near': LQ_TILE.FIRE_WALL_WEST,
        'within': 2,
        'expect': lambda: in_octagram(game.tile()),
        'expect_ms': 6000,
    }), log)
    if touched:
        yield from settle_scene()
    return touched


def summon_demon(log):
    """Open the Book of Binding in front of Ungadulu, which pulls the demon out of him."""
    _w24 = yield from enter_octagram(log)
    if not (_w24):
        return False
    _w25 = yield from traversal.walk_resilient(LQ_TILE.OCTAGRAM_INSIDE, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w25):
        return False
    yield from settle_scene()
    shaman = npcs.query().name(LQ_NPC.UNGADULU).within(10).nearest()
    if not shaman:
        log('no Ungadulu inside the octagram')
        return False
    _w26 = yield from offer_to(LQ_ID.BOOK_OF_BINDING, shaman, log)
    if not (_w26):
        return False
    _result27 = yield from execution.delay_until(lambda: npcs.query().name(LQ_NPC.NEZIKCHENED).within(12).exists(), 25000)
    return _result27


SEEDS_PREFER = ['I need to collect some Yommi tree seeds for Gujuo.', 'I need more Yommi tree seeds.', 'Ok, thanks...']


# Why: After the demon dies, Ungadulu lets the player enter without water.
def ask_for_seeds(log):
    """Ask the freed Ungadulu for the 3 Yommi tree seeds."""
    if held_id(LQ_ID.YOMMI_SEEDS) > 0 or held_id(LQ_ID.YOMMI_SEEDS_GERM) > 0:
        return True
    _w28 = yield from enter_octagram(log)
    if not (_w28):
        return False
    status = yield from reach.npc_dialog(LQ_NPC.UNGADULU, LQ_TILE.OCTAGRAM_INSIDE, log=log)
    if status != 'done':
        log('Ungadulu never opened a dialogue')
        return False
    _result29 = yield from drive_until(lambda: held_id(LQ_ID.YOMMI_SEEDS) > 0, SEEDS_PREFER, log, 90000)
    return _result29


GERMINATE_ATTEMPTS = 4


def close_chat(log):
    """Close the previous dialogue before sending another use-on."""
    if not chat_dialog.is_open() and not chat_dialog.can_continue():
        return
    yield from drive_until(lambda: not chat_dialog.is_open() and not chat_dialog.can_continue(), [], log, 8000)


def germinate_seeds(log):
    """Germinate the seeds in the bowl of pure water."""

    def done():
        return held_id(LQ_ID.YOMMI_SEEDS_GERM) > 0

    if done():
        return True
    for i in range(GERMINATE_ATTEMPTS):
        # Why: The server drops `opheldu` while Ungadulu's final dialogue page is open.
        yield from close_chat(log)
        yield from settle_scene()
        bowl = ([item for item in inventory.items() if item.id == LQ_ID.GOLD_BOWL_BLESSED_PURE] or [None])[0]
        seeds = ([item for item in inventory.items() if item.id == LQ_ID.YOMMI_SEEDS] or [None])[0]
        if not bowl or not seeds:
            log(f"pack holds {('the pure bowl' if bowl else f'bowls [{bowls_held()}]')} and {('the seeds' if seeds else 'no seeds')}")
            return False
        # Why: `opheldu` runs the second item's handler, which is defined on the bowl.
        sent = seeds.use_on(bowl)
        # Why: The germinated seeds are added only after `~doubleobjbox` is dismissed.
        if sent:
            germinated = yield from drive_until(done, [], log, 20000)
            if germinated:
                return True
        said = modal_text()[0:60]
        log(f"seeds on bowl {'sent' if sent else 'refused'}, chat \"{said}\"")
    return done()


def bowls_held():
    """Which bowls are in the pack, for when the pure one isn't."""
    names = [
        [LQ_ID.GOLD_BOWL, 'plain'],
        [LQ_ID.GOLD_BOWL_BLESSED, 'blessed'],
        [LQ_ID.GOLD_BOWL_WATER, 'water'],
        [LQ_ID.GOLD_BOWL_PURE, 'pure'],
        [LQ_ID.GOLD_BOWL_BLESSED_WATER, 'blessed+water'],
    ]
    return ', '.join([row[1] for row in names if held_id(row[0]) > 0]) or 'none'

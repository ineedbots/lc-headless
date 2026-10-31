"""Ported from rs2b0t's src/bot/api/ai/quests/defs/merlinscrystal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.engine.provisioning import gp_short
from rs2004.quests.exec.primitives import NpcStop, goto_npc, pick_preferred, talk_through
from rs2004.quests.food import FOOD_FLOAT
from rs2004.traversal import traversal
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['bread_plan', 'live_fortress_step', 'live_reset_mordred_brief', 'live_mordred_briefed', 'decide', 'merlinscrystal']

EXCALIBUR = 'Excalibur'
UNLIT_CANDLE = 'Black candle'
LIT_CANDLE = 'Lit black candle'
BAT_BONES = 'Bat bones'
WAX = 'Bucket of wax'
BUCKET = 'Bucket'
REPELLENT = 'Insect repellent'
BREAD = 'Bread'
TINDERBOX = 'Tinderbox'
WEAPON = 'Rune mace'
# Why: the 289 cache names him in full, and a query matches the whole name.
THRANTAX = 'Thrantax The Mighty'
KING_ARTHUR = NpcStop('King Arthur', Tile(2764, 3515, 0), 6, ['I want to become a Knight of the Round Table!'])
# Prefer fragments must match the strings in sir_gawain.rs2 / sir_lancelot.rs2.
GAWAIN = NpcStop('Sir Gawain', Tile(2761, 3508, 0), 6, [
    'Do you know how Merlin got trapped?',
    'Thank you for the information.',
    'Any idea how to get into Morgan Le Faye',
    'Any ideas on how to get Merlin out',
])
LANCELOT = NpcStop('Sir Lancelot', Tile(2755, 3511, 1), 8, ['Any ideas on how to get into Morgan Le Faye', 'I want to get Merlin out of the crystal'])
CAM_STAIR_L0 = Tile(2750, 3510, 0)
LADY_LAKE = NpcStop('The Lady of the Lake', Tile(2924, 3405, 0), 6, ['I seek the sword Excalibur.'])
CANDLE_MAKER = NpcStop('Candle maker', Tile(2800, 3439, 0), 6, ['Have you got any black candles?'])
CATHERBY_CRATE_STAND = Tile(2801, 3443, 0)


def inside_keep(t):
    return t.x >= 2762 and t.x <= 2782 and t.z >= 3396 and t.z <= 3410


mordred_briefed = False
MORDRED_TILE = Tile(2769, 3403, 2)
KEEP_STAIR_L0 = Tile(2769, 3404, 0)
KEEP_STAIR_L1_UP = Tile(2769, 3398, 1)
KEEP_STAIR_L2_DOWN = Tile(2769, 3399, 2)
RETURN_CRATE_STAND = Tile(2778, 3401, 0)
MAGIC_SYMBOL = Tile(2780, 3515, 0)
CHAOS_ALTAR_STAND = Tile(3239, 3607, 0)
TOWER_LADDER_0 = Tile(2769, 3493, 0)
TOWER_LADDER_1 = Tile(2767, 3491, 1)
CRYSTAL_STAND = Tile(2767, 3494, 2)
JEWELLER_DOOR_STAND = Tile(3016, 3247, 0)
BEEHIVE_STAND = Tile(2758, 3444, 0)
REPELLENT_SPAWN = Tile(2807, 3450, 0)
BAT_ANCHOR = Tile(2589, 3478, 0)
WYDIN_SHOP = Record({'npc': 'Wydin', 'anchor': Tile(3014, 3204, 0)})
RIMMINGTON_SHOP = Record({'npc': 'Shop keeper', 'anchor': Tile(2947, 3216, 0)})


def answer_is(option, word):
    """Whether the option is the word alone, with or without a full stop."""
    text = option.strip().lower()
    return text == word or text == word + '.'


def has(snap, name):
    return ((snap.inv.get(name.lower()) if snap.inv.get(name.lower()) is not None else 0)) > 0


def wield_weapon(log):
    if equipment.contains(WEAPON) or not inventory.contains(WEAPON):
        return
    _w1 = yield from equipment.equip(WEAPON)
    if _w1:
        log(f'wielded {WEAPON}')


def buy_or_wait(snap, step):
    if gp_short(snap, step.est_gp) > 0:
        return Record({'kind': 'wait', 'reason': f'need ~{step.est_gp} gp for {step.item}'})
    return step


# The East Ardougne Baker's stall has no bread in rev 274 and the beggar needs Bread, so buy from Wydin's in Port Sarim.
def bread_plan(snap, _thieving_level=0, _passes_used=0):
    return buy_or_wait(snap, Record({'kind': 'buy', 'item': 'Bread', 'qty': 1, 'shop': WYDIN_SHOP, 'est_gp': 20}))


def drive_dialogue(prefer, log, max_pages=60):
    for i in range(max_pages):
        if not ((chat_dialog.is_open() or chat_dialog.can_continue())):
            break
        if event_signal.pending():
            return
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        opts = chat_dialog.options()
        if len(opts) > 0:
            pick = pick_preferred(opts, prefer)
            if not pick:
                log(f"  driveDialogue: no preferred option in [{' | '.join(opts)}] — taking the last")
            yield from chat_dialog.choose_option((pick if pick is not None else opts[len(opts) - 1]))
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_ticks(1)


def climb_at(stand, op, log):
    _w2 = yield from traversal.walk_resilient(stand, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w2):
        return False
    stair = locs.query().action(op).within(4).nearest()
    if not stair:
        log(f'climbAt: no \'{op}\' near ({stand.x},{stand.z}) — LIVE-VERIFY the stair')
        return False
    _v3 = (game.tile().level if game.tile() is not None else None)
    before = (_v3 if _v3 is not None else stand.level)
    if not (stair.interact(op)):
        return False
    _w4 = yield from execution.delay_until(lambda: (((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else before)) != before, 6000)
    if not (_w4):
        return False
    yield from execution.delay_ticks(2)
    return True


def descend_tower(log):
    for guard in range(4):
        if not ((((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else 0)) > 0):
            break

        def find():
            return locs.query().name('Ladder').action('Climb-down').within(6).nearest()

        yield from execution.delay_until(lambda: find() is not None, 2000)
        down = find()
        if not down:
            log('descendTower: no Climb-down ladder in range')
            return False
        _v5 = (game.tile().level if game.tile() is not None else None)
        before = (_v5 if _v5 is not None else 0)
        if not (down.interact('Climb-down')):
            return False
        _w6 = yield from execution.delay_until(lambda: (((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else before)) < before, 6000)
        if not (_w6):
            return False
        yield from execution.delay_ticks(2)
    _v7 = (game.tile().level if game.tile() is not None else None)
    return ((_v7 if _v7 is not None else 0)) == 0


def ensure_camelot_l1(log):
    _v8 = (game.tile().level if game.tile() is not None else None)
    if ((_v8 if _v8 is not None else 0)) >= 1:
        return True
    _w9 = yield from traversal.walk_resilient(CAM_STAIR_L0, radius=1, attempts=4, timeout_ms=120000, log=log)
    if not (_w9):
        return False
    _result10 = yield from climb_at(CAM_STAIR_L0, 'Climb-up', log)
    return _result10


def talk_knights(log):
    # Gawain (L0) first, Lancelot's fortress option only appears after spoken_gawain.
    for knight in [GAWAIN, LANCELOT]:
        done = False
        for attempt in range(5):
            if event_signal.pending():
                return
            _c11 = knight.npc == 'Sir Lancelot'
            if _c11:
                _w12 = yield from ensure_camelot_l1(log)
                _c11 = not (_w12)
            if _c11:
                log(f'talkKnights: could not climb to Lancelot\'s floor (attempt {attempt + 1})')
                continue
            # Live tile beats a stale anchor when knights wander rooms.
            live = npcs.query().name(knight.npc).action('Talk-to').nearest()
            here = game.tile()
            if live and here:
                tile = live.tile()
                if tile.level == here.level and tile.distance_to(here) > 1:
                    yield from traversal.walk_resilient(tile, radius=1, attempts=3, timeout_ms=60000, log=log)
            elif not live:
                _w13 = yield from goto_npc(knight, [], log)
                if not (_w13):
                    log(f'talkKnights: \'{knight.npc}\' not in scene — walking to anchor (attempt {attempt + 1})')
                    yield from traversal.walk_resilient(knight.anchor, radius=2, attempts=3, timeout_ms=90000, log=log)
                    continue
            _w14 = yield from talk_through(knight.npc, knight.prefer, log)
            if _w14:
                log(f'talkKnights: \'{knight.npc}\' dialogue done')
                done = True
                break
            log(f'talkKnights: \'{knight.npc}\' talk failed (attempt {attempt + 1})')
        if not done:
            log(f'talkKnights: giving up on \'{knight.npc}\' this pass')


def candle_maker_stage_four(log):
    _w15 = yield from goto_npc(CANDLE_MAKER, [], log)
    if not (_w15):
        return False
    npc = npcs.query().name('Candle maker').action('Talk-to').nearest()
    if not npc or not (npc.interact('Talk-to')):
        return False
    _w16 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w16):
        return False
    stage4 = False
    for i in range(40):
        if not ((chat_dialog.is_open() or chat_dialog.can_continue())):
            break
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        opts = chat_dialog.options()
        if len(opts) > 0:
            if any([('black candles' in o.lower()) for o in opts]):
                stage4 = True
                yield from chat_dialog.choose_option('black candles')
            else:
                yield from chat_dialog.choose_option('No thank you')
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_ticks(1)
    # Only succeed once Morgan is briefed and the black-candle option appears; treating an empty dialogue as success skipped the fortress.
    return stage4


def fortress(log):
    global mordred_briefed
    t = game.tile()
    if not t:
        return False
    # After Morgan's brief the keep is done, never re-board the Catherby crate.
    if mordred_briefed and not inside_keep(t):
        log('fortress: Morgan brief already done and outside the keep')
        return True
    if not inside_keep(t):
        _w17 = yield from traversal.walk_resilient(CATHERBY_CRATE_STAND, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w17):
            return False
        crate = locs.query().name('Crate').action('Hide-in').within(6).nearest()
        if not crate:
            log('fortress: no Catherby Crate to Hide-in')
            return False
        if not (crate.interact('Hide-in')):
            return False
        yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 6000)
        yield from drive_dialogue(['Yes.'], log, 40)

        def _fn18():
            g = game.tile()
            return g is not None and inside_keep(g)
        boarded = yield from execution.delay_until(_fn18, 12000)
        log(f'fortress: crate Hide-in -> insideKeep={boarded} (needs stage>=spoken_lancelot to teleport)')
        return False
    # Why: the dialogue and the Morgan brief outrank Attack, as Mordred stays attackable after the fight ends and re-Attack loops without latching "briefed" (#353).
    # Why: "Yes." is last so crate Hide-in confirms never fall through to No.
    MORGAN_OR_CRATE = [
        'Tell me how to untrap Merlin and I might.',
        'OK I will go do all that.',
        'Tell me how to untrap Merlin',
        'I will go do all that',
        'Yes.',
    ]
    if chat_dialog.is_open() or chat_dialog.can_continue():
        opts = chat_dialog.options()
        crate_confirm = any([answer_is(o, 'yes') for o in opts]) and any([answer_is(o, 'no') for o in opts])
        yield from drive_dialogue((['Yes.'] if crate_confirm else MORGAN_OR_CRATE), log)
        if not crate_confirm:
            mordred_briefed = True
            log('fortress: Morgan brief done — leaving keep (no re-attack)')
        yield from leave_keep(log)
        return False
    if mordred_briefed:
        log('fortress: already briefed by Morgan — leaving keep')
        yield from leave_keep(log)
        return False
    _v19 = (game.tile().level if game.tile() is not None else None)
    lvl = (_v19 if _v19 is not None else 0)
    if lvl < 2:
        if lvl < 1:
            yield from climb_at(KEEP_STAIR_L0, 'Climb-up', log)
        else:
            yield from climb_at(KEEP_STAIR_L1_UP, 'Climb-up', log)
        return False
    _w20 = yield from traversal.walk_resilient(MORDRED_TILE, radius=5, attempts=3, timeout_ms=60000, log=log)
    if not (_w20):
        return False
    # Dialog may have opened while walking up.
    if chat_dialog.is_open() or chat_dialog.can_continue():
        yield from drive_dialogue(MORGAN_OR_CRATE, log)
        mordred_briefed = True
        yield from leave_keep(log)
        return False
    yield from wield_weapon(log)
    game.set_combat_style('strength')
    mordred = npcs.query().name('Sir Mordred').action('Attack').within(8).nearest()
    if mordred:
        here = game.tile()
        if here and mordred.tile().distance_to(here) > 1:
            yield from traversal.walk_resilient(mordred.tile(), radius=1, attempts=2, timeout_ms=20000, log=log)
        mordred.interact('Attack')
        # Why: the wait watches for dialogue every tick and covers combat ending too, so a fight that ended with no dialogue leaves the flag false and the next call may re-engage once.
        for i in range(40):
            if not (not mordred_briefed):
                break
            if chat_dialog.is_open() or chat_dialog.can_continue():
                yield from drive_dialogue(MORGAN_OR_CRATE, log)
                mordred_briefed = True
                break
            if not game.in_combat() and i > 4:
                # Combat ended with no dialog yet; give Morgan a moment.
                yield from execution.delay_ticks(2)
                if chat_dialog.is_open() or chat_dialog.can_continue():
                    continue
                break
            yield from execution.delay_ticks(2)
            yield from sustain.run()
        if mordred_briefed:
            log('fortress: Morgan brief after Mordred fight — leaving keep')
            yield from leave_keep(log)
    return False


def leave_keep(log):
    here = game.tile()
    if here and not inside_keep(here):
        return True
    # Mordred is L2; the exit crate is ground-floor (keep_crate_coord). Descend fully first.
    for guard in range(4):
        if not ((((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else 0)) > 0):
            break
        _v21 = (game.tile().level if game.tile() is not None else None)
        level = (_v21 if _v21 is not None else 0)
        down = locs.query().name('Staircase').action('Climb-down').within(8).nearest()
        if down:
            if not (down.interact('Climb-down')):
                return False
            _w22 = yield from execution.delay_until(lambda: (((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else level)) < level, 8000)
            if not (_w22):
                return False
            yield from execution.delay_ticks(2)
            continue
        stand = (KEEP_STAIR_L2_DOWN if level >= 2 else KEEP_STAIR_L1_UP)
        log(f'leaveKeep: no Climb-down on L{level} — walking to stair ({stand.x},{stand.z})')
        yield from traversal.walk_resilient(stand, radius=2, attempts=3, timeout_ms=60000, log=log)
        return False
    here = game.tile()
    if not here or here.level > 0:
        return False
    if not inside_keep(here):
        return True
    # Prefer the Arhein crate ride home (a mesbox plus a Yes/No header).
    if RETURN_CRATE_STAND.distance_to(here) > 2:
        yield from traversal.walk_resilient(RETURN_CRATE_STAND, radius=2, attempts=2, timeout_ms=45000, log=log)
    crate = locs.query().name('Crate').action('Hide-in').within(6).nearest()
    if crate:
        crate.interact('Hide-in')
        yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 6000)
        for i in range(40):
            if not ((chat_dialog.is_open() or chat_dialog.can_continue())):
                break
            if event_signal.pending():
                break
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
                yield from execution.delay_ticks(1)
                continue
            opts = chat_dialog.options()
            if len(opts) > 0:
                yes = ([o for o in opts if answer_is(o, 'yes')] or [opts[0]])[0]
                yield from chat_dialog.choose_option(yes)
                yield from execution.delay_ticks(2)
                continue
            yield from execution.delay_ticks(1)

        # Crate ride is a multi-mesbox teleport sequence, give it time.
        def _fn24():
            g = game.tile()
            return g is not None and not inside_keep(g)
        yield from execution.delay_until(_fn24, 25000)
        here = game.tile()
        if here and not inside_keep(here):
            log('leaveKeep: crate ride out of the keep')
            return True
        log('leaveKeep: crate Hide-in did not leave the keep')
    # The front door is the west Large door the crate entry uses; the keep box is x 2762..2782, so the exit is west of 2762.
    log('leaveKeep: walking west out the keep door')
    KEEP_WEST_EXIT = Tile(2758, 3401, 0)
    for attempt in range(8):
        here = game.tile()
        if here and not inside_keep(here):
            return True
        door = locs.query().name('Large door').action('Open').within(6).nearest()
        if door:
            door.interact('Open')
            yield from execution.delay_ticks(2)
        yield from traversal.walk_resilient(KEEP_WEST_EXIT, radius=1, attempts=2, timeout_ms=30000, log=log)
    here = game.tile()
    return here is not None and not inside_keep(here)


def opening_leg(log):
    t = game.tile()
    if t and inside_keep(t):
        _result25 = yield from fortress(log)
        return _result25
    if mordred_briefed:
        # Keep is done. Don't thrash the candle maker every tick; decide() does the wax exchange once bones/wax are in the pack.
        _result26 = yield from kill_giant_bat(log)
        return _result26
    if t and BAT_ANCHOR.distance_to(t) <= 25:
        _result27 = yield from kill_giant_bat(log)
        return _result27
    yield from talk_knights(log)
    _w28 = yield from candle_maker_stage_four(log)
    if _w28:
        _result29 = yield from kill_giant_bat(log)
        return _result29
    _result30 = yield from fortress(log)
    return _result30


def kill_giant_bat(log):
    if inventory.contains(BAT_BONES):
        return True
    drop = ground_items.query().name(BAT_BONES).within(6).nearest()
    if drop:
        if not (drop.interact('Take')):
            return False
        _result31 = yield from execution.delay_until(lambda: inventory.contains(BAT_BONES), 6000)
        return _result31
    _w32 = yield from traversal.walk_resilient(BAT_ANCHOR, radius=6, attempts=3, timeout_ms=120000, log=log)
    if not (_w32):
        return False
    yield from wield_weapon(log)
    game.set_combat_style('strength')
    bat = npcs.query().name('Giant bat').action('Attack').within(10).nearest()
    if not bat:
        log('killGiantBat: no Giant bat near the anchor — LIVE-VERIFY the spawn is reachable')
        return False
    bat.interact('Attack')
    yield from execution.delay_until(lambda: ground_items.query().name(BAT_BONES).within(6).nearest() is not None or npcs.query().name('Giant bat').within(2).nearest() is None, 5000)
    yield from sustain.run()
    return False


def get_wax(log):
    if inventory.contains(WAX):
        return True
    if not inventory.contains(REPELLENT):
        rep = ground_items.query().name(REPELLENT).within(8).nearest()
        if rep:
            if not (rep.interact('Take')):
                return False
            _result33 = yield from execution.delay_until(lambda: inventory.contains(REPELLENT), 6000)
            return _result33
        yield from traversal.walk_resilient(REPELLENT_SPAWN, radius=2, attempts=3, timeout_ms=90000, log=log)
        return False
    if not inventory.contains(BUCKET):
        log('getWax: no empty Bucket (should be provisioned) — parking to re-provision')
        return False
    _w34 = yield from traversal.walk_resilient(BEEHIVE_STAND, radius=2, attempts=3, timeout_ms=90000, log=log)
    if not (_w34):
        return False
    hive = locs.query().name('Beehive').action('Take-from').within(8).nearest()
    if not hive:
        log('getWax: no Beehive near the anchor')
        return False
    rep = inventory.first(REPELLENT)
    if rep:
        rep.use_on(hive)
        yield from execution.delay_ticks(2)
    bucket = inventory.first(BUCKET)
    if bucket:
        bucket.use_on(hive)
    _result35 = yield from execution.delay_until(lambda: inventory.contains(WAX), 8000)
    return _result35


def light_candle(log):
    if inventory.contains(LIT_CANDLE):
        return True
    tinder = inventory.first(TINDERBOX)
    candle = inventory.first(UNLIT_CANDLE)
    if not tinder or not candle:
        log('lightCandle: missing Tinderbox or Black candle')
        return False
    if not (tinder.use_on(candle)):
        return False
    _result36 = yield from execution.delay_until(lambda: inventory.contains(LIT_CANDLE), 6000)
    return _result36


def get_excalibur(log):
    if inventory.contains(EXCALIBUR):
        return True
    _w37 = yield from goto_npc(LADY_LAKE, [], log)
    if _w37:
        yield from talk_through('The Lady of the Lake', LADY_LAKE.prefer, log)
    if not inventory.contains(BREAD):
        log('getExcalibur: no Bread for the Beggar (should be provisioned)')
        return False
    _w38 = yield from traversal.walk_resilient(JEWELLER_DOOR_STAND, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w38):
        return False
    beggar = npcs.query().name('Beggar').action('Talk-to').within(6).nearest()
    if beggar:
        yield from talk_through('Beggar', ['Yes, here you go.', 'Yes certainly.'], log)
    else:
        door = locs.query().name('Door').action('Open').within(6).nearest()
        if not door:
            log('getExcalibur: no jeweller Door to Open')
            return False
        if not (door.interact('Open')):
            return False
        _w39 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
        if not (_w39):
            log('getExcalibur: jeweller door opened but the Beggar dialogue never appeared — retry')
            return False
        yield from drive_dialogue(['Yes certainly.', 'Yes, here you go.'], log)
    return inventory.contains(EXCALIBUR)


def summon_and_break(log):
    outcome = yield from try_break_crystal(log)
    if outcome == 'fail':
        return False
    yield from descend_tower(log)
    if outcome == 'broke':
        _w40 = yield from goto_npc(KING_ARTHUR, [], log)
        if not (_w40):
            return False
        yield from talk_through('King Arthur', KING_ARTHUR.prefer, log)
        return True
    yield from summon_thrantax(log)
    return False


def try_break_crystal(log):
    _v42 = (game.tile().level if game.tile() is not None else None)
    _c41 = ((_v42 if _v42 is not None else 0)) < 1
    if _c41:
        _w43 = yield from climb_at(TOWER_LADDER_0, 'Climb-up', log)
        _c41 = not (_w43)
    if _c41:
        return 'fail'
    _v45 = (game.tile().level if game.tile() is not None else None)
    _c44 = ((_v45 if _v45 is not None else 0)) < 2
    if _c44:
        _w46 = yield from climb_at(TOWER_LADDER_1, 'Climb-up', log)
        _c44 = not (_w46)
    if _c44:
        return 'fail'
    _w47 = yield from traversal.walk_resilient(CRYSTAL_STAND, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w47):
        return 'fail'

    def crystal_q():
        return locs.query().name('Giant crystal').within(8).nearest()

    def scene_synced():
        return locs.query().name('Ladder').action('Climb-down').within(8).nearest() is not None

    yield from execution.delay_until(lambda: crystal_q() is not None or scene_synced(), 3000)
    crystal = crystal_q()
    if not crystal:
        if not scene_synced():
            log('tryBreakCrystal: scene not synced on L2 — retrying')
            return 'fail'
        return 'broke'
    excal = inventory.first(EXCALIBUR)
    if not excal:
        log('tryBreakCrystal: no Excalibur to break the crystal')
        return 'fail'
    excal.use_on(crystal)
    yield from execution.delay_ticks(3)
    gone = locs.query().name('Giant crystal').within(8).nearest() is None or npcs.query().name('Merlin').within(8).nearest() is not None
    return ('broke' if gone else 'need-summon')


def summon_thrantax(log):
    _w48 = yield from traversal.walk_resilient(CHAOS_ALTAR_STAND, radius=2, attempts=4, timeout_ms=180000, log=log)
    if not (_w48):
        return False
    altar = locs.query().name('Chaos altar').action('Check').within(8).nearest()
    if altar:
        altar.interact('Check')
        yield from execution.delay_ticks(2)
    _w49 = yield from traversal.walk_resilient(MAGIC_SYMBOL, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w49):
        return False
    _c50 = not inventory.contains(LIT_CANDLE)
    if _c50:
        _w51 = yield from light_candle(log)
        _c50 = not (_w51)
    if _c50:
        return False
    bones = inventory.first(BAT_BONES)
    if not bones:
        log('summonThrantax: no Bat bones')
        return False
    if not (bones.interact('Drop')):
        return False
    _w52 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue() or npcs.query().name(THRANTAX).within(6).nearest() is not None, 6000)
    if not (_w52):
        log('summonThrantax: Thrantax did not appear (words not learned, or off the symbol?)')
        return False
    yield from drive_dialogue(['Snarthon Candtrick Termanto'], log)
    return True


def live_fortress_step(log):
    """Live harness surface for #353, calls the same fortress() product path."""
    _result53 = yield from fortress(log)
    return _result53


def live_reset_mordred_brief():
    global mordred_briefed
    mordred_briefed = False


def live_mordred_briefed():
    return mordred_briefed


def decide(snap):
    global mordred_briefed
    if snap.journal == 'complete':
        mordred_briefed = False
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        mordred_briefed = False
        return Record({'kind': 'talk', 'stop': KING_ARTHUR})
    has_excalibur = has(snap, EXCALIBUR)
    has_unlit = has(snap, UNLIT_CANDLE)
    has_lit = has(snap, LIT_CANDLE)
    has_bones = has(snap, BAT_BONES)
    has_wax = has(snap, WAX)
    any_product = has_excalibur or has_unlit or has_lit or has_bones or has_wax
    if not any_product:
        return Record({'kind': 'custom', 'name': 'opening (knights + fortress)', 'run': opening_leg})
    if not has_bones:
        return Record({'kind': 'custom', 'name': 'kill a Giant bat for bones', 'run': kill_giant_bat})
    if not has_unlit and not has_lit and not has_wax:
        return Record({'kind': 'custom', 'name': 'gather wax for the black candle', 'run': get_wax})
    if has_wax and not has_unlit and not has_lit:
        return Record({'kind': 'talk', 'stop': CANDLE_MAKER})
    if has_unlit and not has_lit:
        return Record({'kind': 'custom', 'name': 'light the black candle', 'run': light_candle})
    if not has_excalibur:
        return Record({'kind': 'custom', 'name': 'get Excalibur (Lady of the Lake + Beggar)', 'run': get_excalibur})
    return Record({'kind': 'custom', 'name': 'summon Thrantax + break the crystal', 'run': summon_and_break})


merlinscrystal = QuestModule(**{
    'record': quest_record('arthur'),
    'bank': Tile(2725, 3491, 0),
    'food': FOOD_FLOAT,
    # Why: the engine calls gather(snap, need), where rs2b0t's JavaScript drops the arguments these don't name.
    'gather': {
        'insect repellent': lambda s, need: Record({'kind': 'grab_ground', 'item': 'Insect repellent', 'anchor': REPELLENT_SPAWN}),
        'bread': lambda s, need: bread_plan(s),
        'tinderbox': lambda s, need: buy_or_wait(s, Record({'kind': 'buy', 'item': 'Tinderbox', 'qty': 1, 'shop': RIMMINGTON_SHOP, 'est_gp': 15})),
        'bucket': lambda s, need: buy_or_wait(s, Record({'kind': 'buy', 'item': 'Bucket', 'qty': 1, 'shop': RIMMINGTON_SHOP, 'est_gp': 15})),
    },
    'tools': [
    'excalibur',
    'black candle',
    'lit black candle',
    'bat bones',
    'bucket of wax',
    'bucket',
    'insect repellent',
    'bread',
    'tinderbox',
    'coins',
    'rune mace',
],
    'decide': decide,
})

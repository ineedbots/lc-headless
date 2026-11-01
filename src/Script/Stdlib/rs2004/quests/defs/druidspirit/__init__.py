"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidspirit/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.fightarena import KIT_KEEP, KIT_SLOTS, kit_wanted, wearing_kind
from rs2004.quests.defs.fightarena.legs import wear_kit
from rs2004.quests.defs.druidspirit.areas import BLOOM_MAX_COST, DREZEL, NS_HOPS, NS_ID, NS_STAGE, in_grotto
from rs2004.quests.defs.druidspirit.camp import ask_to_help, bloom_with_scroll, feed_stones, journal_leg, mirror_leg, solve_puzzle, talk_filliman
from rs2004.quests.defs.druidspirit.ghasts import bloom_with_sickle, fill_pouch, kill_ghast
from rs2004.quests.defs.druidspirit.grotto import bless_sickle, enter_grotto, exit_after_quest, leave_grotto, recharge_prayer, talk_in_grotto
from rs2004.quests.defs.druidspirit.journal import NS_FLAG, read_druid_progress
from rs2004.quests.defs.druidspirit.supplies import NS_TOOLS, amulet, banked_id, held_id, sickle_step

__all__ = ['decide', 'druidspirit']


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


GHOST_TOPIC = "I'm wearing an amulet of ghost speak!"
ANOTHER_SCROLL = 'Could I have another bloom scroll please?'
THANKS = ['Ok thanks.', 'Ok, thanks.']


def harvest_held(snap):
    return held_id(snap, NS_ID.PEAR) + held_id(snap, NS_ID.STEM) + held_id(snap, NS_ID.FUNGI)


# Why: the grotto is sealed, so a surface step taken from inside walks at a tile with no route.
def outside(snap, step):
    """Leave the pocket before any step that acts outside it."""
    return (custom('leave the grotto', leave_grotto) if in_grotto(snap.tile) else step)


# Why: the bloomed log reverts 25 ticks after it grows, so a resume with no fungus casts again.
def fungus(snap):
    """A fungus in the pack, by whatever route is open."""
    if held_id(snap, NS_ID.SPELL) == 0:
        return custom('ask for another bloom scroll', lambda log: talk_filliman(ANOTHER_SCROLL, log))
    return custom('bloom the swamp for a fungus', bloom_with_scroll)


def ritual(snap):
    _v1 = (snap.progress.flags if snap.progress is not None else None)
    flags = (_v1 if _v1 is not None else set())
    if not (NS_FLAG.NATURE in flags) and held_id(snap, NS_ID.FUNGI) == 0:
        return fungus(snap)
    if not (NS_FLAG.NATURE in flags) or not (NS_FLAG.SPIRIT in flags):
        return custom('feed the ritual stones', lambda log: feed_stones(flags, log))
    return custom('solve the ritual', solve_puzzle)


def count_of(counts, name):
    count = None if counts is None else counts.get(name.lower())
    return count if count is not None else 0


# Why: the ghasts are fought with whatever is worn, and a queue that ran Tai Bwo Wannai Trio first left its bow on with
# the quiver empty, so every attack after the pouch made a ghast visible failed on "There is no ammo left in your
# quiver." The melee kit is drawn as Shades of Mort'ton draws it. This departs from rs2b0t.
def melee_kit(snap):
    """Arm the account from the bank for the ghasts, or null once it is dressed."""
    wanted = kit_wanted(snap)
    carried = [name for name in wanted if count_of(snap.inv, name) > 0]
    if len(carried) > 0:
        return custom(f"wear {', '.join(carried)}", lambda log: wear_kit(carried, log))
    # Why: kit_wanted offers only what the snapshot's bank holds, which a session that hasn't read it yet holds none of.
    if not snap.bank_known and any([not wearing_kind(snap, slot.kinds) for slot in KIT_SLOTS]):
        return Record({'kind': 'scan_bank'})
    banked = [name for name in wanted if count_of(snap.bank, name) > 0]
    return Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': 1} for name in banked]}) if len(banked) > 0 else None


def ghast_loop(snap):
    """Bloom, fill, hunt, the loop the last 4 stages share."""
    if held_id(snap, NS_ID.SICKLE_BLESSED) == 0:
        if held_id(snap, NS_ID.SICKLE) > 0:
            return custom('bless the sickle', bless_sickle)
        fetch = sickle_step(snap)
        return (fetch if fetch is not None else custom('bless the sickle', bless_sickle))
    if held_id(snap, NS_ID.POUCH) > 0:
        kit = melee_kit(snap)
        return kit if kit is not None else custom('kill a ghast', kill_ghast)
    if held_id(snap, NS_ID.POUCH_EMPTY) == 0:
        if not snap.bank_known:
            return Record({'kind': 'scan_bank'})
        for id in [NS_ID.POUCH, NS_ID.POUCH_EMPTY]:
            count = banked_id(snap, id)
            if count > 0:
                return Record({
                    'kind': 'withdraw',
                    'items': [{'name': 'Druid pouch', 'id': id, 'qty': (min(3, count) if id == NS_ID.POUCH else 1)}],
                })
        return Record({'kind': 'wait', 'reason': 'no Druid pouch held or banked'})
    if harvest_held(snap) >= 3:
        return custom('fill the druid pouch', fill_pouch)
    # Why: only the bloom costs prayer (pouch fills and ghast kills are free), so the altar trip is taken here only.
    if (snap.prayer if snap.prayer is not None else BLOOM_MAX_COST) < BLOOM_MAX_COST:
        return custom('recharge prayer at the Paterdomus altar', recharge_prayer)
    return custom('harvest natures bounty', bloom_with_sickle)


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v2 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v2 if _v2 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    # Why: Both spirits require the amulet; equipping it before starting avoids an extra Lumbridge round trip.
    wearing = amulet(snap)
    if wearing:
        return outside(snap, wearing)
    if stage == NS_STAGE.NOT_STARTED:
        return outside(snap, Record({'kind': 'talk', 'stop': DREZEL}))
    if stage in [NS_STAGE.STARTED, NS_STAGE.ENTERED_SWAMP, NS_STAGE.FAILED_TALK]:
        return outside(snap, custom('find Filliman', lambda log: talk_filliman(GHOST_TOPIC, log)))
    elif stage == NS_STAGE.SPOKEN_FILLIMAN:
        return outside(snap, custom('mirror', mirror_leg))
    elif stage == NS_STAGE.SHOWN_MIRROR:
        return outside(snap, custom("Tarlock's journal", journal_leg))
    elif stage == NS_STAGE.GIVEN_JOURNAL:
        return outside(snap, custom('offer to help', ask_to_help))
    elif stage == NS_STAGE.RECEIVED_SPELL:
        return outside(snap, Record({'kind': 'talk', 'stop': DREZEL}))
    elif stage in [NS_STAGE.BLESSED, NS_STAGE.CASTED_SPELL, NS_STAGE.PICKED_FUNGI, NS_STAGE.SPOKEN_FILLIMAN2]:
        return outside(snap, ritual(snap))
    elif stage == NS_STAGE.PERFORMED_RITUAL:
        return custom('enter the grotto', enter_grotto)
    elif stage == NS_STAGE.ENTERED_GROTTO:
        return custom('watch the transformation', lambda log: talk_in_grotto(THANKS, log))
    elif stage == NS_STAGE.FULL_TRANSFORM:
        if held_id(snap, NS_ID.SICKLE) > 0 or held_id(snap, NS_ID.SICKLE_BLESSED) > 0:
            return custom('hand over the sickle', lambda log: talk_in_grotto(THANKS, log))
        fetch = sickle_step(snap)
        return (outside(snap, fetch) if fetch else custom('hand over the sickle', lambda log: talk_in_grotto(THANKS, log)))
    elif stage in [NS_STAGE.BLESSED_SICKLE, NS_STAGE.CASTED_SICKLE_BLOOM, NS_STAGE.PICKED_SICKLE, NS_STAGE.ADDED_POUCH, NS_STAGE.KILLED_GHAST1, NS_STAGE.KILLED_GHAST2]:
        return outside(snap, ghast_loop(snap))
    elif stage == NS_STAGE.KILLED_GHAST3:
        return custom('claim the reward', lambda log: talk_in_grotto(THANKS, log))
    else:
        return Record({'kind': 'done'})


druidspirit = QuestModule(**{
    'record': quest_record('druidspirit'),
    # Paterdomus, the swamp and Al Kharid: pinning one booth costs a kingdom crossing on the sickle leg.
    'bank': 'nearest',
    'tools': list(NS_TOOLS) + list(KIT_KEEP),
    'owns_inventory': True,
    'hops': NS_HOPS,
    'read_progress': read_druid_progress,
    'exit': exit_after_quest,
    'decide': decide,
})

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/pack.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_TILE, banked, carried

__all__ = ['manage_pack']

# Why: The bankless middle has incompatible slot needs, so each leg declares its pack before entering the pass.
# Why: a plan is a whitelist plus a set of counts, because the deposit step can't keep a partial stack. An item with a target is left out of the deposit and drawn back, which settles in 3 cycles: shed, draw, done.
# Why: Plans are whitelists; keep replaceable quest items by default because replacing one can require another full pass crossing.
# Why: Iorwerth's letter is here only while it's owed to King Lathas: his reward branch reads it out of the pack and the quest is over, after which it's a slot, so a plan naming it in `shed` drops it.
# Why: Receiving the King's message advances the stage immediately, and no later script consumes it, so keeping it wastes a slot.
KEEP_BY_DEFAULT = [
    RG_ITEM.MESSAGE.id,
    RG_ITEM.PENDANT.id,
    RG_ITEM.BARREL.id,
    RG_ITEM.BARREL_TAR.id,
    RG_ITEM.BARREL_NAPHTHA.id,
    RG_ITEM.BARREL_LID.id,
    RG_ITEM.BARREL_FUSED.id,
    RG_ITEM.MIX_QUICKLIME.id,
    RG_ITEM.MIX_SULPHUR.id,
    RG_ITEM.CLOTH.id,
    RG_ITEM.SULPHUR_DUST.id,
    RG_ITEM.QUICKLIME_DUST.id,
    RG_ITEM.RAW_RABBIT.id,
    RG_ITEM.COOKED_RABBIT.id,
]


def capped(plan, id):
    return any([cap.item.id == id for cap in ((plan.caps if plan.caps is not None else []))])


def allowed(plan):
    """Everything the plan allows, plus what's too expensive to replace to shed by accident."""
    shed = set((plan.shed if plan.shed is not None else []))
    return list(plan.allow) + list([id for id in KEEP_BY_DEFAULT if not (id in shed)])


def holds_junk(snap, plan):
    """True when the pack holds something this leg has no use for."""
    allow = set(allowed(plan))
    for id, count in (snap.inv_ids if snap.inv_ids is not None else {}).items():
        if count > 0 and not (id in allow) and not capped(plan, id):
            return True
    return False


def over_cap(snap, plan):
    """The first item held over its target, or null when every count is at or under it."""
    over = [cap for cap in (plan.caps if plan.caps is not None else []) if carried(snap, cap.item) > cap.qty]
    return over[0].item if len(over) > 0 else None


def under_cap(snap, plan):
    """The first item held below its target that the bank can still supply."""
    for cap in (plan.caps if plan.caps is not None else []):
        have = carried(snap, cap.item)
        if have < cap.qty and banked(snap, cap.item) > 0:
            return Record({'item': cap.item, 'qty': min(cap.qty - have, banked(snap, cap.item))})
    return None


def manage_pack(snap, plan):
    """Shape the pack to `plan`, or null once it already fits. Why: shed first, then draw. The other way round asks the bank for slots the pack hasn't freed yet, and a withdraw into a full pack is silent."""
    if not snap.bank_known:
        return Record({'kind': 'scan_bank', 'bank': RG_TILE.ARDOUGNE_BANK})
    shedding = over_cap(snap, plan)
    if holds_junk(snap, plan) or shedding is not None:
        # Why: the item being trimmed is left out of the keep list, because the deposit is all-or-nothing per item: it goes to the bank in full and comes back at its target next cycle.
        keep_ids = (list(allowed(plan)) + list([cap.item.id for cap in ((plan.caps if plan.caps is not None else []))]) if shedding is None else list(allowed(plan)) + list([cap.item.id for cap in [cap for cap in ((plan.caps if plan.caps is not None else [])) if cap.item.id != shedding.id]]))
        return Record({'kind': 'deposit', 'keep': [], 'keep_ids': keep_ids, 'bank': RG_TILE.ARDOUGNE_BANK})
    drawing = under_cap(snap, plan)
    if drawing is not None:
        return Record({
            'kind': 'withdraw',
            'items': [{'name': drawing.item.name, 'id': drawing.item.id, 'qty': drawing.qty}],
            'bank': RG_TILE.ARDOUGNE_BANK,
        })
    free = (snap.free_slots if snap.free_slots is not None else 28)
    if plan.free_needed is not None and free < plan.free_needed:
        return Record({
            'kind': 'wait',
            'reason': f'{plan.what} needs {plan.free_needed} free slot(s) and the pack has {free} — nothing left to bank',
        })
    return None


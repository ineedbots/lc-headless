"""Ported from rs2b0t's src/bot/api/ai/quests/defs/elementalworkshop/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.catalogs.tools import PICKAXES as MINING_PICKS
from rs2004.game import skills
from rs2004.geometry import Tile
from rs2004.quests.defs.elementalworkshop.areas import EW_ITEM, PICKAXES, SEERS_BANK
from rs2004.quests.weapons import MELEE_WEAPONS, best_banked, best_held, pack_weapon, wielded_weapon

__all__ = ['COAL_NEED', 'FOOD_WITHDRAW', 'EW_OFFICIAL_SKILLS', 'EW_PROVEN_COMBAT_FLOOR', 'EW_FAILED_COMBAT', 'EW_PROBE_COMBAT', 'EW_TESTED_COMBAT', 'EW_RECOMMENDED_COMBAT', 'warn_elemental_workshop_readiness', 'held', 'banked', 'owned', 'held_name', 'has_pickaxe', 'has_held_slash_tool', 'has_slash_tool', 'has_weapon', 'best_held_pickaxe', 'best_bank_pickaxe', 'best_bank_weapon', 'scan_bank', 'withdraw', 'from_bank', 'surface_loadout']

COAL_NEED = 4
THREAD_NEED = 1
FOOD_WITHDRAW = 8
EW_OFFICIAL_SKILLS = {'mining': 20, 'smithing': 20, 'crafting': 20}
# Why: lowest non-required combat profile that has completed a full headed harness on a realistic bank seed at the official skill minimums.
# Why: headed runs so far: max combat on an inventory seed passed (mid-quest loop); Att/Str 40, Def 25, HP 40 on a bank seed died to the Water elemental; Att/Str 50, Def 40, HP 50 on a bank seed passed (about 270s, 2026-08-01).
# Why: the polish goal is to push this down and branch tactics by power level, so update it when a headed run moves the floor.
EW_PROVEN_COMBAT_FLOOR = Record({'attack': 50, 'strength': 50, 'defence': 40, 'hitpoints': 50})
EW_FAILED_COMBAT = Record({'attack': 40, 'strength': 40, 'defence': 25, 'hitpoints': 40})
EW_PROBE_COMBAT = Record({'attack': 45, 'strength': 45, 'defence': 30, 'hitpoints': 45})
EW_TESTED_COMBAT = EW_PROVEN_COMBAT_FLOOR
EW_RECOMMENDED_COMBAT = EW_PROVEN_COMBAT_FLOOR


def warn_elemental_workshop_readiness():
    """One-shot advisory when the account is below the proven combat floor (or only max is proven). Soft; doesn't block the queue. See docs/QUESTS.md polish goal."""
    have = {
        'attack': skills.level('attack'),
        'strength': skills.level('strength'),
        'defence': skills.level('defence'),
        'hitpoints': skills.level('hitpoints'),
        'mining': skills.level('mining'),
        'smithing': skills.level('smithing'),
        'crafting': skills.level('crafting'),
    }
    missing_official = []
    for skill, need in EW_OFFICIAL_SKILLS.items():
        n = (have[skill] if have[skill] is not None else 1)
        if n < need:
            missing_official.append(f'{skill} {n}/{need}')
    if len(missing_official) > 0:
        return f"official skill reqs not met ({', '.join(missing_official)}) — bot will wait or fail gates"
    floor = EW_PROVEN_COMBAT_FLOOR
    at_or_below_failed = have['attack'] <= EW_FAILED_COMBAT.attack and have['strength'] <= EW_FAILED_COMBAT.strength and have['defence'] <= EW_FAILED_COMBAT.defence and have['hitpoints'] <= EW_FAILED_COMBAT.hitpoints
    if at_or_below_failed:
        return (f'combat ≤ failed harness floor (Att/Str {EW_FAILED_COMBAT.attack}, ' + f'Def {EW_FAILED_COMBAT.defence}, HP {EW_FAILED_COMBAT.hitpoints}) — ' + 'died on Water elemental in headed test. Expect death risk; no low-power tactics yet.')
    short = []
    for skill in ['attack', 'strength', 'defence', 'hitpoints']:
        if have[skill] < floor.get(skill):
            short.append(f'{skill} {have[skill]}/{floor.get(skill)}')
    if len(short) == 0:
        return None
    return (f"combat below proven floor ({', '.join(short)}; headed PASS at " + f'{floor.attack}/{floor.strength}/{floor.defence}/{floor.hitpoints}). ' + f'Next probe {EW_PROBE_COMBAT.attack}/{EW_PROBE_COMBAT.strength}/' + f'{EW_PROBE_COMBAT.defence}/{EW_PROBE_COMBAT.hitpoints}. Untested — may fail or need low-power tactics later.')


def held(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, id):
    _v2 = (snap.bank_ids.get(id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def owned(snap, id):
    return held(snap, id) + banked(snap, id)


def held_name(snap, name):
    _v3 = snap.inv.get(name.lower())
    return (_v3 if _v3 is not None else 0)


def _worn_id(snap, id):
    return snap.worn_ids is not None and id in snap.worn_ids


def has_pickaxe(snap):
    return any([held(snap, p.id) > 0 or _worn_id(snap, p.id) for p in PICKAXES])


def is_slash_name(name):
    n = name.lower()
    return n == 'knife' or ('scimitar' in n) or ('sword' in n) or ('longsword' in n) or ('dagger' in n) or ('battleaxe' in n)


def is_combat_weapon_name(name):
    """Melee weapons for the Earth elemental; a knife doesn't count (ensureMeleeWeapon ignores it)."""
    n = name.lower()
    return ('scimitar' in n) or ('sword' in n) or ('longsword' in n) or ('dagger' in n) or ('battleaxe' in n) or ('mace' in n) or ('warhammer' in n)


# Why: the book spine accepts a knife or any slash weapon, as the server checks slashattack_anim.
# Why: `useOn` needs a pack item, so worn blades come off first (see slashBookForKey) or a knife is withdrawn.
def has_held_slash_tool(snap):
    """True when the pack holds something that can slash the book open."""
    if held(snap, EW_ITEM.KNIFE.id) > 0:
        return True
    if pack_weapon(snap) is not None:
        return True
    for name in list(snap.inv.keys()):
        if is_slash_name(name):
            return True
    return False


def has_slash_tool(snap):
    """Pack or worn slash tool, i.e. do we own something that can cut the book once unequipped. Worn-only doesn't skip the bank withdraw."""
    if has_held_slash_tool(snap):
        return True
    if wielded_weapon(snap) is not None:
        return True
    for name in snap.worn:
        if is_slash_name(name):
            return True
    return False


def has_weapon(snap):
    if best_held(snap) is not None:
        return True
    return any([is_combat_weapon_name(_x) for _x in list(list(snap.inv.keys())) + list(snap.worn)])


def best_held_pickaxe(snap):
    return ([p for p in PICKAXES if held(snap, p.id) > 0 or _worn_id(snap, p.id)] or [None])[0]


def best_bank_pickaxe(snap):
    return ([p for p in PICKAXES if banked(snap, p.id) > 0] or [None])[0]


def best_bank_weapon(snap):
    return best_banked(snap)


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': SEERS_BANK})


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': SEERS_BANK})


def from_bank(snap, item, qty=1):
    short = qty - held(snap, item.id)
    if short <= 0:
        return None
    if not snap.bank_known:
        return scan_bank()
    in_bank = banked(snap, item.id)
    return (withdraw([{'name': item.name, 'id': item.id, 'qty': min(short, in_bank)}]) if in_bank > 0 else None)


def keep_names_for_entry():
    return ['battered book', 'battered key', 'knife', 'hammer', 'needle', 'thread', 'leather', 'coal', 'bronze pickaxe', 'iron pickaxe', 'steel pickaxe', 'mithril pickaxe', 'adamant pickaxe', 'rune pickaxe', 'elemental ore', 'elemental metal', 'elemental shield', 'a stone bowl', 'coins', 'lobster', 'swordfish', 'salmon', 'trout'] + list([w.name.lower() for w in MELEE_WEAPONS])


def bank_count_by_name(snap, name):
    _v6 = (snap.bank.get(name.lower()) if snap.bank is not None else None)
    return (_v6 if _v6 is not None else 0)


def gather_coal(snap, mining_level=None):
    short = COAL_NEED - held(snap, EW_ITEM.COAL.id)
    in_bank = banked(snap, EW_ITEM.COAL.id)
    if short <= in_bank:
        return None
    mining = mining_level if mining_level is not None else skills.level('mining')
    picks = [pick for pick in PICKAXES if any([tool.name == pick.name and mining >= tool.level for tool in MINING_PICKS])]
    pick = ([pick for pick in picks if held(snap, pick.id) > 0 or _worn_id(snap, pick.id)] or [None])[0]
    free = snap.free_slots if snap.free_slots is not None else 28
    if free < short + (0 if pick else 1):
        keep = [EW_ITEM.BATTERED_BOOK, EW_ITEM.BATTERED_KEY, EW_ITEM.ELEMENTAL_ORE,
                EW_ITEM.ELEMENTAL_METAL, EW_ITEM.ELEMENTAL_SHIELD, EW_ITEM.COAL] + ([pick] if pick else [])
        return Record({'kind': 'deposit', 'keep': [item.name for item in keep], 'keep_ids': [item.id for item in keep],
                       'bank': SEERS_BANK, 'exact_keep': True})
    if in_bank > 0:
        return withdraw([{'name': EW_ITEM.COAL.name, 'id': EW_ITEM.COAL.id, 'qty': min(short, in_bank)}])
    if mining < 30:
        return Record({'kind': 'wait', 'reason': f'need Mining 30 to mine Coal, or {short} Coal in the bank'})
    if pick is None:
        bank_pick = ([pick for pick in picks if banked(snap, pick.id) > 0] or [None])[0]
        if bank_pick:
            return withdraw([{'name': bank_pick.name, 'id': bank_pick.id, 'qty': 1}])
        return Record({'kind': 'grab_ground', 'item': 'Bronze pickaxe', 'anchor': Tile(2963, 3216, 0), 'wait_if_missing': True})
    return Record({'kind': 'mine_rock', 'rock': 'Coal', 'item': EW_ITEM.COAL.name, 'qty': short, 'anchor': Tile(2581, 3480, 0)})


def surface_loadout(snap, need_bellows_fix, need_smelt):
    """Tools and materials needed before committing to the spiral stairs. Bank first: scan, deposit junk, withdraw the missing kit (food and weapon included)."""
    if not snap.bank_known:
        return scan_bank()
    if need_smelt:
        coal = gather_coal(snap)
        if coal:
            return coal
    # Drop junk before packing so a full pack of misc loot cannot block withdraws.
    # Entry kit can need ~12 free slots (tools + coal + food).
    keep = keep_names_for_entry()
    has_junk = any([not (n.lower() in keep) for n in list(list(snap.inv.keys()))])
    free = (snap.free_slots if snap.free_slots is not None else 28)
    if has_junk and free < 12:
        return Record({
            'kind': 'deposit',
            'keep': keep,
            'keep_ids': workshop_keep_ids(snap),
            'bank': SEERS_BANK,
            'exact_keep': True,
        })
    needed = []

    def push_missing(item, qty):
        short = qty - held(snap, item.id)
        if short <= 0:
            return
        in_bank = banked(snap, item.id)
        if in_bank > 0:
            needed.append({'name': item.name, 'id': item.id, 'qty': min(short, in_bank)})

    # Quest keys/book if re-entering mid-run.
    push_missing(EW_ITEM.BATTERED_BOOK, 1)
    push_missing(EW_ITEM.BATTERED_KEY, 1)
    # Prefer a knife for the book; any slash weapon in the pack also works.
    if not has_held_slash_tool(snap):
        knife = banked(snap, EW_ITEM.KNIFE.id)
        if knife > 0:
            needed.append({'name': EW_ITEM.KNIFE.name, 'id': EW_ITEM.KNIFE.id, 'qty': 1})
        else:
            w = best_bank_weapon(snap)
            if w:
                needed.append({'name': w.name, 'id': w.id, 'qty': 1})
    if need_smelt and not has_pickaxe(snap):
        pick = best_bank_pickaxe(snap)
        if pick:
            needed.append({'name': pick.name, 'id': pick.id, 'qty': 1})
    if held(snap, EW_ITEM.HAMMER.id) == 0:
        push_missing(EW_ITEM.HAMMER, 1)
    if need_smelt and held(snap, EW_ITEM.COAL.id) < COAL_NEED:
        short = COAL_NEED - held(snap, EW_ITEM.COAL.id)
        in_bank = banked(snap, EW_ITEM.COAL.id)
        if in_bank > 0:
            needed.append({'name': EW_ITEM.COAL.name, 'id': EW_ITEM.COAL.id, 'qty': min(short, in_bank)})
    if need_bellows_fix:
        if held(snap, EW_ITEM.THREAD.id) < THREAD_NEED:
            push_missing(EW_ITEM.THREAD, THREAD_NEED)
        # Leather/needle: bank preferred; crates inside workshop are the fallback in decide().
        push_missing(EW_ITEM.LEATHER, 1)
        push_missing(EW_ITEM.NEEDLE, 1)
    # Combat food for the Earth elemental + traversal sustain.
    food_held = held_name(snap, 'lobster') + held_name(snap, 'swordfish') + held_name(snap, 'salmon') + held_name(snap, 'trout')
    if food_held < 3:
        foods = [
            Record({'name': 'Lobster', 'bank_key': 'lobster'}),
            Record({'name': 'Swordfish', 'bank_key': 'swordfish'}),
            Record({'name': 'Salmon', 'bank_key': 'salmon'}),
            Record({'name': 'Trout', 'bank_key': 'trout'}),
        ]
        for f in foods:
            n = bank_count_by_name(snap, f.bank_key)
            if n > 0:
                needed.append({'name': f.name, 'qty': min(FOOD_WITHDRAW, n)})
                break
    # Weapon for the elemental if we only have a knife for the book.
    if need_smelt and not has_weapon(snap):
        w = best_bank_weapon(snap)
        if w and not any([n.get('id') == w.id for n in needed]):
            needed.append({'name': w.name, 'id': w.id, 'qty': 1})
    if len(needed) > 0:
        # If the batch cannot fit, deposit junk first even when freeSlots looked "ok".
        if has_junk and free < len(needed):
            return Record({
                'kind': 'deposit',
                'keep': keep,
                'keep_ids': workshop_keep_ids(snap),
                'bank': SEERS_BANK,
                'exact_keep': True,
            })
        return withdraw(needed)
    # Hard waits when bank is known empty of critical tools.
    if need_smelt and not has_pickaxe(snap) and not best_bank_pickaxe(snap):
        return Record({'kind': 'wait', 'reason': 'need a pickaxe in the bank for Elemental ore'})
    if held(snap, EW_ITEM.HAMMER.id) == 0 and banked(snap, EW_ITEM.HAMMER.id) == 0:
        return Record({'kind': 'wait', 'reason': 'need a Hammer in the bank to smith the Elemental shield'})
    if need_bellows_fix and held(snap, EW_ITEM.THREAD.id) < THREAD_NEED and banked(snap, EW_ITEM.THREAD.id) == 0:
        return Record({'kind': 'wait', 'reason': 'need Thread in the bank to fix the bellows'})
    if need_smelt and not has_weapon(snap) and not best_bank_weapon(snap):
        return Record({'kind': 'wait', 'reason': 'need a melee weapon in the bank for the Earth elemental'})
    # source_knife falls back to the ground knife spawn, so there's no wait for one here.
    return None


def workshop_keep_ids(_snap):
    return [EW_ITEM.BATTERED_BOOK.id, EW_ITEM.BATTERED_KEY.id, EW_ITEM.STONE_BOWL.id, EW_ITEM.STONE_BOWL_FULL.id, EW_ITEM.ELEMENTAL_ORE.id, EW_ITEM.ELEMENTAL_METAL.id, EW_ITEM.ELEMENTAL_SHIELD.id, EW_ITEM.KNIFE.id, EW_ITEM.NEEDLE.id, EW_ITEM.THREAD.id, EW_ITEM.LEATHER.id, EW_ITEM.COAL.id, EW_ITEM.HAMMER.id, EW_ITEM.COINS.id] + list([p.id for p in PICKAXES]) + list([w.id for w in MELEE_WEAPONS])

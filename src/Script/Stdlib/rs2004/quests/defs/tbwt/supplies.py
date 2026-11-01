"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs.record import Record
from rs2004.items import equipment
from rs2004.quests.armour import armour_choice, armour_worn
from rs2004.quests.defs.tbwt.areas import AGILITY_DOSES, ARROW_TARGET, COIN_TARGET, FOOD_TARGET, TB_ARMOUR_SLOTS, TB_ARROWS, TB_BOWS, TB_ID, TB_LUBUFU, TB_NAME, TB_NPC, TB_POTIONS, TB_POTION_IDS, TB_SPEARS, TB_SPEAR_IDS, TB_TAMAYU, TB_TILE, TB_TINSAY, on_karamja
from rs2004.quests.defs.tbwt.journal import TB_FLAG
from rs2004.quests.engine.types import flag_value, has_flag
from rs2004.quests.food import quest_food

__all__ = ['held_id', 'banked_id', 'held', 'banked', 'worn', 'lubufu_stage', 'tinsay_stage', 'tamayu_stage', 'tiadeche_stage', 'food_names', 'food_held', 'outstanding_supplies', 'TB_KEEP_IDS', 'kp_spear_held', 'bare_spear_held', 'spear_wanted', 'doses_held', 'doses_wanted', 'spear_in_bank', 'potions_in_bank', 'bow_choice', 'arrow_choice', 'prepare', 'TB_PROVEN', 'readiness']


def count_in(counts, key):
    count = None if counts is None else counts.get(key)
    return count if count is not None else 0


def held_id(snap, id):
    return count_in(snap.inv_ids, id)


def banked_id(snap, id):
    return count_in(snap.bank_ids, id)


def held(snap, name):
    return count_in(snap.inv, name.lower())


def banked(snap, name):
    return count_in(snap.bank, name.lower())


def worn(snap, name):
    return (name.lower() in snap.worn)


def lubufu_stage(snap):
    value = flag_value(snap.progress, TB_FLAG.LUBUFU)
    return value if value is not None else TB_LUBUFU.UNKNOWN


def tinsay_stage(snap):
    value = flag_value(snap.progress, TB_FLAG.TINSAY)
    return value if value is not None else TB_TINSAY.UNKNOWN


def tamayu_stage(snap):
    value = flag_value(snap.progress, TB_FLAG.TAMAYU)
    return value if value is not None else TB_TAMAYU.UNKNOWN


def tiadeche_stage(snap):
    value = flag_value(snap.progress, TB_FLAG.TIADECHE)
    return value if value is not None else 0


def food_names():
    """Food this quest will carry, the script's chosen food first."""
    chosen = (quest_food.name.strip() if quest_food.name is not None else None)
    names = [n for n in [chosen, 'Lobster', 'Swordfish', 'Tuna', 'Trout', 'Salmon'] if bool(n)]
    unique = []
    seen = set()
    for n in names:
        if n.lower() in seen:
            continue
        seen.add(n.lower())
        unique.append(n)
    return unique


def food_held(snap):
    return sum([held(snap, name) for name in food_names()])


NET = Record({'name': TB_NAME.NET, 'id': TB_ID.NET, 'qty': 1})
KNIFE = Record({'name': TB_NAME.KNIFE, 'id': TB_ID.KNIFE, 'qty': 1, 'from_jiminua': True})
PESTLE = Record({'name': TB_NAME.PESTLE, 'id': TB_ID.PESTLE, 'qty': 1, 'from_jiminua': True})
TINDERBOX = Record({'name': TB_NAME.TINDERBOX, 'id': TB_ID.TINDERBOX, 'qty': 1, 'from_jiminua': True})
SEAWEED = Record({'name': TB_NAME.SEAWEED, 'id': TB_ID.SEAWEED, 'qty': 1})


# Why: a supply drops off the list once its leg is behind us, so the quest never crosses back to Ardougne for a knife it already used.
def outstanding_supplies(snap):
    """Everything the legs still ahead of the bot consume."""
    lubufu = lubufu_stage(snap)
    tinsay = tinsay_stage(snap)
    tamayu = tamayu_stage(snap)
    out = []
    # Karambwanji bait Lubufu, load the vessel for Tiadeche, and grind into Tinsay's marinade.
    if lubufu < TB_LUBUFU.COMPLETE or tinsay < TB_TINSAY.COMPLETE:
        out.append(NET)
    if tinsay < TB_TINSAY.GIVEN_RUM:
        out.append(KNIFE)
    if tamayu < TB_TAMAYU.COMPLETE or tinsay < TB_TINSAY.COMPLETE:
        out.append(PESTLE)
    if tinsay < TB_TINSAY.COMPLETE:
        out.append(TINDERBOX)
    # The sandwich consumes it, and the stage only advances when Tinsay eats, so a made sandwich retires the need.
    if tinsay < TB_TINSAY.GIVEN_SANDWICH and held_id(snap, TB_ID.SANDWICH) == 0:
        out.append(SEAWEED)
    return out


TB_KEEP_IDS = [TB_ID.get(key) for key in TB_ID.keys()] + list(TB_SPEAR_IDS) + list(TB_POTION_IDS)


# Why: a pack holding paste and no shaft still needs a spear.
def kp_spear_held(snap):
    """The Karambwan-poisoned spear the pack is carrying, 0 when there is none."""
    spear = ([spear for spear in TB_SPEARS if held_id(snap, spear.kp_id) > 0] or [None])[0]
    return 0 if spear is None else spear.kp_id


def bare_spear_held(snap):
    """The bare spear the paste still has to go on, null when the pack holds none."""
    return ([spear for spear in TB_SPEARS if held_id(snap, spear.id) > 0] or [None])[0]


def spear_wanted(snap):
    """True while the Tamayu leg still owes him a spear and the pack holds nothing that becomes one."""
    return tamayu_stage(snap) < TB_TAMAYU.COMPLETE and not has_flag(snap.progress, TB_FLAG.SPEAR) and kp_spear_held(snap) == 0 and bare_spear_held(snap) is None


def doses_held(snap):
    """Doses of agility potion the pack is carrying, across every bottle size."""
    return sum([held_id(snap, potion.id) * potion.doses for potion in TB_POTIONS])


# Why: Only the fourth dose appears in the journal, so fill all four before starting another bottle.
def doses_wanted(snap):
    """True while Tamayu is still short of his 4 doses and the pack has nothing to pour."""
    return tamayu_stage(snap) < TB_TAMAYU.COMPLETE and not has_flag(snap.progress, TB_FLAG.AGILITY) and doses_held(snap) == 0


def spear_in_bank(snap):
    """The cheapest spear the bank holds that Tamayu will take, bare ones before poisoned ones."""
    bare = ([spear for spear in TB_SPEARS if banked_id(snap, spear.id) > 0] or [None])[0]
    if bare:
        return Record({'name': bare.name, 'id': bare.id})
    done = ([spear for spear in TB_SPEARS if banked_id(snap, spear.kp_id) > 0] or [None])[0]
    return (Record({'name': done.kp_name, 'id': done.kp_id}) if done else None)


def potions_in_bank(snap):
    """Bottles to draw for Tamayu's 4 doses, fullest first. Empty when the bank holds no agility potion."""
    lines = []
    doses = 0
    for potion in TB_POTIONS:
        stocked = banked_id(snap, potion.id)
        take = min(stocked, math.ceil((AGILITY_DOSES - doses) / potion.doses))
        if take > 0:
            lines.append({'name': potion.name, 'qty': take, 'id': potion.id})
            doses += take * potion.doses
        if doses >= AGILITY_DOSES:
            break
    return lines


def bow_choice(snap):
    """The bow this run draws: what is worn or carried, else the best one the bank holds and the account can wield."""
    ranged = snap.ranged if snap.ranged is not None else 99
    usable = [bow for bow in TB_BOWS if ranged >= bow.ranged]
    bow = ([bow for bow in usable if worn(snap, bow.name) or held(snap, bow.name) > 0] or [None])[0]
    if bow is None:
        bow = ([bow for bow in usable if banked(snap, bow.name) > 0] or [None])[0]
    return None if bow is None else bow.name


def arrow_choice(snap):
    """The arrows this run fires: what is worn or carried, else the first the bank holds."""
    carried = ([name for name in TB_ARROWS if worn(snap, name) or held(snap, name) > 0] or [None])[0]
    return carried if carried is not None else ([name for name in TB_ARROWS if banked(snap, name) > 0] or [None])[0]


scan_bank = Record({'kind': 'scan_bank', 'bank': TB_TILE.ARDOUGNE_BANK})


def keep_names(snap):
    kit = [n for n in [bow_choice(snap), arrow_choice(snap)] if bool(n)]

    armour = []
    for slot in TB_ARMOUR_SLOTS:
        piece = armour_choice(snap, slot)
        if piece:
            armour.append(piece.name)
    return [n.lower() for n in list(kit) + list(armour) + list(food_names())]


def wear_all(names):
    def _fn10(log):
        for name in names:
            _w11 = yield from equipment.equip(name)
            if not (_w11):
                log(f'cannot wear {name} — not in the pack, or the server refused it')
                return False
        return True
    return Record({'kind': 'custom', 'name': f"wear {', '.join(names)}", 'run': _fn10})


# Why: `buy` walks back to a bank whenever the pack holds less than `estGp`, so the estimate stays under the float; none of these 3 costs more than 100.
def buy_at_jiminua(item, qty):
    return (Record({
        'kind': 'buy',
        'item': item,
        'qty': qty,
        'shop': Record({'npc': TB_NPC.JIMINUA, 'anchor': TB_TILE.JIMINUA}),
        'est_gp': 150,
    }))


DEPOSIT_BELOW_FREE = 6


# Why: this runs on every decide() tick, so each branch is idempotent and falls silent as soon as the pack is right.
def prepare(snap):
    """The pack and the worn kit, bank first. Null once nothing is outstanding."""
    missing = [s for s in outstanding_supplies(snap) if held_id(snap, s.id) < s.qty]
    bow = bow_choice(snap)
    arrows = arrow_choice(snap)
    kit = [n for n in [bow, arrows] if bool(n)]
    armour = [(Record({'slot': slot, 'piece': armour_choice(snap, slot)})) for slot in TB_ARMOUR_SLOTS]
    armour_missing = [entry for entry in armour if not entry.piece]
    gear_missing = [name for name in kit if not worn(snap, name)]
    for entry in armour:
        if entry.piece and not armour_worn(snap, entry.piece):
            gear_missing.append(entry.piece.name)
    # Why: only an outstanding purchase justifies a crossing for coin; the ferry's own 30gp fare is covered by the float this withdraws.
    buying = tinsay_stage(snap) < TB_TINSAY.GIVEN_RUM or any([s.from_jiminua for s in missing])
    coins_low = buying and held(snap, TB_NAME.COINS) < 100
    starving = food_held(snap) == 0
    want_spear = spear_wanted(snap)
    want_doses = doses_wanted(snap)
    if len(missing) == 0 and len(gear_missing) == 0 and len(armour_missing) == 0 and len(kit) == 2 and not coins_low and not starving and not want_spear and not want_doses:
        return None
    # Wearing what is already in the pack never needs a bank.
    carried = [name for name in gear_missing if held(snap, name) > 0]
    if len(carried) > 0:
        return wear_all(carried)
    if not snap.bank_known:
        return scan_bank
    # Jiminua's counter is inside the quest area; only the ferry is worth avoiding.
    if on_karamja(snap.tile) and not coins_low and not starving and len(gear_missing) == 0 and len(armour_missing) == 0 and len(kit) == 2:
        shopped = ([s for s in missing if s.from_jiminua and banked_id(snap, s.id) == 0] or [None])[0]
        if shopped:
            return buy_at_jiminua(shopped.name, shopped.qty)
    if (snap.free_slots if snap.free_slots is not None else 28) < DEPOSIT_BELOW_FREE:
        return Record({
            'kind': 'deposit',
            'keep': keep_names(snap),
            'keep_ids': TB_KEEP_IDS,
            'bank': TB_TILE.ARDOUGNE_BANK,
            'exact_keep': True,
        })
    from_bank = []
    unavailable = [f'usable {entry.slot} armour' for entry in armour_missing]
    for s in missing:
        stocked = banked_id(snap, s.id)
        if stocked > 0:
            from_bank.append({'name': s.name, 'qty': min(s.qty - held_id(snap, s.id), stocked), 'id': s.id})
        elif not s.from_jiminua:
            unavailable.append(s.name)
    if not bow:
        ranged = snap.ranged if snap.ranged is not None else '?'
        unavailable.append(f'any bow this account can draw at Ranged {ranged}')
    if not arrows:
        unavailable.append('any arrows')
    for name in gear_missing:
        if banked(snap, name) > 0:
            from_bank.append({'name': name, 'qty': (ARROW_TARGET if name == arrows else 1)})
        else:
            unavailable.append(name)
    # Why: Jogres drop spears and their patch is on the route, so an empty bank isn't a dead end.
    if want_spear:
        stocked = spear_in_bank(snap)
        if stocked:
            from_bank.append({'name': stocked.name, 'qty': 1, 'id': stocked.id})
    if want_doses:
        bottles = potions_in_bank(snap)
        if len(bottles) > 0:
            from_bank.extend(bottles)
        else:
            unavailable.append('an agility potion, any dose')
    if coins_low and banked(snap, TB_NAME.COINS) > 0:
        from_bank.append({'name': TB_NAME.COINS, 'qty': COIN_TARGET})
    if food_held(snap) < FOOD_TARGET:
        stocked = ([name for name in food_names() if banked(snap, name) > 0] or [None])[0]
        if stocked:
            from_bank.append({'name': stocked, 'qty': FOOD_TARGET - food_held(snap)})
        elif starving:
            unavailable.append('any combat food')
    if len(from_bank) > 0:
        return Record({'kind': 'withdraw', 'items': from_bank, 'bank': TB_TILE.ARDOUGNE_BANK})
    if len(unavailable) > 0:
        return Record({'kind': 'wait', 'reason': f"bank has none of: {', '.join(unavailable)}"})
    # What is left is a Jiminua line and the bank does not stock it.
    shopped = ([s for s in missing if s.from_jiminua] or [None])[0]
    return (buy_at_jiminua(shopped.name, shopped.qty) if shopped else None)


TB_PROVEN = Record({'skills': 70, 'firemaking': 30, 'cooking': 30, 'karambwan_fishing': 65})


def readiness(level_of):
    short = []
    if level_of('firemaking') < TB_PROVEN.firemaking:
        short.append(f"Firemaking {level_of('firemaking')} < {TB_PROVEN.firemaking} — Jogre bones cannot be burnt")
    if level_of('cooking') < TB_PROVEN.cooking:
        short.append(f"Cooking {level_of('cooking')} < {TB_PROVEN.cooking} — the marinade cannot be cooked")
    if len(short) == 0:
        return None
    return f"proven at {TB_PROVEN.skills} across the board; {'; '.join(short)}"

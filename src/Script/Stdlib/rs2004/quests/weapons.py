"""The melee weapons and pickaxes a quest arms itself with: rs2b0t's api/ai/quests/weapons.ts (MIT, see
thirdparty/rs2b0t). See rs2b0t's docs/reference/quest-provisioning.md."""

from rs2004.catalogs.tables import item_db
from rs2004.game import skills
from rs2004.items import equipment, inventory
from rs2004.tabs import quests

__all__ = [
    'MeleeWeapon', 'MELEE_WEAPONS', 'PICKAXES', 'banked_pickaxe', 'wieldable', 'held_weapon', 'banked_weapon',
    'quest_done', 'best_held', 'wielded_weapon', 'pack_weapon', 'best_banked', 'live_best_weapon',
]


class MeleeWeapon:
    """A weapon: its id and name, its metal tier, the Attack level the tier needs, and the quest whose journal must
    read complete before it can be wielded, or None."""

    def __init__(self, id, name, tier, attack, quest=None):
        self.id = id
        self.name = name
        self.tier = tier
        self.attack = attack
        self.quest = quest

    def __repr__(self):
        return f'MeleeWeapon({repr(self.name)})'


# What each metal tier costs in Attack, best first.
TIERS = [
    ('Dragon', 60), ('Rune', 40), ('Adamant', 30), ('Mithril', 20), ('Black', 10), ('Steel', 5), ('Iron', 1), ('Bronze', 1),
]

# Why: one-handed only; a two-hander takes the shield slot, and every quest that arms itself also wears one.
# Melee types within a tier, best first.
TYPES = ['scimitar', 'longsword', 'battleaxe', 'sword', 'mace', 'dagger', 'warhammer']

# Why: tier60.rs2 gates dragon melee on a quest as well as Attack 60, so a level check alone withdraws a weapon that
# can't be wielded.
QUEST_GATE = {
    'Dragon longsword': 'Lost City',
    'Dragon dagger': 'Lost City',
    'Dragon battleaxe': "Hero's Quest",
    'Dragon mace': "Hero's Quest",
}


def _item_named(name, one_handed=False):
    for row in item_db():
        if row.name == name and (not one_handed or (row.slot == 'righthand' and not row.two_handed)):
            return row
    return None


def _build():
    out = []
    for tier, attack in TIERS:
        for kind in TYPES:
            name = f'{tier} {kind}'
            row = _item_named(name, True)
            if row is not None:
                out.append(MeleeWeapon(row.id, name, tier, attack, QUEST_GATE.get(name)))
    return out


# Every one-handed melee weapon the item db knows, best tier first.
MELEE_WEAPONS = _build()


def _build_pickaxes():
    out = []
    for tier, attack in TIERS:
        row = _item_named(f'{tier} pickaxe')
        if row is not None:
            out.append(MeleeWeapon(row.id, row.name, tier, attack))
    return out


# Why: tier40.rs2 gates a rune pickaxe on Attack 40, so a pickaxe rides the same tiers as a scimitar; it's kept out of
# MELEE_WEAPONS so nothing goes to a fight holding one.
# Every pickaxe the item db knows, best tier first.
PICKAXES = _build_pickaxes()


def banked_pickaxe(banked, attack):
    """The best pickaxe this account may wield and has banked, or None."""
    for p in PICKAXES:
        if attack >= p.attack and banked is not None and banked.get(p.id, 0) > 0:
            return p
    return None


def wieldable(attack, quest_done):
    """Weapons this account may wield right now, best first."""
    return [w for w in MELEE_WEAPONS if attack >= w.attack and (w.quest is None or quest_done(w.quest))]


def held_weapon(held, worn, attack, quest_done):
    """The best wieldable weapon the pack (held, counts by id) or the worn set (ids) already has."""
    for w in wieldable(attack, quest_done):
        if (held is not None and held.get(w.id, 0) > 0) or (worn is not None and w.id in worn):
            return w
    return None


def banked_weapon(banked, attack, quest_done):
    """The best wieldable weapon the last bank read saw."""
    for w in wieldable(attack, quest_done):
        if banked is not None and banked.get(w.id, 0) > 0:
            return w
    return None


def quest_done(quest):
    """True when the journal reads complete, which is what the dragon gates test."""
    return quests.status(quest) == 'complete'


def _attack_of(snap):
    return snap.attack if snap.attack is not None else skills.level('attack')


def best_held(snap):
    """The best weapon this account can wield and already holds or wears."""
    return held_weapon(snap.inv_ids, snap.worn_ids, _attack_of(snap), quest_done)


def wielded_weapon(snap):
    """The weapon already wielded, when it's one this account may use."""
    return held_weapon(None, snap.worn_ids, _attack_of(snap), quest_done)


def pack_weapon(snap):
    """The best wieldable weapon sitting in the pack."""
    return held_weapon(snap.inv_ids, None, _attack_of(snap), quest_done)


def best_banked(snap):
    """The best weapon this account can wield and has banked; None until a bank read lands."""
    return banked_weapon(snap.bank_ids, _attack_of(snap), quest_done) if snap.bank_known else None


# Why: some fight loops resolve a weapon with no snapshot to hand, so the live pack, worn set and bank stand in for one.
def live_best_weapon():
    """The best weapon this account may wield, read from the live pack and worn set."""
    held = {}
    for i in inventory.items():
        held[i.id] = i.count
    worn = set([i.id for i in equipment.items()])
    return held_weapon(held, worn, skills.level('attack'), quest_done)

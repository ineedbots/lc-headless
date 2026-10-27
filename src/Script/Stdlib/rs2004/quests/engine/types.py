"""What a quest module reads and answers: rs2b0t's api/ai/quests/engine/types.ts (MIT, see thirdparty/rs2b0t).

The engine builds a QuestSnapshot each pass and asks the running module's decide(snap) for one step. A step is a
Record made by quest_step(kind, ...), with rs2b0t's kinds in snake case:
    talk          stop (an NpcStop)
    grab_ground   item, anchor, wait_if_missing
    pick_loc      loc, op, item, anchor
    interact_loc  loc, op, anchor, expect_item
    use_on        item, target_kind ('npc', 'loc' or 'item'), target, anchor, product
    equip         item
    scan_bank     bank
    withdraw      items (dicts of name, qty and an optional id), bank, leave_open
    deposit       keep (names), keep_ids, bank, leave_open, exact_keep
    mine_rock     rock, item, qty, anchor
    buy           item, qty, shop ({'npc': ..., 'anchor': ...}), est_gp, bank
    custom        name, run(log), a generator that gives True when the step worked
    wait          reason
    done
A field the step doesn't set reads as None."""

from rs2004.catalogs.record import Record

__all__ = [
    'QuestProgress', 'has_flag', 'flag_value', 'QuestSnapshot', 'held_id', 'banked_id', 'quest_step', 'QuestPrayer',
    'QuestSustain', 'QuestModule',
]


class QuestProgress:
    """The quest's stage, and the journal's sub-progress the stage can't carry: flags of 'name', or 'name:N' for a
    counted one."""

    def __init__(self, stage=0, flags=None):
        self.stage = stage
        self.flags = flags if flags is not None else set()


def has_flag(progress, name):
    return progress is not None and name in progress.flags


def flag_value(progress, name):
    """The N of a 'name:N' flag, or None."""
    if progress is None:
        return None
    prefix = name + ':'
    for flag in progress.flags:
        if flag.startswith(prefix):
            try:
                return int(flag[len(prefix):])
            except Exception:
                return None
    return None


class QuestSnapshot:
    """What decide() sees: the journal status ('not_started', 'in_progress', 'complete' or 'unknown'), the pack
    (inv, by lower-case name, and inv_ids, by object id), what's worn (worn by lower-case name, worn_ids), the last
    bank read (bank, bank_ids, bank_known, bank_coins), the stage and progress when the module reads them, and the
    tile, prayer, levels, free slots and combat xp. no_progress counts the steps since anything changed."""

    FIELDS = [
        'journal', 'inv', 'inv_ids', 'worn', 'worn_ids', 'no_progress', 'bank_coins', 'stage', 'progress', 'bank', 'bank_ids',
        'bank_known', 'tile', 'prayer', 'attack', 'ranged', 'magic', 'free_slots', 'combat_xp',
    ]

    def with_fields(self, changes):
        """A copy with the fields in the changes dict replaced: rs2b0t's {...snap, field: value}."""
        copy = QuestSnapshot()
        for name in QuestSnapshot.FIELDS:
            setattr(copy, name, changes[name] if name in changes else getattr(self, name))
        return copy

    def __init__(self, journal='unknown', inv=None, inv_ids=None, worn=None, worn_ids=None, no_progress=0, bank_coins=0,
                 stage=None, progress=None, bank=None, bank_ids=None, bank_known=None, tile=None, prayer=None, attack=None,
                 ranged=None, magic=None, free_slots=None, combat_xp=None):
        self.journal = journal
        self.inv = inv if inv is not None else {}
        self.inv_ids = inv_ids
        self.worn = worn if worn is not None else set()
        self.worn_ids = worn_ids
        self.no_progress = no_progress
        self.bank_coins = bank_coins
        self.stage = stage
        self.progress = progress
        self.bank = bank
        self.bank_ids = bank_ids
        self.bank_known = bank_known
        self.tile = tile
        # Why: None means the snapshot doesn't report it, and a step that needs prayer treats that as "not short".
        self.prayer = prayer
        self.attack = attack
        self.ranged = ranged
        self.magic = magic
        self.free_slots = free_slots
        self.combat_xp = combat_xp


# Why: display names collide: "Broken shield", "Certificate", "Fishing spot" and "Gate" each name more than one thing,
# so a name lookup silently accepts the wrong object.
def held_id(snap, id):
    """How many of an exact object id the pack holds."""
    return snap.inv_ids.get(id, 0) if snap.inv_ids is not None else 0


# Why: keep an unread bank unknown instead of treating it as empty.
def banked_id(snap, id):
    """How many of an exact object id the last bank read saw; 0 until one lands."""
    if not snap.bank_known or snap.bank_ids is None:
        return 0
    return snap.bank_ids.get(id, 0)


def quest_step(kind, **fields):
    """A step of this kind, with its fields (see the module's docstring)."""
    fields['kind'] = kind
    return Record(fields)


class QuestPrayer:
    """The protection prayer to hold through a quest's fights ('melee', 'magic' or 'missiles'), and the prayer
    potion doses drawn into the float alongside the food."""

    def __init__(self, protect='melee', potions=None):
        self.protect = protect
        self.potions = potions


class QuestSustain:
    """The foods a quest can source and eat on the way, and the hitpoints fraction below which the host eats."""

    def __init__(self, foods=None, eat_below_hp=0.5):
        self.foods = foods if foods is not None else []
        self.eat_below_hp = eat_below_hp


class QuestModule:
    """A quest: its record and decide(snap), and what it tells the engine.

    - hops: the LadderHops its walks may need.
    - bank: the Tile of the bank it uses, or 'nearest' to work it out from where the bot stands. Most quests sit in
      one town, so naming its bank beats working it out; 'nearest' is for those that don't.
    - grind: the NPCs it fights, which the random-event guard leaves alone.
    - food: the food float to carry; gather: a function per lower-case item name, gather(snap, need), giving the step
      that sources it; tools: lower-case names the spillover deposit keeps, or a function returning them.
    - exit(log): walked once the quest is finished, before the retreat to a bank, for the quests that end somewhere
      the walker can't leave on its own; a generator giving True once a bank walk can start.
    - owns_inventory: the module makes every banking and loadout decision, restarts in bankless areas included.
    - food_ready(snap): False to hold the food float back this pass. Food is the bulkiest withdrawal, so a module that
      arms itself from the bank is dressed before the pack fills.
    - read_stage(), read_progress(): the exact stage, or a QuestProgress, from what the client can see. Either may be a
      generator; read_progress wins.
    - sustain: a QuestSustain; pray: a QuestPrayer, declared only on the quests whose fights threaten the account.
    - coin_float: spending money to keep in the pack, default COIN_FLOAT; 0 for a quest that spends nothing.
    - warn_readiness(): a one-off advisory when the quest starts, or None.
    - observe(snap, step): extra log lines when it decides a step, or on death.
    - on_start(): called once, when the quest first runs."""

    # Why: the members are plain attributes, never methods, since pocketpy calls a class's method over a function set
    # on its instance.
    def __init__(self, record=None, decide=None, on_start=None, hops=None, bank=None, grind=None, food=None, gather=None,
                 tools=None, exit=None, owns_inventory=False, food_ready=None, read_stage=None, read_progress=None,
                 sustain=None, pray=None, coin_float=None, warn_readiness=None, observe=None):
        self.record = record
        self.decide = decide
        self.on_start = on_start
        self.hops = hops
        self.bank = bank
        self.grind = grind
        self.food = food
        self.gather = gather
        self.tools = tools
        self.exit = exit
        self.owns_inventory = owns_inventory
        self.food_ready = food_ready
        self.read_stage = read_stage
        self.read_progress = read_progress
        self.sustain = sustain
        self.pray = pray
        self.coin_float = coin_float
        self.warn_readiness = warn_readiness
        self.observe = observe

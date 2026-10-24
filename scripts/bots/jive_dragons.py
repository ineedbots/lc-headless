# Fights dragons on the hunting framework's sites: Taverley Dungeon's blue or black dragons, the Heroes' Guild
# dragon through its fence, the Gu'Tanoth Enclave's blue dragons and greater demons, and Brimhaven Dungeon's iron
# and steel dragons. rs2b0t's JiveDragons (MIT, see thirdparty/rs2b0t). Magic and range fight from a derived
# safespot; melee wears the Dragonfire shield and, on the metal dragons, prays Protect from Melee under an Antifire
# dose. It opens the dusty-key gate, fetching the key from Velrak when the bank has none. rs2b0t also solves the hard
# clues the dragons drop; that comes with the clue solver, and until then a clue is banked.

import time

from rs2004.catalogs import ARROWS, AXES, BOWS, EMPTY_VIAL, LOADOUT_SETTING, MELEE_WEAPONS, SPELL_DB, STAFFS, SUPER_SET, ContinueDialog
from rs2004.catalogs import DeathRecovery, Record, best_melee_weapon, casts_available, drop_db, food_count, food_heal_amount, is_edible_food
from rs2004.catalogs import known_melee_weapon, planned_potions, potion_to_sip, ranging_plan, script_food, selected_loadout
from rs2004.catalogs import should_eat_to_use_food, supplies_of, sustain
from rs2004.hunting import ANTIFIRE_DOSES, ANTIFIRE_MARGIN_TICKS, ANTIFIRE_TICKS, ANTIPOISON_DOSES, BRIMHAVEN_IRON, BRIMHAVEN_STEEL, COINS
from rs2004.hunting import ENCLAVE_TARGET_OPTIONS, GUTANOTH_BLUE, HEROES_BLUE, MAX_STANDS, POISONED, POTION_PROTECTS, PRAYER_DOSES
from rs2004.hunting import SHIELD, SHIELD_ABSORBS, SITE_OPTIONS, STAND_SITE_KEYS, TAVERLEY_BLACK, TAVERLEY_BLUE, BankOpts, Fight, HoldSafespot
from rs2004.hunting import Retreat, WalkToSpot, acquire_key, anchor_for, antifire_due, antifire_lapsed, antifire_plan, antipoison_plan
from rs2004.hunting import bank_routine, chase_mode, chases_target, dose_to_drink, enclave_targets, enter_lair, escape_runes_for, fee_prepaid
from rs2004.hunting import hunt_names, in_cell, keep_doses, key_status, leave_cell, loot_halts, loot_reach, needs_shield, prayer_for
from rs2004.hunting import prayer_plan, prayer_sip_due, site_for, site_tile_of, stand_for, style_gate, wants_drop

LOOT_BURST_MAX = 8
# How near a dragon has to be for the overhead to go up ahead of the fight.
PRAYER_FIELD_RADIUS = 10
LOOT_SKIP_MS = 30000
LOOT_WAIT_MS = 4000
LOOT_WALK_MS = 30000
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000
SIP_RETRY_MS = 5000
PARK_TICKS = 10
RUNE_ARROW = 892
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']

SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}
SHOW_SPECIAL = {'key': 'combat_style', 'any_of': ['melee', 'range']}
SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}
BEST_WEAPON = 'Best available'
SHOW_SAFESPOT = {'key': 'combat_style', 'any_of': ['mage', 'range']}
SHOW_STAND = {'key': 'site', 'any_of': STAND_SITE_KEYS}
SHOW_BRIMHAVEN = {'key': 'site', 'any_of': [BRIMHAVEN_IRON.key, BRIMHAVEN_STEEL.key]}


def _without(drops, names):
    return [n for n in drops if n.lower() not in names]


DROPS = drop_db().get(TAVERLEY_BLUE.target) or []
# Why: bass is food the run never eats and a coin pile is 11 to 440, so both spend a walk off the safespot that the
# hides pay for better.
DEFAULT_LOOT = _without(DROPS, ['bass', 'coins'])
BLACK_DROPS = drop_db().get('Black dragon') or []
DEFAULT_BLACK_LOOT = _without(BLACK_DROPS, ['coins', 'chocolate cake'])
# Why: the Enclave kills blue dragons and greater demons off one stand, so its loot is the two tables merged.
ENCLAVE_DROPS = sorted(set(DROPS + (drop_db().get('Greater demon') or [])))
# Why: the same rule, plus Ashes and Thread, which a greater demon drops by the pile and neither sells nor stacks.
DEFAULT_ENCLAVE_LOOT = _without(ENCLAVE_DROPS, ['bass', 'coins', 'ashes', 'thread', 'tuna'])
# Why: the bars are the drop the trip is for, five a kill, and a coin pile here is 270 to 990 against a walk of a few
# tiles, so only the bolts and the curry start unticked.
IRON_DROPS = drop_db().get(BRIMHAVEN_IRON.target) or []
DEFAULT_IRON_LOOT = _without(IRON_DROPS, ['bolts', 'curry'])
STEEL_DROPS = drop_db().get(BRIMHAVEN_STEEL.target) or []
DEFAULT_STEEL_LOOT = _without(STEEL_DROPS, ['bolts', 'curry'])

# Why: Taverley blue and the guild pen read the same drop table off the same loot setting, so it shows for either.
SHOW_BLUE = {'key': 'site', 'any_of': [TAVERLEY_BLUE.key, HEROES_BLUE.key]}
SHOW_ENCLAVE = {'key': 'site', 'any_of': [GUTANOTH_BLUE.key]}
SHOW_BLACK = {'key': 'site', 'any_of': [TAVERLEY_BLACK.key]}
SHOW_IRON = {'key': 'site', 'any_of': [BRIMHAVEN_IRON.key]}
SHOW_STEEL = {'key': 'site', 'any_of': [BRIMHAVEN_STEEL.key]}

SETTINGS = {
    'enclave_targets': SettingDef('string', 'both', "Gu'Tanoth targets", options=ENCLAVE_TARGET_OPTIONS, group='Combat', show_if=SHOW_ENCLAVE,
                                  help='dragons, greater demons, or both. Both prefers dragons and kills demons between spawns. Stand 1 can see both for mage and range; melee follows targets into reach'),
    'combat_style': SettingDef('string', 'range', 'Combat style', options=['melee', 'mage', 'range'],
                               help='mage and range fight from a tile no dragon can path to. Melee stands in the dragonfire and needs the Dragonfire shield'),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE),
    'weapon': SettingDef('string', BEST_WEAPON, 'Weapon', options=[BEST_WEAPON] + MELEE_WEAPONS, group='Combat', show_if=SHOW_MELEE,
                         help='Best available wears whatever the bank, the pack or the body holds that ranks highest and the Attack level allows, stab first on the metal dragons; a name pins that weapon. 1-handed, so the shield slot stays free for the Dragonfire shield'),
    'staff': SettingDef('string', 'Staff of fire', 'Staff', options=STAFFS, group='Combat', show_if=SHOW_MAGE),
    'spell': SettingDef('string', 'Fire Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 2000, group='Combat', show_if=SHOW_MAGE),
    'rune_buffer': SettingDef('number', 300, 'Spare runes per type', 0, 2000, group='Combat', show_if=SHOW_MAGE,
                              help='withdrawn on top of the cast budget. Blue dragons drop fire, water, nature and law runes, so looted runes let a trip cast past its budget and drain whichever rune is scarcest. When that is the law rune the escape teleport needs, the way home is the long walk out'),
    'bow': SettingDef('string', 'Maple shortbow', 'Bow', options=BOWS, group='Combat', show_if=SHOW_RANGE),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE),
    'ammo': SettingDef('string', 'Iron arrow', 'Ammo', options=ARROWS, group='Combat', show_if=SHOW_RANGE),
    'ammo_withdraw': SettingDef('number', 500, 'Ammo per bank trip', 1, 5000, group='Combat', show_if=SHOW_RANGE),
    'use_special': SettingDef('boolean', True, 'Use special attacks', group='Combat', show_if=SHOW_SPECIAL,
                              help="arms the spec bar whenever the energy covers the wielded weapon's special, for the swing or the shot about to go out; a staff has none"),
    'use_potions': SettingDef('boolean', True, 'Drink super sets', group='Combat', show_if=SHOW_MELEE,
                              help='sips attack, strength and defence potions once each boost decays to within a tenth of the base level. The loadout carry list sets the dose form and count per trip, otherwise one three-dose flask of each'),
    'pray_melee': SettingDef('boolean', True, 'Pray Protect from Melee on the metal dragons', group='Combat', show_if=SHOW_MELEE,
                             help='the metal dragons stop at ten tiles and breathe, so melee walks to one and fights beside it, where it headbutts for up to 22; the overhead makes that 0 and the shield with a dose takes the close breath. Needs 43 Prayer'),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing'),
    'panic_hp': SettingDef('number', 30, 'Panic-to-bank below HP%', 1, 98, group='Food & healing', help='out of food and this low, the run leaves the lair for the bank'),
    'retreat_hp': SettingDef('number', 50, 'Retreat to a safespot below HP%', 0, 99, group='Food & healing',
                             help='off the safespot and this hurt, the run walks back to the nearest one and heals there. Eating in dragonfire loses the race, so this outranks the bite. An empty pack sends it back whatever the HP, since nothing in the lair heals. 0 turns off both'),
    'food_reserve': SettingDef('number', 4, 'Food kept back from slot-freeing', 0, 27, group='Food & healing',
                               help='a full pack spends food to make room for loot instead of banking, never below this many'),
    'heal_to': SettingDef('number', 90, 'Heal to HP% before heading back', 10, 100, group='Food & healing',
                          help='the walk in is long, so the trip eats up at the booth and tops the food back up after'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot to pick up (drop table)', options=DROPS, group='Banking & loot', show_if=SHOW_BLUE,
                       help='the blue dragon table. Everything picked up is banked. Bass and Coins start unticked because neither pays for the walk off the safespot'),
    'loot_black': SettingDef('string[]', DEFAULT_BLACK_LOOT, 'Loot to pick up (drop table)', options=BLACK_DROPS, group='Banking & loot', show_if=SHOW_BLACK,
                             help='the black dragon table, a different list from the blue one. Everything picked up is banked. Coins and Chocolate cake start unticked because neither pays for the walk off the safespot'),
    'loot_enclave': SettingDef('string[]', DEFAULT_ENCLAVE_LOOT, 'Loot to pick up (drop table)', options=ENCLAVE_DROPS, group='Banking & loot', show_if=SHOW_ENCLAVE,
                               help='the blue dragon and greater demon tables merged, since the stand kills both. Everything picked up is banked. Bass, Coins, Tuna, Ashes and Thread start unticked because none pays for the walk off the safespot'),
    'loot_iron': SettingDef('string[]', DEFAULT_IRON_LOOT, 'Loot to pick up (drop table)', options=IRON_DROPS, group='Banking & loot', show_if=SHOW_IRON,
                            help='the iron dragon table. Every kill drops five Iron bars and the bones, and the coin piles are 270 to 990, so all three start ticked; untick the bars to spend the slots on food. Bolts and Curry start unticked'),
    'loot_steel': SettingDef('string[]', DEFAULT_STEEL_LOOT, 'Loot to pick up (drop table)', options=STEEL_DROPS, group='Banking & loot', show_if=SHOW_STEEL,
                             help='the steel dragon table. Every kill drops five Steel bars and the bones, and the coin piles are 470 to 650, so all three start ticked. Bolts and Curry start unticked'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'bury_bones': SettingDef('boolean', False, 'Bury dragon bones', group='Banking & loot',
                             help='bury Dragon bones for Prayer xp instead of banking them (always looted when on). They are the best drop here, so this trades gold for xp'),
    'ranging_potion': SettingDef('boolean', False, 'Drink a ranging potion', group='Combat', show_if=SHOW_RANGE,
                                 help='sips a dose once the boost decays to within a tenth of the base level. The loadout carry list sets the dose form and the count per trip, otherwise one Ranging potion(3)'),
    'antipoison_doses': SettingDef('number', 1, 'Superantipoison flasks per trip', 0, 4, group='Food & healing', show_if=SHOW_BLACK,
                                   help='the walk to the black dragons passes the dungeon spiders. A dose is drunk on the poison message; 0 carries none'),
    'antifire_doses': SettingDef('number', 3, 'Antifire potion flasks per trip', 0, 6, group='Food & healing', show_if=SHOW_BRIMHAVEN,
                                 help='a metal dragon breathes from ten tiles and the shield alone leaves 5 a breath; a dose on top makes it 0 for six minutes, and the next goes down as the last lapses, so the doses are what a trip burns and three flasks is 72 minutes. The Brimhaven sites carry 8 food a trip while the food knob sits on its default. 0 carries none and the food takes the breaths'),
    'prayer_doses': SettingDef('number', 3, 'Prayer potion flasks per trip', 0, 6, group='Food & healing', show_if=SHOW_BRIMHAVEN,
                               help='melee only. A dose restores a quarter of the level plus seven, and Protect from Melee drains about a point every two seconds beside a dragon'),
    'axe': SettingDef('string', 'Rune axe', 'Axe for the vines', options=[t.name for t in AXES], group='Location', show_if=SHOW_BRIMHAVEN,
                      help='the walk in chops through two vine walls, so an axe rides in the pack every trip; any tier works, a better one chops faster'),
    'solve_clues': SettingDef('boolean', True, 'Solve clue drops', group='Clues', help='blue dragons drop hard clues. The trail leaves the dungeon and comes back'),
    'site': SettingDef('string', 'taverley-blue', 'Dragon site', options=SITE_OPTIONS, group='Location',
                       help="below combat 97 the Taverley baby blues aggress on the walk in, above it they never do. The Heroes' Guild dragon is one adult penned behind a fence. Mage and range attack through it; melee and looting open the gate. The guild doors need Heroes' Quest. The Gu'Tanoth Enclave offers dragons, greater demons or both: the Enclave guard waves you past once Watch Tower is complete, the six stands cover different dragons, stand 1 also reaches greater demons, and the cave shares its floor with greater demons, ogre shamans and chieftains. The Brimhaven Dungeon metal dragons cost Saniboch 875 coins a trip and the walk in chops two vines and crosses stepping stones, a log and a pipe, so it wants Woodcutting 22, Agility 34 and an axe; they park at ten tiles and breathe, so the stand is the open tile that sees the most of them, every style wears the Dragonfire shield with an Antifire dose up, range is refused, iron and steel finish whichever bites, and the trip banks at Ardougne on the Ardougne teleport, which needs Plague City"),
    'rotate_spawns': SettingDef('boolean', False, 'Alternate blue dragon spawns', group='Location', show_if=SHOW_MELEE,
                                help="Taverley and Gu'Tanoth melee search all loaded blue dragons inside the chosen site, preferring spawns killed least recently. Finishes each fight and its loot before moving to the next. Other players' fights are skipped"),
    'stand': SettingDef('number', 1, 'Stand', 1, MAX_STANDS, group='Location', show_if=SHOW_STAND,
                        help="which of the site's numbered stands to fight from, one per dragon. The Enclave has six, listed north, west, north-west, south, east, far east; 1 is the roomiest and the one with a live proof behind it. The iron dragons have two open camps. A number past the end takes the last, and a site with one stand ignores it"),
    'safespot1': SettingDef('tile', TAVERLEY_BLUE.safespots[0], 'Safespot 1', group='Location', show_if=SHOW_SAFESPOT, help='the chosen stand fills these; set one to move it off the derived tile'),
    'safespot2': SettingDef('tile', TAVERLEY_BLUE.safespots[1], 'Safespot 2', group='Location', show_if=SHOW_SAFESPOT,
                            help='the ladder rotates here when a hit lands, or when nothing is in range for 20s'),
    'safespot3': SettingDef('tile', TAVERLEY_BLUE.safespots[2], 'Safespot 3', group='Location', show_if=SHOW_SAFESPOT),
    'melee_tile': SettingDef('tile', TAVERLEY_BLUE.melee_anchor, 'Melee anchor tile', group='Location', show_if=SHOW_MELEE,
                             help='starts here; blue dragon and metal dragon melee follows the target into reach'),
    'bank_tile': SettingDef('tile', TAVERLEY_BLUE.bank, 'Bank stand tile', group='Location'),
    'leave_via': SettingDef('string', 'teleport', 'Leave the lair by', options=['teleport', 'walk'],
                            option_labels={'teleport': 'The escape teleport this site names', 'walk': 'Walk out'}, group='Location',
                            help='the teleport falls back to the walk when the runes or the magic level are short. Each site names the one spell that lands nearest its bank: Falador for Taverley and the guild, Watchtower for the Enclave, Ardougne for Brimhaven'),
    'tele_stock': SettingDef('number', 2, 'Spare escape casts', 0, 10, group='Location', help='casts carried on top of the one needed to leave'),
    'log_detail': SettingDef('string', 'Normal', 'Log detail', options=['Normal', 'Verbose'], group='Diagnostics',
                             help='Verbose adds the loot, slot-freeing and key-state traces'),
}

# The settings the safespot ladder is offered through. A site with more tiles keeps the rest of its own.
SPOT_KEYS = ['safespot1', 'safespot2', 'safespot3']


def site_tile(bag, key, site):
    """The site's own tile, unless the setting has been moved off its schema default."""
    return site_tile_of(SETTINGS, bag, key, site)


def now_ms():
    return time.time() * 1000


def loot_key(g):
    return f'{g.name or ""}@{g.tile().x},{g.tile().z}'


def held_doses(doses):
    return sum([inventory.count(name) for name in doses])


def holding(doses):
    return ', '.join([f'{inventory.count(n)}x {n}' for n in doses if inventory.count(n) > 0]) or 'none'


def potions_held(plan):
    return sum([inventory.count(dose) for dose in plan.potion.doses])


def loot_stacks_into_pack(name):
    """Loot that merges into a stack already held needs no slot."""
    if not name:
        return False
    held = inventory.first(name)
    if held is None:
        return False
    kind = reader.item_type(held.id)
    return held.count > 1 or (kind is not None and kind.stackable)


def find_on(id, tile):
    wanted_id = id
    wanted_tile = tile
    return ground_items.query().where(lambda g: g.id == wanted_id and g.tile().equals(wanted_tile)).first()


def melee_weapon_held():
    """A melee weapon worn or carried, when the pick may settle on one without a bank stop."""
    return known_melee_weapon([i.name or '' for i in equipment.items()]) or known_melee_weapon([i.name or '' for i in inventory.items()])


class LootRun:
    """A loot walk under way: the food dropped for room, as (id, tile), to take back once the pile is clear, whether
    food was eaten for room, and how many times taking it back failed."""

    def __init__(self):
        self.food = []
        self.spent_food = False
        self.recovery_fails = 0


class Parked(Task):
    def __init__(self, bot):
        Task.__init__(self, label='parked')
        self.bot = bot

    def validate(self):
        return self.bot.parked

    def execute(self):
        yield from execution.delay_ticks(PARK_TICKS)


# Why: the poison varp never reaches the client and the poisoning prints its line once per fresh poisoning, so the
# line is the only signal, and the mark moves past it whether or not a dose was there to answer it.
class CurePoison(Task):
    def __init__(self, bot):
        Task.__init__(self, label='cure poison')
        self.bot = bot
        self.mark = game_messages.mark()
        self.warned = False

    def validate(self):
        return self.bot.antipoison_want > 0 and game_messages.saw_since(self.mark, POISONED)

    def execute(self):
        bot = self.bot
        self.mark = game_messages.mark()
        bot.set_status('poisoned, drinking an antipoison')
        drank = yield from bot.drink_antipoison()
        if drank:
            bot.log('poisoned. Drank a Superantipoison')
            self.warned = False
            return
        if not self.warned:
            bot.log('WARNING: poisoned with no Superantipoison in the pack. The food covers it until the bank run.')
            self.warned = True


# Why: a due dose with nothing to drink is what the operator has to hear about, so the empty pack warns once and then
# leaves the loop alone for a minute rather than validating every pass.
class SipAntifire(Task):
    def __init__(self, bot):
        Task.__init__(self, label='sip antifire')
        self.bot = bot
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        return bot.antifire_want > 0 and now_ms() >= self.retry_at and bot.antifire_due()

    def execute(self):
        bot = self.bot
        if held_doses(ANTIFIRE_DOSES) == 0:
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            if not bot.antifire_warned:
                bot.log('WARNING: an Antifire dose is due and the pack holds no flask. The shield holds the breaths to 5 until the bank run.')
                bot.antifire_warned = True
            return
        # Why: a sip sent mid-walk can miss its window, and a minute without a dose is five a breath, so a held flask
        # is tried again in a few seconds.
        sipped = yield from bot.sip_antifire()
        if not sipped:
            self.retry_at = now_ms() + SIP_RETRY_MS
            bot.vlog('the Antifire sip did not land, trying again shortly')


# Why: the overhead spends points every tick it's up, so it goes on when a dragon is in the field and comes off
# outside the lair, where the bank trip would drain a flask for nothing.
class PrayMelee(Task):
    def __init__(self, bot):
        Task.__init__(self, label='pray melee')
        self.bot = bot
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        if bot.prayer_name is None or now_ms() < self.retry_at:
            return False
        want = bot.prayer_wanted()
        return prayer.active(bot.prayer_name) != want and (not want or prayer.available(bot.prayer_name))

    def execute(self):
        done = yield from self.bot.set_overhead(self.bot.prayer_wanted())
        if not done:
            self.retry_at = now_ms() + SIP_RETRY_MS


class SipPrayer(Task):
    def __init__(self, bot):
        Task.__init__(self, label='sip prayer')
        self.bot = bot
        self.retry_at = 0
        self.warned = False

    def validate(self):
        bot = self.bot
        return bot.prayer_want > 0 and now_ms() >= self.retry_at and bot.prayer_due()

    def execute(self):
        bot = self.bot
        if held_doses(PRAYER_DOSES) == 0:
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            if not self.warned:
                bot.log('WARNING: prayer is low and the pack holds no Prayer potion. The overhead drops when it hits 0 and the headbutts land full until the bank run.')
                self.warned = True
            return
        self.warned = False
        sipped = yield from bot.sip_prayer()
        if not sipped:
            self.retry_at = now_ms() + SIP_RETRY_MS


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return self.bot.need_eat()

    def execute(self):
        yield from self.bot.eat_once()


class GearEquip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='gear equip')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def merge_due(self):
        """Whether ammo picked up from the floor goes onto the quiver now."""
        bot = self.bot
        return bot.combat_style == 'range' and equipment.contains(bot.ammo) and inventory.first(bot.ammo) is not None \
            and (bot.has_food() or bot.recoverable_food()) and not bot.need_eat() and not bot.too_hurt_to_loot() and not bot.died \
            and not event_signal.pending()

    def _missing(self):
        bot = self.bot
        wear = ([SHIELD] if needs_shield(bot.site, bot.combat_style) else []) + [bot.weapon, bot.ammo if bot.combat_style == 'range' else '']
        for name in wear:
            if name != '' and not equipment.contains(name) and inventory.first(name) is not None:
                return name
        return bot.ammo if self.merge_due() else None

    def validate(self):
        return now_ms() >= self.retry_at and self._missing() is not None

    def execute(self):
        bot = self.bot
        item = self._missing()
        if item is None:
            return
        bot.set_status(f'equipping {item}')
        equipped = False
        if bot.combat_style == 'range' and item == bot.ammo and equipment.contains(bot.ammo):
            closed = True
            if bank.is_open():
                closed = yield from bank.close()
            if closed:
                ammo = inventory.first(bot.ammo)
                op = None
                for action in (ammo.actions() if ammo is not None else []):
                    lower = action.lower()
                    if 'wield' in lower or 'wear' in lower or 'equip' in lower:
                        op = action
                        break
                before = inventory.count(bot.ammo)
                worn = bot.quiver_count()
                if ammo is not None and op is not None and self.merge_due() and ammo.interact(op):
                    equipped = yield from execution.delay_until(lambda: inventory.count(bot.ammo) < before and bot.quiver_count() > worn, 3000)
        else:
            equipped = yield from equipment.equip(item)
        if equipped:
            bot.log(f'equipped {item}')
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            # Why: a wield the engine refuses is a level or a quest short, and a picked weapon has a next best behind
            # it; a pinned one only has the retry.
            if bot.weapon_picked and item == bot.weapon:
                bot.unusable_weapons.add(item)
                bot.weapon = ''
                bot.log(f'{item} will not go on, a level or a quest short. Picking another at the bank.')
                return
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f'could not equip {item}. Retrying in {ASSERT_RETRY_MS // 1000}s.')


class SetAttackStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='set attack style')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def _selected(self):
        bot = self.bot
        return game.combat_mode() == bot.range_mode if bot.combat_style == 'range' else game.has_combat_style(bot.melee_style)

    def validate(self):
        return self.bot.combat_style != 'mage' and not self._selected() and now_ms() >= self.retry_at

    def execute(self):
        bot = self.bot
        bot.set_status('setting the combat style')
        if bot.combat_style == 'range':
            game.set_combat_mode(bot.range_mode)
        else:
            game.set_combat_style(bot.melee_style)
        ok = yield from execution.delay_until(lambda: self._selected(), 3000)
        if ok:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f'could not set the {bot.combat_style} attack style. Retrying in {ASSERT_RETRY_MS // 1000}s.')


class SetRetaliate(Task):
    """Auto retaliate on where two metal dragons breathe at the stand, so whichever bites gets the casts; off for a
    chase, which retaliating to a bite from ten tiles walked off its own dragon."""

    def __init__(self, bot):
        Task.__init__(self, label='set retaliate')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        controlled = bot.site.fire_at_range == True or chases_target(bot.site, bot.combat_style)
        return controlled and game.auto_retaliate_on() != bot.retaliate_wanted() and now_ms() >= self.retry_at

    def execute(self):
        bot = self.bot
        want = bot.retaliate_wanted()
        bot.set_status(f"turning auto-retaliate {'on' if want else 'off'}")
        game.set_auto_retaliate(want)
        done = yield from execution.delay_until(lambda: game.auto_retaliate_on() == want, 3000)
        if done:
            bot.log('auto-retaliate on, so whichever dragon bites gets the casts and the fight follows it' if want
                    else 'auto-retaliate off; the script handles target selection')
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f"could not turn auto-retaliate {'on' if want else 'off'}. Retrying in {ASSERT_RETRY_MS // 1000}s.")


class ArmAutocast(Task):
    def __init__(self, bot):
        Task.__init__(self, label='arm autocast')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        if bot.combat_style != 'mage' or autocast.armed() or now_ms() < self.retry_at or bot.casts_left() < 1:
            return False
        return autocast.staff_tab_attached() or (bot.weapon != '' and equipment.contains(bot.weapon))

    def execute(self):
        bot = self.bot
        bot.set_status(f'arming autocast: {bot.spell}')
        yield from execution.delay_ticks(3)
        armed = yield from autocast.arm(bot.spell, lambda m: bot.log(m))
        if armed:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f"WARNING: could not arm autocast for '{bot.spell}'. Retrying in {ASSERT_RETRY_MS // 1000}s.")


# Why: Fight owns the bot for a kill, so a sibling task only lands between kills and on the walks, which is often
# enough for a boost that decays over minutes.
class SipPotion(Task):
    def __init__(self, bot):
        Task.__init__(self, label='sip potion')
        self.bot = bot
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        # Why: a boost drunk at the bank has faded by the time the walk in ends, so a dose is sipped only inside the
        # lair; an empty vial is dropped wherever it is.
        return len(bot.potions) > 0 and now_ms() >= self.retry_at and (inventory.contains(EMPTY_VIAL) or (bot.site.in_area(game.tile()) and bot.sip_due() is not None))

    def execute(self):
        bot = self.bot
        dropped = yield from bot.drop_vial()
        if dropped:
            return
        for _ in range(len(bot.potions)):
            if event_signal.pending() or bot.died:
                return
            if bot.sip_due() is None:
                if inventory.contains(EMPTY_VIAL):
                    self.retry_at = now_ms() + ASSERT_RETRY_MS
                return
            sipped = yield from self._sip()
            if not sipped:
                self.retry_at = now_ms() + ASSERT_RETRY_MS
                return
            yield from execution.delay_ticks(2)
            yield from sustain.run()

    def _sip(self):
        bot = self.bot
        plan = bot.sip_due()
        dose = None
        if plan is not None:
            for name in plan.potion.doses:
                if inventory.first(name) is not None:
                    dose = inventory.first(name)
                    break
        if plan is None or dose is None:
            return False
        skill = plan.potion.skill
        name = dose.name or plan.flask
        before = skills.effective(skill)
        bot.set_status(f'drinking {name}')
        if not dose.interact('Drink'):
            return False
        took = yield from execution.delay_until_ticks(lambda: skills.effective(skill) > before, 3)
        if not took:
            return False
        bot.sips += 1
        bot.log(f'drank {name}, {skill} {before} to {skills.effective(skill)}')
        return True


class PanicBank(Task):
    def __init__(self, bot):
        Task.__init__(self, label='panic bank')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return not bot.parked and not bot.bank_empty and skills.hp_fraction() < bot.panic_at and not bot.has_food()

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.set_status('panicking, retreating to the bank')
        bot.log(f'panic at {round(skills.hp_fraction() * 100)}% hp with no food. Banking.')
        yield from bot.bank_trip()


class BuryBones(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bury bones')
        self.bot = bot
        self.fails = 0
        bot.burial_retry_at = 0

    def validate(self):
        bot = self.bot
        return bot.burial_available() and inventory.contains(bot.site.bones)

    def execute(self):
        bot = self.bot
        bones = inventory.first(bot.site.bones)
        if bones is None:
            return
        bot.set_status(f'burying {bot.site.bones}')
        before = inventory.used()
        if bones.interact('Bury'):
            buried = yield from execution.delay_until(lambda: inventory.used() < before, 3000)
            if buried:
                bot.buried += 1
                self.fails = 0
                return
        yield from execution.delay_ticks(2)
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            bot.burial_retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f'could not bury {bot.site.bones}. Pausing burial for {ASSERT_RETRY_MS // 1000}s.')


class FreeSlot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='free slot')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.loot_ready() and bot.slot_action(bot.find_loot()) != 'none'

    def execute(self):
        yield from self.bot.free_slot()


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.parked:
            return False
        if not bot.shield_ready() and inventory.count(SHIELD) == 0:
            return True
        run = bot.loot_run
        returning = run is not None and (inventory.is_full() or run.spent_food or bot.recoverable_food())
        if not bot.has_food() and not bot.bank_empty and not (bot.combat_style != 'melee' and bot.site.ranged_threat != True and returning and bot.loot_can_progress()):
            return True
        if bot.need_style_supplies() and not bot.supply_empty:
            return True
        # Why: the fee is spent on the way in, so a pack short of it outside the dungeon has nowhere to go but the booth.
        if bot.need_coins() and not bot.site.in_area(game.tile()) and not bot.supply_empty:
            return True
        # Why: food is a resource the run spends and FreeSlot turns it into room, so a pack full of food is no reason to
        # walk to Falador.
        return inventory.is_full() and bot.food_count() <= bot.slot_food_reserve() and not bot.loot_can_progress()

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.set_status('banking, restocking')
        casts = f', casts {bot.casts_left()}' if bot.combat_style == 'mage' else ''
        ammo = f', ammo {bot.ammo_left()}' if bot.combat_style == 'range' else ''
        coins = '' if bot.site.coins is None else f', coins {inventory.count(COINS)}'
        bot.log(f'banking (food {bot.food_count()}{casts}{ammo}{coins})')
        yield from bot.bank_trip()


class LootCorpse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot corpse')
        self.bot = bot

    def validate(self):
        return self.bot.loot_can_progress()

    def execute(self):
        yield from self.bot.loot_burst()


# Why: fetching from Velrak can leave the key in hand behind a cell door that won't open, a dead end nothing else
# walks out of.
class AcquireKey(Task):
    def __init__(self, bot):
        Task.__init__(self, label='acquire key')
        self.bot = bot

    def validate(self):
        bot = self.bot
        item = bot.site.key_item
        if item is None or bot.parked:
            return False
        return in_cell() or key_status(inventory.count_by_id(item.id), bank.count_by_id(item.id)) != 'held'

    def execute(self):
        bot = self.bot
        if in_cell():
            bot.set_status('leaving the jail cell')
            out = yield from leave_cell(bot)
            if not out:
                bot.log('the cell door would not open from the inside. Retrying.')
                return
            bot.log('out of the cell')
        bot.key_state = yield from acquire_key(bot, bot.site)
        bot.vlog(f'key state: {bot.key_state}')


class EnterLair(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter lair')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.parked or not bot.shield_ready() or bot.site.in_area(game.tile()) or skills.hp_fraction() < bot.panic_at or bot.need_coins():
            return False
        return bot.site.key_item is None or inventory.count_by_id(bot.site.key_item.id) > 0

    def execute(self):
        yield from enter_lair(self.bot, self.bot.site)


class JiveDragons(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.kills = 0
        self.bank_trips = 0
        self.looted = 0
        self.loot_counts = {}
        self.loot_skip = {}
        self.safespot_idx = 0
        self.key_state = 'fetch'
        self.buried = 0
        self.sips = 0
        self.specials = 0
        self.parked = False
        self.park_reason = ''
        self.died = False
        self.target_idx = None
        self.loot_run = None
        self.burial_retry_at = 0
        self.bank_empty = False
        self.supply_empty = False
        self.unusable_weapons = set()
        self.antifire_until = 0
        self.antifire_mark = game_messages.mark()
        self.antifire_warned = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        base = enclave_targets(site_for(s.str('site', 'taverley-blue')), s.str('enclave_targets', 'both'))
        stands = len(base.stands) if base.stands else 1
        self.active_stand = min(max(1, int(s.num('stand', 1))), stands)
        stand = stand_for(base, self.active_stand)
        spots = []
        for i in range(len(stand.tiles)):
            spots.append(site_tile(s, SPOT_KEYS[i] if i < len(SPOT_KEYS) else None, stand.tiles[i]))
        self.site = base.with_changes(safespots=spots, melee_anchor=site_tile(s, 'melee_tile', stand.anchor), bank=site_tile(s, 'bank_tile', base.bank))
        site = self.site
        if stands > 1:
            self.log(f"standing at {stand.label}, stand {s.num('stand', 1)} of {stands}")
        self.combat_style = s.str('combat_style', 'range')
        self.roaming = s.bool('rotate_spawns', False)
        self.melee_style = parse_combat_style(s.str('melee_style', 'strength'))
        self.range_mode = parse_range_style(s.str('range_style', 'rapid'))
        self.spell = s.str('spell', 'Fire Strike')
        self.ammo = s.str('ammo', 'Iron arrow')
        if self.combat_style == 'mage':
            self.weapon = s.str('staff', 'Staff of fire')
        elif self.combat_style == 'range':
            self.weapon = s.str('bow', 'Maple shortbow')
        else:
            self.weapon = s.str('weapon', BEST_WEAPON)
        self.weapon_picked = self.combat_style == 'melee' and self.weapon == BEST_WEAPON
        if self.weapon_picked:
            self.weapon = melee_weapon_held() or ''
        self.food = script_food(s, site.food or 'Lobster')
        self.leave_walk = s.str('leave_via', 'teleport') == 'walk'
        escape = 'walk out' if self.leave_walk else escape_runes_for(site.escape_teleport_id).label
        self.bury = s.bool('bury_bones', False) and site.bones != 'Ashes'
        self.solve_clues = s.bool('solve_clues', True)
        self.panic_at = s.num('panic_hp', 30) / 100
        self.retreat_at = s.num('retreat_hp', 50) / 100
        self.rune_casts = s.num('runes_withdraw', 150)
        self.rune_buffer = s.num('rune_buffer', 300)
        self.ammo_withdraw = s.num('ammo_withdraw', 500)
        # Why: the food setting is one for every site, so a site with its own figure takes it only while the setting
        # sits on its default.
        food_knob = s.num('food_withdraw', 20)
        self.food_withdraw_count = site.food_per_trip if site.food_per_trip is not None and food_knob == SETTINGS['food_withdraw'].default else food_knob
        self.food_reserve = s.num('food_reserve', 4)
        self.escape_stock = s.num('tele_stock', 2)
        self.heal_to = s.num('heal_to', 90) / 100
        # Why: each site names the loot setting whose choices are its own drop table, and its default is that list.
        loot_setting = site.loot_setting or 'loot'
        definition = SETTINGS.get(loot_setting)
        loot_default = definition.default if definition is not None else DEFAULT_LOOT
        self.loot_set = set([n.lower() for n in s.list(loot_setting, loot_default)])
        # Why: fired arrows land where the dragon dies and are on no drop table, so the 500 a trip withdraws come home
        # only if the loot set names them.
        if self.combat_style == 'range':
            self.loot_set.add(self.ammo.lower())
        self.bank_common = s.bool('bank_common_junk', True)
        self.verbose = s.str('log_detail', 'Normal') == 'Verbose'
        self.use_special = s.bool('use_special', True)
        carry = supplies_of(selected_loadout(s))
        if self.combat_style == 'melee' and s.bool('use_potions', True):
            self.potions = planned_potions(carry, SUPER_SET)
        elif self.combat_style == 'range' and s.bool('ranging_potion', False):
            self.potions = [ranging_plan(carry)]
        else:
            self.potions = []
        self.antipoison_want = s.num('antipoison_doses', 1) if site.antipoison == True else 0
        self.antifire_want = s.num('antifire_doses', 1) if site.antifire == True else 0
        self.prayer_name = prayer_for(self.combat_style, site.fire_at_range == True) if s.bool('pray_melee', True) else None
        self.prayer_want = 0 if self.prayer_name is None else s.num('prayer_doses', 3)
        if self.prayer_name is not None and not prayer.known(self.prayer_name):
            self.prayer_name = None
        self.axe = s.str('axe', 'Rune axe') if site.axe == True else ''
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in COMBAT_SKILLS])
        item = site.key_item
        self.key_state = 'held' if item is None else key_status(inventory.count_by_id(item.id), bank.count_by_id(item.id))
        gate = style_gate(self.combat_style, site.fire_at_range == True)
        if gate is not None:
            self.park_for(gate)
        weapon = '' if self.weapon == '' else f' w/ {self.weapon}'
        spell = f' ({self.spell})' if self.combat_style == 'mage' else ''
        burying = f', burying {site.bones}' if self.bury else ''
        self.log(f"JiveDragons: {site.label}, style {self.combat_style}{weapon}{spell}, food '{self.food}' (retreat<{round(self.retreat_at * 100)}%, "
                 + f"panic<{round(self.panic_at * 100)}%), escape {escape}, clues {'on' if self.solve_clues else 'off'}{burying}, bank {site.bank}")
        self.vlog(f"safespots [{' '.join([str(t) for t in site.safespots])}], melee anchor {site.melee_anchor}, loot [{', '.join(sorted(self.loot_set))}]")
        if self.prayer_name is not None:
            if prayer.max() >= 43:
                self.log(f'melee here chases the dragon from {site.melee_anchor} and prays {self.prayer_name}, {self.prayer_want} Prayer flask(s) a trip')
            else:
                self.log(f'WARNING: {self.prayer_name} needs 43 Prayer and this character has {prayer.max()}, so the headbutts land; melee here chases the dragon and eats through them')

        # Why: the hunting framework's waits, idle ticks and walks all pump sustain, and with no hook they stood in
        # dragonfire without taking a bite. A fight holds the loop for two minutes and a walk out longer, so the
        # antifire and the prayer pool are kept up from inside them too.
        def upkeep():
            if self.need_eat():
                yield from self.eat_once()
            if self.antifire_want > 0 and held_doses(ANTIFIRE_DOSES) > 0 and self.antifire_due():
                yield from self.sip_antifire()
            if self.prayer_name is not None:
                if self.prayer_want > 0 and held_doses(PRAYER_DOSES) > 0 and self.prayer_due():
                    yield from self.sip_prayer()
                yield from self.set_overhead(self.prayer_wanted())

        sustain.set(upkeep)
        self.fight = Fight(self, site)
        self.gear_equip = GearEquip(self)
        self.add(
            Parked(self), ContinueDialog(),
            DeathRecovery(self, site.bank, 6, on_death=self.died_now, on_recovered=self.recovered),
            Retreat(self, site), Eat(self), CurePoison(self), SipAntifire(self), SipPrayer(self), PrayMelee(self), self.gear_equip, SetAttackStyle(self),
            SetRetaliate(self), ArmAutocast(self), SipPotion(self), PanicBank(self), BuryBones(self), FreeSlot(self), BankRun(self), LootCorpse(self),
            AcquireKey(self), EnterLair(self), WalkToSpot(self, site), HoldSafespot(self, site), self.fight,
        )

    def died_now(self):
        self.fight.reset()
        self.loot_run = None
        self.died = True
        self.set_status('died, recovering')
        self.log('died! recovering')

    def recovered(self):
        self.died = False

    def recovery_anchor(self):
        # Why: from a fee-gated camp the bank is out through the whole dungeon and another payment, so inside the lair
        # the stand is the anchor and a wedge there starts the loop again in place.
        if self.site.in_area(game.tile()):
            return self.site.safespots[0] if self.site.safespots else self.site.bank
        return self.site.bank

    def grind_targets(self):
        return [n.lower() for n in hunt_names(self.site)]

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(skill) for skill in COMBAT_SKILLS]) - self.xp_at_start
        report = {
            'Status': self.status,
            'Kills': self.kills,
            'Kills/hr': round(self.kills * 60 / minutes) if minutes > 0.5 else '-',
            'Looted': self.looted,
            'Bank trips': self.bank_trips,
            'Food': self.food_count(),
            'Key': self.key_state,
            'Stand': self.active_stand,
            'Safespot': self.safespot_idx,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }
        if self.antifire_want > 0:
            report['Antifire'] = f'{held_doses(ANTIFIRE_DOSES)} held, {max(0, self.antifire_until - game.tick())} ticks left'
        if self.prayer_name is not None:
            report['Prayer'] = f'{prayer.points()}/{prayer.max()}'
        if self.parked:
            report['Parked'] = self.park_reason
        return report

    # The host the hunting framework drives

    def set_status(self, text):
        self.status = text

    def vlog(self, message):
        if self.verbose:
            self.log(message)

    def park_for(self, reason):
        if self.parked:
            return
        self.parked = True
        self.park_reason = reason
        self.set_status('parked')
        self.log(f'PARKED: {reason}')

    def rotate_spawns(self):
        return self.roaming and self.combat_style == 'melee' and self.site.target == 'Blue dragon' and self.site.key in [TAVERLEY_BLUE.key, GUTANOTH_BLUE.key]

    def style(self):
        return self.combat_style

    def shield_ready(self):
        return not needs_shield(self.site, self.combat_style) or equipment.contains(SHIELD)

    def food_name(self):
        return self.food

    def food_withdraw(self):
        return self.food_withdraw_count

    def pick_weapon(self, available):
        if not self.weapon_picked:
            return
        attack = skills.level('attack')
        chosen = best_melee_weapon(available, attack, self.site.fire_at_range == True, self.unusable_weapons)
        if chosen is None:
            self.park_for(f'no melee weapon the character can wield at {attack} Attack is in the bank, the pack or worn. Deposit one and resume.')
            return
        if chosen != self.weapon:
            stab = ', stab first for the metal dragons' if self.site.fire_at_range == True else ''
            self.log(f'weapon: {chosen}, the best on hand at {attack} Attack{stab}')
            self.weapon = chosen

    def weapon_name(self):
        return self.weapon

    def ammo_name(self):
        return self.ammo

    def spell_name(self):
        return self.spell

    def keep_extra(self):
        extra = keep_doses(self.potion_keep_names(), ANTIPOISON_DOSES, self.antipoison_want > 0)
        if self.antifire_want > 0:
            extra = extra + ANTIFIRE_DOSES
        if self.prayer_want > 0:
            extra = extra + PRAYER_DOSES
        if self.axe != '':
            extra = extra + [self.axe]
        return extra

    def leave_by_walk(self):
        return self.leave_walk

    def hp_fraction(self):
        return skills.hp_fraction()

    def panic_hp(self):
        return self.panic_at

    def retreat_hp(self):
        return self.retreat_at

    def food_count(self):
        return food_count(inventory.items(), self.food)

    def has_food(self):
        return self.food_count() > 0

    def need_eat(self):
        if not self.has_food():
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food), self.food_count())

    def eat_once(self):
        food = None
        for item in inventory.items():
            if is_edible_food(item, self.food):
                food = item
                break
        if food is None:
            return False
        self.set_status(f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)')
        before = skills.effective('hitpoints')
        id = food.id
        count = inventory.count_by_id(id)
        if not food.interact('Eat'):
            return False
        ate = yield from execution.delay_until_ticks(lambda: inventory.count_by_id(id) < count or skills.effective('hitpoints') > before, 2)
        return ate

    def arm_special(self):
        """A staff has no special, and a weapon without one has no bar to click."""
        if not self.use_special or self.combat_style == 'mage' or special.armed():
            return
        if not special.ready(self.weapon) or not equipment.contains(self.weapon):
            return
        armed = yield from special.arm()
        if armed:
            self.specials += 1
            self.log(f'special armed ({special.energy()} energy left)')

    def bury_bones(self):
        return self.bury

    def bone_name(self):
        return self.site.bones

    def safespot_index(self):
        return self.safespot_idx

    def set_safespot_index(self, n):
        self.safespot_idx = n

    def count_kill(self):
        self.kills += 1

    def count_burial(self):
        self.buried += 1

    def count_bank_trip(self):
        self.bank_trips += 1

    # Supplies

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), lambda rune: inventory.count(rune))

    def quiver_count(self):
        wanted = self.ammo.lower()
        for item in equipment.items():
            if (item.name or '').lower() == wanted:
                return item.count
        return 0

    def ammo_left(self):
        return self.quiver_count() + inventory.count(self.ammo)

    def need_style_supplies(self):
        if self.combat_style == 'mage':
            return self.casts_left() < 1
        # Why: a melee run with its weapon in the bank walked in and fought with its fists, since nothing on the bank
        # list was about the weapon.
        if self.combat_style == 'melee':
            return self.weapon == '' or (not equipment.contains(self.weapon) and inventory.first(self.weapon) is None)
        return self.combat_style == 'range' and self.ammo_left() == 0

    def need_coins(self):
        """Whether the pack is short of the coins the way in costs; a fee already paid needs none."""
        fee = self.site.fee_gate
        return fee is not None and not fee_prepaid(self.site) and inventory.count(COINS) < fee.coins

    def potion_keep_names(self):
        names = []
        for plan in self.potions:
            if self.combat_style == 'melee':
                names.append(plan.flask)
            else:
                names.extend(plan.potion.doses)
        return names

    def sip_due(self):
        return potion_to_sip(self.potions, potions_held, lambda skill: (skills.level(skill), skills.effective(skill)))

    def drop_vial(self):
        vial = inventory.first(EMPTY_VIAL)
        if vial is None:
            return False
        self.set_status(f'dropping an empty {EMPTY_VIAL}')
        before = inventory.used()
        if not vial.interact('Drop'):
            return False
        dropped = yield from execution.delay_until_ticks(lambda: inventory.used() < before, 3)
        return dropped

    def drink_antipoison(self):
        """Drinks the smallest antipoison flask held. False with none in the pack."""
        name = dose_to_drink(lambda n: inventory.count(n))
        dose = inventory.first(name) if name is not None else None
        if name is None or dose is None:
            return False
        # Why: a sip turns the (4) into a (3), so the flask count never moves; the dose form's own count drops.
        before = inventory.count(name)
        if not dose.interact('Drink'):
            return False
        drank = yield from execution.delay_until(lambda: inventory.count(name) < before, 3000)
        return drank

    # Antifire: `%dragonresist` never reaches the client, so the lapse is kept as a tick from the sip, and a breath
    # the shield took with no potion line after it resets the clock to now.

    def note_breaths(self):
        if antifire_lapsed(game_messages.saw_since(self.antifire_mark, SHIELD_ABSORBS), game_messages.saw_since(self.antifire_mark, POTION_PROTECTS)):
            self.antifire_until = 0
        self.antifire_mark = game_messages.mark()

    def antifire_due(self):
        self.note_breaths()
        return antifire_due(self.site.in_area(game.tile()), game.tick(), self.antifire_until)

    def sip_antifire(self):
        """Drinks the smallest Antifire flask held and starts the clock. False with none in the pack."""
        name = dose_to_drink(lambda n: inventory.count(n), ANTIFIRE_DOSES)
        dose = inventory.first(name) if name is not None else None
        if name is None or dose is None:
            return False
        # Why: the sip runs inside walks and fights through sustain, so the status goes back to whatever was up.
        status = self.status
        self.set_status('drinking an Antifire potion')
        before = inventory.count(name)
        drunk = dose.interact('Drink')
        if drunk:
            drunk = yield from execution.delay_until(lambda: inventory.count(name) < before, 3000)
        self.set_status(status)
        if not drunk:
            return False
        self.antifire_until = game.tick() + ANTIFIRE_TICKS
        self.antifire_warned = False
        minutes = round((ANTIFIRE_TICKS - ANTIFIRE_MARGIN_TICKS) * 0.6 / 60)
        self.log(f'drank {name}, the next dose in {minutes} minutes (holding {holding(ANTIFIRE_DOSES)})')
        return True

    # Prayer

    def adult_in_field(self):
        """Whether a dragon the run hunts stands inside the fight's field of the bot."""
        names = hunt_names(self.site)
        return len(npcs.query().where(lambda n: (n.name or '') in names).within(PRAYER_FIELD_RADIUS).results()) > 0

    def prayer_wanted(self):
        """Whether the overhead should be up: inside the lair with a dragon in reach or a fight live."""
        return self.prayer_name is not None and self.site.in_area(game.tile()) and (self.target_idx is not None or self.adult_in_field())

    def prayer_due(self):
        return self.prayer_name is not None and self.site.in_area(game.tile()) and prayer_sip_due(prayer.points(), prayer.max())

    # Why: sustain flips the overhead from inside walks and fights and the task flips it between them, so one helper
    # carries the log line.
    def set_overhead(self, want):
        """Puts the overhead up or takes it down, saying so once per change. False when the toggle didn't land."""
        name = self.prayer_name
        if name is None or prayer.active(name) == want or (want and not prayer.available(name)):
            return True
        done = yield from prayer.set(name, want)
        if not done:
            return False
        self.log(f'praying {name} ({prayer.points()}/{prayer.max()})' if want else f'{name} off, nothing in reach')
        return True

    def sip_prayer(self):
        """Drinks the smallest Prayer flask held and puts the overhead back if the pool ran dry mid-fight."""
        name = dose_to_drink(lambda n: inventory.count(n), PRAYER_DOSES)
        dose = inventory.first(name) if name is not None else None
        if name is None or dose is None:
            return False
        status = self.status
        self.set_status('drinking a Prayer potion')
        before = inventory.count(name)
        drunk = dose.interact('Drink')
        if drunk:
            drunk = yield from execution.delay_until(lambda: inventory.count(name) < before, 3000)
        self.set_status(status)
        if not drunk:
            return False
        self.log(f'drank {name}, prayer {prayer.points()}/{prayer.max()} (holding {holding(PRAYER_DOSES)})')
        yield from self.set_overhead(self.prayer_wanted())
        return True

    # Why: on the metal dragons two breathe at the stand at once and losing either's aggro is harder than killing it,
    # so auto retaliate stays on; a chase stands beside its own dragon and keeps it off.
    def retaliate_wanted(self):
        return self.site.fire_at_range == True and not chase_mode(self.combat_style, True)

    # The bank

    def bank_opts(self):
        """Every setting bank_routine reads."""
        flasks = []
        if self.antipoison_want > 0:
            flasks.append(antipoison_plan(self.antipoison_want))
        if self.antifire_want > 0:
            flasks.append(antifire_plan(self.antifire_want))
        if self.prayer_want > 0:
            flasks.append(prayer_plan(self.prayer_want))
        return BankOpts(withdraw_food=True, rune_casts=self.rune_casts, rune_buffer=self.rune_buffer, ammo=self.ammo_withdraw, escape_stock=self.escape_stock,
                        heal_to=self.heal_to, potions=self.potions, flasks=flasks, carry=[self.axe] if self.site.axe == True and self.axe != '' else [])

    # Why: bank_routine counts a trip only where it runs to the end, so the counter moving tells an empty bank from a
    # walk that never got there.
    def bank_trip(self):
        """Takes the trip, and notes what it came back with when it finished."""
        self.fight.reset()
        self.loot_run = None
        before = self.bank_trips
        yield from bank_routine(self, self.site, self.bank_opts())
        if self.bank_trips > before:
            self.note_trip(self.has_food(), not self.need_style_supplies())

    # Why: a finished trip with no food is the one state the run can't fix from inside, so it stops at the booth
    # rather than walking back unable to heal.
    def note_trip(self, food, supplies):
        self.bank_empty = not food
        self.supply_empty = not supplies
        if not food:
            self.park_for(f"no '{self.food}' left in the bank after a full trip. The run stopped at the booth rather than walk back to the dragons "
                          + 'with no way to heal. Deposit food, or point the loadout at food the bank has, and restart.')

    # Loot

    def loot_filter(self):
        return Record({'loot': self.loot_set, 'bank_common': self.bank_common, 'solve_clues': self.solve_clues, 'bury_bones': self.bury,
                       'bone_name': self.site.bones})

    def too_hurt_to_loot(self):
        return loot_halts(skills.hp_fraction(), self.panic_at, self.retreat_at)

    def slot_food_reserve(self):
        return 0 if self.combat_style != 'melee' and self.site.ranged_threat != True and not self.too_hurt_to_loot() else self.food_reserve

    def burial_available(self):
        return self.bury and now_ms() >= self.burial_retry_at

    def find_loot(self):
        now = now_ms()
        stacks_only = inventory.is_full() and self.food_count() <= self.slot_food_reserve()
        bones = self.site.bones.lower()
        f = self.loot_filter()
        burial = self.burial_available()
        few_rune_arrows = self.site.key == TAVERLEY_BLUE.key and self.combat_style == 'range'

        def wanted(g):
            name = (g.name or '').lower()
            if not self.site.in_area(g.tile()) or self.loot_skip.get(loot_key(g), 0) >= now or not wants_drop(g, f):
                return False
            if few_rune_arrows and g.id == RUNE_ARROW and g.count < 4:
                return False
            if self.bury and not burial and name == bones:
                return False
            return not stacks_only or loot_stacks_into_pack(g.name)

        drops = ground_items.query().where(wanted).within(loot_reach(self.site.fire_at_range == True)).results()

        def rank(g):
            name = (g.name or '').lower()
            first = 0 if not self.bury else (0 if name == bones else (1 if name == 'dragonhide' else 2))
            return (first, g.distance())

        drops.sort(key=rank)
        return drops[0] if drops else None

    def recoverable_food(self):
        run = self.loot_run
        if run is None:
            return False
        for food in run.food:
            if find_on(food[0], food[1]) is not None:
                return True
        return False

    def loot_ready(self):
        return not event_signal.pending() and not self.died and not self.fight.blocks_loot() and (self.combat_style != 'range' or not self.need_style_supplies()) \
            and not self.need_eat() and not self.too_hurt_to_loot()

    def loot_can_progress(self):
        if not self.loot_ready() or (self.burial_available() and inventory.contains(self.site.bones)):
            return False
        drop = self.find_loot()
        return self.loot_run is not None or (drop is not None and (not inventory.is_full() or loot_stacks_into_pack(drop.name)))

    def return_from_loot(self):
        if self.combat_style == 'melee':
            return True
        anchor = anchor_for(self.site, self.combat_style, self.safespot_idx)
        here = game.tile()
        if here is not None and anchor.equals(here):
            return True
        if not self.loot_ready():
            return False
        self.fight.interrupt_watch()
        yield from traversal.walk_resilient(anchor, radius=0, attempts=3, timeout_ms=LOOT_WALK_MS)
        arrived = game.tile()
        return arrived is not None and anchor.equals(arrived) and self.loot_ready()

    def defer_loot_recovery(self):
        run = self.loot_run
        if run is None or not self.loot_ready():
            return
        run.recovery_fails += 1
        if run.recovery_fails >= ASSERT_BATCH:
            self.loot_run = None

    def finish_loot(self):
        """Back on the stand once the pile is clear, the ammo picked up goes on, and the food dropped for room is taken
        back."""
        run = self.loot_run
        if run is None:
            return
        back = yield from self.return_from_loot()
        if not back or self.find_loot() is not None:
            self.defer_loot_recovery()
            return
        if self.gear_equip.merge_due() and self.gear_equip.validate():
            yield from self.gear_equip.execute()
        while len(run.food) > 0:
            if not self.loot_ready():
                return
            if inventory.is_full():
                self.loot_run = None
                return
            id, tile = run.food[0]
            drop = find_on(id, tile)
            if drop is None:
                run.food.pop(0)
                continue
            here = game.tile()
            if here is None or not tile.equals(here):
                self.defer_loot_recovery()
                return
            before = inventory.count_by_id(id)
            took = drop.interact('Take')
            if took:
                took = yield from execution.delay_until(lambda: inventory.count_by_id(id) > before, LOOT_WAIT_MS)
            if not took:
                self.defer_loot_recovery()
                return
            run.food.pop(0)
        self.loot_run = None

    def slot_action(self, drop):
        """Trades a food slot for a loot slot: 'eat', 'drop' or 'none'. Eating wins while the heal isn't wasted, and
        at full hp the food is dropped instead."""
        if drop is None or not inventory.is_full() or loot_stacks_into_pack(drop.name):
            return 'none'
        if self.food_count() <= self.slot_food_reserve():
            return 'none'
        return 'eat' if skills.hp_fraction() < 1 else 'drop'

    # Why: a Take click walks on the scene's own collision and never opens a door, so a drop behind one dies on the
    # click; the Heroes' Guild dragon drops inside its pen, past the gate.
    def reach_drop(self, drop):
        """Walks to a drop the Take click can't path to, opening whatever is in the way."""
        tile = drop.tile()
        if reachability.can_reach(tile):
            return
        self.vlog(f"{drop.name or 'loot'} at {tile} is behind something the Take click cannot open. Walking to it.")
        yield from traversal.walk_resilient(tile, radius=1, attempts=3, timeout_ms=LOOT_WALK_MS, log=lambda m: self.vlog(f'  {m}'))

    def loot_once(self):
        if not self.loot_ready():
            return False
        drop = self.find_loot()
        if drop is None or (inventory.is_full() and not loot_stacks_into_pack(drop.name)):
            return False
        if self.loot_run is None:
            self.loot_run = LootRun()
        self.fight.interrupt_watch()
        name = drop.name or ''
        self.set_status(f'looting {name}')
        yield from self.reach_drop(drop)
        if not self.loot_ready() or (inventory.is_full() and not loot_stacks_into_pack(drop.name)):
            return False
        current = find_on(drop.id, drop.tile())
        if current is None or (self.site.key == TAVERLEY_BLUE.key and self.combat_style == 'range' and current.id == RUNE_ARROW and current.count < 4):
            return False
        used_before = inventory.used()
        count_before = inventory.count(name)
        # Why: a stackable drop merges into a slot already held, so used() alone never moves for the coins, runes and
        # arrows that are most of the table.
        took = current.interact('Take')
        if took:
            took = yield from execution.delay_until(lambda: inventory.used() > used_before or inventory.count(name) > count_before, LOOT_WAIT_MS)
        if took:
            self.looted += 1
            self.loot_counts[name] = self.loot_counts.get(name, 0) + 1
            self.log(f'looted {name}')
            return True
        self.loot_skip[loot_key(drop)] = now_ms() + LOOT_SKIP_MS
        self.log(f'could not pick up {name} at {drop.tile()}. Ignoring it for {LOOT_SKIP_MS // 1000}s.')
        return False

    def loot_burst(self):
        """Clears the drop pile in one pass rather than one item per task hop."""
        for i in range(LOOT_BURST_MAX):
            if not self.loot_ready() or (self.burial_available() and inventory.contains(self.site.bones)):
                return
            drop = self.find_loot()
            if drop is None:
                break
            if inventory.is_full() and not loot_stacks_into_pack(drop.name):
                yield from self.free_slot()
                if inventory.is_full():
                    break
            took = yield from self.loot_once()
            if not took:
                break
            if self.burial_available() and inventory.contains(self.site.bones):
                return
            if i == LOOT_BURST_MAX - 1 and self.find_loot() is not None:
                return
        yield from self.finish_loot()

    def free_slot(self):
        if not self.loot_ready():
            return
        drop = self.find_loot()
        action = self.slot_action(drop)
        want = drop.name if drop is not None and drop.name else 'loot'
        self.vlog(f"slot check: {inventory.used()} used, {self.food} x{self.food_count()} (reserve {self.food_reserve}), "
                  + f"hp {round(skills.hp_fraction() * 100)}%, ground '{want}' -> {action}")
        if self.loot_run is None and action != 'none':
            self.loot_run = LootRun()
        if action == 'eat':
            self.log(f'pack full. Eating {self.food} to make room for {want}')
            ate = yield from self.eat_once()
            if ate:
                self.loot_run.spent_food = True
            return
        if action != 'drop':
            return
        back = yield from self.return_from_loot()
        if not back or not self.loot_ready() or self.slot_action(self.find_loot()) != 'drop':
            return
        food = None
        for item in inventory.items():
            if is_edible_food(item, self.food):
                food = item
                break
        here = game.tile()
        if food is None or here is None:
            return
        run = self.loot_run
        food_id = food.id
        existing = sum([g.count for g in ground_items.query().where(lambda g: g.id == food_id and g.tile().equals(here)).results()])
        ours = len([f for f in run.food if f[0] == food_id and f[1].equals(here)])
        self.set_status(f'dropping {food.name} for pack space')
        self.log(f'pack full at full hp. Dropping {food.name} to make room for {want}')
        before = inventory.used()
        if food.interact('Drop'):
            dropped = yield from execution.delay_until(lambda: inventory.used() < before, 3000)
            if dropped and existing == ours:
                run.food.append((food_id, Tile(here.x, here.z, here.level)))


BOT = define_bot(
    name='JiveDragons',
    create=JiveDragons,
    description="Taverley Dungeon blue or black dragons, or the Heroes' Guild dragon fought through its fence: mage or range from a derived safespot, or melee with the Dragonfire shield. Opens the dusty-key gate, fetching the key off Velrak when the bank has none.",
    category='Combat',
    tags=['taverley', 'heroes guild', 'dragons', 'safespot', 'members', 'banking', 'clues'],
    settings_schema=SETTINGS,
)

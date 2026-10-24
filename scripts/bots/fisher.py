# Fishes the chosen method, banking, cooking or dropping the catch, or handing it to a mule: rs2b0t's Fisher, a
# preset of GatheringBot (MIT, see thirdparty/rs2b0t). The fish_method setting is what makes the bot a fisher; see
# gathering/bot.py.

from rs2004.catalogs import FISHING_LOCATION_OPTIONS, FISHING_METHOD_OPTIONS, FORGETFUL_BANK_SETTING, TOOL_ACQUIRE_SETTING
from rs2004.market import format_gp

from bots.gathering.bot import GATHERING_SETTINGS, GatheringBot
from bots.gathering.fish_cook import AFTER_COOK_OPTIONS, BURNT_POLICY_OPTIONS, COOK_FISH_OPTIONS, COOK_MODE_OPTIONS
from bots.gathering.logic import FEATHER_BUYOUT_GP, FEATHER_RESTOCK_MINUTES
from bots.gathering.tick_manip import FISH_TICK_MANIP_OPTIONS, TICK_MANIP_UNSHIPPED_HELP, tick_manip_ui_options

COOKING = {'key': 'cook_mode', 'any_of': ['Cook then bank', 'Bank raw then cook']}
BANK_RAW = {'key': 'cook_mode', 'any_of': ['Bank raw then cook']}
BAIT_METHODS = ['Bait rod — sardine/herring', 'Fly fishing — trout/salmon', 'Bait rod — pike', 'Oily rod — lava eel']

SETTINGS = {
    'fish_method': SettingDef('string', FISHING_METHOD_OPTIONS[0], 'Fishing method', options=FISHING_METHOD_OPTIONS,
                              help='What to fish — picks the right spot (each spot offers a PAIR of ops) and the correct op of the two, e.g. small net (shrimp) vs big net (mackerel).'),
    'bait_qty': SettingDef('number', 1000, 'Bait / feathers qty', 1, group='Tools', show_if={'key': 'fish_method', 'any_of': BAIT_METHODS},
                           help='Shown when the method needs bait or feathers. Restock withdraws up to this many from the bank; with Buy/repair, buys up to this many from Harry (bait) or Gerrant (feathers) when bank+inv are short. No upper limit. Ignored for cage/net/harpoon methods.'),
    'leash_radius': SettingDef('number', 18, 'Leash radius (tiles)', 2, 64,
                               help='How far from the camp/start anchor to prefer fishing spots. Only Location Use Closest / Use Start Position / Use Custom Position use this as-is. Named camps floor to 64 (Fishing Guild / Catherby piers are huge). The bot still hunts past the leash when spots hop along the pier. Freeform locations do not mob-flee (expert / may-die).'),
    'tick_manip': SettingDef('string', 'Off', 'Tick manip', options=tick_manip_ui_options(FISH_TICK_MANIP_OPTIONS), group='Tick manip', help=TICK_MANIP_UNSHIPPED_HELP),
    'guild_feather_minutes': SettingDef('number', 0, 'Feather supply trip every (minutes)', 0, 120, show_if={'key': 'location', 'any_of': ['Fishing Guild', 'Shilo Village']},
                                        help=f"In the Fishing Guild, buys Roachey's feathers with up to {format_gp(FEATHER_BUYOUT_GP)}gp; a full shelf restocks in {FEATHER_RESTOCK_MINUTES} minutes. In Shilo, banks the catch, buys Fernahei's feathers first, then affordable water vials from Obli, banks the vials and returns to fishing. 0 disables scheduled trips; running out of feathers still triggers a paced supply trip."),
    'location': SettingDef('string', 'Auto', 'Location / full inventory', options=FISHING_LOCATION_OPTIONS,
                           help='Fishing camp + full-pack behaviour. Auto = snap to a camp in your map square, otherwise stay at your start tile. Use Closest = nearest camp by distance. Use Start Position = freeform around your start tile + nearest bank. Use Custom Position = freeform around the custom tile. Named camps pin pier + bank (and range for Catherby cook). Power-fish via Bank=false (always drop; cook is disabled). Legacy None also power-fishes.'),
    'custom_location': GATHERING_SETTINGS['custom_location'],
    'bank': GATHERING_SETTINGS['bank'],
    'bank_location': GATHERING_SETTINGS['bank_location'],
    'cook_mode': SettingDef('string', 'Off', 'Cook mode', options=COOK_MODE_OPTIONS, group='Cooking',
                            help='More options appear below when you leave Off. Off = bank or drop raw only (see Location). Cook then bank = fish a full pack, cook it, bank cooked — reveals Fish to cook + Burnt fish. Bank raw then cook = fish+bank raw until the bank holds N of the cook filter, then withdraw/cook/bank — also reveals Bank N raw before cook + After cook cycle. Needs a Range near the bank (Catherby preset works well). Cook requires Location not None.'),
    'cook_fish': SettingDef('string', 'All raw', 'Fish to cook', options=COOK_FISH_OPTIONS, group='Cooking', show_if=COOKING,
                            help='Shown when Cook mode is on. Which raw fish to cook; other raw species are banked as-is (e.g. cook Swordfish, bank Tuna raw). Choose Custom to reveal a free-text filter.'),
    'cook_fish_custom': SettingDef('string', '', 'Custom cook filter', group='Cooking', show_if={'key': 'cook_fish', 'any_of': ['Custom']},
                                   help='Shown when Fish to cook is Custom. Contains-match against raw names, e.g. "swordfish" or "Raw tuna". Empty = all raw.'),
    'burnt_policy': SettingDef('string', 'Drop', 'Burnt fish', options=BURNT_POLICY_OPTIONS, group='Cooking', show_if=COOKING,
                               help='Shown when Cook mode is on. Drop (default) or bank burnt fish after cooking.'),
    'bank_raw_before_cook': SettingDef('number', 56, 'Bank N raw before cook', 1, group='Cooking', show_if=BANK_RAW,
                                       help='Shown only for Bank raw then cook. Live bank total of the cook-filter raw (after each deposit). When the bank holds ≥ N, withdraw a load and cook. Type any amount (no artificial max).'),
    'after_cook_cycle': SettingDef('string', 'Stop', 'After cook cycle', options=AFTER_COOK_OPTIONS, group='Cooking', show_if=BANK_RAW,
                                   help='Shown only for Bank raw then cook. Stop = end the script after one cook cycle of the accumulated batch. Continue = keep fishing/banking/cooking in increments of N.'),
    'mule_mode': GATHERING_SETTINGS['mule_mode'],
    'mule_partner': GATHERING_SETTINGS['mule_partner'],
    'tool_acquire': TOOL_ACQUIRE_SETTING,
    'forgetful_bank': FORGETFUL_BANK_SETTING,
    'purge_pack_on_start': GATHERING_SETTINGS['purge_pack_on_start'],
    'pack_junk': GATHERING_SETTINGS['pack_junk'],
    'withdraw_coins': GATHERING_SETTINGS['withdraw_coins'],
    'bank_teleport': GATHERING_SETTINGS['bank_teleport'],
    'tele_casts': GATHERING_SETTINGS['tele_casts'],
}


class Fisher(GatheringBot):
    pass


BOT = define_bot(
    name='Fisher',
    create=Fisher,
    description='Fishes a chosen method at the spot that offers it; banks the catch, optionally cooks at a nearby range, or drops it. Change Cook mode to reveal fish filter, burnt policy, and (for bank-raw-then-cook) the N quantity. Optional Buy/repair buys missing gear from the nearest fishing shop (Harry at Catherby, Gerrant for feathers/fly rod) and can buy bait/feathers up to Bait qty.',
    category='Fishing',
    tags=['gathering', 'drop', 'banking', 'cooking'],
    settings_schema=SETTINGS,
)

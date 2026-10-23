# Chops the chosen trees, banking, dropping or burning the logs: rs2b0t's Woodcutter, a preset of GatheringBot (MIT,
# see thirdparty/rs2b0t). The tree_name setting is what makes the bot a woodcutter; see gathering/bot.py.

from rs2004.catalogs import BURN_MODE_OPTIONS, FIRE_SPOT_OPTIONS, FORGETFUL_BANK_SETTING, TOOL_ACQUIRE_SETTING, WOODCUTTING_LOCATION_OPTIONS

from bots.gathering.bot import GATHERING_SETTINGS, GatheringBot
from bots.gathering.tick_manip import TICK_MANIP_UNSHIPPED_HELP, WC_TICK_MANIP_OPTIONS, tick_manip_ui_options

SETTINGS = {
    'tree_name': SettingDef('string', 'Tree', 'Tree name', options=['Tree', 'Oak', 'Willow', 'Maple tree', 'Yew', 'Magic tree'],
                            help='In-game scenery name to chop (exact match). Pick a common tree from the list.'),
    'leash_radius': GATHERING_SETTINGS['leash_radius'],
    'location': SettingDef('string', 'Auto', 'Location / full inventory', options=WOODCUTTING_LOCATION_OPTIONS,
                           help='Chop camp + full-pack behaviour. Auto = snap to a camp in your map square, otherwise stay at your start tile. Use Closest = nearest camp by distance. Use Start Position = freeform around your start tile. Use Custom Position = freeform around the custom tile. Named camps pin trees + bank. Bank=false or legacy None drops logs and disables burn mode.'),
    'custom_location': GATHERING_SETTINGS['custom_location'],
    'bank': GATHERING_SETTINGS['bank'],
    'bank_location': GATHERING_SETTINGS['bank_location'],
    'tick_manip': SettingDef('string', 'Off', 'Tick manip', options=tick_manip_ui_options(WC_TICK_MANIP_OPTIONS), group='Tick manip', help=TICK_MANIP_UNSHIPPED_HELP),
    'burn_mode': SettingDef('string', 'Off', 'Burn mode', options=BURN_MODE_OPTIONS, group='Firemaking',
                            help='Off = keep/bank logs (see Full inventory). Chop then burn = when the pack is full, walk to a fire plot and light the logs instead of banking them (needs tinderbox + Full inventory Auto). Choosing Chop then burn reveals Fire spot below.'),
    'fire_spot': SettingDef('string', 'Auto', 'Fire spot', options=['Auto'] + FIRE_SPOT_OPTIONS, group='Firemaking', show_if={'key': 'burn_mode', 'any_of': ['Chop then burn']},
                            help='Shown only when Burn mode is Chop then burn. Where to light fires. Auto = burn near where you started the script until the pack is empty (repaths/expands when tiles fill with fires). Named spots = fixed bank-side strips (Varrock East, Draynor, …).'),
    'tool_acquire': TOOL_ACQUIRE_SETTING,
    'forgetful_bank': FORGETFUL_BANK_SETTING,
    'purge_pack_on_start': GATHERING_SETTINGS['purge_pack_on_start'],
    'pack_junk': GATHERING_SETTINGS['pack_junk'],
    'withdraw_coins': GATHERING_SETTINGS['withdraw_coins'],
    'bank_teleport': GATHERING_SETTINGS['bank_teleport'],
    'tele_casts': GATHERING_SETTINGS['tele_casts'],
}


class Woodcutter(GatheringBot):
    pass


BOT = define_bot(
    name='Woodcutter',
    create=Woodcutter,
    description='Chops the chosen tree type, then banks logs, drops them, or burns a full load (chop-then-burn). Needs an axe; burn mode also needs a tinderbox (both restock from the bank when Full inventory is Auto). Optional Buy/repair acquires axes from Bob or smiths mith+ from bars.',
    category='Woodcutting',
    tags=['gathering', 'banking', 'drop', 'firemaking'],
    settings_schema=SETTINGS,
)

# Mines the chosen rocks, banking the ore or dropping it: rs2b0t's Miner, a preset of GatheringBot (MIT, see
# thirdparty/rs2b0t). The rocks setting is what makes the bot a miner; see gathering/bot.py.

from rs2004.catalogs import FORGETFUL_BANK_SETTING, MINING_LOCATION_OPTION_LABELS, MINING_LOCATION_OPTIONS, ROCK_OPTIONS, TOOL_ACQUIRE_SETTING

from bots.gathering.bot import GATHERING_SETTINGS, GatheringBot
from bots.gathering.miner_logic import MINER_FOOD_SETTINGS
from bots.gathering.tick_manip import MINE_TICK_MANIP_OPTIONS, TICK_MANIP_UNSHIPPED_HELP, tick_manip_ui_options

SETTINGS = {
    'rocks': SettingDef('string[]', ['Iron'], 'Rock types', options=ROCK_OPTIONS,
                        help='Which rocks to mine — every rock is named "Rocks" in-game, so pick the ore types here (multi-select). Empty = mine any rock.'),
    'leash_radius': GATHERING_SETTINGS['leash_radius'],
    'location': SettingDef('string', 'Auto', 'Location / full inventory', options=MINING_LOCATION_OPTIONS, option_labels=MINING_LOCATION_OPTION_LABELS,
                           help='Mine camp + full-pack behaviour. Auto = snap to a camp in your map square, otherwise stay at your start tile. Use Closest = nearest camp by distance. Use Start Position = freeform around your start tile + nearest bank. Use Custom Position = freeform around the custom tile. Named camps pin spot + bank. Camps with aggressive NPCs show a recommended combat level (2× highest aggro + 1). Power-mine via Bank=false (drop ore; configured food still restocks from the nearest bank). Legacy None also power-mines.'),
    'custom_location': GATHERING_SETTINGS['custom_location'],
    'bank': GATHERING_SETTINGS['bank'],
    'bank_location': GATHERING_SETTINGS['bank_location'],
}
SETTINGS.update(MINER_FOOD_SETTINGS)
SETTINGS.update({
    'tick_manip': SettingDef('string', 'Off', 'Tick manip', options=tick_manip_ui_options(MINE_TICK_MANIP_OPTIONS), group='Tick manip', help=TICK_MANIP_UNSHIPPED_HELP),
    'tool_acquire': TOOL_ACQUIRE_SETTING,
    'forgetful_bank': FORGETFUL_BANK_SETTING,
    'purge_pack_on_start': GATHERING_SETTINGS['purge_pack_on_start'],
    'pack_junk': GATHERING_SETTINGS['pack_junk'],
    'withdraw_coins': GATHERING_SETTINGS['withdraw_coins'],
    'bank_teleport': GATHERING_SETTINGS['bank_teleport'],
    'tele_casts': GATHERING_SETTINGS['tele_casts'],
})


class Miner(GatheringBot):
    pass


BOT = define_bot(
    name='Miner',
    create=Miner,
    description='Mines the selected rock types, then banks the ore or drops the whole haul in a batch when Bank=false. Power mode keeps food for healing and restocks when it runs out. Needs a pickaxe (best available is restocked from the bank when Full inventory is Auto). Optional Buy/repair acquires picks from Nurmof (and repairs broken picks).',
    category='Mining',
    tags=['gathering', 'banking', 'drop'],
    settings_schema=SETTINGS,
)

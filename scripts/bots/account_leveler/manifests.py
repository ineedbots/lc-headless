"""Load only the training method selected by the planner."""

MODULES = {
    'AutoFighter': 'auto_fighter', 'RangingGuild': 'ranging_guild', 'Fisher': 'fisher', 'Woodcutter': 'woodcutter',
    'Miner': 'miner', 'CookBot': 'cook_bot', 'Firemaker': 'firemaker',
    'BankFletcher': 'bank_fletcher', 'SmithingBot': 'smithing_bot', 'SmelterBot': 'smelter_bot',
    'LeatherCrafter': 'leather_crafter', 'FlaxAIO': 'flax_aio', 'GnomeCourse': 'gnome_course',
    'EdgevilleMonkeyBars': 'edgeville_monkey_bars', 'Thiever': 'thiever',
    'AIOQuester': 'aio_quester', 'PotionMaker': 'potion_maker', 'RuneCrafter': 'rune_crafter',
    'TannerBot': 'tanner_bot', 'HerbCleaner': 'herb_cleaner', 'EssMiner': 'ess_miner',
    'GreenDragon': 'green_dragon', 'JiveDragons': 'jive_dragons',
    'HerbloreSecondaries': 'herblore_secondaries',
}


def manifest_for(name):
    module = MODULES.get(name)
    if module is None:
        raise ValueError(f'Missing activity script {name}')
    return __import__('bots.' + module).BOT

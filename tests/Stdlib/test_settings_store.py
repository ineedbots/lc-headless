"""settings_store, rs2b0t's SettingsStore, and SettingDef's show_if."""

from helpers import raises
from rs2004.settings import GLOBAL_SETTINGS, apply_schema, settings_store


def test_saved_values_come_from_the_account_file_and_from_save():
    settings_store.load({'Miner': {'rock': 'Tin'}, 'Global': {'use_mage_bank': True}})
    assert settings_store.saved('Miner', 'rock') == 'Tin'
    assert settings_store.saved('Miner', 'trips') is None
    assert settings_store.saved('Nobody', 'rock') is None

    settings_store.save('Miner', 'rock', 'Iron')
    settings_store.save('Miner', 'home', Tile(1, 2, 0))
    settings_store.save('Loadouts', 'sets', [{'name': 'Melee', 'gear': ['Bronze sword']}])
    assert settings_store.saved('Miner', 'rock') == 'Iron'
    assert settings_store.saved('Miner', 'home') == [1, 2, 0]
    assert settings_store.saved('Loadouts', 'sets') == [{'name': 'Melee', 'gear': ['Bronze sword']}]
    assert 'namespace and a key' in raises(ValueError, lambda: settings_store.save('', 'rock', 1))


def test_the_store_keeps_its_own_copy_of_the_settings():
    values = {'Miner': {'rock': 'Tin'}}
    settings_store.load(values)
    settings_store.save('Miner', 'rock', 'Iron')
    assert values == {'Miner': {'rock': 'Tin'}}


def test_resolve_takes_what_was_saved_then_globals_then_defaults():
    settings_store.load({'Miner': {'trips': 'many', 'rock': 'Tin'}, 'Global': {'lamp_skill': 'mining'}})
    schema = {
        'trips': SettingDef('number', 5),
        'rock': SettingDef('string', 'Copper'),
        'lamp_skill': SettingDef('string', 'attack'),
        'partner': SettingDef('string', None),
    }
    assert settings_store.resolve('Miner', schema) == {'trips': 5, 'rock': 'Tin', 'lamp_skill': 'mining', 'partner': None}


def test_the_global_bag_has_rs2b0ts_account_wide_settings():
    settings_store.load({'Global': {'use_mage_bank': True, 'nav_path_deviation': 99}})
    bag = settings_store.global_bag()
    assert bag.bool('use_mage_bank')
    assert not bag.bool('use_zanaris_bank')
    assert bag.str('lamp_skill') == 'strength'
    # Out of range, so the default, as rs2b0t falls back.
    assert bag.num('nav_path_deviation') == 10
    assert bag.num('nav_path_stall_ticks') == 5
    assert sorted(GLOBAL_SETTINGS.keys()) == [
        'bank_common_junk', 'clue_duel_partner', 'lamp_skill', 'nav_path_deviation', 'nav_path_stall_ticks', 'nav_teleports',
        'use_mage_bank', 'use_zanaris_bank',
    ]


def test_listeners_hear_each_save_until_they_unsubscribe():
    settings_store.load({})
    heard = []
    unsubscribe = settings_store.on_change(lambda name, key, value: heard.append([name, key, value]))
    settings_store.save('Fighter', 'style', 'melee')
    unsubscribe()
    settings_store.save('Fighter', 'style', 'range')
    assert heard == [['Fighter', 'style', 'melee']]


def test_display_strings_are_as_rs2b0ts_panel_shows_them():
    settings_store.load({'Miner': {'home': [1, 2, 0], 'keep': ['Bronze pickaxe', 'Coins'], 'power': True}})
    assert settings_store.display_string('Miner', 'home', SettingDef('tile', None)) == '1,2,0'
    assert settings_store.display_string('Miner', 'keep', SettingDef('string[]', [])) == 'Bronze pickaxe, Coins'
    assert settings_store.display_string('Miner', 'power', SettingDef('boolean', False)) == 'true'
    assert settings_store.display_string('Miner', 'trips', SettingDef('number', 7)) == '7'


def test_show_if_must_name_a_setting_of_its_schema():
    schema = {
        'style': SettingDef('string', 'melee', options=['melee', 'mage']),
        'spell': SettingDef('string', 'Wind strike', show_if={'key': 'style', 'any_of': ['mage']}),
    }
    bag = SettingsBag({})
    assert apply_schema(bag, schema) == []
    assert bag.spell == 'Wind strike'

    lacking = {'spell': SettingDef('string', 'Wind strike', show_if={'key': 'style', 'any_of': ['mage']})}
    assert "names 'style', which the schema lacks" in raises(ValueError, lambda: apply_schema(SettingsBag({}), lacking))
    shapeless = {'spell': SettingDef('string', 'Wind strike', show_if='style')}
    assert 'show_if must be a dict' in raises(TypeError, lambda: apply_schema(SettingsBag({}), shapeless))


def test_rs2b0ts_panel_only_fields_are_kept():
    definition = SettingDef('number', 0.5, step=0.05, color=False, options_from='loadouts', csv_toggle='mode')
    assert definition.step == 0.05
    assert definition.options_from == 'loadouts'

"""The grind bots' half of rs2b0t's test/scripts/RockCrab/RockCrabRangeLogic.test.ts (MIT, see thirdparty/rs2b0t), on
spec.py's describe, test and expect: every ranged grind bot offers the same weapons and custom fields."""

from rs2004.catalogs import RANGED_WEAPONS, range_loadout_of, ranged_item
import bots.brimhaven_moss_giants as brimhaven
import bots.fire_giant as fire_giant
import bots.moss_giant as moss_giant
import bots.rock_crab as rock_crab


def wired_like_rock_crab():
    for settings in [rock_crab.SETTINGS, moss_giant.SETTINGS]:
        expect(settings['bow'].label).to_be('Ranged weapon')
        expect(settings['bow'].options).to_equal(RANGED_WEAPONS + ['Other'])
        expect(settings['ammo'].label).to_be('Bow ammo')
        expect('ignored when the ranged weapon is a dart' in settings['ammo'].help).to_be(True)
    expect(moss_giant.SETTINGS['ammo_withdraw'].label).to_be('Projectiles per bank trip')


def custom_fields():
    for settings in [rock_crab.SETTINGS, moss_giant.SETTINGS, fire_giant.SETTINGS, brimhaven.SETTINGS]:
        expect(settings['bow'].options).to_contain('Other')
        expect(settings['ammo'].options).to_contain('Other')
        expect(settings['custom_bow'].show_if).to_equal({'key': 'bow', 'any_of': ['Other']})
        expect(settings['custom_ammo'].show_if).to_equal({'key': 'ammo', 'any_of': ['Other']})


def loadout(weapon, projectile, thrown):
    return {'weapon': weapon, 'projectile': projectile, 'thrown': thrown}


def custom_choices_trimmed():
    settings = SettingsBag({'bow': 'Other', 'custom_bow': '  Crossbow ', 'ammo': 'Other', 'custom_ammo': ' Bolts '})
    expect(range_loadout_of(ranged_item(settings, 'bow', 'Maple shortbow'), ranged_item(settings, 'ammo', 'Iron arrow'))).to_equal(
        loadout('Crossbow', 'Bolts', False))
    expect(ranged_item(SettingsBag({'bow': 'Maple shortbow', 'custom_bow': 'Crossbow'}), 'bow', '')).to_be('Maple shortbow')
    expect(lambda: ranged_item(SettingsBag({'bow': 'Other'}), 'bow', '')).to_throw('custom ranged weapon')


describe('shared ranged loadouts (RockCrab + MossGiant)', lambda: [
    test('wires the persisted bow setting to the unified ranged weapon control', wired_like_rock_crab),
])

test('all ranged grind scripts expose custom weapon and ammunition fields', custom_fields)

test('matching custom weapon and ammo use one thrown projectile stack', lambda: [
    expect(range_loadout_of('Rune knife', 'Rune knife')).to_equal(loadout('Rune knife', 'Rune knife', True)),
    expect(range_loadout_of('Crossbow', 'Bolts')).to_equal(loadout('Crossbow', 'Bolts', False)),
])

test('custom ranged choices reach the loadout with whitespace trimmed', custom_choices_trimmed)

"""Phase 11's shared helpers: spells' runes and combat styles (rs2b0t's test/api/combat combatStyleLogic and
combat-style tests), teleports (test/api/map/teleport.test.ts), the pack rules, the loadout store and the game's
reads."""

from rs2004.catalogs import Loadout, LOADOUT_SETTING, casts_available, count_matching, in_ess_mine, loadouts
from rs2004.catalogs import matches_any, parse_loadouts, resolve_teleport, resolve_teleport_component, rune_withdraw_list
from rs2004.catalogs import runes_per_cast, selected_loadout, serialize_loadouts, should_bank, should_panic, slots_matching
from rs2004.catalogs import spell_button_com, teleport_button_text
from rs2004.catalogs.record import Record
from rs2004.settings import settings_store
from rs2004.tabs import CombatStyleController, describe_combat_style, resolve_combat_style, resolve_split_combat_settings


def runes(*pairs):
    return [{'rune': rune, 'count': count} for rune, count in pairs]


def test_a_cast_costs_its_runes_less_what_a_staff_gives():
    assert runes_per_cast('Wind Strike', []) == runes(('Mind rune', 1), ('Air rune', 1))
    assert runes_per_cast('Fire Strike', ['Staff of fire']) == runes(('Mind rune', 1), ('Air rune', 2))
    assert runes_per_cast('Fire Blast', ['Staff of air']) == runes(('Death rune', 1), ('Fire rune', 5))
    # A lava battlestaff gives both earth and fire.
    assert runes_per_cast('Earth Blast', ['Lava battlestaff']) == runes(('Death rune', 1), ('Air rune', 3))
    assert runes_per_cast('Fire Blast', ['Lava battlestaff']) == runes(('Death rune', 1), ('Air rune', 4))
    assert runes_per_cast('Wind Strike', ['Bronze sword']) == runes(('Mind rune', 1), ('Air rune', 1))
    assert runes_per_cast('fire strike', ['staff of fire']) == runes(('Mind rune', 1), ('Air rune', 2))
    assert runes_per_cast('Confuse', []) is None


def test_casts_are_limited_by_the_scarcest_rune():
    held = {'Mind rune': 100, 'Air rune': 7}
    assert casts_available('Fire Strike', ['Staff of fire'], lambda name: held.get(name, 0)) == 3
    assert casts_available('Wind Strike', ['Staff of air'], lambda name: 0) == 0
    assert casts_available('Wind Strike', ['Staff of air'], lambda name: 5 if name == 'Mind rune' else 0) == 5
    assert rune_withdraw_list('Fire Strike', ['Staff of fire'], 100) == runes(('Mind rune', 100), ('Air rune', 200))
    # The chooser's buttons are found while it's open; an unknown spell has none.
    assert spell_button_com('nope') == -1


ORDINARY_SWORD = [(0, '(Accurate)'), (1, '(Aggressive)'), (2, '(Controlled)'), (3, '(Defensive)')]
THREE_MODE = [(0, '(Accurate)'), (1, '(Aggressive)'), (2, '(Defensive)')]
SPEAR = [(0, '(Controlled)'), (1, '(Controlled)'), (2, '(Controlled)'), (3, '(Defensive)')]


def test_a_description_owns_up_to_a_fallback_style():
    assert describe_combat_style(resolve_combat_style('controlled', ORDINARY_SWORD)) == 'controlled (training Attack, Strength & Defence)'
    assert describe_combat_style(resolve_combat_style('controlled', THREE_MODE)) == 'defence (training Defence; controlled unavailable)'
    assert describe_combat_style(resolve_combat_style('strength', SPEAR)) == 'defence (training Defence; strength unavailable)'


def split(raw_combat_style, raw_melee_style=None):
    found = resolve_split_combat_settings(raw_combat_style, raw_melee_style)
    return (found.kind, found.melee_style, found.legacy_migrated)


def test_an_old_combat_style_setting_moves_to_the_melee_style():
    assert split('defence') == ('melee', 'defence', 'defence')
    assert split('strength') == ('melee', 'strength', 'strength')
    assert split('defence', 'attack') == ('melee', 'attack', None)
    assert split('melee', 'defence') == ('melee', 'defence', None)
    assert split('range') == ('range', 'strength', None)
    assert split('mage', 'controlled') == ('mage', 'controlled', None)


class Backend:
    def __init__(self, modes, current):
        self.modes = modes
        self.current = current
        self.selected = []

    def offered_modes(self):
        return self.modes

    def current_mode(self):
        return self.current

    def select_mode(self, mode):
        if self.modes is None or mode not in [m for m, _ in self.modes]:
            return False
        self.selected.append(mode)
        self.current = mode
        return True


def test_the_controller_resolves_sets_and_checks_one_target():
    backend = Backend(ORDINARY_SWORD, 1)
    controller = CombatStyleController(backend)
    found = controller.resolution('controlled')
    assert (found.requested, found.effective, found.mode) == ('controlled', 'controlled', 2)
    assert not controller.has('controlled')
    assert controller.set('controlled')
    assert backend.selected == [2]
    assert controller.has('controlled')
    backend = Backend(THREE_MODE, 0)
    controller = CombatStyleController(backend)
    assert controller.resolution('controlled').effective == 'defence'
    assert controller.set('controlled')
    assert backend.current == 2
    assert controller.has('controlled') and controller.has('defence')


def test_the_controller_fails_closed_without_a_combat_interface():
    backend = Backend(None, 0)
    controller = CombatStyleController(backend)
    assert controller.resolution('attack') is None
    assert controller.mode('attack') is None
    assert not controller.has('attack')
    assert not controller.set('attack')
    backend.modes = []
    assert controller.resolution('strength') is None
    assert not controller.set('strength')
    assert backend.selected == []


def test_teleports_are_named_loosely_and_found_live_first():
    assert resolve_teleport('varrock').name == 'Varrock'
    assert resolve_teleport('  VARROCK teleport ').name == 'Varrock'
    assert resolve_teleport('Cast @gre@Varrock teleport').name == 'Varrock'
    assert resolve_teleport('Trollheim').fallback_com_id == 7455
    assert resolve_teleport('Edgeville') is None
    assert resolve_teleport('') is None
    varrock = resolve_teleport('Varrock')
    assert teleport_button_text(varrock) == 'Cast @gre@Varrock teleport'
    assert resolve_teleport_component(varrock, lambda text: 9001 if text == 'Cast @gre@Varrock teleport' else -1) == 9001
    assert resolve_teleport_component(varrock, lambda text: -1) == 1164
    assert in_ess_mine(2911, 4832)
    assert not in_ess_mine(3253, 3402)


def test_pack_rules_match_by_part_and_bank_at_the_loot_target():
    pack = [Record({'name': 'Big bones', 'count': 1}), Record({'name': 'Bones', 'count': 1}), Record({'name': 'Coins', 'count': 30})]
    assert matches_any('Big bones', ['bones'])
    assert not matches_any('Big bones', ['', '  '])
    assert not matches_any(None, ['bones'])
    assert count_matching(pack, ['bones', 'coins']) == 32
    assert slots_matching(pack, ['bones', 'coins']) == 3
    assert should_bank(14, 14, False)
    assert not should_bank(13, 14, False)
    assert should_bank(2, 14, True)
    assert not should_bank(0, 14, True)
    assert should_panic(0.2, 0.3, 0)
    assert not should_panic(0.2, 0.3, 1)


def test_loadouts_are_shared_through_the_account_file_unless_a_bot_has_its_own():
    settings_store.load({})
    melee = Loadout('Melee', {'righthand': 'Bronze sword'})
    loadouts.save([melee, Loadout('Range', {'righthand': 'Shortbow'})])
    assert loadouts.names() == ['Melee', 'Range']
    assert loadouts.by_name(' range ').worn == {'righthand': 'Shortbow'}
    assert loadouts.by_name('Mage') is None
    assert selected_loadout({'loadout': 'Range'}).name == 'Range'
    assert selected_loadout({}).name == 'Melee'
    own = [{'name': 'Own', 'worn': {'righthand': 'Staff'}, 'carry': []}]
    assert selected_loadout({'loadouts': own}).name == 'Own'
    # The text form reads back as it was written.
    assert [l.name for l in parse_loadouts(serialize_loadouts(loadouts.all()))] == ['Melee', 'Range']
    assert LOADOUT_SETTING.options_from == 'loadouts'
    settings_store.load({})
    assert selected_loadout({}) is None


def test_the_game_reads_retaliate_faces_and_the_pack_size():
    assert retaliate_on_from_varp(0)
    assert not retaliate_on_from_varp(1)
    assert facing_player(PLAYER_FACE_BASE + 3)
    assert not facing_player(12)
    assert facing_player(('player', 3))
    assert not facing_player(('npc', 3))
    assert not facing_player(None)
    assert backpack_capacity() == INVENTORY_SIZE

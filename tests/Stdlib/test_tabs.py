from rs2004.tabs import clean_text, quest_status


def test_combat_styles_parse_from_names_and_labels():
    assert parse_combat_style('Aggressive') == 'strength'
    assert parse_combat_style('defense') == 'defence'
    assert parse_combat_style('nonsense') == 'strength'
    assert try_parse_combat_style('nonsense') is None
    assert parse_interface_combat_style('(Accurate)') == 'attack'
    assert parse_interface_combat_style(' (Defensive) ') == 'defence'
    assert parse_interface_combat_style('(Crush)') is None
    assert parse_range_style('Long range') == 2
    assert parse_range_style('anything') == 1


def test_a_style_the_weapon_lacks_falls_back_to_its_last_defensive_one():
    offered = [(0, '(Accurate)'), (1, '(Aggressive)'), (3, '(Defensive)'), (1, '(Aggressive)'), (2, '(Crush)')]
    assert resolve_combat_style('strength', offered).mode == 1
    fallback = resolve_combat_style('controlled', offered)
    assert fallback.requested == 'controlled' and fallback.effective == 'defence' and fallback.mode == 3
    assert resolve_combat_style('controlled', [(0, '(Accurate)')]) is None
    assert resolve_combat_style('attack', []) is None


def test_quest_colours_read_as_statuses():
    assert quest_status(0xFF0000) == 'not_started'
    assert quest_status(0xF80000) == 'not_started'
    assert quest_status(0xF8F800) == 'in_progress'
    assert quest_status(0x00F800) == 'complete'
    assert quest_status(0xFFFFFF) == 'in_progress'
    assert quest_status(0x000000) == 'unknown'


def test_colour_tags_are_cleaned_from_button_text():
    assert clean_text('Cast @gre@Varrock teleport') == 'Cast Varrock teleport'
    assert clean_text('Use @gre@Special Attack') == 'Use Special Attack'


def test_the_tabs_are_empty_without_a_game():
    assert quests.all() == [] and quests.status('Cook\'s Assistant') == 'unknown'
    assert not prayer.active('thick skin') and not prayer.known('smite')
    assert special.bar_component() == -1 and special.cost('Dragon dagger') == 250 and special.cost('Bronze dagger') is None
    assert game.combat_styles() is None and game.combat_style_mode('attack') is None
    assert not game.teleport('Varrock') and not game.cast_on_item('High level alchemy', None)
    assert not autocast.staff_tab_attached()

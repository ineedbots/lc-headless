from rs2004.routeplan import essence_return_id_from_tile, is_quest_lock_text, records_have_slash_tool, resolve_path_follow_config


def test_the_289_doors_refusals_read_as_locks():
    # rs2b0t's patterns miss "won't", which is how the 289 doors refuse.
    assert is_quest_lock_text("The door won't open - you need at least 32 Quest Points.")
    assert not is_quest_lock_text('You open the door.')
    assert not is_quest_lock_text("I won't be long.")


def test_follow_settings_come_from_the_global_settings_under_a_walks_own():
    settings_store.load({'Global': {'nav_path_stall_ticks': 9, 'nav_path_deviation': 14}})
    follow = resolve_path_follow_config()
    assert follow.stall_ticks == 9 and follow.deviation_chebyshev == 14
    assert resolve_path_follow_config({'stall_ticks': 3}).stall_ticks == 3
    # The hop trigger never drops under the corridor.
    assert resolve_path_follow_config({'transport_approach_chebyshev': 1}).transport_approach_chebyshev == 3
    settings_store.load({})


def test_a_knife_or_a_bladed_weapon_slashes_webs_but_a_thrown_knife_does_not():
    assert records_have_slash_tool({'Knife': 1})
    assert records_have_slash_tool({}, {'Rune scimitar': 1})
    assert records_have_slash_tool({'Dragon two-handed sword': 1})
    assert not records_have_slash_tool({'Bronze knife': 5})
    assert not records_have_slash_tool({'Knife': 0})


def test_an_essence_return_is_the_wizard_whose_stand_is_near():
    assert essence_return_id_from_tile(Tile(3253, 3401, 0)) == 'aubury'
    assert essence_return_id_from_tile(Tile(3255, 3403, 0)) == 'aubury'
    assert essence_return_id_from_tile(Tile(3260, 3401, 0)) is None

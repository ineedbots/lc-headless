from rs2004.tutorial import in_tutorial_area, offers_skip, on_tutorial_island


def test_the_island_and_its_dungeon_are_the_tutorial_area():
    assert in_tutorial_area(3094, 3106)
    assert in_tutorial_area(3053, 3056)
    assert in_tutorial_area(3156, 3136)
    assert in_tutorial_area(3100, 9510)
    assert not in_tutorial_area(3222, 3222)
    assert not in_tutorial_area(3052, 3100)
    assert not in_tutorial_area(3100, 3137)
    assert not in_tutorial_area(3100, 9491)


def test_unplaced_isnt_on_the_island():
    assert not on_tutorial_island()


def test_the_guide_offers_the_skip_by_its_yes():
    assert offers_skip(['Yes please.', 'No, thank you.'])
    assert offers_skip(['yes please'])
    assert not offers_skip(['No, thank you.'])
    assert not offers_skip([])

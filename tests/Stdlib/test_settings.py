from helpers import raises
from rs2004.settings import apply_schema

SCHEMA = {
    'rock': SettingDef('string', 'Copper rocks', options=['Copper rocks', 'Tin rocks']),
    'power': SettingDef('boolean', False),
    'trips': SettingDef('number', 10, min=1, max=100),
    'keep': SettingDef('string[]', ['Bronze pickaxe']),
    'home': SettingDef('tile', None),
}


def checked(values):
    bag = SettingsBag(values)
    warnings = apply_schema(bag, SCHEMA)
    return bag, warnings


def test_missing_settings_take_their_defaults():
    bag, warnings = checked({})
    assert bag.rock == 'Copper rocks'
    assert bag.power is False
    assert bag.trips == 10
    assert bag.keep == ['Bronze pickaxe']
    assert bag.home is None
    assert warnings == []


def test_values_are_checked_and_normalised():
    bag, _ = checked({'rock': 'tin ROCKS', 'keep': 'Pickaxe, Hammer', 'home': '3222,3218,1'})
    assert bag.rock == 'Tin rocks'
    assert bag.keep == ['Pickaxe', 'Hammer']
    assert bag.home == Tile(3222, 3218, 1)
    assert checked({'home': [3222, 3218]})[0].home == Tile(3222, 3218, 0)
    assert checked({'home': {'x': 1, 'z': 2, 'level': 3}})[0].home == Tile(1, 2, 3)


def test_values_that_dont_fit_are_errors_naming_the_setting():
    assert raises(ValueError, lambda: checked({'rock': 'Gold rocks'})) == 'settings.rock must be one of: Copper rocks, Tin rocks'
    assert raises(ValueError, lambda: checked({'power': 1})) == 'settings.power must be true or false'
    assert raises(ValueError, lambda: checked({'trips': 0})) == 'settings.trips must be at least 1'
    assert raises(ValueError, lambda: checked({'trips': 101})) == 'settings.trips must be at most 100'
    assert raises(ValueError, lambda: checked({'trips': True})) == 'settings.trips must be a number'
    assert raises(ValueError, lambda: checked({'keep': [1]})) == 'settings.keep must be a list of strings'
    assert 'must be a tile' in raises(ValueError, lambda: checked({'home': 'lumbridge'}))


def test_settings_the_schema_lacks_are_warned_about():
    _, warnings = checked({'colour': 'red'})
    assert warnings == ["has settings.colour, which its settings schema doesn't declare"]


def test_typed_getters_fall_back_on_another_type():
    bag = SettingsBag({'name': 'Bob', 'count': 3, 'flag': True, 'list': ['a'], 'tile': Tile(1, 2)})
    assert bag.str('name') == 'Bob'
    assert bag.str('count', 'none') == 'none'
    assert bag.num('count') == 3
    assert bag.num('flag', -1) == -1
    assert bag.bool('flag') is True
    assert bag.list('list') == ['a']
    assert bag.list('name') == []
    assert bag.tile('tile', None) == Tile(1, 2)
    assert bag.raw() == {'name': 'Bob', 'count': 3, 'flag': True, 'list': ['a'], 'tile': Tile(1, 2)}
    assert bag.get('missing', 5) == 5
    assert 'name' in bag
    assert 'missing' in raises(AttributeError, lambda: bag.missing)


def test_a_bad_schema_is_an_error():
    assert 'must be a dict' in raises(TypeError, lambda: apply_schema(SettingsBag({}), ['rock']))
    assert 'must be a SettingDef' in raises(TypeError, lambda: apply_schema(SettingsBag({}), {'rock': 'Copper rocks'}))
    assert 'a setting type must be one of' in raises(ValueError, lambda: SettingDef('colour', 'red'))

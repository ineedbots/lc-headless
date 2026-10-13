from helpers import raises
from rs2004 import _runtime


def _clear():
    for name in console.names():
        console.remove(name)


def test_adding_a_command_lists_it_for_the_host():
    _clear()
    remove = console.command('Bank', lambda command: None, 'Banks the logs')
    assert console.names() == ['bank']
    assert _commands['bank'] == 'Banks the logs'

    console.command('drop', lambda command: None)
    assert _commands['drop'] == ''

    remove()
    assert console.names() == ['drop']
    assert 'bank' not in _commands
    _clear()


def test_bad_commands_are_refused():
    _clear()
    assert 'one word' in raises(ValueError, lambda: console.command('two words', lambda command: None))
    assert 'one word' in raises(ValueError, lambda: console.command('@bot1', lambda command: None))
    assert "client's own" in raises(ValueError, lambda: console.command('Quit', lambda command: None))
    assert 'callable' in raises(TypeError, lambda: console.command('dig', 5))
    console.command('dig', lambda command: None)
    assert 'already' in raises(ValueError, lambda: console.command('DIG', lambda command: None))
    _clear()


def test_the_runtime_calls_the_handler_with_the_line():
    _clear()
    seen = []
    console.command('echo', lambda command: seen.append([command.name, command.text, command.args]))
    _runtime.command('echo', 'hello  world', ['hello', 'world'])
    assert seen == [['echo', 'hello  world', ['hello', 'world']]]

    # A command removed after the line was queued is skipped.
    _runtime.command('gone', '', [])
    _clear()


def _waits(command):
    yield 600


def test_a_handler_cannot_wait():
    _clear()
    console.command('wait', _waits)
    assert "can't wait" in raises(TypeError, lambda: _runtime.command('wait', '', []))
    _clear()


def test_a_bots_commands_end_when_it_stops():
    _clear()
    bot = LoopingBot()
    bot.command('dig', lambda command: None, 'Digs')
    assert _commands['dig'] == 'Digs'
    bot._dispose_subscriptions()
    assert 'dig' not in _commands

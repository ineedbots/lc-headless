"""Exercise the new gathering bots and the final quest runtime adapters."""
import _core
from bots.flour_collector import FlourCollector
from bots.rogues_purse import RoguesPurse, PURSE
import rs2004.quests.defs.priestperil as priest
import rs2004.quests.defs.tribaltotem as totem
import rs2004.quests.defs.murder.journal as murder
from rs2004 import execution
from rs2004.bank import bank, banking
from rs2004.dialogue import chat_dialog
from rs2004.items import inventory
from rs2004.game import game, reader
from rs2004.catalogs.record import Record


def result(value):
    return value
    yield


def flour_banking():
    bot = FlourCollector()
    spy_on(banking, 'open', impl=lambda *args, **kwargs: result(True))
    spy_on(bank, 'ready', returns=True)
    spy_on(execution, 'delay_until', impl=instant_until)
    def deposit(predicate):
        expect(predicate('Pot of flour', 1933)).to_be(True)
        expect(predicate('Pot', 1931)).to_be(False)
        return True
        yield
    spy_on(bank, 'deposit_all_matching', impl=deposit)
    spy_on(bank, 'count_by_id', returns=50)
    spy_on(bank, 'set_note_mode', impl=instant_ticks)
    spy_on(inventory, 'free', returns=28)
    drawn = spy_on(bank, 'withdraw_x_by_id', impl=lambda id, count: result(id == 1931 and count == 28))
    closed = spy_on(bank, 'close', impl=instant_ticks)
    expect(run_wait(bot.restock())).to_be(True)
    expect(drawn.calls).to_equal([(1931, 28)])
    expect(len(closed.calls)).to_be(1)


test('FlourCollector banks the flour and draws unnoted empty pots', flour_banking)


def flour_close_on_error():
    bot = FlourCollector()
    spy_on(banking, 'open', impl=lambda *args, **kwargs: result(True))
    spy_on(bank, 'ready', returns=True)
    spy_on(execution, 'delay_until', impl=instant_until)
    def fail(predicate):
        raise RuntimeError('deposit failed')
        yield
    spy_on(bank, 'deposit_all_matching', impl=fail)
    closed = spy_on(bank, 'close', impl=instant_ticks)
    caught = False
    try:
        run_wait(bot.restock())
    except RuntimeError:
        caught = True
    expect(caught).to_be(True)
    expect(len(closed.calls)).to_be(1)


test('FlourCollector closes the bank when restocking raises', flour_close_on_error)


def purse_cycle(mode, expected):
    def run():
        bot = RoguesPurse()
        destination = mode
        bot.settings = Fake(str=lambda key, default: destination)
        bot.dead_searches = 8
        bot.searches = 0
        bot.refusal = None
        calls = []
        spy_on(inventory, 'items', returns=[Fake(id=1533, interact=lambda op: calls.append(op)), Fake(id=1534, interact=lambda op: calls.append(op))])
        spy_on(inventory, 'free', returns=26)
        spy_on(chat_dialog, 'can_continue', returns=True)
        spy_on(_core, 'continue_dialogue', impl=lambda: calls.append('Continue'))
        wall = Fake(interact=lambda op: calls.append(op) or True)
        run_wait(bot.cycle(wall))
        expect(calls).to_equal(expected)
        expect(bot.searches).to_be(1)
        expect(bot.dead_searches).to_be(1)
    return run


test('RoguesPurse sends continue, identify, drop and search in order', purse_cycle('drop', ['Continue','Identify','Drop','Search']))
test('RoguesPurse banking mode preserves the identified herb', purse_cycle('bank', ['Continue','Identify','Search']))


def purse_bank_load():
    bot = RoguesPurse()
    bot.banked = 0
    state = {'herbs': 27}
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(inventory, 'count_by_id', impl=lambda id: state['herbs'] if id == PURSE.id else 0)
    import bots.rogues_purse as module
    spy_on(module, 'leave_pothole', impl=lambda log: result(True))
    spy_on(banking, 'open', impl=lambda *args, **kwargs: result(True))
    def deposit(predicate):
        assert predicate('Rogues purse', 1534) and not predicate('Coins', 995)
        state['herbs'] = 0
        return True
        yield
    spy_on(bank, 'deposit_all_matching', impl=deposit)
    spy_on(bank, 'close', impl=instant_ticks)
    expect(run_wait(bot.bank_load())).to_be(True)
    expect(bot.banked).to_be(27)
    expect(bot.need_fare).to_be(True)


test('RoguesPurse banks a load while preserving its return fare', purse_bank_load)


def priest_attack():
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(game, 'in_combat', returns=True)
    spy_on(priest.npcs, 'all', returns=[])
    npc = Fake(index=1, interact=lambda op: op == 'Attack')
    expect(run_wait(priest.kill_target(npc, 'temple guardian'))).to_be(True)


test('Priest in Peril accepts the synchronous NPC attack result', priest_attack)


def trap_message():
    spy_on(reader, 'chat_modal_texts', returns=['There is a trap in these stairs.'])
    spy_on(reader, 'main_modal_texts', returns=[])
    def prompt(step, log):
        expect(step.expect()).to_be(True)
        return step.expect()
        yield
    spy_on(totem, 'prompt_loc', impl=prompt)
    expect(run_wait(totem.disarm_trap(lambda message: None))).to_be(True)


test('Tribal Totem remembers the trap message inside its prompt predicate', trap_message)


def murder_last_page():
    from rs2004.tabs import quests
    spy_on(quests, 'status', returns='in_progress')
    state = {'line':'Lord Sinclair, a prominent nobleman. I have indisputable evidence'}
    spy_on(quests, 'journal', impl=lambda name: result([state['line']]))
    spy_on(reader, 'modals', returns=Fake(main=-1))
    murder.reset_murder_progress_cache()
    first = run_wait(murder.read_murder_progress())
    state['line'] = ''
    expect(run_wait(murder.read_murder_progress())).to_be(first)
    murder.reset_murder_progress_cache()


test('Murder Mystery retains the last valid page across an empty poison-stage read', murder_last_page)


def sea_slug_messages():
    from rs2004.quests.defs.seaslug.legs import panel_reply, crane_reply, sticks_reply
    for message in ['The panel crumbles away.', 'Nothing interesting happens.']:
        expect(panel_reply(message)).to_be(True)
    for message in ['You rotate the crane around.', 'I need to get closer to use that.']:
        expect(crane_reply(message)).to_be(True)
    for message in ['The sticks catch alight.', 'They smoke momentarily.', 'You need a Firemaking level of 30.']:
        expect(sticks_reply(message)).to_be(True)
    expect(sticks_reply('You search a crate.')).to_be(False)


test('Sea Slug accepts each message alternative without regex literals', sea_slug_messages)


def combination_dial():
    state = {'letter': 'A'}
    def click(button):
        assert button == totem.DIAL_DOWN[0]
        state['letter'] = 'Z'
        return True
    spy_on(reader, 'if_text', impl=lambda id: state['letter'])
    spy_on(_core, 'click_component', impl=click)
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(totem.set_dial(0, 'Z', lambda message: None))).to_be(True)
    state['letter'] = ''
    expect(totem.dial_letter(0)).to_be(None)


test('Tribal Totem turns a dial by character code and waits for the echoed letter', combination_dial)

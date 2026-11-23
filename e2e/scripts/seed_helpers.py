"""Local development-server preparation helpers; no quest progress is set here."""

from rs2004 import execution
from rs2004.bank import bank
from rs2004.game import chat
from rs2004.items import inventory

def send(command):
    chat.command(command)
    yield from execution.delay_ticks(2)


def stash():
    chat.command('~bank')
    ok = yield from execution.delay_until(bank.is_open, 8000)
    assert ok, 'seed bank absent'
    ok = yield from bank.wait_ready()
    assert ok, 'seed bank contents absent'
    yield from bank.deposit_inventory()
    yield from execution.delay_ticks(2)
    assert inventory.used() == 0, 'seed deposit incomplete'
    log('SEED bank', [(i.id, i.name, i.count) for i in bank.items()])
    yield from bank.close()

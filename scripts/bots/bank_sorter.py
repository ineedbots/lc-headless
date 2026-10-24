# Walks to a bank and sorts it into categories, coins first and junk last, then stops; it can report, and drop,
# the items a finished quest left behind: rs2b0t's BankSorter (MIT, see thirdparty/rs2b0t).

from rs2004.banksort import find_quest_junk, sort_bank

SETTINGS = {
    'sort_bank': SettingDef('boolean', True, 'Sort the bank'),
    'report_quest_junk': SettingDef('boolean', True, 'Report obsolete quest items', help='logs what a finished quest left behind, and changes nothing'),
    'drop_quest_junk': SettingDef('boolean', False, 'Drop what the report found', help='withdraws and drops them. There is no bank-side destroy, and a drop cannot be undone'),
}


# BankSorterLogic.ts


def droppable_of(found, armed):
    return [f for f in found if f.droppable] if armed else []


def quest_categories(found):
    """{id: 'questObsolete' or 'questLive'} for the leftovers found.

    Why: no name rule can tell a live quest item from a dead one, because that lives in the journal."""
    out = {}
    for f in found:
        out[f.id] = 'questObsolete' if f.status == 'complete' else 'questLive'
    return out


def report_line(found):
    """Why: the live harness shows a bounded number of log lines per poll, so one line per item reads as silence."""
    parts = [f'{f.name} ({f.quest}, {f.status})' for f in found]
    return f"BankSorter: quest leftovers — {'; '.join(parts) or 'none'}"


def summary_line(result, found, dropped):
    return ', '.join([
        f'BankSorter: {result.reason}',
        f"{result.moves} moves ({result.mode if result.mode is not None else 'none'})",
        f'{len(result.unmatched)} unfiled',
        f'{len(found)} quest leftovers',
        f'{dropped} dropped',
    ])


class SortOff:
    """The result when sorting is turned off."""
    sorted = False
    moves = 0
    mode = None
    unmatched = []
    reason = 'sorting turned off'


class BankSorter(TaskBot):
    loop_delay = 600

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.sort = self.settings.bool('sort_bank', True)
        self.report = self.settings.bool('report_quest_junk', True)
        self.drop = self.settings.bool('drop_quest_junk', False)
        self.status = 'starting'
        self.moves = 0
        self.done = False
        self.add(Task(lambda: not self.done, self.run))

    def drop_all(self, found):
        """Withdraws each leftover and drops it, opening the bank again after. Use with yield from: how many went."""
        dropped = 0
        for item in found:
            if not bank.withdraw_by_id(item.id, 'Withdraw All'):
                continue
            landed = yield from execution.delay_until(lambda: inventory.count_by_id(item.id) > 0, 3000)
            if not landed:
                continue
            yield from bank.close()
            held = [i for i in inventory.items() if i.id == item.id]
            if len(held) > 0 and held[0].interact('Drop'):
                gone = yield from execution.delay_until(lambda: inventory.count_by_id(item.id) == 0, 3000)
                if gone:
                    dropped += 1
            opened = yield from banking.open()
            if not opened:
                break
        return dropped

    def run(self):
        self.done = True
        # Here the quest list reads without opening its tab, so the statuses are read with the bank open too.
        self.status = 'walking to the bank'
        opened = yield from banking.open()
        if not opened:
            self.request_finish('BankSorter: could not open a bank')
            return

        found = []
        if self.report or self.drop:
            self.status = 'reading quest leftovers'
            found = find_quest_junk(bank.items(), quests.status)
            self.log(report_line(found))

        self.status = 'dropping quest leftovers'
        dropped = 0
        if self.drop:
            dropped = yield from self.drop_all(droppable_of(found, True))

        self.status = 'sorting'
        result = SortOff()
        if self.sort:
            result = yield from sort_bank(self.log, quest_categories(found))

        self.moves = result.moves
        self.status = result.reason
        self.log(summary_line(result, found, dropped))
        yield from bank.close()
        self.request_finish(f'BankSorter: {result.reason}')

    def on_progress_report(self):
        return {'Status': self.status, 'Moves sent': self.moves, 'Sorting': 'on' if self.sort else 'off', 'Drop': 'ARMED' if self.drop else 'off'}


BOT = define_bot(
    name='BankSorter',
    create=BankSorter,
    description='Walks to a bank and rewrites the slot order into categories, coins first and junk last, then stops. Optionally reports, and drops, quest items a finished quest no longer needs',
    category='Utility',
    tags=['bank', 'sort', 'tidy', 'quest'],
    settings_schema=SETTINGS,
)

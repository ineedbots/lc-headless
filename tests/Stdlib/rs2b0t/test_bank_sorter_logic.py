"""rs2b0t's test/scripts/BankSorter/BankSorterLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from bots.bank_sorter import droppable_of, quest_categories, report_line, summary_line


def finding(name, droppable, id=1):
    return Record({
        'id': id,
        'name': name,
        'quest': 'A Quest',
        'status': ('complete' if droppable else 'inProgress'),
        'droppable': droppable,
    })


def _fn1():
    def _fn2():
        found = [finding('a', True), finding('b', False)]
        expect([f.name for f in droppable_of(found, True)]).to_equal(['a'])
    test('it keeps only droppable findings when arming is on', _fn2)

    def _fn3():
        expect(droppable_of([finding('a', True)], False)).to_equal([])
    test('it keeps nothing when arming is off', _fn3)


describe('droppableOf', _fn1)


def _fn4():
    def _fn5():
        expect(quest_categories([finding('a', True, 42)]).get(42)).to_be('questObsolete')
    test('a complete quest sinks its leftover to questObsolete', _fn5)

    def _fn6():
        expect(quest_categories([finding('a', False, 43)]).get(43)).to_be('questLive')
    test('anything else stays questLive', _fn6)


describe('questCategories', _fn4)


def _fn7():
    def _fn8():
        line = report_line([finding('Stake', True), finding("Rat's tail", False)])
        expect(line).to_contain('Stake')
        expect(line).to_contain("Rat's tail")
        expect(line.split('\n')).to_have_length(1)
    test('it names each finding and its quest on one line', _fn8)

    def _fn9():
        expect(report_line([])).to_contain('none')
    test('nothing found still says so', _fn9)


describe('reportLine', _fn7)


def _fn10():
    def _fn11():
        line = summary_line(Record({'sorted': True, 'moves': 12, 'mode': 'insert', 'unmatched': [1, 2], 'reason': 'sorted'}), [finding('a', True)], 1)
        expect(line).to_contain('12 moves')
        expect(line).to_contain('insert')
        expect(line).to_contain('2 unfiled')
        expect(line).to_contain('1 dropped')
        expect(line.split('\n')).to_have_length(1)
    test('it names the moves, the mode and the leftovers on one line', _fn11)

    def _fn12():
        line = summary_line(Record({'sorted': False, 'moves': 4, 'mode': 'swap', 'unmatched': [], 'reason': 'bank closed'}), [], 0)
        expect(line).to_contain('bank closed')
    test('an unsorted run says why', _fn12)


describe('summaryLine', _fn10)


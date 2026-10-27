"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-config.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.config import arrav_config, hash_name, resolve_gang

def _fn1():

    def _fn2():
        expect(resolve_gang('phoenix', 'anyone')).to_be('phoenix')
        expect(resolve_gang('blackarm', 'anyone')).to_be('blackarm')
    test('an explicit setting is returned unchanged', _fn2)

    def _fn3():
        first = resolve_gang('random', 'Zezima')
        for i in range(20):
            expect(resolve_gang('random', 'Zezima')).to_be(first)
    test('random is stable for one name across calls', _fn3)

    def _fn4():
        expect(resolve_gang('random', 'Jon Snow')).to_be(resolve_gang('random', 'jon_snow'))
        expect(resolve_gang('random', 'JONSNOW')).to_be(resolve_gang('random', 'jonsnow'))
    test('random ignores case, spaces and underscores', _fn4)

    def _fn5():
        names = [f'bot{i}' for i in range(200)]
        phoenix = len([n for n in names if resolve_gang('random', n) == 'phoenix'])
        expect(phoenix).to_be_greater_than(60)
        expect(phoenix).to_be_less_than(140)
    test('random splits a population of names across both gangs', _fn5)

    def _fn6():
        expect(resolve_gang('random', None)).to_be('phoenix')
        expect(resolve_gang('random', '')).to_be('phoenix')
    test('random falls back to phoenix when the name is not known yet', _fn6)

    def _fn7():
        expect(hash_name('a')).to_be_greater_than_or_equal(0)
        expect(hash_name('a')).to_be_less_than(2 ** 32)
        expect(hash_name('a')).not_.to_be(hash_name('b'))
    test('hashName is a 32-bit unsigned value', _fn7)

    def _fn8():
        expect(arrav_config.gang).to_be('random')
        expect(arrav_config.partner).to_be('')
        expect(arrav_config.cert_target).to_be(2)
    test('the config defaults match the documented settings', _fn8)
describe('arrav gang selection', _fn1)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

"""rs2b0t's test/api/ai/quests/exec/fundCoins.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.quests.exec.fund_coins import AL_KHARID_ENTRY_CASH, AL_KHARID_FUNDING_MAN, AL_KHARID_TOLL, KEBAB_SELLER, SAFE_PICKPOCKET_HP, VARROCK_FUNDING_MAN, earn_quest_coins_step, east_of_al_kharid_gate, fund_quest_coins, in_al_kharid_funding_area

after_each(lambda: event_signal.set_interrupt(None))


def _fn1():
    def _fn2():
        # Same tiles Waterfall / Goblin Diplomacy used successfully live.
        expect(Record({'x': AL_KHARID_FUNDING_MAN.x, 'z': AL_KHARID_FUNDING_MAN.z, 'level': AL_KHARID_FUNDING_MAN.level})).to_equal(Record({'x': 3279, 'z': 3188, 'level': 0}))
        expect(Record({'x': KEBAB_SELLER.x, 'z': KEBAB_SELLER.z, 'level': KEBAB_SELLER.level})).to_equal(Record({'x': 3272, 'z': 3182, 'level': 0}))
        expect(AL_KHARID_FUNDING_MAN.distance_to(KEBAB_SELLER)).to_be_less_than_or_equal(10)
    test('Al Kharid Man stands next to the kebab shop', _fn2)

    def _fn3():
        expect(AL_KHARID_TOLL).to_be(10)
        expect(AL_KHARID_ENTRY_CASH).to_be(13)
        expect(SAFE_PICKPOCKET_HP).to_be(3)
        expect(Record({'x': VARROCK_FUNDING_MAN.x, 'z': VARROCK_FUNDING_MAN.z, 'level': VARROCK_FUNDING_MAN.level})).to_equal(Record({'x': 3240, 'z': 3405, 'level': 0}))
    test('toll entry cash covers gate + one kebab', _fn3)

    def _fn4():
        expect(in_al_kharid_funding_area(Record({'x': 3279, 'z': 3188, 'level': 0}))).to_be(True)
        expect(in_al_kharid_funding_area(Record({'x': 3304, 'z': 3120, 'level': 0}))).to_be(False)
        expect(in_al_kharid_funding_area(Record({'x': 3240, 'z': 3405, 'level': 0}))).to_be(False)
        expect(in_al_kharid_funding_area(None)).to_be(False)
    test('inAlKharidFundingArea covers the man/kebab block only', _fn4)

    def _fn5():
        expect(east_of_al_kharid_gate(Record({'x': 3303, 'z': 3129, 'level': 0}))).to_be(True)
        expect(east_of_al_kharid_gate(Record({'x': 3279, 'z': 3188, 'level': 0}))).to_be(True)
        expect(east_of_al_kharid_gate(Record({'x': 3240, 'z': 3405, 'level': 0}))).to_be(False)
        expect(east_of_al_kharid_gate(Record({'x': 3093, 'z': 3243, 'level': 0}))).to_be(False)
    test('eastOfAlKharidGate treats Shantay north as already past the toll', _fn5)

    def _fn6():
        step = earn_quest_coins_step(50, 'test')
        expect(step.kind).to_be('custom')
        if step.kind == 'custom':
            expect(step.name).to_contain('50')
            expect(step.name.lower()).to_contain('al kharid')
    test('earnQuestCoinsStep is a custom earn step', _fn6)

    def _fn7():
        event_signal.set_interrupt(lambda: True)
        _w8 = yield from fund_quest_coins(50, lambda *_args: None)
        expect(_w8).to_be(False)
    test('funding yields before navigation when a runtime event is pending', _fn7)


describe('fundCoins anchors', _fn1)

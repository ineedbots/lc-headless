"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/ernest-basement.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.ernest.basement import CHAIN, DOOR_OPEN, REGION_BOX, basement_region
LEVER = Fake(**{'A': 1 << 0, 'B': 1 << 1, 'C': 1 << 2, 'D': 1 << 3, 'E': 1 << 4, 'F': 1 << 5})
boxes = list(REGION_BOX._fields.items())

def _fn1():

    def _fn2():
        for a_name, a in boxes:
            for b_name, b in boxes:
                if a_name == b_name:
                    continue
                overlaps = a.min_x <= b.max_x and b.min_x <= a.max_x and (a.min_z <= b.max_z) and (b.min_z <= a.max_z)
                expect(overlaps, f'{a_name} overlaps {b_name}').to_be(False)
    test('every region box is disjoint from every other', _fn2)

    def _fn3():
        expect(basement_region(Fake(**{'x': 3116, 'z': 9754, 'level': 0}))).to_be('entry')
        expect(basement_region(Fake(**{'x': 3092, 'z': 9755, 'level': 0}))).to_be('r9')
        expect(basement_region(Fake(**{'x': 3111, 'z': 9761, 'level': 0}))).to_be('r1r4')
        expect(basement_region(Fake(**{'x': 3097, 'z': 9765, 'level': 0}))).to_be('r3')
    test('the landmarks fall in the rooms the chain assumes', _fn3)

    def _fn4():
        expect(basement_region(Fake(**{'x': 3093, 'z': 3243, 'level': 0}))).to_be('outside')
        expect(basement_region(Fake(**{'x': 3116, 'z': 9754, 'level': 1}))).to_be('outside')
        expect(basement_region(None)).to_be('outside')
    test('anything outside the basement, or on another level, is outside', _fn4)
describe('Ernest basement geography', _fn1)

def _fn5():

    def _fn6():
        bits = 0
        for move in CHAIN:
            if move.kind == 'pull':
                bits ^= LEVER._fields.get(move.lever)
                is_down = bits & LEVER._fields.get(move.lever) != 0
                expect(is_down, f'lever {move.lever} should end {move.to}').to_be(move.to == 'down')
            else:
                expect(DOOR_OPEN.get(move.door)(bits), f'{move.door} closed at step').to_be(True)
    test('every move is legal in the bit state it runs in', _fn6)

    def _fn7():
        for move in CHAIN:
            if move.kind != 'door':
                continue
            from_ = basement_region(move.stand)
            to = basement_region(move.arrive)
            expect(from_, f'{move.door} stand is outside').not_.to_be('outside')
            expect(to, f'{move.door} arrival is outside').not_.to_be('outside')
            expect(from_, f'{move.door} does not change room').not_.to_be(to)
    test('every crossing starts in the region its stand is in and lands in another', _fn7)

    def _fn8():
        bits = 0
        for move in CHAIN:
            if move.kind == 'pull':
                bits ^= LEVER._fields.get(move.lever)
        expect(bits).to_be(LEVER.C | LEVER.D | LEVER.F)
        expect(DOOR_OPEN.get('8to9')(bits)).to_be(True)
    test('ends holding C, D and F down — which keeps 8to9 open for the walk out', _fn8)

    def _fn9():
        states = []
        bits = 0
        for move in CHAIN:
            states.append(bits)
            if move.kind == 'pull':
                bits ^= LEVER._fields.get(move.lever)
        for i in range(len(CHAIN) - 1, 0 - 1, -1):
            move = CHAIN[i]
            if move.kind == 'door':
                expect(DOOR_OPEN.get(move.door)(states[i]), f'{move.door} not re-crossable').to_be(True)
    test('undoing the chain in reverse is legal, which is what recovery relies on', _fn9)

    def _fn10():
        last = CHAIN[len(CHAIN) - 1]
        expect(last.kind).to_be('door')
        expect(last.kind == 'door' and basement_region(last.arrive)).to_be('r9')
    test('ends in the oil-can room', _fn10)
describe('Ernest basement chain', _fn5)

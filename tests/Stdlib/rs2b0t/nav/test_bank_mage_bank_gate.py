"""rs2b0t's test/api/bank/mageBankGate.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record, bank_distance

# Here a bank is a dict; rs2b0t's tests read its fields as attributes, so the calls are adapted at the boundary.
BANK_LOCATIONS = as_records(BANK_LOCATIONS)
nearest_bank = record_view(nearest_bank)
nearest_usable_bank = record_view(nearest_usable_bank)
nearest_banks = record_view(nearest_banks)
nearest_bank_reachable = record_view(nearest_bank_reachable)
bank_unlocked = record_view(bank_unlocked)
bank_distance = record_view(bank_distance)
approach_of = record_view(approach_of)


MAGE = ([b for b in BANK_LOCATIONS if b.name == 'Mage Arena'] or [None])[0]
DEEP_WILDERNESS = Record({'x': 3091, 'z': 3958, 'level': 0})


def set_setting(on):
    # Here the Global settings come from the account file, as settings_store.load gives them.
    settings_store.load({} if on is None else {'Global': {'use_mage_bank': on}})


after_each(lambda: set_setting(None))


def _fn1():
    def _fn2():
        # transports.json: magearena_ladder_to_cellar (3091,3958) -> (2542,4714).
        # Not Kolodion's arena teleport. That is the minigame, not the bank.
        expect(MAGE.tile.x).to_be(2542)
        expect(MAGE.tile.z).to_be(4714)
        expect((MAGE.approach.x if MAGE.approach is not None else None)).to_be(3091)
        expect((MAGE.approach.z if MAGE.approach is not None else None)).to_be(3958)
        expect((MAGE.npc_access.name if MAGE.npc_access is not None else None)).to_be('Gundai')
    test('sits where the ladder lands, approached from the ladder mouth', _fn2)

    # 'the surface route it is ranked by is baked into the nav graph' reads rs2b0t's transports.json; here the webs and
    # ladder are data/nav's edges, which the real-cache walker tests route through.


    def _fn4():
        expect(bank_unlocked(MAGE)).to_be(False)
        near = nearest_bank(DEEP_WILDERNESS)
        expect((near.name if near is not None else None)).not_.to_be('Mage Arena')
    test('off by default, so nothing routes through the Wilderness to bank', _fn4)

    def _fn5():
        set_setting(False)
        expect(bank_unlocked(MAGE)).to_be(False)
        expect((nearest_bank(DEEP_WILDERNESS).name if nearest_bank(DEEP_WILDERNESS) is not None else None)).not_.to_be('Mage Arena')
    test('stays off when the setting is explicitly false', _fn5)

    def _fn6():
        set_setting(True)
        expect(bank_unlocked(MAGE)).to_be(True)
        expect((nearest_bank(DEEP_WILDERNESS).name if nearest_bank(DEEP_WILDERNESS) is not None else None)).to_be('Mage Arena')
    test('opting in makes it selectable, and it wins from inside the Wilderness', _fn6)

    def _fn7():
        set_setting(True)
        ardy = nearest_bank(Record({'x': 2616, 'z': 3332, 'level': 0}))
        expect((ardy.name if ardy is not None else None)).to_be('Ardougne West')
    test('even opted in, an Ardougne bot still banks in Ardougne', _fn7)


describe('Mage Arena bank gate', _fn1)

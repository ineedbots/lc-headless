"""rs2b0t's test/scripts/ShopBuyout/shopPresets.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from bots.shop_buyout import SHOP_PRESETS, preset_buyable_names, preset_by_label, shop_record_of


def _fn1():
    def _fn2():
        labels = [p.label for p in SHOP_PRESETS]
        expect(len(set(labels))).to_be(len(labels))
    test('labels are unique (they are the dropdown options)', _fn2)

    def _fn3():
        for p in SHOP_PRESETS:
            expect(shop_record_of(p.keeper), f"no shopdb shop for keeper '{p.keeper}' ({p.label})").to_be_defined()
    test('every keeper matches a shopdb shopkeeper (catches typos on new shops)', _fn3)

    def _fn4():
        expect(preset_by_label(SHOP_PRESETS[0].label).keeper).to_be(SHOP_PRESETS[0].keeper)
        expect(preset_by_label('nope')).to_be_undefined()
    test('presetByLabel round-trips; unknown label -> undefined', _fn4)

    def _fn5():
        names = [n.lower() for n in preset_buyable_names()]
        expect(len([n for n in names if 'rune' in n]) > 0).to_be(True)
        expect(len([n for n in names if 'arrow' in n]) > 0).to_be(True)
        expect(names).to_contain('feather')
        expect(names).to_contain('vial of water')
    test('buyable names cover the listed shops (arrows + feathers + runes present)', _fn5)


describe('shop presets', _fn1)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/barcrawl/BarcrawlLogic.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.banksort import BARS
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.barcrawl.barcrawl_logic import BARCRAWL_GP, BARS, next_bar, parse_card
from rs2004.geometry import Tile

def card(done):
    """Verbatim from scroll.rs2's `scroll_barcrawl_card`."""
    label = Fake(**{'bluemoon': 'BlueMoon Inn', 'blurberry': "Blurberry's Bar", 'deadman': "Dead Man's Chest", 'dragoninn': 'Dragon Inn', 'flyinghorse': 'Flying Horse Inn', 'forestersarms': 'Foresters Arms', 'jollyboar': 'Jolly Boar Inn', 'karamjaspirits': 'Karamja Spirits Bar', 'risingsun': 'Rising Sun Inn', 'rustyanchor': 'Rusty Anchor Inn'})
    return ['@blu@The Official Alfred Grimhand Barcrawl!'] + list([f'@gre@{name} - Completed!' if key in done else f'@red@{name} - Not Completed...' for key, name in list(label._fields.items())])

def _fn2():

    def _fn3():
        progress = parse_card(card([]))
        expect(len(progress.remaining if progress is not None else None)).to_be(len(BARS))
        expect(progress.done if progress is not None else None).to_be(False)
    test('an untouched card leaves every bar outstanding', _fn3)

    def _fn4():
        progress = parse_card(card(list(Fake(**{'bluemoon': 0, 'blurberry': 0, 'deadman': 0, 'dragoninn': 0, 'flyinghorse': 0, 'forestersarms': 0, 'jollyboar': 0, 'karamjaspirits': 0, 'risingsun': 0, 'rustyanchor': 0})._fields.keys())))
        expect(progress.done if progress is not None else None).to_be(True)
        expect(progress.remaining if progress is not None else None).to_equal([])
    test('a fully signed card is done', _fn4)

    def _fn5():
        progress = parse_card(card(['jollyboar', 'risingsun']))
        expect([b.line for b in (progress.remaining if progress is not None else None)]).not_.to_contain('jolly boar')
        expect([b.line for b in (progress.remaining if progress is not None else None)]).not_.to_contain('rising sun')
        expect(len(progress.remaining if progress is not None else None)).to_be(len(BARS) - 2)
    test('signed bars drop out one at a time', _fn5)

    def _fn6():
        expect(parse_card(['@dbl@Some other scroll.'])).to_be_null()
    test('a page that is not the card reads as nothing', _fn6)
describe('barcrawl card', _fn2)

def _fn7():

    def _fn8():
        expect(next_bar(BARS, Tile(3213, 3424, 0)).line if next_bar(BARS, Tile(3213, 3424, 0)) is not None else None).to_be('bluemoon')
    test('heads for the nearest outstanding bar', _fn8)

    def _fn9():
        expect(next_bar(BARS, None).line if next_bar(BARS, None) is not None else None).to_be(BARS[0].line)
    test('falls back to list order when the tile is unknown', _fn9)

    def _fn10():
        outstanding = [b for b in BARS if b.line != 'bluemoon']
        expect(next_bar(outstanding, Tile(3213, 3424, 0)).line if next_bar(outstanding, Tile(3213, 3424, 0)) is not None else None).not_.to_be('bluemoon')
    test('never picks a bar that is already signed', _fn10)

    def _fn11():
        expect(BARCRAWL_GP).to_be_greater_than(sum([b.gp for b in BARS]))
    test('the coin float covers every drink with slack', _fn11)
describe('barcrawl tour order', _fn7)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

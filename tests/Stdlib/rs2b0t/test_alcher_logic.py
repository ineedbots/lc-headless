"""rs2b0t's test/scripts/Alcher/AlcherLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. The bundled-schema test reads the bot's own SETTINGS, since there's no script registry here."""

import math

from rs2004.catalogs import Record, item_db
from bots.alcher import ALCH_FODDER_OBJS, ALCH_ITEMS, ALCH_OPTIONS, ALCH_OPTION_LABELS, BOT, CUSTOM_ALCH_KEY, DEFAULT_ALCH_ITEMS
from bots.alcher import FIRE_STAFF, FIRE_STAVES, HIGH_ALCH_LEVEL, HIGH_ALCH_RATE, HIGH_ALCH_SPELL, LOW_ALCH_LEVEL, LOW_ALCH_RATE
from bots.alcher import LOW_ALCH_SPELL, SETTINGS, SPELL_HIGH, SPELL_LOW, SPELL_OPTIONS, alch_item, alch_value_of, custom_alch_item
from bots.alcher import fmt_gp, next_alch_target, pick_fire_staff, resolve_alch_spell, selected_alch_items


def _fn1():
    def _fn2():
        missing = [obj for obj in ALCH_FODDER_OBJS if not any([r.obj == obj for r in item_db()])]
        expect(missing).to_equal([])
        expect(ALCH_ITEMS).to_have_length(len(ALCH_FODDER_OBJS))
    test('every listed obj is in item_db()', _fn2)

    def _fn3():
        for item in ALCH_ITEMS:
            rec = ([r for r in item_db() if r.obj == item.key] or [None])[0]
            expect(item.alch_value).to_be(math.floor(rec.cost * HIGH_ALCH_RATE))
    test('the alch value is 60% of the shop cost, rounded down', _fn3)

    def _fn4():
        expect((alch_item('yew_longbow').alch_value if alch_item('yew_longbow') is not None else None)).to_be(768)
        expect((alch_item('magic_longbow').alch_value if alch_item('magic_longbow') is not None else None)).to_be(1536)
        expect((alch_item('steel_platebody').alch_value if alch_item('steel_platebody') is not None else None)).to_be(1200)
        expect((alch_item('dragonhide_body').alch_value if alch_item('dragonhide_body') is not None else None)).to_be(4680)
        expect((alch_item('black_dragonhide_body').alch_value if alch_item('black_dragonhide_body') is not None else None)).to_be(8088)
    test('the classic fodder pays what the game pays', _fn4)

    def _fn5():
        ids = [i.id for i in ALCH_ITEMS]
        expect(len(set(ids))).to_be(len(ids))
    test('item ids are unique', _fn5)

    def _fn6():
        for i in range(1, len(ALCH_ITEMS)):
            expect(ALCH_ITEMS[i - 1].alch_value).to_be_greater_than_or_equal(ALCH_ITEMS[i].alch_value)
    test('entries are ordered by alch value, richest first', _fn6)


describe('the fodder table resolves against the item database', _fn1)


def _fn7():
    def _fn8():
        hides = [i for i in ALCH_ITEMS if i.name == 'Dragonhide body']
        expect(hides).to_have_length(4)
        expect(len(set([i.label for i in hides]))).to_be(4)
    test('all four dragonhide bodies share one client name', _fn8)

    def _fn9():
        labels = [i.label for i in ALCH_ITEMS]
        expect(len(set(labels))).to_be(len(labels))
    test('every label is unique, so a chip never names two items', _fn9)

    def _fn10():
        expect(ALCH_OPTION_LABELS.get('magic_longbow')).to_be('Magic longbow (1,536)')
        expect(ALCH_OPTION_LABELS.get('black_dragonhide_body')).to_be("Black d'hide body (8,088)")
    test('the chip label carries the alch value', _fn10)

    def _fn11():
        expect(sorted(list(ALCH_OPTION_LABELS.keys()))).to_equal(sorted(list(ALCH_OPTIONS)))
    test('every option has a label and every label an option', _fn11)

    # Why: the chips are for finding an item, so they read in name order; the drain still runs richest first off ALCH_ITEMS.
    def _fn12():
        shown = [ALCH_OPTION_LABELS.get(key) for key in ALCH_OPTIONS[1:]]
        expect(shown).to_equal(sorted(list(shown)))
        # Why: a cheap adamant sword ahead of the far richer rune platebody is what says this is not the old value order.
        expect(shown[0]).to_be('Adamant 2h sword (3,840)')
        expect((shown.index('Adamant 2h sword (3,840)') if 'Adamant 2h sword (3,840)' in shown else -1)).to_be_less_than((shown.index('Rune platebody (39,000)') if 'Rune platebody (39,000)' in shown else -1))
    test('the chips after the custom one read alphabetically by the label shown', _fn12)

    def _fn13():
        expect([i.alch_value for i in ALCH_ITEMS]).to_equal(sorted(list([i.alch_value for i in ALCH_ITEMS]), key=lambda b: b, reverse=True))
        expect([i.key for i in selected_alch_items(['yew_longbow', 'rune_platebody'])]).to_equal(['rune_platebody', 'yew_longbow'])
    test('the drain order is untouched by the chip order, richest first', _fn13)


describe('labels disambiguate what the client name does not', _fn7)


def _fn14():
    def _fn15():
        expect(ALCH_OPTIONS[0]).to_be(CUSTOM_ALCH_KEY)
        expect(ALCH_OPTION_LABELS.get(CUSTOM_ALCH_KEY)).to_be('Custom item (named below)')
        expect(any([i.key == CUSTOM_ALCH_KEY for i in ALCH_ITEMS])).to_be(False)
    test('is the first option and says where its item comes from', _fn15)

    def _fn16():
        expect(custom_alch_item('Iron platebody')).to_equal(Record({
        'key': 'iron_platebody',
        'id': 1115,
        'name': 'Iron platebody',
        'label': 'Iron platebody',
        'alch_value': 336,
    }))
    test('resolves a display name from the item database at 60% of shop cost', _fn16)

    def _fn17():
        expect((custom_alch_item(' IRON_PLATEBODY ').id if custom_alch_item(' IRON_PLATEBODY ') is not None else None)).to_be(1115)
        expect((custom_alch_item('iron  platebody').id if custom_alch_item('iron  platebody') is not None else None)).to_be(1115)
    test('accepts the obj name, any case, with stray spaces', _fn17)

    def _fn18():
        expect(custom_alch_item("Black d'hide body")).to_be(alch_item('black_dragonhide_body'))
        expect(custom_alch_item('rune_chainbody')).to_be(alch_item('rune_chainbody'))
    test('a name already in the fodder table resolves to that entry, label and all', _fn18)

    def _fn19():
        expect((custom_alch_item('Dragonhide body').key if custom_alch_item('Dragonhide body') is not None else None)).to_be('dragonhide_body')
        expect((custom_alch_item('Dragonhide chaps').key if custom_alch_item('Dragonhide chaps') is not None else None)).to_be('dragonhide_chaps')
    test('a client name several items share goes to the obj spelled the same way', _fn19)

    def _fn20():
        expect(custom_alch_item('nonsense')).to_be_null()
        expect(custom_alch_item('')).to_be_null()
        expect(custom_alch_item('   ')).to_be_null()
    test('an unknown or blank name is null', _fn20)


describe('the custom chip', _fn14)


def _fn21():
    def _fn22():
        for key in DEFAULT_ALCH_ITEMS:
            expect(ALCH_OPTIONS).to_contain(key)
    test('every default is a real option', _fn22)

    def _fn23():
        expect(DEFAULT_ALCH_ITEMS).to_contain('yew_longbow')
        expect(DEFAULT_ALCH_ITEMS).to_contain('magic_longbow')
        expect(DEFAULT_ALCH_ITEMS).to_contain('steel_platebody')
        expect(len([k for k in DEFAULT_ALCH_ITEMS if ('dragonhide' in k)])).to_be_greater_than_or_equal(4)
    test('the usual suspects are ticked out of the box', _fn23)


describe('defaults', _fn21)


def _fn24():
    def _fn25():
        picked = selected_alch_items(['yew_longbow', 'black_dragonhide_body', 'magic_longbow'])
        expect([i.key for i in picked]).to_equal(['black_dragonhide_body', 'magic_longbow', 'yew_longbow'])
    test('resolves in table order however the keys arrive', _fn25)

    def _fn26():
        expect([i.key for i in selected_alch_items(['yew_longbow', 'Rune platebody', 'nonsense'])]).to_equal(['yew_longbow'])
    test('drops keys that are not fodder', _fn26)

    def _fn27():
        expect([i.key for i in selected_alch_items(['YEW_LONGBOW'])]).to_equal(['yew_longbow'])
    test('matches keys case-insensitively', _fn27)

    def _fn28():
        expect(sorted([i.key for i in selected_alch_items([])])).to_equal(sorted(list(DEFAULT_ALCH_ITEMS)))
    test('an empty selection falls back to the defaults', _fn28)

    def _fn29():
        expect(sorted([i.key for i in selected_alch_items(['nonsense'])])).to_equal(sorted(list(DEFAULT_ALCH_ITEMS)))
    test('a selection of nothing but junk falls back to the defaults', _fn29)

    def _fn30():
        picked = selected_alch_items([CUSTOM_ALCH_KEY, 'yew_longbow', 'magic_longbow'], 'Rune platebody')
        expect([i.key for i in picked]).to_equal(['rune_platebody', 'magic_longbow', 'yew_longbow'])
    test('the custom chip adds the named item, slotted by value with the rest', _fn30)

    def _fn31():
        picked = selected_alch_items([CUSTOM_ALCH_KEY, 'maple_longbow'], 'Iron platebody')
        expect([i.key for i in picked]).to_equal(['maple_longbow', 'iron_platebody'])
    test('an item outside the fodder table drains last when it is the cheapest', _fn31)

    def _fn32():
        expect([i.key for i in selected_alch_items([CUSTOM_ALCH_KEY, 'yew_longbow'], 'Yew longbow')]).to_equal(['yew_longbow'])
    test('a custom item that is also ticked as a chip is listed once', _fn32)

    def _fn33():
        expect(selected_alch_items([CUSTOM_ALCH_KEY], 'nonsense')).to_equal([])
        expect(selected_alch_items([CUSTOM_ALCH_KEY], '')).to_equal([])
    test('the custom chip alone with a name the database lacks selects nothing, never the defaults', _fn33)

    def _fn34():
        expect([i.key for i in selected_alch_items(['yew_longbow'], 'Rune platebody')]).to_equal(['yew_longbow'])
        expect(sorted([i.key for i in selected_alch_items([], 'Rune platebody')])).to_equal(sorted(list(DEFAULT_ALCH_ITEMS)))
    test('the custom name is ignored while its chip is clear', _fn34)


describe('selectedAlchItems', _fn24)


def _fn35():
    selected = selected_alch_items(['yew_longbow', 'magic_longbow', 'steel_platebody'])

    def _fn36():
        expect((next_alch_target(selected, set()).key if next_alch_target(selected, set()) is not None else None)).to_be('magic_longbow')
    test('takes the richest item the bank still has', _fn36)

    def _fn37():
        expect((next_alch_target(selected, set(['magic_longbow'])).key if next_alch_target(selected, set(['magic_longbow'])) is not None else None)).to_be('steel_platebody')
        expect((next_alch_target(selected, set(['magic_longbow', 'steel_platebody'])).key if next_alch_target(selected, set(['magic_longbow', 'steel_platebody'])) is not None else None)).to_be('yew_longbow')
    test('skips the ones the bank has run out of', _fn37)

    def _fn38():
        expect(next_alch_target(selected, set([i.key for i in selected]))).to_be_null()
    test('is null once every item is empty', _fn38)

    def _fn39():
        expect(next_alch_target([], set())).to_be_null()
    test('is null with nothing selected', _fn39)


describe('nextAlchTarget', _fn35)


def _fn40():
    def _fn41():
        expect(fmt_gp(0)).to_be('0')
        expect(fmt_gp(768)).to_be('768')
        expect(fmt_gp(1536)).to_be('1.5k')
        expect(fmt_gp(15360)).to_be('15k')
        expect(fmt_gp(412900)).to_be('413k')
        expect(fmt_gp(4812000)).to_be('4.8m')
        expect(fmt_gp(38900000)).to_be('38.9m')
    test('reads at a glance across four orders of magnitude', _fn41)

    def _fn42():
        expect(fmt_gp(999.6)).to_be('1.0k')
    test('rounds rather than truncating a fractional rate', _fn42)


describe('fmtGp', _fn40)


def _fn43():
    def _fn44():
        expect(resolve_alch_spell('')).to_equal(Record({'key': SPELL_HIGH, 'name': HIGH_ALCH_SPELL, 'level': HIGH_ALCH_LEVEL, 'rate': HIGH_ALCH_RATE}))
        expect(resolve_alch_spell('High').name).to_be(HIGH_ALCH_SPELL)
        expect(resolve_alch_spell('high level alchemy').name).to_be(HIGH_ALCH_SPELL)
    test('High is the default, so a missing setting keeps saved items and alchs working', _fn44)

    def _fn45():
        expect(resolve_alch_spell('Low')).to_equal(Record({'key': SPELL_LOW, 'name': LOW_ALCH_SPELL, 'level': LOW_ALCH_LEVEL, 'rate': LOW_ALCH_RATE}))
        expect(resolve_alch_spell('low level alchemy').name).to_be(LOW_ALCH_SPELL)
        expect(resolve_alch_spell('lowalch').level).to_be(LOW_ALCH_LEVEL)
    test('Low maps to Low Level Alchemy at 21 Magic and 40% of shop cost', _fn45)

    def _fn46():
        cost = ([r for r in item_db() if r.obj == 'yew_longbow'] or [None])[0].cost
        expect(alch_value_of(cost, HIGH_ALCH_RATE)).to_be(768)
        expect(alch_value_of(cost, LOW_ALCH_RATE)).to_be(512)
        expect(((selected_alch_items(['yew_longbow'], '', LOW_ALCH_RATE) or [None])[0].alch_value if (selected_alch_items(['yew_longbow'], '', LOW_ALCH_RATE) or [None])[0] is not None else None)).to_be(512)
    test('a yew longbow pays 512 under Low and 768 under High', _fn46)

    def _fn47():
        expect(SETTINGS['spell'].type).to_be('string')
        expect(SETTINGS['spell'].default).to_be(SPELL_HIGH)
        expect(SETTINGS['spell'].options).to_equal(SPELL_OPTIONS)
        expect(SETTINGS['items'].default).to_equal(DEFAULT_ALCH_ITEMS)
        expect(SETTINGS['alchs'].default).to_be(27)
        expect(BOT.settings_schema['spell'].default).to_be(SPELL_HIGH)
    test('the bundled Alcher defaults spell to High and leaves items and alchs alone', _fn47)


describe('the spell setting', _fn43)


def _fn49():
    def _fn50():
        expect(FIRE_STAVES[0]).to_be(FIRE_STAFF)
        expect(pick_fire_staff(lambda name: name == 'Fire battlestaff' or name == 'Staff of fire')).to_be('Staff of fire')
    test('Staff of fire is first so a bank that has both keeps the old withdraw', _fn50)

    def _fn51():
        expect(pick_fire_staff(lambda name: name == 'Fire battlestaff')).to_be('Fire battlestaff')
        expect(pick_fire_staff(lambda name: False)).to_be_undefined()
    test('accepts a Fire battlestaff on its own', _fn51)


describe('pickFireStaff', _fn49)


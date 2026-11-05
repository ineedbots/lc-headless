"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerEquipment.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.equipment import gathering_tool, melee_equipment, ranged_bow
from bots.account_leveler.offers import supply_offer
from bots.account_leveler.shopping import audit_supplies

def snapshot(levels=None, stock=None):
    if levels is None:
        levels = Record({})
    if stock is None:
        stock = Record({'coins': 500000})
    _merged1 = {}
    for _k, _v in {'attack': 1, 'strength': 1, 'defence': 1, 'ranged': 1, 'woodcutting': 1, 'mining': 1}.items():
        _merged1[_k] = _v
    for _k, _v in ((levels._fields if isinstance(levels, Record) else levels)).items():
        _merged1[_k] = _v
    return Record({'levels': Record(_merged1), 'stock': stock, 'bank_ready': True, 'quests': Record({}), 'target': 40, 'wilderness': False, 'now': 0})

def _fn2(*_args):
    expect(gathering_tool(snapshot(Record({}), Record({'coins': 0, 'rune axe': 1})), 'axe')).to_equal(Record({'item': 'Rune axe', 'count': 1, 'carry': 1}))
test('uses a banked rune axe from inventory at woodcutting and attack level one', _fn2)

def _fn3(*_args):
    expect(gathering_tool(snapshot(), 'axe')).to_equal(Record({'item': 'Steel axe', 'count': 1, 'carry': 1}))
test('buys the best stocked axe rather than requiring an unavailable higher tier', _fn3)

def _fn4(mining, name, *_args):
    expect(gathering_tool(snapshot(Record({'mining': float(mining)})), 'pickaxe')).to_equal(Record({'item': name, 'count': 1, 'carry': 1}))
test_each([[1, 'Iron pickaxe'], [5, 'Iron pickaxe'], [6, 'Steel pickaxe'], [20, 'Steel pickaxe'], [21, 'Mithril pickaxe'], [30, 'Mithril pickaxe'], [31, 'Adamant pickaxe'], [40, 'Adamant pickaxe'], [41, 'Rune pickaxe']])('mining level %i selects %s independently of attack level', _fn4)

def _fn5(*_args):
    expect(gathering_tool(snapshot(Record({'mining': 41}), Record({'coins': 1040})), 'pickaxe').item).to_be('Iron pickaxe')
    expect(gathering_tool(snapshot(Record({'mining': 41}), Record({'coins': 1039})), 'pickaxe').item).to_be('Bronze pickaxe')
    expect(gathering_tool(snapshot(Record({'mining': 41}), Record({'coins': 0, 'adamant pickaxe': 1})), 'pickaxe').item).to_be('Adamant pickaxe')
    expect(gathering_tool(snapshot(Record({'mining': 40}), Record({'coins': 0, 'rune pickaxe': 1, 'steel pickaxe': 1})), 'pickaxe').item).to_be('Steel pickaxe')
test('picks fall back to an affordable tier while protecting travel funds', _fn5)

def _fn6(*_args):
    offer = supply_offer('Rune pickaxe')
    expect((offer.keeper if offer is not None else None)).to_be('Nurmof')
    expect((offer.tile if offer is not None else None)).to_equal(Record({'x': 2997, 'z': 9844, 'level': 0}))
test('pickaxe upgrades have a proven Nurmof shop destination', _fn6)

def _fn7(*_args):
    owned = Record({'coins': 500000, 'rune scimitar': 1, 'rune chainbody': 1, 'rune platelegs': 1})
    expect([need.item for need in melee_equipment(snapshot(Record({'attack': 40, 'defence': 40}), owned))]).to_equal(['Rune scimitar', 'Rune chainbody', 'Rune platelegs', 'Adamant full helm'])
    expect([need.item for need in melee_equipment(snapshot(Record({'attack': 20, 'defence': 1}), owned))]).to_equal(['Mithril scimitar', 'Iron platebody', 'Iron platelegs', 'Iron full helm'])
    expect([need.item for need in melee_equipment(snapshot(Record({'attack': 1, 'defence': 20})))]).to_equal(['Iron scimitar', 'Mithril platebody', 'Mithril platelegs', 'Mithril full helm'])
test('melee chooses owned or stocked upgrades with independent attack and defence gates', _fn7)

def _fn8(*_args):
    kit = melee_equipment(snapshot(Record({'attack': 40, 'defence': 40}), Record({'coins': 200, 'steel scimitar': 1, 'iron chainbody': 1, 'bronze platelegs': 1})))
    expect([need.item for need in kit]).to_equal(['Steel scimitar', 'Iron chainbody', 'Bronze platelegs'])
    expect(all([need.count == 1 and need.carry == 1 and (need.equip == True) for need in kit])).to_be(True)
test('melee kit keeps existing usable gear when no purchase is affordable', _fn8)

def _fn9(*_args):
    expect(ranged_bow(snapshot(Record({'ranged': 40}), Record({'coins': 0, '#857': 1})))).to_equal(Record({'item': 'Yew shortbow', 'id': 857, 'count': 1, 'carry': 1, 'equip': True}))
    expect(ranged_bow(snapshot(Record({'ranged': 30}), Record({'coins': 500000, '#857': 1, '#64': 10, 'yew shortbow': 11}))).id).to_be(843)
    expect(ranged_bow(snapshot(Record({'ranged': 1}))).id).to_be(841)
test('ranged upgrades only choose usable strung bow ids', _fn9)

def _fn10(*_args):
    _merged11 = {}
    for _k, _v in ((snapshot(Record({'mining': 41}))._fields if isinstance(snapshot(Record({'mining': 41})), Record) else snapshot(Record({'mining': 41})))).items():
        _merged11[_k] = _v
    for _k, _v in {'unavailable_items': ['Rune pickaxe', 'adamant pickaxe']}.items():
        _merged11[_k] = _v
    s = Record(_merged11)
    expect(gathering_tool(s, 'pickaxe').item).to_be('Mithril pickaxe')
    s.stock['rune pickaxe'] = 1
    expect(gathering_tool(s, 'pickaxe').item).to_be('Rune pickaxe')
    _merged12 = {}
    for _k, _v in ((snapshot(Record({'ranged': 5}))._fields if isinstance(snapshot(Record({'ranged': 5})), Record) else snapshot(Record({'ranged': 5})))).items():
        _merged12[_k] = _v
    for _k, _v in {'unavailable_items': ['#843', 'Oak longbow']}.items():
        _merged12[_k] = _v
    expect(ranged_bow(Record(_merged12)).id).to_be(841)
test('unavailable upgrades fall back without discarding an already owned tool', _fn10)

def _fn13(*_args):
    expect(ranged_bow(snapshot(Record({'ranged': 50}), Record({'coins': 0, '#859': 1}))).id).to_be(859)
test('owned higher tier longbows retain exact usable ids', _fn13)

def _fn14(*_args):
    s = snapshot(Record({'attack': 40, 'defence': 40, 'ranged': 40, 'strength': 40, 'mining': 6}), Record({'coins': 3500}))
    audit = audit_supplies(s)
    expect(audit.needs).to_equal([Record({'item': 'Steel axe', 'count': 1}), Record({'item': 'Iron pickaxe', 'count': 1})])
    expect(audit.budget + audit.reserve).to_be_less_than_or_equal(3500)
test('startup tool upgrades share a budget and fall back after earlier purchases', _fn14)

def _fn15(*_args):
    s = snapshot(Record({'attack': 40, 'defence': 40, 'ranged': 40, 'strength': 40, 'mining': 21}), Record({'coins': 0, 'rune axe': 1, 'mithril pickaxe': 1}))
    expect(audit_supplies(s).needs).to_equal([])
    expect(audit_supplies(s).skipped).to_equal([])
test('startup recognizes banked upgrades instead of buying extra bronze tools', _fn15)

def _fn16(*_args):
    expect([need.item for need in melee_equipment(snapshot(Record({}), Record({'coins': 3000})))]).to_equal(['Iron scimitar', 'Iron chainbody', 'Bronze platelegs', 'Bronze full helm'])
test('an affordable full melee kit takes priority over spending its leg budget on a stronger body', _fn16)

def _fn17(defence, legs, helm, *_args):
    kit = melee_equipment(snapshot(Record({'defence': float(defence)})))
    expect(kit).to_contain_equal(Record({'item': f'{legs} platelegs', 'count': 1, 'carry': 1, 'equip': True}))
    expect(kit).to_contain_equal(Record({'item': f'{helm} full helm', 'count': 1, 'carry': 1, 'equip': True}))
    expect((supply_offer(f'{legs} platelegs').keeper if supply_offer(f'{legs} platelegs') is not None else None)).to_be('Louie legs')
    expect((supply_offer(f'{helm} full helm').keeper if supply_offer(f'{helm} full helm') is not None else None)).to_be('Peksa')
test_each([[1, 'Iron', 'Iron'], [5, 'Steel', 'Steel'], [10, 'Black', 'Steel'], [20, 'Mithril', 'Mithril'], [30, 'Adamant', 'Adamant'], [40, 'Adamant', 'Adamant']])('defence %i buys usable legs and helmets from their specialist shops', _fn17)

def _fn18(*_args):
    _merged19 = {}
    for _k, _v in ((snapshot(Record({'defence': 30}))._fields if isinstance(snapshot(Record({'defence': 30})), Record) else snapshot(Record({'defence': 30})))).items():
        _merged19[_k] = _v
    for _k, _v in {'unavailable_items': ['Adamant platelegs', 'Adamant full helm']}.items():
        _merged19[_k] = _v
    s = Record(_merged19)
    kit = melee_equipment(s)
    expect([need.item for need in kit]).to_contain('Mithril platelegs')
    expect([need.item for need in kit]).to_contain('Adamant med helm')
test('sold-out legs and full helmets fall back to available tiers and medium helmets', _fn18)

def _fn20(*_args):
    kit = melee_equipment(snapshot(Record({'defence': 40}), Record({'coins': 200, 'iron scimitar': 1, 'iron chainbody': 1, 'iron platelegs': 1, 'rune full helm': 1})))
    expect(kit).to_contain_equal(Record({'item': 'Rune full helm', 'count': 1, 'carry': 1, 'equip': True}))
test('owned usable helmets are equipped even without a shopping budget', _fn20)

def resolved_wait(value):
    if False:
        yield
    return value

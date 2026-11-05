"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerSupplies.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.supplies import game_supply_port, provision, stock_counts, SupplyStockError
from bots.account_leveler.equipment import melee_equipment
from bots.account_leveler.offers import supply_offer, supply_offers

def fixture(coins=10000):
    bank = Record({'Coins': coins, 'Shrimps': 30})
    pack = Record({})
    worn = Record({'Bronze sword': 1})
    purchases = [0]
    spent = [0]
    price = [112]

    def _fn1():
        return True
        if False:
            yield

    def _fn2():
        for name, count in pack.items():
            _v3 = bank.get(name)
            bank[name] = ((_v3 if _v3 is not None else 0)) + count
            pack.pop(name)
        if False:
            yield

    def _fn6():
        _merged8 = {}
        for _k, _v in (({_k: _v for _k, _v in [[k.lower(), v] for k, v in list(bank.items())]}._fields if isinstance({_k: _v for _k, _v in [[k.lower(), v] for k, v in list(bank.items())]}, Record) else {_k: _v for _k, _v in [[k.lower(), v] for k, v in list(bank.items())]})).items():
            _merged8[_k] = _v
        for _k, _v in ((Record({})._fields if isinstance(Record({}), Record) else Record({}))).items():
            _merged8[_k] = _v
        return Record(_merged8)

    def _fn9(name):
        _v10 = pack.get(name)
        _v11 = worn.get(name)
        pack[name] = ((_v10 if _v10 is not None else 0)) + ((_v11 if _v11 is not None else 0))
        worn.pop(name, None)
        return True
        if False:
            yield

    def _fn12(name, count):
        _v13 = bank.get(name)
        n = min((_v13 if _v13 is not None else 0), count)
        _v14 = bank.get(name)
        bank[name] = ((_v14 if _v14 is not None else 0)) - n
        _v15 = pack.get(name)
        pack[name] = ((_v15 if _v15 is not None else 0)) + n
        return n == count
        if False:
            yield

    def _fn16():
        return True
        if False:
            yield

    def _fn17(*_args, **_kwargs):
        return True
        if False:
            yield

    def _fn18(*_args, **_kwargs):
        return True
        if False:
            yield

    def _fn19(name, count):
        _v20 = pack.get('Coins')
        _v21 = pack.get('Coins')
        n = min(count, ((_v21 if _v21 is not None else 0)) // price[0])
        pack['Coins'] -= n * price[0]
        spent[0] += n * price[0]
        _v22 = pack.get(name)
        pack[name] = ((_v22 if _v22 is not None else 0)) + n
        purchases[0] += 1
        return n
        if False:
            yield

    def _fn23(name):
        _v24 = worn.get(name)
        _v25 = pack.get(name)
        worn[name] = ((_v24 if _v24 is not None else 0)) + ((_v25 if _v25 is not None else 0))
        pack.pop(name, None)
        return True
        if False:
            yield
    port = Record({'bank': _fn1, 'deposit': _fn2, 'stock': _fn6, 'held': lambda name: (pack.get(name) if pack.get(name) is not None else 0), 'worn': lambda name: (worn.get(name) if worn.get(name) is not None else 0), 'equipment': lambda: list(worn.keys()), 'unequip': _fn9, 'withdraw': _fn12, 'close_bank': _fn16, 'walk': _fn17, 'shop': _fn18, 'shop_stock': lambda *_args: 3, 'buy': _fn19, 'close_shop': lambda *_args: empty_wait(), 'equip': _fn23, 'log': lambda *_args: None})

    def _fn26(p):
        price[0] = p
    return Record({'port': port, 'bank': bank, 'pack': pack, 'worn': worn, 'purchases': lambda: purchases[0], 'spent': lambda: spent[0], 'set_price': _fn26})
plan = Record({'id': 'combat', 'label': 'combat', 'objective': 'attack', 'script': 'AutoFighter', 'settings': Record({}), 'combat': True, 'food': 'Shrimps', 'needs': [Record({'item': 'Iron scimitar', 'count': 1, 'carry': 1, 'equip': True}), Record({'item': 'Shrimps', 'count': 24, 'carry': 12})]})

def _fn27(*_args, **_kwargs):
    f = fixture()
    yield from provision(plan, f.port)
    expect(f.worn).to_equal(Record({'Iron scimitar': 1}))
    expect(f.pack).to_equal(Record({'Shrimps': 12}))
    expect(f.bank.get('Bronze sword')).to_be(1)
    expect(f.bank.get('Coins')).to_be(10000 - f.spent())
    expect(f.purchases()).to_be(1)
    if False:
        yield
test('provisioning replaces equipped gear, buys a weapon, banks change and carries unnoted food', _fn27)

def _fn28(*_args, **_kwargs):
    f = fixture()
    f.bank['Iron scimitar'] = 1
    yield from provision(plan, f.port)
    expect(f.purchases()).to_be(0)
    expect(f.worn.get('Iron scimitar')).to_be(1)
    if False:
        yield
test('banked weapons prevent unnecessary purchases', _fn28)

def _fn29(*_args, **_kwargs):
    f = fixture()

    def _fn30(*_args, **_kwargs):
        return 1
        if False:
            yield
    f.port.buy = _fn30
    reject(lambda: provision(plan, f.port), 'Iron scimitar')
test('a purchase with no inventory delta is rejected even when shop reports success', _fn29)

def _fn31(*_args, **_kwargs):
    f = fixture()
    f.port.shop_stock = lambda *_args: 0
    reject(lambda: provision(plan, f.port), 'stock')
    expect(f.purchases()).to_be(0)
    _v32 = f.pack.get('Coins')
    expect((_v32 if _v32 is not None else 0)).to_be_less_than(1000)
    if False:
        yield
test('missing shop stock fails without buying or carrying bank wealth', _fn31)

def _fn33(*_args, **_kwargs):
    counts = stock_counts([Record({'name': 'Shrimps', 'id': 316, 'count': 50, 'noted': True}), Record({'name': 'Shrimps', 'id': 315, 'count': 3, 'noted': False}), Record({'name': 'Herb', 'id': 199, 'count': 2, 'noted': False}), Record({'name': 'Herb', 'id': 201, 'count': 10, 'noted': False})])
    expect(counts.get('shrimps')).to_be(3)
    expect(counts.get('#199')).to_be(2)
test('noted food and herbs of another id do not satisfy a usable manifest', _fn33)

def _fn34(*_args, **_kwargs):
    f = fixture()

    def _fn35():
        return False
        if False:
            yield
    f.port.bank = _fn35
    reject(lambda: provision(plan, f.port), 'bank')
    expect(f.purchases()).to_be(0)
test('an unavailable bank snapshot cannot be treated as no weapon or no coins', _fn34)
bow_plan = Record({'id': 'range', 'label': 'ranged combat', 'objective': 'ranged', 'script': 'AutoFighter', 'settings': Record({}), 'needs': [Record({'item': 'Shortbow', 'id': 841, 'count': 1, 'carry': 1, 'equip': True})]})

def bow_fixture(strung):
    f = fixture()
    f.bank['#50'] = 20
    f.bank['#841'] = strung

    def key(name, items):
        return ((('#50' if items.get('#50') else '#841')) if name == 'Shortbow' else name)

    def _fn38():
        _merged40 = {}
        for _k, _v in (({_k: _v for _k, _v in [[k.lower(), v] for k, v in list(f.bank.items())]}._fields if isinstance({_k: _v for _k, _v in [[k.lower(), v] for k, v in list(f.bank.items())]}, Record) else {_k: _v for _k, _v in [[k.lower(), v] for k, v in list(f.bank.items())]})).items():
            _merged40[_k] = _v
        for _k, _v in {'shortbow': f.bank.get('#50') + f.bank.get('#841')}.items():
            _merged40[_k] = _v
        return Record(_merged40)
    f.port.stock = _fn38
    f.port.held = lambda name: (f.pack.get(key(name, f.pack)) if f.pack.get(key(name, f.pack)) is not None else 0)
    f.port.worn = lambda name: (f.worn.get(key(name, f.worn)) if f.worn.get(key(name, f.worn)) is not None else 0)
    withdraw = f.port.withdraw
    f.port.withdraw = lambda name, count: withdraw(key(name, f.bank), count)
    buy = f.port.buy
    f.port.buy = lambda name, count: buy(('#841' if name == 'Shortbow' else name), count)

    def _fn41(name):
        id = key(name, f.pack)
        if id != '#841' or not f.pack.get(id):
            return False
        f.worn[id] = f.pack.get(id)
        f.pack.pop(id)
        return True
        if False:
            yield
    f.port.equip = _fn41
    return f

def _fn42(strung, *_args, **_kwargs):
    f = bow_fixture(strung)
    yield from provision(bow_plan, f.port)
    expect(f.worn.get('#841')).to_be(1)
    expect(f.bank.get('#50')).to_be(20)
    expect(f.purchases()).to_be((0 if strung else 1))
    if False:
        yield
test_each([0, 1])('equips a strung bow when the bank also holds unstrung bows (strung=%i)', _fn42)

def _fn43(*_args, **_kwargs):
    f = bow_fixture(0)

    def _fn44(*_args, **_kwargs):
        f.pack['#50'] = 1
        return 1
        if False:
            yield
    f.port.buy = _fn44
    reject(lambda: provision(bow_plan, f.port), 'Purchase of Shortbow')
test('rejects a same-name purchase that supplies the wrong bow id', _fn43)

def _fn45(*_args, **_kwargs):
    f = bow_fixture(1)

    def _fn46(*_args, **_kwargs):
        f.pack['#50'] = 1
        return True
        if False:
            yield
    f.port.withdraw = _fn46
    reject(lambda: provision(bow_plan, f.port), 'Could not withdraw')
test('rejects a same-name withdrawal that supplies the wrong bow id', _fn45)

def _fn47(*_args, **_kwargs):
    f = bow_fixture(1)

    def _fn48(*_args, **_kwargs):
        f.worn['#50'] = 1
        return True
        if False:
            yield
    f.port.equip = _fn48
    reject(lambda: provision(bow_plan, f.port), 'Failed to equip')
test('verifies the equipped bow id even when equip reports success', _fn47)

def _fn53(*_args, **_kwargs):
    f = fixture()
    visits = []
    progress = []

    def _fn54(keeper):
        visits.append(keeper)
        return True
        if False:
            yield
    f.port.shop = _fn54
    _merged55 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged55[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Iron chainbody', 'count': 1}), Record({'item': 'Iron platebody', 'count': 1})]}.items():
        _merged55[_k] = _v
    armor = Record(_merged55)

    def _fn56(update):
        progress.append(f'{update.id}:{update.state}')
        if update.id == 'shop:Horvik' and update.state == 'done':
            expect(f.bank.get('Iron chainbody')).to_be(1)
            expect(f.bank.get('Iron platebody')).to_be(1)
    yield from provision(armor, f.port, _fn56)
    expect(visits).to_equal(['Horvik'])
    expect(progress).to_contain('shop:Horvik:done')
    expect(f.bank.get('Coins')).to_be(10000 - f.spent())
test('shops for both armor pieces on one visit and marks the vendor done after banking both', _fn53)

def _fn57(*_args, **_kwargs):
    f = fixture()
    f.set_price(1)
    departing = [0]

    def _fn58(*_args, **_kwargs):
        departing[0] = f.pack.get('Coins')
        f.pack['Coins'] -= 60
        return True
        if False:
            yield
    f.port.walk = _fn58
    _merged59 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged59[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Hammer', 'count': 1})]}.items():
        _merged59[_k] = _v
    yield from provision(Record(_merged59), f.port)
    expect(departing[0]).to_be(207)
    expect(f.bank.get('Hammer')).to_be(1)
    expect(f.bank.get('Coins')).to_be(9939)
test('shopping withdraws fare money in addition to the full item budget', _fn57)

def _fn60(*_args, **_kwargs):
    f = fixture(700)
    reject(lambda: provision(plan, f.port), 'Coins')
    expect(f.purchases()).to_be(0)
    expect(f.bank.get('Coins')).to_be(700)
    if False:
        yield
test('shopping refuses to use the last travel coins for an item', _fn60)

def _fn61(*_args, **_kwargs):
    f = fixture()
    visits = [0]
    largest_pack = [0]
    f.set_price(2)
    f.port.shop_stock = lambda *_args: 500

    def _fn62(*_args, **_kwargs):
        visits[0] += 1
        return True
        if False:
            yield
    f.port.shop = _fn62
    buy = f.port.buy

    def _fn63(name, count):
        bought = run_wait(buy(name, count))
        used = sum([(float(quantity > 0) if item == 'Coins' else quantity) for item, quantity in list(f.pack.items())])
        largest_pack[0] = max(largest_pack[0], used)
        if used > 28:
            raise RuntimeError('Inventory full')
        return bought
        if False:
            yield
    f.port.buy = _fn63
    _merged65 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged65[_k] = _v
    for _k, _v in {'food': None, 'needs': [Record({'item': 'Vial of water', 'count': 54})]}.items():
        _merged65[_k] = _v
    yield from provision(Record(_merged65), f.port)
    expect(f.bank.get('Vial of water')).to_be(54)
    expect(visits[0]).to_be(2)
    expect(largest_pack[0]).to_be(28)
test('batches unstackable supplies without filling more than 28 inventory slots', _fn61)

def _fn66(*_args, **_kwargs):
    f = fixture()
    message = ['']
    destination = [None]

    def _fn67(tile):
        expect(message[0]).to_contain('Zeke')
        expect(destination[0]).to_equal(tile)
        return True
        if False:
            yield
    f.port.walk = _fn67
    buy = f.port.buy

    def _fn68(name, count):
        expect(message[0]).to_contain('1 Iron scimitar')
        return run_wait(buy(name, count))
        if False:
            yield
    f.port.buy = _fn68

    def _fn69(update):
        message[0] = update.message
        destination[0] = update.destination
    yield from provision(plan, f.port, _fn69)
test('progress identifies travel and purchase counts before the external action starts', _fn66)

def _fn70(*_args, **_kwargs):
    f = fixture()
    visits = [0]
    largest_pack = [0]
    f.set_price(2)
    f.port.shop_stock = lambda *_args: 500

    def _fn71(*_args, **_kwargs):
        visits[0] += 1
        return True
        if False:
            yield
    f.port.shop = _fn71
    buy = f.port.buy

    def _fn72(name, count):
        bought = run_wait(buy(name, count))
        used = sum([(float(quantity > 0) if item == 'Coins' else quantity) for item, quantity in list(f.pack.items())])
        largest_pack[0] = max(largest_pack[0], used)
        if used > 28:
            raise RuntimeError('Inventory full')
        return bought
        if False:
            yield
    f.port.buy = _fn72
    _merged74 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged74[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Vial of water', 'count': 27}), Record({'item': 'Rope', 'count': 2})]}.items():
        _merged74[_k] = _v
    yield from provision(Record(_merged74), f.port)
    expect(f.bank.get('Vial of water')).to_be(27)
    expect(f.bank.get('Rope')).to_be(2)
    expect(visits[0]).to_be(2)
    expect(largest_pack[0]).to_be(28)
    expect(f.bank.get('Shrimps')).to_be(30)
test('multiple unstackable needs share a vendor inventory limit including travel food', _fn70)

def _fn75(*_args, **_kwargs):
    f = fixture()
    f.set_price(2)
    visits = [0]
    done = [0]

    def _fn76(*_args, **_kwargs):
        visits[0] += 1
        return True
        if False:
            yield
    f.port.shop = _fn76
    buy = f.port.buy
    f.port.buy = lambda name, count: buy(name, min(count, 1))
    _merged77 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged77[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Small fishing net', 'count': 2}), Record({'item': 'Fly fishing rod', 'count': 2})]}.items():
        _merged77[_k] = _v

    def _fn78(event):
        if event.id == 'shop:Gerrant' and event.state == 'done':
            done[0] += 1
            expect(f.bank.get('Small fishing net')).to_be(2)
            expect(f.bank.get('Fly fishing rod')).to_be(2)
    yield from provision(Record(_merged77), f.port, _fn78)
    expect(visits[0]).to_be(2)
    expect(done[0]).to_be(1)
test('partial purchases are banked and deficits retried before a vendor completes', _fn75)

def _fn79(*_args, **_kwargs):
    f = fixture()
    f.port.shop_stock = lambda name: (0 if name == 'Iron platelegs' else 3)
    _merged80 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged80[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Iron chainbody', 'count': 1}), Record({'item': 'Iron platelegs', 'count': 1})]}.items():
        _merged80[_k] = _v
    armor = Record(_merged80)
    reject(lambda: provision(armor, f.port), Record({'name': 'SupplyStockError', 'items': ['iron platelegs']}))
    expect(f.purchases()).to_be(1)
    expect(f.bank.get('Iron chainbody')).to_be(1)
    expect(f.pack).to_equal(Record({}))
    if False:
        yield
test('sold out gear banks earlier purchases and reports a temporary stock shortage', _fn79)

def _fn81(*_args, **_kwargs):
    f = fixture()

    def _fn82(*_args, **_kwargs):
        return 1
        if False:
            yield
    f.port.buy = _fn82
    reject(lambda: provision(plan, f.port), Record({'name': 'SupplyStockError', 'items': ['iron scimitar']}))
test('a purchase with no usable inventory delta reports a temporary stock shortage', _fn81)

def _fn83(*_args, **_kwargs):
    f = fixture()
    stock = [1]
    attempts = [0]
    buy = f.port.buy
    f.port.shop_stock = lambda *_args: stock[0]

    def _fn84(name, count):
        attempts[0] += 1
        if name == 'Iron platelegs':
            stock[0] = 0
            return 0
        return run_wait(buy(name, count))
        if False:
            yield
    f.port.buy = _fn84
    _merged85 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged85[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Iron chainbody', 'count': 1}), Record({'item': 'Iron platelegs', 'count': 1})]}.items():
        _merged85[_k] = _v
    armor = Record(_merged85)
    reject(lambda: provision(armor, f.port), Record({'name': 'SupplyStockError', 'items': ['iron platelegs']}))
    expect(attempts[0]).to_be(2)
    expect(f.port.shop_stock('Iron platelegs')).to_be(0)
    expect(f.bank.get('Iron chainbody')).to_be(1)
    expect(f.pack).to_equal(Record({}))
test('stock disappearing during purchase banks earlier items before a temporary retry', _fn83)

def _fn86(operation, *_args, **_kwargs):
    f = fixture()

    def _fn87(*_args, **_kwargs):
        return False
        if False:
            yield
    f.port[operation] = _fn87
    _merged88 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged88[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Iron chainbody', 'count': 1}), Record({'item': 'Iron platebody', 'count': 1})]}.items():
        _merged88[_k] = _v
    armor = Record(_merged88)
    reject(lambda: provision(armor, f.port), Record({'name': 'SupplyUnavailableError', 'items': ['iron chainbody', 'iron platebody']}))
    expect(f.purchases()).to_be(0)
test_each(['walk', 'shop'])('an unavailable vendor during %s reports every item at that stop', _fn86)

def _fn89(*_args, **_kwargs):
    f = fixture(100000)
    shelves = Record({'Zeke': ['Mithril scimitar'], 'Horvik': ['Mithril platebody'], 'Louie legs': ['Mithril platelegs'], 'Peksa': ['Mithril full helm']})
    keeper = ['']
    visits = []

    def _fn90(name):
        keeper[0] = name
        visits.append(name)
        return name in shelves
        if False:
            yield
    f.port.shop = _fn90
    f.port.shop_stock = lambda item: (1 if ((item in shelves.get(keeper[0]) if shelves.get(keeper[0]) is not None else None)) else 0)
    needs = melee_equipment(Record({'levels': Record({'attack': 20, 'defence': 20}), 'stock': Record({'coins': 100000}), 'bank_ready': True, 'quests': Record({}), 'target': 40, 'wilderness': False, 'now': 0}))
    _merged91 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged91[_k] = _v
    for _k, _v in {'needs': needs}.items():
        _merged91[_k] = _v
    yield from provision(Record(_merged91), f.port)
    expect(visits).to_equal(['Zeke', 'Horvik', 'Louie legs', 'Peksa'])
    expect(f.worn).to_equal(Record({'Mithril scimitar': 1, 'Mithril platebody': 1, 'Mithril platelegs': 1, 'Mithril full helm': 1}))
    expect(f.bank.get('Coins')).to_be_greater_than_or_equal(200)
test('a planned melee kit buys and equips legs and a helmet from their actual vendors', _fn89)

def _fn94(failure, *_args, **_kwargs):
    f = fixture((1 if failure == 'coins' else 10000))
    if failure == 'bank':

        def _fn95():
            return False
            if False:
                yield
        f.port.bank = _fn95
    reject(lambda: provision(plan, f.port), Record({'name': 'RuntimeError'}))
test_each(['bank', 'coins'])('%s failure does not blacklist purchasable equipment', _fn94)

def _fn98(*_args, **_kwargs):
    f = fixture()
    f.bank['Bronze arrow'] = 79
    f.set_price(1)
    visits = []
    messages = []
    f.port.shop_stock = lambda *_args: 8

    def _fn99(keeper):
        visits.append(keeper)
        return True
        if False:
            yield
    f.port.shop = _fn99
    _merged100 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged100[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Bronze arrow', 'count': 1000})]}.items():
        _merged100[_k] = _v
    yield from provision(Record(_merged100), f.port, lambda event: messages.append(event.message), Record({'best_effort': True}).get('best_effort'))
    expect(visits).to_equal(['Lowe', 'Hickton'])
    expect(f.bank.get('Bronze arrow')).to_be(95)
    expect(any(['905' in message and 'Bronze arrow' in message for message in messages])).to_be(True)
test('best effort takes the available arrows once per supplier instead of chasing the target', _fn98)

def _fn101(*_args, **_kwargs):
    f = fixture()
    f.set_price(1)
    f.port.shop_stock = lambda name: (0 if name == 'Bronze arrow' else 3)
    _merged102 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged102[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Bronze arrow', 'count': 1000}), Record({'item': 'Shortbow', 'count': 1}), Record({'item': 'Hammer', 'count': 1})]}.items():
        _merged102[_k] = _v
    yield from provision(Record(_merged102), f.port, None, Record({'best_effort': True}).get('best_effort'))
    _v103 = f.bank.get('Bronze arrow')
    expect((_v103 if _v103 is not None else 0)).to_be(0)
    expect(f.bank.get('Shortbow')).to_be(1)
    expect(f.bank.get('Hammer')).to_be(1)
    if False:
        yield
test('best effort skips sold out supplies and continues buying other items and vendors', _fn101)

def _fn104(*_args, **_kwargs):
    f = fixture()
    f.set_price(1)
    f.port.shop_stock = lambda *_args: 1000
    buy = f.port.buy
    f.port.buy = lambda name, count: buy(name, min(count, 8))
    _merged105 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged105[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Bronze arrow', 'count': 1000})]}.items():
        _merged105[_k] = _v
    yield from provision(Record(_merged105), f.port, None, Record({'best_effort': True}).get('best_effort'))
    expect(f.purchases()).to_be(2)
    expect(f.bank.get('Bronze arrow')).to_be(16)
    if False:
        yield
test('best effort does not revisit a vendor after a partially fulfilled purchase', _fn104)

def _fn106(*_args, **_kwargs):
    f = fixture()
    f.set_price(1)
    keeper = ['']

    def _fn107(name):
        keeper[0] = name
        return True
        if False:
            yield
    f.port.shop = _fn107
    f.port.shop_stock = lambda *_args: (27 if keeper[0] == 'Aemad' else 0)
    _merged108 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged108[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Vial of water', 'count': 54})]}.items():
        _merged108[_k] = _v
    yield from provision(Record(_merged108), f.port, None, Record({'best_effort': True}).get('best_effort'))
    expect(f.bank.get('Vial of water')).to_be(27)
    expect(f.purchases()).to_be(2)
test('best effort permits capacity-limited batches without exceeding initially available stock', _fn106)

def _fn109(operation, *_args, **_kwargs):
    f = fixture()
    f.set_price(1)
    calls = [0]

    def _fn110(*_args, **_kwargs):
        calls[0] += 1
        return calls[0] > 1
        if False:
            yield
    f.port[operation] = _fn110
    _merged111 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged111[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Shortbow', 'count': 1}), Record({'item': 'Hammer', 'count': 1})]}.items():
        _merged111[_k] = _v
    yield from provision(Record(_merged111), f.port, None, Record({'best_effort': True}).get('best_effort'))
    _v112 = f.bank.get('Shortbow')
    expect((_v112 if _v112 is not None else 0)).to_be(0)
    expect(f.bank.get('Hammer')).to_be(1)
test_each(['walk', 'shop'])('best effort recovers from a failed %s and continues to another supplier', _fn109)

def _fn113(*_args, **_kwargs):
    f = fixture()
    f.bank['Iron scimitar'] = 1
    open = [True]
    stock = f.port.stock
    f.port.stock = lambda: (stock() if open[0] else Record({}))

    def _fn114():
        open[0] = True
        return True
        if False:
            yield
    f.port.bank = _fn114

    def _fn115():
        open[0] = False
        return True
        if False:
            yield
    f.port.close_bank = _fn115
    messages = []
    _merged116 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged116[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Iron scimitar', 'count': 2})]}.items():
        _merged116[_k] = _v
    yield from provision(Record(_merged116), f.port, lambda event: messages.append(event.message))
    expect(([message for message in messages if message.startswith('Buying')] or [None])[0]).to_contain('(1/2 banked)')
test('purchase progress retains bank counts while the shop has replaced the bank modal', _fn113)

def _fn117(*_args, **_kwargs):
    f = fixture()
    f.bank['Bronze arrow'] = 79
    f.set_price(1)
    f.port.shop_stock = lambda *_args: 8
    _merged118 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged118[_k] = _v
    for _k, _v in {'settings': Record({'ammo_withdraw': 300}), 'needs': [Record({'item': 'Bronze arrow', 'count': 1000, 'carry': 300, 'equip': True, 'minimum': 1})]}.items():
        _merged118[_k] = _v
    activity = Record(_merged118)
    yield from provision(activity, f.port)
    expect(f.purchases()).to_be(2)
    expect(f.worn.get('Bronze arrow')).to_be(95)
    expect(activity.needs[0]).to_match_object(Record({'count': 95, 'carry': 95}))
    expect(activity.settings.get('ammo_withdraw')).to_be(95)
    if False:
        yield
test('mandatory ammunition uses a partial purchase and rebases the carried training batch', _fn117)

def _fn119(*_args, **_kwargs):
    f = fixture()
    f.bank['Bronze arrow'] = 79
    f.port.shop_stock = lambda *_args: 0
    _merged120 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged120[_k] = _v
    for _k, _v in {'settings': Record({}), 'needs': [Record({'item': 'Bronze arrow', 'count': 300, 'carry': 300, 'equip': True, 'minimum': 1})]}.items():
        _merged120[_k] = _v
    activity = Record(_merged120)
    yield from provision(activity, f.port)
    expect(f.worn.get('Bronze arrow')).to_be(79)
    expect(f.purchases()).to_be(0)
    if False:
        yield
test('mandatory ammunition uses banked arrows when the shop has none', _fn119)

def _fn121(*_args, **_kwargs):
    f = fixture()
    visits = [0]

    def _fn122(*_args, **_kwargs):
        visits[0] += 1
        return True
        if False:
            yield
    f.port.shop = _fn122
    f.port.shop_stock = lambda *_args: 0
    _merged123 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged123[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Bronze arrow', 'count': 300, 'carry': 300, 'equip': True, 'minimum': 1})]}.items():
        _merged123[_k] = _v
    reject(lambda: provision(Record(_merged123), f.port), Record({'name': 'SupplyStockError', 'items': ['bronze arrow']}))
    expect(visits[0]).to_be(2)
test('mandatory out of stock ammunition reports a retryable shortage after trying both suppliers', _fn121)

def _fn124(*_args, **_kwargs):
    f = fixture(1000000)
    f.bank['Chaos rune'] = 79
    f.bank['Fire rune'] = 160
    f.set_price(1)
    f.port.shop_stock = lambda *_args: 8
    _merged125 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged125[_k] = _v
    for _k, _v in {'settings': Record({'combat_style': 'mage', 'runes_withdraw': 150}), 'needs': [Record({'item': 'Chaos rune', 'count': 200, 'carry': 150, 'minimum': 1}), Record({'item': 'Fire rune', 'count': 800, 'carry': 600, 'minimum': 4})]}.items():
        _merged125[_k] = _v
    activity = Record(_merged125)
    yield from provision(activity, f.port)
    expect(f.purchases()).to_be(4)
    expect(f.pack).to_equal(Record({'Chaos rune': 44, 'Fire rune': 176}))
    expect([[need.count, need.carry] for need in activity.needs]).to_equal([[44, 44], [176, 176]])
    expect(activity.settings.get('runes_withdraw')).to_be(44)
    if False:
        yield
test('rune shortfalls rebase both runes and autocast restocking to the same complete cast batch', _fn124)

def _fn126(*_args, **_kwargs):
    f = fixture(1000000)
    f.bank['Chaos rune'] = 200
    f.bank['Fire rune'] = 3
    f.port.shop_stock = lambda *_args: 0
    _merged127 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged127[_k] = _v
    for _k, _v in {'settings': Record({'combat_style': 'mage'}), 'needs': [Record({'item': 'Chaos rune', 'count': 200, 'carry': 150, 'minimum': 1}), Record({'item': 'Fire rune', 'count': 800, 'carry': 600, 'minimum': 4})]}.items():
        _merged127[_k] = _v
    activity = Record(_merged127)
    reject(lambda: provision(activity, f.port), Record({'name': 'SupplyStockError', 'items': ['fire rune']}))
    expect(f.pack).to_equal(Record({}))
    if False:
        yield
test('an incomplete elemental rune set never launches autocasting', _fn126)

def _fn128(*_args, **_kwargs):
    f = fixture()
    f.set_price(1)
    f.port.shop_stock = lambda *_args: 8
    _merged129 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged129[_k] = _v
    for _k, _v in {'script': 'Fisher', 'settings': Record({'bait_qty': 200}), 'needs': [Record({'item': 'Feather', 'count': 200, 'carry': 200, 'minimum': 1})]}.items():
        _merged129[_k] = _v
    activity = Record(_merged129)
    yield from provision(activity, f.port)
    expect(f.pack.get('Feather')).to_be(8)
    expect(activity.settings.get('bait_qty')).to_be(8)
    if False:
        yield
test('partial feathers update the child fishing restock amount', _fn128)

def _fn130(*_args, **_kwargs):
    f = fixture()
    logs = [0]
    updates = [0]

    def _fn131(*_args, **_kwargs):
        logs[0] += 1
    f.port.log = _fn131

    def _fn132(*_args, **_kwargs):
        updates[0] += 1
    yield from provision(plan, f.port, _fn132)
    expect(updates[0]).to_be_greater_than(0)
    expect(logs[0]).to_be(0)
    if False:
        yield
test('progress uses one logging channel when an action reporter is supplied', _fn130)

def _fn133(*_args, **_kwargs):
    f = fixture()
    f.port.shop_stock = lambda *_args: 0
    _merged134 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged134[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Small fishing net', 'count': 1, 'carry': 1})]}.items():
        _merged134[_k] = _v
    result = provision(Record(_merged134), f.port)
    reject(lambda: result, Record({'name': 'SupplyStockError', 'items': ['small fishing net']}))
    expect(f.purchases()).to_be(0)
    expect(f.pack).to_equal(Record({}))
    if False:
        yield
test('a sold out mandatory tool reports a temporary stock shortage', _fn133)

def _fn135(*_args, **_kwargs):
    f = fixture()
    f.set_price(1)
    f.port.shop_stock = lambda *_args: 8
    _merged136 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged136[_k] = _v
    for _k, _v in {'script': 'LeatherCrafter', 'settings': Record({'thread_per_trip': 100}), 'needs': [Record({'item': 'Thread', 'count': 100, 'carry': 100, 'minimum': 1})]}.items():
        _merged136[_k] = _v
    activity = Record(_merged136)
    yield from provision(activity, f.port)
    expect(f.pack.get('Thread')).to_be(8)
    expect(activity.settings.get('thread_per_trip')).to_be(8)
    if False:
        yield
test('partial thread updates the child crafting restock amount', _fn135)

def vial_fixture(shelves):
    f = fixture()
    f.set_price(2)
    keeper = ['']
    visits = []

    def _fn137(name):
        keeper[0] = name
        visits.append(name)
        return True
        if False:
            yield
    f.port.shop = _fn137
    f.port.shop_stock = lambda *_args: (shelves.get(keeper[0]) if shelves.get(keeper[0]) is not None else 0)
    buy = f.port.buy

    def _fn138(name, count):
        _v139 = shelves.get(keeper[0])
        bought = run_wait(buy(name, min(count, (_v139 if _v139 is not None else 0))))
        shelves[keeper[0]] -= bought
        return bought
        if False:
            yield
    f.port.buy = _fn138

    def _fn140(count):
        _v141 = f.pack.get('Vial')
        filled = min(count, (_v141 if _v141 is not None else 0))
        _v142 = f.pack.get('Vial')
        f.pack['Vial'] = ((_v142 if _v142 is not None else 0)) - filled
        _v143 = f.pack.get('Vial of water')
        f.pack['Vial of water'] = ((_v143 if _v143 is not None else 0)) + filled
        return filled == count
        if False:
            yield
    f.port.fill_vials = _fn140
    _merged144 = {}
    for _k, _v in ((f._fields if isinstance(f, Record) else f)).items():
        _merged144[_k] = _v
    for _k, _v in {'visits': visits}.items():
        _merged144[_k] = _v
    return Record(_merged144)

def _fn145(item, primary, alternate, *_args, **_kwargs):
    for primary_stock in [0, 6, 20]:
        f = vial_fixture({primary: primary_stock, alternate: 100})
        _merged146 = {}
        for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
            _merged146[_k] = _v
        for _k, _v in {'needs': [Record({'item': item, 'count': 20, 'carry': 20, 'minimum': 1})]}.items():
            _merged146[_k] = _v
        yield from provision(Record(_merged146), f.port)
        expect(f.visits).to_equal(([primary, alternate] if primary_stock < 20 else [primary]))
        expect(f.pack.get(item)).to_be(20)
        expect(f.bank.get(item)).to_be(0)
        expect(f.spent()).to_be(40)
    f = vial_fixture({primary: 100, alternate: 100})
    buy = f.port.buy
    f.port.buy = lambda name, count: (resolved_wait(None) if ((f.visits[-1] if len(f.visits) > 0 else None)) == primary else buy(name, count))
    _merged147 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged147[_k] = _v
    for _k, _v in {'needs': [Record({'item': item, 'count': 20, 'carry': 20, 'minimum': 1})]}.items():
        _merged147[_k] = _v
    yield from provision(Record(_merged147), f.port)
    expect(f.visits).to_equal([primary, alternate])
    expect(f.pack.get(item)).to_be(20)
    expect(f.spent()).to_be(40)
    if False:
        yield
test_each([['Mind rune', 'Aubury', 'Betty'], ['Bronze arrow', 'Lowe', 'Hickton']])('%s uses the alternate supplier for partial, empty, and failed primary purchases', _fn145)

def _fn148(item, primary, alternate, *_args, **_kwargs):
    f = vial_fixture({alternate: 100})
    shop = f.port.shop
    f.port.shop = lambda keeper: (resolved_wait(None) if keeper == primary else shop(keeper))
    _merged149 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged149[_k] = _v
    for _k, _v in {'needs': [Record({'item': item, 'count': 20, 'carry': 20, 'minimum': 1})]}.items():
        _merged149[_k] = _v
    yield from provision(Record(_merged149), f.port)
    expect(f.visits).to_equal([alternate])
    expect(f.pack.get(item)).to_be(20)
    if False:
        yield
test_each([['Mind rune', 'Aubury', 'Betty'], ['Bronze arrow', 'Lowe', 'Hickton']])('%s falls back when its primary shop cannot be opened', _fn148)

def vial_plan(count=27):
    _merged150 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged150[_k] = _v
    for _k, _v in {'food': None, 'needs': [Record({'item': 'Vial of water', 'count': count})]}.items():
        _merged150[_k] = _v
    return Record(_merged150)

def _fn151(*_args, **_kwargs):
    f = vial_fixture(Record({'Jatix': 800}))
    yield from provision(vial_plan(), f.port)
    expect(f.visits).to_equal(['Aemad', 'Jatix'])
    expect(f.bank.get('Vial of water')).to_be(27)
    _v152 = f.bank.get('Vial')
    expect((_v152 if _v152 is not None else 0)).to_be(0)
    if False:
        yield
test('a sold out Aemad falls back to Jatix and fills his empty vials', _fn151)

def _fn153(*_args, **_kwargs):
    f = vial_fixture(Record({'Aemad': 5, 'Jatix': 800}))
    yield from provision(vial_plan(), f.port)
    expect(f.visits).to_equal(['Aemad', 'Jatix'])
    expect(f.bank.get('Vial of water')).to_be(27)
    expect(f.spent()).to_be(54)
    if False:
        yield
test('partial water stock buys only the remaining deficit from the next source', _fn153)

def _fn154(*_args, **_kwargs):
    f = vial_fixture(Record({}))
    f.bank['Vial'] = 56
    _merged155 = {}
    for _k, _v in ((vial_plan(54)._fields if isinstance(vial_plan(54), Record) else vial_plan(54))).items():
        _merged155[_k] = _v
    for _k, _v in {'needs': list(vial_plan(54).needs) + [Record({'item': 'Vial', 'count': 2})]}.items():
        _merged155[_k] = _v
    yield from provision(Record(_merged155), f.port)
    expect(f.visits).to_equal([])
    expect(f.bank.get('Vial')).to_be(2)
    expect(f.bank.get('Vial of water')).to_be(54)
    expect(f.spent()).to_be(0)
    if False:
        yield
test('banked empty vials are filled before shopping, preserving required empty vials', _fn154)

def _fn156(*_args, **_kwargs):
    f = vial_fixture(Record({'Jatix': 800, 'Sigmund The Merchant': 10, 'Jiminua': 50}))

    def _fn157(*_args, **_kwargs):
        return False
        if False:
            yield
    f.port.fill_vials = _fn157
    yield from provision(vial_plan(), f.port)
    expect(f.visits).to_equal(['Aemad', 'Jatix', 'Sigmund The Merchant', 'Jiminua'])
    expect(f.bank.get('Vial')).to_be(27)
    expect(f.bank.get('Vial of water')).to_be(27)
test('failed filling banks empty vials and tries another water supplier', _fn156)

def _fn158(best_effort, *_args, **_kwargs):
    f = vial_fixture(Record({'Aemad': 2}))
    result = provision(vial_plan(), f.port, None, Record({'best_effort': best_effort}).get('best_effort'))
    if best_effort:
        yield from result
    else:
        reject(lambda: result, Record({'name': 'SupplyStockError', 'items': ['vial of water']}))
    expect(f.visits).to_equal(['Aemad', 'Jatix', 'Sigmund The Merchant', 'Jiminua'])
    expect(f.bank.get('Vial of water')).to_be(2)
    expect(f.bank.get('Coins')).to_be(9996)
test_each([False, True])('exhausted vial sources are bounded and preserve partial purchases (optional=%s)', _fn158)

def _fn159(*_args, **_kwargs):
    f = vial_fixture(Record({'Sigmund The Merchant': 10}))
    _merged160 = {}
    for _k, _v in ((vial_plan()._fields if isinstance(vial_plan(), Record) else vial_plan())).items():
        _merged160[_k] = _v
    for _k, _v in {'needs': [Record({'item': 'Vial', 'count': 5})]}.items():
        _merged160[_k] = _v
    yield from provision(Record(_merged160), f.port)
    expect(f.visits).to_equal(['Jatix', 'Sigmund The Merchant'])
    expect(f.bank.get('Vial')).to_be(5)
    _v161 = f.bank.get('Vial of water')
    expect((_v161 if _v161 is not None else 0)).to_be(0)
    if False:
        yield
test('empty vial needs use alternate empty-vial shops without filling', _fn159)

def _fn164(operation, *_args, **_kwargs):
    f = vial_fixture(Record({'Jatix': 800}))
    calls = [0]
    if operation == 'walk':

        def _fn165(*_args, **_kwargs):
            calls[0] += 1
            return calls[0] > 1
            if False:
                yield
        f.port.walk = _fn165
    else:
        shop = f.port.shop

        def _fn166(keeper):
            calls[0] += 1
            return (False if calls[0] == 1 else run_wait(shop(keeper)))
            if False:
                yield
        f.port.shop = _fn166
    yield from provision(vial_plan(), f.port)
    expect(f.bank.get('Vial of water')).to_be(27)
test_each(['walk', 'shop'])('a failed vial supplier %s proceeds to the next source', _fn164)

def _fn167(*_args, **_kwargs):
    f = vial_fixture(Record({'Aemad': 500, 'Jatix': 800}))
    buy = f.port.buy
    f.port.buy = lambda name, count: (resolved_wait(None) if name == 'Vial of water' else buy(name, count))
    yield from provision(vial_plan(), f.port)
    expect(f.bank.get('Vial of water')).to_be(27)
    expect(f.visits).to_equal(['Aemad', 'Jatix'])
    if False:
        yield
test('a lying purchase result does not satisfy vial demand', _fn167)

def _fn168(*_args, **_kwargs):
    f = vial_fixture(Record({'Jatix': 800, 'Sigmund The Merchant': 10, 'Jiminua': 50}))
    fill = f.port.fill_vials

    def _fn169(*_args, **_kwargs):
        yield from fill(3)
        return False
    f.port.fill_vials = _fn169
    yield from provision(vial_plan(), f.port)
    expect(f.bank.get('Vial of water')).to_be(27)
    expect(f.bank.get('Vial')).to_be(24)
    expect(f.spent()).to_be(102)
test('partial filling counts only water vials before trying the next supplier', _fn168)

def _fn170(*_args, **_kwargs):
    f = vial_fixture(Record({}))
    f.bank['Vial'] = 54
    fill = f.port.fill_vials
    batches = []

    def _fn171(count):
        batches.append(count)
        expect(f.pack.get('Coins')).to_be(200)
        expect(f.pack.get('Shrimps')).to_be(3)
        expect(count + 4).to_be_less_than_or_equal(28)
        _result172 = run_wait(fill(count))
        return _result172
    f.port.fill_vials = lambda count: resolved_wait(_fn171(count))
    _merged173 = {}
    for _k, _v in ((vial_plan(54)._fields if isinstance(vial_plan(54), Record) else vial_plan(54))).items():
        _merged173[_k] = _v
    for _k, _v in {'food': 'Shrimps'}.items():
        _merged173[_k] = _v
    yield from provision(Record(_merged173), f.port)
    expect(batches).to_equal([24, 24, 6])
    expect(f.bank.get('Vial of water')).to_be(54)
    expect(f.bank.get('Shrimps')).to_be(30)
    expect(f.bank.get('Coins')).to_be(10000)
test('banked vial filling reserves pack space for travel money and food', _fn170)

def _fn174(*_args, **_kwargs):
    f = vial_fixture(Record({'Jatix': 800}))
    _merged175 = {}
    for _k, _v in ((vial_plan(14)._fields if isinstance(vial_plan(14), Record) else vial_plan(14))).items():
        _merged175[_k] = _v
    for _k, _v in {'needs': list(vial_plan(14).needs) + [Record({'item': 'Vial', 'count': 14})]}.items():
        _merged175[_k] = _v
    yield from provision(Record(_merged175), f.port)
    expect(f.bank.get('Vial of water')).to_be(14)
    expect(f.bank.get('Vial')).to_be(14)
    expect(f.spent()).to_be(56)
    if False:
        yield
test('purchasing both empty and water vials never fills the reserved empty supplies', _fn174)

def empty_wait():
    if False:
        yield

def reject(call, wanted):
    try:
        run_wait(call())
    except Exception as error:
        if isinstance(wanted, str):
            assert wanted in str(error), str(error)
        else:
            actual = Record({'name': type(error).__name__, 'items': getattr(error, 'items', None)})
            if isinstance(wanted, type):
                assert isinstance(error, wanted), str(error)
            else:
                expect(actual).to_match_object(wanted)
        return
    raise AssertionError('expected a supply failure')

def resolved_wait(value):
    if False:
        yield
    return value

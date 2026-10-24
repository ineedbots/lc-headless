"""rs2b0t's test/scripts/ShopRunner/shopRunnerRingLogic.test.ts and shopRunnerRoute.test.ts (MIT, see
thirdparty/rs2b0t), on spec.py's describe, test and expect. The shop database is shop_record here, and the Mage
Arena's setting is mage_arena."""

from rs2004.catalogs import Record, shop_db
from bots.shop_runner import ROUTE, SETTINGS, buyout_cost_from_baseline, cluster_eligible, cluster_sells_chosen
from bots.shop_runner import estimate_cluster_gp, item_def, next_cluster, shop_record, withdraw_for


def acct(levels):
    return Record({'qp': 0, 'quests': {}, 'skills': levels})


ALL = set()
for _key in shop_db():
    for _item in shop_db()[_key]['items']:
        ALL.add(_item['name'].lower())

BY_ID = {}
for _cluster in ROUTE.clusters:
    BY_ID[_cluster.id] = _cluster


def _fn1():
    def _fn2():
        expect(cluster_eligible(BY_ID['rangingguild'], acct({'ranged': 39}), {})).to_be(False)
        expect(cluster_eligible(BY_ID['rangingguild'], acct({'ranged': 40}), {})).to_be(True)
        expect(cluster_eligible(BY_ID['magicguild'], acct({'magic': 65}), {})).to_be(False)
        expect(cluster_eligible(BY_ID['magicguild'], acct({'magic': 66}), {})).to_be(True)
    test('skill gates skip under-levelled accounts', _fn2)

    def _fn3():
        expect(cluster_eligible(BY_ID['magearena'], acct({}), {})).to_be(False)
        expect(cluster_eligible(BY_ID['magearena'], acct({}), {'mage_arena': False})).to_be(False)
        expect(cluster_eligible(BY_ID['magearena'], acct({}), {'mage_arena': True})).to_be(True)
    test('the mageArena toggle gates its cluster', _fn3)


describe('clusterEligible', _fn1)


def _next_id(last, a, t, chosen):
    cluster = next_cluster(ROUTE, last, a, t, chosen, shop_record)
    return cluster.id if cluster is not None else None


def _fn4():
    def _fn5():
        a = acct({'fishing': 99, 'ranged': 99, 'magic': 99})
        t = {'mage_arena': True}
        expect(_next_id(None, a, t, ALL)).to_be('varrock')
        expect(_next_id('varrock', a, t, ALL)).to_be('portsarim')
        expect(_next_id('magearena', a, t, ALL)).to_be('varrock')
    test('advances the ring in order and wraps', _fn5)

    def _fn6():
        fresh = acct({'fishing': 1, 'ranged': 1, 'magic': 1})
        expect(_next_id('catherby', fresh, {}, ALL)).to_be('ardougne')
    test('skips ineligible clusters', _fn6)

    def _fn7():
        a = acct({'fishing': 99, 'ranged': 99, 'magic': 99})
        t = {'mage_arena': True}
        vials = set(['vial', 'vial of water'])
        expect(cluster_sells_chosen(BY_ID['magearena'], shop_record, vials)).to_be(False)
        expect(cluster_sells_chosen(BY_ID['taverley'], shop_record, vials)).to_be(True)
        expect(cluster_sells_chosen(BY_ID['ardougne'], shop_record, vials)).to_be(True)
        expect(_next_id(None, a, t, vials)).to_be('taverley')
        expect(_next_id('taverley', a, t, vials)).to_be('ardougne')
        expect(_next_id('ardougne', a, t, vials)).to_be('taverley')
        expect(_next_id('magicguild', a, t, vials)).to_be('taverley')
    test('skips Mage Arena (and every other stop) when only vials are selected (#743)', _fn7)


describe('nextCluster', _fn4)


def _fn8():
    def _fn9():
        expect(withdraw_for(1000, 25, 100000)).to_be(1250)
        expect(withdraw_for(90000, 25, 100000)).to_be(100000)
        expect(withdraw_for(0, 25, 100000)).to_be(0)
    test('withdrawFor applies buffer and cap', _fn9)

    def _fn10():
        rec = shop_record('runeshop')
        item = item_def(rec, 'deathrune')
        cost = buyout_cost_from_baseline(rec, 'deathrune')
        expect(cost).to_be_greater_than(0)
        expect(cost).to_be_greater_than_or_equal(item.baseline * ((max(100, rec.sell) * item.cost) // 1000))
    test('buyout cost rises as stock is drained (engine curve)', _fn10)

    def _fn11():
        varrock = ROUTE.clusters[0]
        all_ = estimate_cluster_gp(varrock, shop_record, ALL)
        none = estimate_cluster_gp(varrock, shop_record, set())
        death_only = estimate_cluster_gp(varrock, shop_record, set(['death rune']))
        expect(all_).to_be_greater_than(0)
        expect(none).to_be(0)
        expect(death_only).to_be_greater_than(0)
        expect(death_only).to_be_less_than(all_)
    test('estimateClusterGp respects the chosen filter', _fn11)


describe('gp math', _fn8)


def _fn12():
    def _fn13():
        for name in ['Vial', 'Vial of water', 'Eye of newt']:
            expect(SETTINGS['buy_items'].options).to_contain(name)
            expect(SETTINGS['buy_items'].default).to_contain(name)
    test('ShopRunner exposes both requested Herblore supplies', _fn13)

    def _fn14():
        expect(ROUTE.ring).to_equal([c.id for c in ROUTE.clusters])
        for cluster in ROUTE.clusters:
            for shop in cluster.shops:
                rec = shop_record(shop.shop_id)
                expect(rec, shop.shop_id).to_be_defined()
                expect(rec.keepers).to_contain(shop.keeper_npc)
                expect(rec.scope).to_be('shared')
                for buy in shop.buys:
                    item = item_def(rec, buy.obj)
                    expect(item, buy.obj).to_be_defined()
                    if not item.stackable:
                        expect(cluster.repeat_while_full).to_be(True)
                    expect(item.baseline).to_be_greater_than(0)
        expect([c.id for c in ROUTE.clusters]).to_equal(['varrock', 'portsarim', 'taverley', 'catherby', 'fishingguild', 'rangingguild', 'ardougne', 'magicguild', 'magearena'])
    test('live route resolves entirely against SHOP_DB', _fn14)

    def _fn15():
        for id in ['varrock', 'portsarim', 'taverley', 'catherby', 'ardougne', 'magearena']:
            expect(BY_ID[id].gates).to_equal([])
        expect(BY_ID['fishingguild'].gates).to_equal([Record({'skill': Record({'name': 'fishing', 'level': 68})})])
        expect(BY_ID['rangingguild'].gates).to_equal([Record({'skill': Record({'name': 'ranged', 'level': 40})})])
        expect(BY_ID['magicguild'].gates).to_equal([Record({'skill': Record({'name': 'magic', 'level': 66})})])
    test('skill gates sit on the guild clusters', _fn15)

    def _fn16():
        ma = BY_ID['magearena']
        expect(ma.setting).to_be('mage_arena')
        expect(ma.keep).to_equal(['Knife'])
        expect(ma.wield).to_be_undefined()
        expect(ma.keep_fallback.item).to_be('Knife')
        expect(ma.keep_fallback.spawn).to_equal(Tile(3218, 3418, 1))
        expect(ma.haul_bank.stand).to_equal(Tile(2533, 4714, 0))
        expect(ma.haul_bank.banker).to_be('Gundai')
        expect(len(ma.waypoints)).to_be_greater_than(0)
        expect(ma.bank.banker).to_be_undefined()
    test('the Mage Arena cluster carries the knife-only wilderness protocol', _fn16)

    def _fn17():
        taverley = BY_ID['taverley']
        expect(taverley.repeat_while_full).to_be(True)
        expect(taverley.bank.stand).to_equal(Tile(2946, 3369, 0))
        expect(len(taverley.shops)).to_be(1)
        expect(taverley.shops[0].shop_id).to_be('herbloreshop')
        expect(taverley.shops[0].keeper_npc).to_be('Jatix')
        expect([b.obj for b in taverley.shops[0].buys]).to_equal(['eye_of_newt', 'vial_empty'])
    test('Taverley repeats Jatix trips for both non-stackable Herblore supplies', _fn17)

    def _fn18():
        ardougne = BY_ID['ardougne']
        expect(ardougne.repeat_while_full).to_be(True)
        expect(ardougne.bank.stand).to_equal(Tile(2655, 3283, 0))
        expect(ardougne.shops[0].keeper_npc).to_be('Aemad')
        expect([b.obj for b in ardougne.shops[0].buys]).to_equal(['vial_water'])
    test('Ardougne buys filled vials from Aemad and banks at East Ardougne', _fn18)

    def _fn19():
        expect('route' in SETTINGS).to_be(False)
    test('ShopRunner has no smoke-varrock route setting', _fn19)


describe('route data integrity vs generated shopdb', _fn12)


def _fn20():
    # Why: the planner spends the gp cap greedily in buys order, so a cheap-first list starves the valuable tail.
    def _fn21():
        for cluster in ROUTE.clusters:
            for shop in cluster.shops:
                rec = shop_record(shop.shop_id)
                costs = [item_def(rec, b.obj).cost for b in shop.buys]
                expect([shop.shop_id, costs]).to_equal([shop.shop_id, sorted(costs, reverse=True)])
    test('every shop lists its buys in descending item cost', _fn21)


describe('buys[] priority order', _fn20)

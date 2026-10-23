"""rs2b0t's test/api/bank/bank-locations.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

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


def set_setting(on):
    # Here the Global settings come from the account file, as settings_store.load gives them.
    settings_store.load({} if on is None else {'Global': {'use_mage_bank': on}})


after_each(lambda: set_setting(None))


def _fn1():
    names = [b.name for b in BANK_LOCATIONS]
    expect(len(set(names))).to_be(len(names))


test('bank names are unique', _fn1)


def _fn2():
    for b in BANK_LOCATIONS:
        expect(b.tile.level, b.name).to_be_greater_than_or_equal(0)
        expect(b.tile.level, b.name).to_be_less_than_or_equal(3)
        expect(b.tile.x, b.name).to_be_greater_than(2300)
        expect(b.tile.x, b.name).to_be_less_than(3600)
        expect(b.tile.z, b.name).to_be_greater_than(2900)
        # Why: the Mage Arena chamber is its own region above the surface map (^mage_arena_finish_coord z=4716), so the band is asserted on the walked-to tile.
        expect(b.tile.z, b.name).to_be_less_than((9600 if b.name == 'Zanaris' else 4800))


test('every bank centre is a plausible world tile', _fn2)


def _fn3():
    for b in BANK_LOCATIONS:
        a = approach_of(b)
        expect(a.x, b.name).to_be_greater_than(2300)
        expect(a.x, b.name).to_be_less_than(3600)
        expect(a.z, b.name).to_be_greater_than(2900)
        expect(a.z, b.name).to_be_less_than((9600 if b.name == 'Zanaris' else 4000))


test('every bank is approached from somewhere on the surface map', _fn3)


def _fn4():
    gt = ([b for b in BANK_LOCATIONS if b.name == 'Grand Tree'] or [None])[0]
    # Field-wise, like the Yanille case below: a Tile carries methods an object literal
    # does not, so toEqual against a bare literal does not typecheck.
    expect((gt.tile if gt is not None else None).x).to_be(2449)
    expect((gt.tile if gt is not None else None).z).to_be(3482)
    expect((gt.tile if gt is not None else None).level).to_be(1)
    expect((gt.requires if gt is not None else None)).to_be_undefined()


test('Grand Tree bank is 1F at booths (no quest gate)', _fn4)


def _fn5():
    yanille = ([b for b in BANK_LOCATIONS if b.name == 'Yanille'] or [None])[0]
    expect((yanille.tile if yanille is not None else None).x).to_be(2612)
    expect((yanille.tile if yanille is not None else None).z).to_be(3092)


test('Yanille bank centre matches its bank_zones midpoint', _fn5)


def _fn6():
    duel_arena = ([b for b in BANK_LOCATIONS if b.name == 'Duel Arena'] or [None])[0]
    expect((duel_arena.access if duel_arena is not None else None)).to_equal(Record({'name': 'Open chest', 'op': 'Bank', 'open_first': Record({'name': 'Closed chest', 'op': 'Open'})}))


test('Duel Arena opens its chest before using the bank action', _fn6)


def _fn7():
    shantay = ([b for b in BANK_LOCATIONS if b.name == 'Shantay Pass'] or [None])[0]
    expect((shantay.tile if shantay is not None else None).x).to_be(3308)
    expect((shantay.tile if shantay is not None else None).z).to_be(3120)
    expect((shantay.access if shantay is not None else None)).to_equal(Record({'name': 'Shantay chest', 'op': 'Open'}))
    expect(sorted([bank.name for bank in [bank for bank in BANK_LOCATIONS if bank.access]])).to_equal(['Duel Arena', 'Shantay Pass'])


test('Shantay Pass banks via the Shantay chest (Open then continue chat)', _fn7)


def _fn8():
    expect((nearest_bank(Record({'x': 2605, 'z': 3085, 'level': 0})).name if nearest_bank(Record({'x': 2605, 'z': 3085, 'level': 0})) is not None else None)).to_be('Yanille')
    expect((nearest_bank(Record({'x': 3270, 'z': 3168, 'level': 0})).name if nearest_bank(Record({'x': 3270, 'z': 3168, 'level': 0})) is not None else None)).to_be('Al Kharid')
    expect((nearest_bank(Record({'x': 3090, 'z': 3245, 'level': 0})).name if nearest_bank(Record({'x': 3090, 'z': 3245, 'level': 0})) is not None else None)).to_be('Draynor')


test('nearestBank returns the closest bank on the same level', _fn8)


def _fn9():
    # Chebyshev wrongly picks Falador East; Euclidean walk is shorter to Edgeville.
    expect((nearest_bank(Record({'x': 3080, 'z': 3420, 'level': 0})).name if nearest_bank(Record({'x': 3080, 'z': 3420, 'level': 0})) is not None else None)).to_be('Edgeville')
    expect((nearest_bank(Record({'x': 3078, 'z': 3415, 'level': 0})).name if nearest_bank(Record({'x': 3078, 'z': 3415, 'level': 0})) is not None else None)).to_be('Edgeville')


test('Barbarian Village tin/coal banks at Edgeville (not Falador East)', _fn9)


def _fn10():
    expect((nearest_bank(Record({'x': 2449, 'z': 3482, 'level': 1})).name if nearest_bank(Record({'x': 2449, 'z': 3482, 'level': 1})) is not None else None)).to_be('Grand Tree')


test('nearestBank on Grand Tree 1F picks Grand Tree (ungated)', _fn10)


def _fn11():
    expect((nearest_bank(Record({'x': 2460, 'z': 3490, 'level': 0})).name if nearest_bank(Record({'x': 2460, 'z': 3490, 'level': 0})) is not None else None)).to_be('Grand Tree')


test('Grand Tree still wins from the ground floor beneath it', _fn11)


def _fn12():
    # Why: the Grand Tree is the only bank off level 0, so filtering by plane made it the sole candidate for anyone upstairs. Stairs are in the nav graph; rank on x/z.
    def _fn13():
        expect((nearest_bank(Record({'x': 3250, 'z': 3420, 'level': 1})).name if nearest_bank(Record({'x': 3250, 'z': 3420, 'level': 1})) is not None else None)).to_be('Varrock East')
    test('Varrock East 1F banks downstairs, not at the Grand Tree', _fn13)

    def _fn14():
        expect((nearest_bank(Record({'x': 3301, 'z': 3169, 'level': 1})).name if nearest_bank(Record({'x': 3301, 'z': 3169, 'level': 1})) is not None else None)).to_be('Al Kharid')
    test('Al Kharid palace 1F banks at Al Kharid', _fn14)

    def _fn15():
        expect((nearest_bank(Record({'x': 2971, 'z': 3386, 'level': 1})).name if nearest_bank(Record({'x': 2971, 'z': 3386, 'level': 1})) is not None else None)).to_be('Falador West')
    test('Falador 1F banks at Falador West', _fn15)

    def _fn16():
        expect((nearest_bank(Record({'x': 2748, 'z': 3495, 'level': 2})).name if nearest_bank(Record({'x': 2748, 'z': 3495, 'level': 2})) is not None else None)).to_be('Seers')
        expect((nearest_bank(Record({'x': 2612, 'z': 3092, 'level': 2})).name if nearest_bank(Record({'x': 2612, 'z': 3092, 'level': 2})) is not None else None)).to_be('Yanille')
    test('level 2 finds a bank rather than giving up', _fn16)


describe('upstairs banks at the nearest bank, not the only bank off level 0', _fn12)


def open_only(bank):
    return bank.requires is None


def all_(_bank):
    return True


def _fn17():
    def _fn18():
        guild = ([b for b in BANK_LOCATIONS if b.name == 'Fishing Guild'] or [None])[0]
        expect((guild.requires.skill if guild.requires is not None else None)).to_equal(Record({'name': 'fishing', 'level': 68}))
    test('Fishing Guild carries the Fishing 68 gate', _fn18)

    def _fn19():
        shilo = ([b for b in BANK_LOCATIONS if b.name == 'Shilo Village'] or [None])[0]
        expect((shilo.requires.quest if shilo.requires is not None else None)).to_be('Shilo Village')
    test('Shilo Village carries its quest gate', _fn19)

    def _fn20():
        canifis = ([b for b in BANK_LOCATIONS if b.name == 'Canifis'] or [None])[0]
        expect((canifis.requires.quest if canifis.requires is not None else None)).to_be('Priest in Peril')
    test('Canifis carries its Priest in Peril gate', _fn20)

    def _fn21():
        gt = ([b for b in BANK_LOCATIONS if b.name == 'Grand Tree'] or [None])[0]
        expect(gt.requires).to_be_undefined()
    test('Grand Tree bank is ungated (mine still needs the quest)', _fn21)

    def _fn22():
        gated = sorted([b.name for b in [b for b in BANK_LOCATIONS if b.requires is not None]])
        expect(gated).to_equal(['Canifis', 'Fishing Guild', 'Legends Guild', 'Mage Arena', 'Shilo Village', 'Zanaris'])
    test('every other bank is ungated', _fn22)


describe('bank entry gates', _fn17)


def _fn23():
    def _fn24():
        picked = nearest_usable_bank(Record({'x': 2600, 'z': 3420, 'level': 0}), open_only)
        expect((picked.name if picked is not None else None)).to_be('Ardougne West')
    test('near Hemenster, a gated-out character routes past the Fishing Guild to Ardougne West', _fn24)

    def _fn25():
        picked = nearest_usable_bank(Record({'x': 2600, 'z': 3420, 'level': 0}), all_)
        expect((picked.name if picked is not None else None)).to_be('Fishing Guild')
    test('near Hemenster, a 68+ fisher still gets the Fishing Guild', _fn25)

    def _fn26():
        picked = nearest_usable_bank(Record({'x': 2850, 'z': 2950, 'level': 0}), open_only)
        expect((picked.name if picked is not None else None)).to_be('Yanille')
    test('near Shilo without the quest, routes to Yanille instead', _fn26)

    def _fn27():
        picked = nearest_usable_bank(Record({'x': 3510, 'z': 3481, 'level': 0}), all_)
        expect((picked.name if picked is not None else None)).to_be('Canifis')
    test('in Canifis, a Priest-in-Peril character banks at Canifis', _fn27)

    def _fn28():
        expect((nearest_usable_bank(Record({'x': 2600, 'z': 3420, 'level': 2}), all_).name if nearest_usable_bank(Record({'x': 2600, 'z': 3420, 'level': 2}), all_) is not None else None)).to_be('Fishing Guild')
        expect((nearest_usable_bank(Record({'x': 2600, 'z': 3420, 'level': 2}), open_only).name if nearest_usable_bank(Record({'x': 2600, 'z': 3420, 'level': 2}), open_only) is not None else None)).to_be('Ardougne West')
    test('an upstairs caller still gets its nearest bank', _fn28)

    def _fn29():
        expect((nearest_usable_bank(Record({'x': 2449, 'z': 3482, 'level': 1}), open_only).name if nearest_usable_bank(Record({'x': 2449, 'z': 3482, 'level': 1}), open_only) is not None else None)).to_be('Grand Tree')
        expect((nearest_usable_bank(Record({'x': 2449, 'z': 3482, 'level': 1}), all_).name if nearest_usable_bank(Record({'x': 2449, 'z': 3482, 'level': 1}), all_) is not None else None)).to_be('Grand Tree')
    test('on Grand Tree 1F, banks at Grand Tree without a quest gate', _fn29)


describe('nearestUsableBank', _fn23)


def _fn30():
    def _fn31():
        # Why: from the Lumbridge respawn the three nearest banks by air sit behind the 10gp toll gate a dead bot cannot pay, so callers must probe this shortlist for path costs.
        order = [b.name for b in nearest_banks(Record({'x': 3222, 'z': 3218, 'level': 0}))]
        expect(order[0:4]).to_equal(['Al Kharid', 'Shantay Pass', 'Draynor', 'Duel Arena'])
    test('is a shortlist in straight-line order, not an answer', _fn31)

    def _fn32():
        for from_ in [
        Record({'x': 3013, 'z': 3355, 'level': 0}),
        Record({'x': 2660, 'z': 3300, 'level': 0}),
        Record({'x': 3222, 'z': 3218, 'level': 0}),
    ]:
            list_ = nearest_banks(from_)
            _v33 = (list_[0].name if list_[0] is not None else None)
            _v34 = (nearest_bank(from_).name if nearest_bank(from_) is not None else None)
            expect((_v33 if _v33 is not None else '')).to_be((_v34 if _v34 is not None else ''))
            for i in range(1, len(list_)):
                expect(bank_distance(from_, list_[i - 1].tile)).to_be_less_than_or_equal(bank_distance(from_, list_[i].tile))
    test('agrees with nearestBank on the head, and covers the same banks', _fn32)

    def _fn35():
        upstairs = [b.name for b in nearest_banks(Record({'x': 2449, 'z': 3482, 'level': 1}))]
        expect(upstairs[0]).to_be('Grand Tree')
        expect(upstairs).to_contain('Ardougne West')
        expect(len(upstairs)).to_be_greater_than(1)
    test('shortlists banks on another plane too', _fn35)


describe('nearestBanks', _fn30)


# Here the navigator's find_path plans at once, taking max_expansions and a policy, so the fakes are plain functions.
class FakeNavigator:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0
        self.policies = []

    def find_path(self, start, dest, max_expansions=None, policy=None):
        self.calls += 1
        self.policies.append(policy)
        return self.outcome


def _fn36():
    def _fn37():
        navigator = FakeNavigator(Record({'ok': False, 'reason': 'should never be reached standing at the bank'}))
        picked = nearest_bank_reachable(Record({'x': 3185, 'z': 3440, 'level': 0}), navigator)
        expect((picked.name if picked is not None else None)).to_be('Varrock West')
        expect(navigator.calls).to_be(0)
    test('standing at a booth returns that bank without a single worker search', _fn37)

    def _fn39():
        navigator = FakeNavigator(Record({'ok': False, 'reason': 'should never be reached'}))
        picked = nearest_bank_reachable(Record({'x': 3188, 'z': 3442, 'level': 0}), navigator)
        expect((picked.name if picked is not None else None)).to_be('Varrock West')
        expect(navigator.calls).to_be(0)
    test('within 4 tiles of a booth also short-circuits', _fn39)

    def _fn41():
        # 5 tiles out from the Varrock West stand: the fast-path radius must not fire, and the
        # walk-cost pick must be attempted rather than silently returning the air-nearest.
        navigator = FakeNavigator(Record({'ok': True, 'cost': 1000}))
        picked = nearest_bank_reachable(Record({'x': 3180, 'z': 3440, 'level': 0}), navigator)
        expect(picked).not_.to_be_null()
        # every candidate costs the same, so "navigating" means the batch ran over the shortlist
        expect(navigator.calls).to_be_greater_than(1)
    test('a bank in reach but far by air still navigates', _fn41)

    def _fn43():
        # Shilo Village's gate is the quest; the stand is right there but the account could not use
        # it, so nearestBank must not short-circuit onto it.
        navigator = FakeNavigator(Record({'ok': True, 'cost': 999999}))
        picked = nearest_bank_reachable(Record({'x': 2852, 'z': 2954, 'level': 0}), navigator)
        expect((picked.name if picked is not None else None)).not_.to_be('Shilo Village')
        expect(navigator.calls).to_be_greater_than(0)
    test('a gated booth within 4 tiles still navigates (fast-path respects the gate)', _fn43)


describe('nearestBankReachable near-bank fast-path', _fn36)


# --- nav-cost edit to nearest bank (dungeon offset) ---
def _fn46():
    navigator = FakeNavigator(Record({'ok': True, 'cost': 42}))
    cost = bank_cost_for_navigator(navigator)
    expect(cost(Tile(0, 0, 0), Tile(1, 1, 0))).to_be(42)
    # Off by catalog: the route is planned without teleports.
    expect(navigator.policies[0].get('use_teleports')).to_be(False)
    expect(bank_cost_for_navigator(FakeNavigator(Record({'ok': False, 'reason': 'blocked'})))(Tile(0, 0, 0), Tile(1, 1, 0))).to_be_null()


test('bankCostForNavigator maps navigator outcomes to a cost, off by catalog', _fn46)


# 'nearestWalkableBank picks the walkable-nearest bank' runs rs2b0t's own nav pack; tests/Script's real-cache tests
# walk this client's.


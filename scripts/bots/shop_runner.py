# Runs a ring of shop clusters, banking for each and buying out what's selected at its shops, then moving on:
# rs2b0t's ShopRunner (MIT, see thirdparty/rs2b0t). Clusters gated on a skill or a setting are skipped when the
# account doesn't meet them, and one that runs the pack full with stock left goes round again.

import time

from rs2004.catalogs import AcquireTask, ContinueDialog, ItemNeed, Record, buyout_plan, shop_db, unit_price
from rs2004.quests.exec.primitives import talk_through

COOLDOWN_MS = 10 * 60000
STATE_NAMESPACE = 'ShopRunner'
STATE_KEY = 'last_cluster_id'


# ShopRunnerRoute.ts

BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
RUNES = ['deathrune', 'chaosrune', 'firerune', 'waterrune', 'airrune', 'earthrune', 'mindrune', 'bodyrune']


def _shop(shop_id, keeper_npc, stand, buys):
    return Record({'shop_id': shop_id, 'keeper_npc': keeper_npc, 'stand': stand, 'buys': [Record({'obj': obj}) for obj in buys]})


def _cluster(id, bank_stand, shops, gates=None, repeat_while_full=False, keep=None, keep_fallback=None, waypoints=None, setting=None, haul_bank=None):
    return Record({
        'id': id,
        'bank': Record({'stand': bank_stand, 'booth_name': BOOTH_NAME, 'booth_op': BOOTH_OP}),
        'shops': shops,
        'gates': gates if gates is not None else [],
        'repeat_while_full': repeat_while_full,
        'keep': keep,
        'keep_fallback': keep_fallback,
        'waypoints': waypoints,
        'setting': setting,
        'haul_bank': haul_bank,
    })


def _skill_gate(name, level):
    return Record({'skill': Record({'name': name, 'level': level})})


ROUTE = Record({
    'clusters': [
        _cluster('varrock', Tile(3251, 3420, 0), [
            _shop('runeshop', 'Aubury', Tile(3253, 3401, 0), RUNES),
            _shop('archeryshop', 'Lowe', Tile(3231, 3421, 0), ['steel_arrow', 'iron_arrow', 'bronze_arrow']),
        ]),
        _cluster('portsarim', Tile(3092, 3243, 0), [
            _shop('magicshop', 'Betty', Tile(3012, 3258, 0), RUNES),
            _shop('fishingshop', 'Gerrant', Tile(3013, 3224, 0), ['feather']),
        ]),
        _cluster('taverley', Tile(2946, 3369, 0), [
            _shop('herbloreshop', 'Jatix', Tile(2899, 3427, 0), ['eye_of_newt', 'vial_empty']),
        ], repeat_while_full=True),
        _cluster('catherby', Tile(2809, 3441, 0), [
            _shop('archeryshop2', 'Hickton', Tile(2821, 3442, 0), ['rune_arrowheads', 'adamant_arrowheads', 'mithril_arrowheads', 'steel_arrowheads', 'iron_arrow', 'iron_arrowheads', 'bronze_arrow', 'bronze_arrowheads']),
        ]),
        _cluster('fishingguild', Tile(2586, 3420, 0), [
            _shop('fishingguild', 'Roachey', Tile(2596, 3399, 0), ['feather']),
        ], gates=[_skill_gate('fishing', 68)]),
        _cluster('rangingguild', Tile(2725, 3493, 0), [
            _shop('ranging_guild_bowshop', 'Bow and Arrow salesman', Tile(2673, 3434, 0), [
                'rune_arrow', 'rune_arrowheads', 'adamant_arrow', 'adamant_arrowheads', 'mithril_arrow', 'mithril_arrowheads',
                'steel_arrow', 'steel_arrowheads', 'iron_arrow', 'iron_arrowheads', 'bronze_arrow', 'bronze_arrowheads']),
        ], gates=[_skill_gate('ranged', 40)]),
        _cluster('ardougne', Tile(2655, 3283, 0), [
            _shop('adventurershop', 'Aemad', Tile(2613, 3294, 0), ['vial_water']),
        ], repeat_while_full=True),
        _cluster('magicguild', Tile(2612, 3092, 0), [
            _shop('magicguildshop', 'Magic Store owner', Tile(2594, 3087, 1), ['soulrune', 'firerune', 'waterrune', 'airrune', 'earthrune', 'mindrune', 'bodyrune']),
        ], gates=[_skill_gate('magic', 66)]),
        _cluster('magearena', Tile(3094, 3493, 0), [
            _shop('magearena_runeshop', 'Lundail', Tile(2535, 4719, 0), [
                'lawrune', 'deathrune', 'naturerune', 'chaosrune', 'cosmicrune', 'firerune', 'waterrune', 'airrune', 'earthrune', 'mindrune', 'bodyrune']),
        ], keep=['Knife'],
            # The free kitchen spawn upstairs in Varrock's Blue Moon Inn.
            keep_fallback=Record({'item': 'Knife', 'spawn': Tile(3218, 3418, 1)}),
            waypoints=[Tile(3092, 3760, 0), Tile(3092, 3900, 0)], setting='mage_arena',
            haul_bank=Record({'stand': Tile(2533, 4714, 0), 'banker': 'Gundai'})),
    ],
    'ring': ['varrock', 'portsarim', 'taverley', 'catherby', 'fishingguild', 'rangingguild', 'ardougne', 'magicguild', 'magearena'],
})


_records = {}


def shop_record(shop_id):
    """The shop database's record by its inventory name, as a Record whose items are Records, or None."""
    if shop_id not in _records:
        shop = shop_db().get(shop_id)
        if shop is None:
            _records[shop_id] = None
        else:
            fields = {}
            for field in shop:
                fields[field] = shop[field]
            fields['items'] = [Record(item) for item in shop['items']]
            _records[shop_id] = Record(fields)
    return _records[shop_id]


def item_def(rec, obj):
    for item in rec.items:
        if item.obj == obj:
            return item
    return None


# ShopRunnerRingLogic.ts


def buyout_cost_from_baseline(rec, obj):
    """What the shop's whole baseline stock of the obj costs, one at a time."""
    item = item_def(rec, obj)
    if item is None:
        return 0
    cost = 0
    for stock in range(item.baseline, 0, -1):
        cost += unit_price(item, rec, stock)
    return cost


def _record_in(db, shop_id):
    """A shop's record from db, which is shop_record or a dict of Records, as rs2b0t's tests pass SHOP_DB."""
    return db.get(shop_id) if isinstance(db, dict) else db(shop_id)


def _chosen_buys(cluster, db, chosen):
    """(shop record, obj) for each of the cluster's buys whose item is chosen."""
    out = []
    for shop in cluster.shops:
        rec = _record_in(db, shop.shop_id)
        if rec is None:
            continue
        for buy in shop.buys:
            item = item_def(rec, buy.obj)
            if item is not None and item.name.lower() in chosen:
                out.append((rec, buy.obj))
    return out


def estimate_cluster_gp(cluster, db, chosen):
    """The gp to buy out every chosen item at the cluster's shops. db is shop_record, or a dict of records."""
    return sum([buyout_cost_from_baseline(rec, obj) for rec, obj in _chosen_buys(cluster, db, chosen)])


def withdraw_for(estimate, buffer_pct, max_gp_per_leg):
    return min(max_gp_per_leg, int(-((-estimate * (100 + buffer_pct)) // 100)))


def cluster_eligible(cluster, acct, toggles):
    """The account meets the cluster's gates, and its setting, if any, is on. acct has qp, quests ({name:
    complete}) and skills ({name: level})."""
    if cluster.setting is not None and toggles.get(cluster.setting) is not True:
        return False
    for gate in cluster.gates:
        if gate.qp is not None and acct.qp < gate.qp:
            return False
        if gate.quest is not None and acct.quests.get(gate.quest) is not True:
            return False
        if gate.skill is not None and acct.skills.get(gate.skill.name, 1) < gate.skill.level:
            return False
    return True


def cluster_sells_chosen(cluster, db, chosen):
    """Why: Mage Arena, and every other stop, was still walked when the selection was only vials."""
    return len(_chosen_buys(cluster, db, chosen)) > 0


def next_cluster(route, last_id, acct, toggles, chosen, db):
    """The next cluster round the ring after last_id that the account can use and that sells something chosen."""
    ids = route.ring
    start = 0 if last_id is None or last_id not in ids else (ids.index(last_id) + 1) % len(ids)
    for i in range(len(ids)):
        wanted = ids[(start + i) % len(ids)]
        for cluster in route.clusters:
            if cluster.id == wanted and cluster_eligible(cluster, acct, toggles) and cluster_sells_chosen(cluster, db, chosen):
                return cluster
    return None


def _buyable_names():
    names = set()
    for cluster in ROUTE.clusters:
        for shop in cluster.shops:
            rec = shop_record(shop.shop_id)
            if rec is None:
                continue
            for buy in shop.buys:
                item = item_def(rec, buy.obj)
                if item is not None:
                    names.add(item.name)
    return sorted(list(names))


BUYABLE_NAMES = _buyable_names()

SETTINGS = {
    'buy_items': SettingDef('string[]', BUYABLE_NAMES, 'Items to buy', options=BUYABLE_NAMES, help='multi-select — shops with none of the selected items are skipped'),
    'gp_buffer_pct': SettingDef('number', 25, 'Gp buffer %', min=0, max=100, help='withdraw the cluster buyout estimate plus this margin'),
    'max_gp_per_leg': SettingDef('number', 100000, 'Max gp per withdrawal', min=1000),
    'stop_floor_gp': SettingDef('number', 5000, 'Stop below bank gp', min=0, help='clean stop when the bank runs dry'),
    'mage_arena': SettingDef('boolean', True, 'Mage Arena leg', help='the deep-wilderness Lundail buyout (knife-only protocol)'),
}


def now_ms():
    return time.time() * 1000


class ShopRunner(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.route = ROUTE
        self.started_at = time.time()
        self.status = 'starting'
        self.session_haul = {}
        self.session_spent = 0
        self.repeat_cluster_id = None
        self.cooldowns = {}
        self.open_fails = {}
        self.gp_buffer_pct = self.settings.num('gp_buffer_pct', 25)
        self.max_gp_per_leg = self.settings.num('max_gp_per_leg', 100000)
        self.stop_floor_gp = self.settings.num('stop_floor_gp', 5000)
        self.toggles = {'mage_arena': self.settings.bool('mage_arena', True)}
        self.chosen = set([s.lower() for s in self.settings.list('buy_items', BUYABLE_NAMES)])
        if len(self.chosen) == 0:
            self.request_finish('[shoprun] no buy items selected')
            return
        acct = self.account_view()
        if len([c for c in self.route.clusters if cluster_eligible(c, acct, self.toggles) and cluster_sells_chosen(c, shop_record, self.chosen)]) == 0:
            self.request_finish('[shoprun] no eligible cluster sells the selected items')
            return
        # rs2b0t keeps where the ring stopped in the browser's storage; here it's the account file's.
        self.last_cluster_id = settings_store.saved(STATE_NAMESPACE, STATE_KEY)
        self.add(ContinueDialog(), RunCluster(self))

    def account_view(self):
        quest_done = {}
        levels = {}
        for cluster in self.route.clusters:
            for gate in cluster.gates:
                if gate.quest is not None:
                    quest_done[gate.quest] = quests.status(gate.quest) == 'complete'
                if gate.skill is not None:
                    levels[gate.skill.name] = skills.level(gate.skill.name)
        return Record({'qp': quests.points(), 'quests': quest_done, 'skills': levels})

    def save_state(self):
        settings_store.save(STATE_NAMESPACE, STATE_KEY, self.last_cluster_id)

    def on_progress_report(self):
        minutes = int((time.time() - self.started_at) / 60)
        haul = ', '.join([f'{k} +{self.session_haul[k]}' for k in self.session_haul]) or 'no haul yet'
        return {'Status': self.status, 'Runtime': f'{minutes}m', 'Gp held': inventory.count('Coins'), 'Spent': self.session_spent,
                'Last stop': self.last_cluster_id or '—', 'Haul': haul}


def walk_near(bot, dest, radius=2):
    """Use with yield from."""
    here = game.tile()
    if here is not None and here.level == dest.level and max(abs(here.x - dest.x), abs(here.z - dest.z)) <= radius:
        return True
    arrived = yield from traversal.walk_resilient(dest, radius=radius, attempts=6, timeout_ms=240000, log=lambda m: bot.log(f'  {m}'))
    return arrived


def open_npc_bank(bot, banker):
    """Use with yield from."""
    if bank.is_open():
        return True
    yield from talk_through(banker, ['access my bank'], lambda m: bot.log(f'  {m}'))
    opened = yield from execution.delay_until(lambda: bank.is_open(), 4000)
    return opened


def _not_kept(keep):
    return lambda name, id: len(name) > 0 and name.lower() not in keep


class RunCluster(Task):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        return True

    def find_cluster(self, id):
        for cluster in self.bot.route.clusters:
            if cluster.id == id:
                return cluster
        return None

    def execute(self):
        bot = self.bot
        if bot.repeat_cluster_id is None:
            cluster = next_cluster(bot.route, bot.last_cluster_id, bot.account_view(), bot.toggles, bot.chosen, shop_record)
        else:
            cluster = self.find_cluster(bot.repeat_cluster_id)
        if cluster is None:
            bot.request_finish('[shoprun] no eligible cluster on the ring')
            return

        bot.status = f'banking for {cluster.id}'
        arrived = yield from walk_near(bot, cluster.bank.stand)
        if not arrived:
            return
        opened = yield from bank.open_nearest(cluster.bank.booth_name, cluster.bank.booth_op)
        if not opened:
            bot.log('[shoprun] bank open failed — will retry')
            return
        keep_list = cluster.keep if cluster.keep is not None else []
        keep = set([s.lower() for s in keep_list])
        yield from bank.deposit_all_matching(_not_kept(keep))

        for item in keep_list:
            if inventory.contains(item) or equipment.contains(item):
                continue
            took = yield from bank.withdraw_x(item, 1)
            if took:
                continue
            fallback = cluster.keep_fallback
            if fallback is not None and fallback.item.lower() == item.lower():
                bot.log(f'[shoprun] bank has no {item} — fetching the free {item} spawn')
                yield from bank.close()
                bot.status = f'fetching a {item}'
                yield from AcquireTask(bot, [ItemNeed(fallback.item, 1, ('ground', fallback.spawn))]).execute()
                if inventory.contains(item):
                    bot.log(f'[shoprun] picked up the {item} — heading back to the bank')
                # The cluster runs again from the top, banking with the item in hand.
                return
            bot.log(f'[shoprun] {cluster.id} needs a {item} and the bank has none — skipping the cluster')
            bot.last_cluster_id = cluster.id
            bot.save_state()
            return

        bank_gp = bank.count('Coins')
        if bank_gp < bot.stop_floor_gp:
            bot.request_finish(f'[shoprun] out of operating gp (bank {bank_gp} < floor {bot.stop_floor_gp})')
            return
        estimate = estimate_cluster_gp(cluster, shop_record, bot.chosen)
        want = withdraw_for(estimate, bot.gp_buffer_pct, bot.max_gp_per_leg)
        held = inventory.count('Coins')
        if held < want:
            take = min(want - held, bank_gp)
            if take > 0:
                took = yield from bank.withdraw_x('Coins', take)
                if not took:
                    bot.log('[shoprun] coin withdrawal failed — will retry')
                    return
            bot.log(f'[shoprun] {cluster.id}: withdrew {take}gp (estimate {estimate} +{bot.gp_buffer_pct}%, cap {bot.max_gp_per_leg})')

        for waypoint in cluster.waypoints or []:
            bot.status = f'walking the {cluster.id} route'
            arrived = yield from walk_near(bot, waypoint, 4)
            if not arrived or event_signal.pending():
                return

        now = now_ms()
        repeat_while_full = False
        for shop_stop in cluster.shops:
            if event_signal.pending():
                return
            if bot.cooldowns.get(shop_stop.shop_id, 0) > now:
                continue
            rec = shop_record(shop_stop.shop_id)
            if rec is None:
                continue
            route_objs = set([b.obj for b in shop_stop.buys])
            wanted = [obj for obj in route_objs if item_def(rec, obj) is not None and item_def(rec, obj).name.lower() in bot.chosen]
            if len(wanted) == 0:
                continue
            bot.status = f'buying at {shop_stop.shop_id}'
            arrived = yield from walk_near(bot, shop_stop.stand)
            if not arrived:
                return
            opened = yield from shop.open(shop_stop.keeper_npc)
            if not opened:
                fails = bot.open_fails.get(shop_stop.shop_id, 0) + 1
                bot.open_fails[shop_stop.shop_id] = fails
                if fails >= 3:
                    bot.cooldowns[shop_stop.shop_id] = now_ms() + COOLDOWN_MS
                    bot.open_fails[shop_stop.shop_id] = 0
                    bot.log(f'[shoprun] shop-open failed 3x — cooling {shop_stop.shop_id} for 10m')
                return
            bot.open_fails[shop_stop.shop_id] = 0

            by_name = {}
            for item in rec.items:
                by_name[item.name.lower()] = item.obj
            stock = {}
            for row in shop.stock():
                obj = by_name.get(row.name.lower())
                if obj is not None:
                    stock[obj] = row.count
            plan = [p for p in buyout_plan(rec, stock, inventory.count('Coins'), bot.chosen) if p.obj in route_objs]
            for buy in plan:
                gp_before = inventory.count('Coins')
                bought = yield from shop.buy(buy.name, buy.units)
                spent = gp_before - inventory.count('Coins')
                if bought > 0:
                    bot.session_haul[buy.obj] = bot.session_haul.get(buy.obj, 0) + bought
                    bot.session_spent += spent
                    bot.log(f'[shoprun] buy shop={shop_stop.shop_id} item={buy.obj} n={bought} spent={spent}')
            if cluster.repeat_while_full and inventory.is_full():
                for row in shop.stock():
                    obj = by_name.get(row.name.lower())
                    if row.count > 0 and obj is not None and obj in route_objs and row.name.lower() in bot.chosen:
                        repeat_while_full = True
            yield from shop.close()

        if repeat_while_full:
            bot.repeat_cluster_id = cluster.id
            bot.log(f'[shoprun] {cluster.id}: backpack full with selected stock remaining — banking and returning')
            return
        bot.repeat_cluster_id = None

        if cluster.haul_bank is not None:
            bot.status = f'banking the haul with {cluster.haul_bank.banker}'
            arrived = yield from walk_near(bot, cluster.haul_bank.stand)
            if not arrived:
                return
            opened = yield from open_npc_bank(bot, cluster.haul_bank.banker)
            if not opened:
                bot.log('[shoprun] in-cellar bank failed — retrying next pass')
                return
            yield from bank.deposit_all_matching(_not_kept(keep))

        bot.last_cluster_id = cluster.id
        bot.save_state()
        bot.log(f'[shoprun] cluster {cluster.id} done — advancing the ring')


BOT = define_bot(
    name='ShopRunner',
    create=ShopRunner,
    description='Runs a ring of shop clusters, banking for each and buying out the selected stock at its shops. Skips clusters the account is gated out of, and goes round a cluster again while it fills the pack with stock left',
    category='Money making',
    tags=['shopping', 'banking', 'runes', 'arrows', 'feathers'],
    settings_schema=SETTINGS,
)

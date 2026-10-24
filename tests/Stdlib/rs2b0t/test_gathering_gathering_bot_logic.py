"""rs2b0t's test/scripts/GatheringBot/GatheringBotLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import AXE_BAR_FOR, DEFAULT_CAMP_RADIUS, DEFAULT_CHASE_RADIUS, HOME_ARRIVE_RADIUS, Record, pick_nearest_prefer_local, resolve_camp_radius, resolve_chase_radius, should_cooldown_gather_tile, should_soft_home_from_gather_miss, should_walk_home_to_gather_anchor
from bots.gathering.camp import NAMED_CAMP_LEASH_FLOOR, effective_gather_leash, gather_hunt_radius, gather_spot_range_origin, is_auto_location, resource_within_camp, spot_within_gather_range
from bots.gathering.logic import BAIT_RETRY_MINUTES, FEATHER_BUYOUT_GP, FEATHER_RESTOCK_MINUTES, bait_trip_due, feather_coins_to_draw, ent_abort_action, feather_buyout_due, fishing_session_broken, gathering_combat_policy, hostile_attacker_nearby, loc_gather_should_yield, should_flee_combat, should_yield_gathering
from bots.gathering.tasks import LOCAL_MINE_PREFER_RADIUS

MIN = 60000


def _fn1():
    def _fn2():
        expect(feather_buyout_due(None, 15, 0)).to_be(True)
        expect(feather_buyout_due(0, 15, 14 * 60000)).to_be(False)
        expect(feather_buyout_due(0, 15, 15 * 60000)).to_be(True)
        expect(feather_buyout_due(None, 0, 999 * 60000)).to_be(False)
        expect(feather_buyout_due(0, 5, 5 * 60000)).to_be(True)
    test('starts immediately and honors the configured interval, including disabled', _fn2)

    def due(over=None):
        if over is None:
            over = Record({})
        _merged3 = {}
        for _k, _v in {'has_vendor': True, 'out_of_bait': False, 'last_at_ms': None, 'interval_minutes': 0, 'now_ms': 0}.items():
            _merged3[_k] = _v
        for _k, _v in (over._fields if isinstance(over, Record) else over).items():
            _merged3[_k] = _v
        return bait_trip_due(_merged3.get('has_vendor'), _merged3.get('out_of_bait'), _merged3.get('last_at_ms'), _merged3.get('interval_minutes'), _merged3.get('now_ms'))

    def _fn4():
        expect(due(Record({'has_vendor': False, 'out_of_bait': True, 'interval_minutes': 15}))).to_be(False)
    test('never sends camps without a vendor', _fn4)

    def _fn5():
        expect(due(Record({'out_of_bait': True}))).to_be(True)
        expect(due(Record({'out_of_bait': True, 'last_at_ms': 0, 'now_ms': 30000}))).to_be(False)
        expect(due(Record({'out_of_bait': True, 'last_at_ms': 0, 'now_ms': BAIT_RETRY_MINUTES * 60000}))).to_be(True)
        expect(due()).to_be(False)
    test('retries missing bait after a minute even with the scheduled trip disabled', _fn5)

    def _fn6():
        expect(due(Record({'interval_minutes': 15}))).to_be(True)
        expect(due(Record({'interval_minutes': 15, 'last_at_ms': 0, 'now_ms': 14 * 60000}))).to_be(False)
        expect(due(Record({'interval_minutes': 15, 'last_at_ms': 0, 'now_ms': 15 * 60000}))).to_be(True)
    test('sends scheduled trips even with bait already held', _fn6)


describe('Shilo supply cadence', _fn1)


def _fn7():
    def _fn8():
        expect(HOME_ARRIVE_RADIUS).to_be(8)
        anchor = Tile(2845, 3431, 0)
        # Inside disk → walkHomeIfNeeded short-circuits (no robotic pin).
        expect(anchor.distance_to(Tile(2845 + 8, 3431, 0))).to_be(8)
        expect(anchor.distance_to(Tile(2845 + 9, 3431, 0))).to_be(9)
    test('is a camp disk, not a single pin tile', _fn8)


describe('HOME_ARRIVE_RADIUS (soft home after bank/shop)', _fn7)


def _fn9():
    # Catherby pier anchor + bank stand (FishingLocations).
    catherby_spot = Tile(2845, 3431, 0)
    catherby_bank = Tile(2809, 3441, 0)

    def _fn10():
        bank_dist = catherby_spot.distance_to(catherby_bank)
        expect(bank_dist).to_be(36)
        expect(bank_dist).to_be_less_than_or_equal(NAMED_CAMP_LEASH_FLOOR)
        expect(bank_dist).to_be_greater_than(HOME_ARRIVE_RADIUS)
        # Full-leash "already home" was the bug, bank must still request a walk.
        expect(should_walk_home_to_gather_anchor(bank_dist)).to_be(True)
        expect(should_walk_home_to_gather_anchor(bank_dist, NAMED_CAMP_LEASH_FLOOR)).to_be(False)
    test('Catherby bank is inside named-camp leash but outside soft arrive disk', _fn10)

    def _fn11():
        expect(should_walk_home_to_gather_anchor(0)).to_be(False)
        expect(should_walk_home_to_gather_anchor(HOME_ARRIVE_RADIUS)).to_be(False)
        expect(should_walk_home_to_gather_anchor(HOME_ARRIVE_RADIUS + 1)).to_be(True)
        # Draynor bank ~12 from willows, short walk into arrive disk is correct.
        expect(should_walk_home_to_gather_anchor(12)).to_be(True)
    test('skips walk only inside the soft arrive disk', _fn11)

    def _fn12():
        expect(should_walk_home_to_gather_anchor(None)).to_be(False)
        expect(should_walk_home_to_gather_anchor(None)).to_be(False)
        expect(should_walk_home_to_gather_anchor(float("nan"))).to_be(False)
    test('null / non-finite distance does not force a walk', _fn12)


describe('shouldWalkHomeToGatherAnchor (#154 post-bank)', _fn9)


def _fn13():
    def _fn14():
        # Ardougne river: after hunting toward a hop, spots near the player must
        # still count even when far from the start-tile anchor.
        expect(gather_spot_range_origin(True, True)).to_be('player')
        expect(gather_spot_range_origin(True, True, False)).to_be('player')
    test('freeform fish with a live player tile measures from the player', _fn14)

    def _fn15():
        # Spot beside the player mid-pier must count even when far from the home pin.
        expect(gather_spot_range_origin(False, True, True)).to_be('player')
        # Freeform flag false + named still player.
        expect(gather_spot_range_origin(False, True, True)).to_be('player')
    test('named camp measures from the player (pier hop chase)', _fn15)

    def _fn16():
        expect(gather_spot_range_origin(False, True, False)).to_be('anchor')
    test('loc freeform (non-fish) without named camp pins the anchor', _fn16)

    def _fn17():
        expect(gather_spot_range_origin(True, False)).to_be('anchor')
        expect(gather_spot_range_origin(False, False, True)).to_be('anchor')
    test('without a player tile falls back to anchor', _fn17)

    def _fn18():
        # Stuck tile 2582,3353 vs start 2566,3374 is cheb 21, outside a 10 leash
        # from start, but a spot 3 tiles from the player is still fishable freeform.
        expect(spot_within_gather_range(3, 40)).to_be(True)
        expect(spot_within_gather_range(40, 40)).to_be(True)
        expect(spot_within_gather_range(41, 40)).to_be(False)
        expect(spot_within_gather_range(21, 10)).to_be(False)
        expect(spot_within_gather_range(float("nan"), 40)).to_be(False)
    test('spotWithinGatherRange is inclusive Chebyshev disk', _fn18)


describe('gatherSpotRangeOrigin (Auto freeform fish vs named camp)', _fn13)


def _fn19():
    def _fn20():
        expect(resource_within_camp(0, NAMED_CAMP_LEASH_FLOOR)).to_be(True)
        expect(resource_within_camp(64, NAMED_CAMP_LEASH_FLOOR)).to_be(True)
        expect(resource_within_camp(65, NAMED_CAMP_LEASH_FLOOR)).to_be(False)
        # Spot 72 from the pin is outside default membership.
        expect(resource_within_camp(72, NAMED_CAMP_LEASH_FLOOR)).to_be(False)
        # Wider per-camp membership covers long piers.
        expect(resource_within_camp(72, 80)).to_be(True)
    test('camp membership is inclusive Chebyshev from home pin', _fn20)

    def _fn21():
        # Spot 50 from player is still valid if within camp membership of home.
        expect(resource_within_camp(50, NAMED_CAMP_LEASH_FLOOR)).to_be(True)
        expect(resource_within_camp(64, NAMED_CAMP_LEASH_FLOOR)).to_be(True)
        # Outside membership → wrong coastline / off-camp.
        expect(resource_within_camp(70, NAMED_CAMP_LEASH_FLOOR)).to_be(False)
        # Wider per-camp membership covers long piers.
        expect(resource_within_camp(72, 80)).to_be(True)
    test('named camps accept any spot inside membership (no player-distance wall)', _fn21)

    def _fn22():
        expect(DEFAULT_CAMP_RADIUS).to_be(64)
        expect(DEFAULT_CHASE_RADIUS).to_be(40)
        expect(resolve_camp_radius(None)).to_be(64)
        expect(resolve_camp_radius(48)).to_be(48)
        expect(resolve_chase_radius(None)).to_be(40)
        expect(resolve_chase_radius(30)).to_be(30)
        # Freeform hunt: L+24 with a floor of 48, so leash 28 → 52.
        expect(gather_hunt_radius(28)).to_be(52)
        expect(gather_hunt_radius(18)).to_be(48)
        expect(gather_hunt_radius(40)).to_be(64)
    test('resolveCampRadius / freeform hunt defaults', _fn22)


describe('resourceWithinCamp + chase (named camp hop fence)', _fn19)


def _fn23():
    def _fn24():
        # Bank/restock still use the tight disk; gather miss must not.
        expect(should_walk_home_to_gather_anchor(12)).to_be(True)
        expect(should_soft_home_from_gather_miss(12)).to_be(False)
        expect(should_soft_home_from_gather_miss(HOME_ARRIVE_RADIUS + 1)).to_be(False)
        expect(should_soft_home_from_gather_miss(19)).to_be(False)
    test('does not thrash on freeform pier-hops just outside the 8-tile disk', _fn24)

    def _fn25():
        # Default leash = NAMED_CAMP_LEASH_FLOOR → threshold max(20, min(L,28)) = 28.
        expect(should_soft_home_from_gather_miss(20)).to_be(False)
        expect(should_soft_home_from_gather_miss(28)).to_be(False)
        expect(should_soft_home_from_gather_miss(29)).to_be(True)
        # Catherby bank ~36 from pier, clearly off-camp.
        expect(should_soft_home_from_gather_miss(36)).to_be(True)
        # Varrock W bank → SW mine is far past any camp disk.
        expect(should_soft_home_from_gather_miss(69)).to_be(True)
    test('pulls home from bank square / long wander', _fn25)

    def _fn26():
        # leash 12 → threshold max(20, min(12,28)) = 20 (HOME+12 floor).
        expect(should_soft_home_from_gather_miss(15, 12)).to_be(False)
        expect(should_soft_home_from_gather_miss(21, 12)).to_be(True)
        # Huge leash still caps threshold at 28.
        expect(should_soft_home_from_gather_miss(28, 64)).to_be(False)
        expect(should_soft_home_from_gather_miss(29, 64)).to_be(True)
    test('respects a tight freeform leash without using the soft disk', _fn26)

    def _fn27():
        expect(should_soft_home_from_gather_miss(None)).to_be(False)
        expect(should_soft_home_from_gather_miss(None)).to_be(False)
        expect(should_soft_home_from_gather_miss(float("nan"))).to_be(False)
    test('null / non-finite distance does not force a walk', _fn27)


describe('shouldSoftHomeFromGatherMiss (gather no-target thrash)', _fn23)


def _fn28():
    def npc(dist, attack=None, targets_me=None, in_combat=None, targets_another=None):
        return (Record({
            'in_combat': (in_combat if in_combat is not None else False),
            'targets_me': lambda: (targets_me if targets_me is not None else False),
            'targets_another_player': lambda: (targets_another if targets_another is not None else False),
            'actions': lambda: ((['Talk-to'] if attack == False else ['Attack'])),
            'distance': lambda: dist,
        }))

    def _fn29():
        expect(hostile_attacker_nearby([])).to_be(False)
        expect(hostile_attacker_nearby([npc(2, attack=False, targets_me=True)])).to_be(False)
        expect(hostile_attacker_nearby([npc(20, targets_me=True)])).to_be(False)
    test('empty / non-attackers are clear', _fn29)

    def _fn30():
        expect(hostile_attacker_nearby([npc(5, targets_me=True)])).to_be(True)
        expect(hostile_attacker_nearby([npc(5, targets_me=True)], 4)).to_be(False)
    test('attacker targeting us within radius is hostile', _fn30)

    def _fn31():
        expect(hostile_attacker_nearby([npc(2, in_combat=True, targets_another=False)])).to_be(True)
        # Fighting someone else a bit further out is not our problem.
        expect(hostile_attacker_nearby([npc(5, in_combat=True, targets_another=False)])).to_be(False)
        expect(hostile_attacker_nearby([npc(1, in_combat=True, targets_another=True)])).to_be(False)
    test('adjacent multi-combat pack member counts even if not on us', _fn31)


describe('hostileAttackerNearby (post-kite camp suppress)', _fn28)


def _fn32():
    def _fn33():
        expect(should_flee_combat(True, False, True)).to_be(True)
        expect(should_flee_combat(True, False, False)).to_be(False)
        expect(should_flee_combat(False, False, True)).to_be(False)
    test('requires combat + real attacker, not sticky flag alone', _fn33)

    def _fn34():
        expect(should_flee_combat(True, True, True)).to_be(False)
    test('yields while a random event is pending', _fn34)


describe('shouldFleeCombat (no blind kite on sticky combatCycle)', _fn32)


def _fn35():
    def policy(overrides=None):
        if overrides is None:
            overrides = Record({})
        _merged36 = {}
        for _k, _v in {
            'is_miner': True,
            'tile': Record({'x': 3018, 'z': 3590, 'level': 0}),
            'incoming_player_attacker': False,
            'auto_location': False,
            'tick_manip_allow_combat': False,
        }.items():
            _merged36[_k] = _v
        for _k, _v in (overrides._fields if isinstance(overrides, Record) else overrides).items():
            _merged36[_k] = _v
        return gathering_combat_policy(_merged36.get('is_miner'), _merged36.get('tile'), _merged36.get('incoming_player_attacker'), _merged36.get('auto_location'), _merged36.get('tick_manip_allow_combat'), _merged36.get('desert_camp_miner', False))

    def _fn37():
        expect(policy()).to_equal(Record({'mode': 'wilderness-miner-npc', 'allow_gather': True, 'flee': False}))
        # Plane 1 is still the surface Wilderness zone.
        expect(policy(Record({'tile': Record({'x': 3093, 'z': 3751, 'level': 1})})).mode).to_be('wilderness-miner-npc')
    test('holds ground and gathers through NPC combat at a surface Wilderness mine', _fn37)

    def _fn38():
        expect(policy(Record({'tile': Record({'x': 3100, 'z': 9920, 'level': 0})}))).to_equal(Record({'mode': 'wilderness-miner-npc', 'allow_gather': True, 'flee': False}))
    test('recognizes the canonical underground Wilderness strip', _fn38)

    def _fn39():
        expect(policy(Record({'tile': Record({'x': 3132, 'z': 9874, 'level': 0})}))).to_equal(Record({'mode': 'standard', 'allow_gather': False, 'flee': True}))
    test('does not treat the Edgeville Dungeon Mine as Wilderness', _fn39)

    def _fn40():
        expect(policy(Record({'incoming_player_attacker': True, 'auto_location': True, 'tick_manip_allow_combat': True}))).to_equal(Record({'mode': 'wilderness-miner-player', 'allow_gather': False, 'flee': True}))
    test('a detectable player attack vetoes mining and restores flee', _fn40)

    def _fn41():
        expect(policy(Record({'is_miner': False}))).to_equal(Record({'mode': 'standard', 'allow_gather': False, 'flee': True}))
        expect(policy(Record({'is_miner': False, 'auto_location': True}))).to_equal(Record({'mode': 'standard', 'allow_gather': False, 'flee': False}))
        expect(policy(Record({'is_miner': False, 'tick_manip_allow_combat': True}))).to_equal(Record({'mode': 'standard', 'allow_gather': True, 'flee': False}))
    test('non-Miner gatherers keep standard named, Auto, and tick-manip behavior', _fn41)

    def _fn42():
        expect(policy(Record({'tile': None})).mode).to_be('standard')
        expect(policy(Record({'tile': Record({'x': 3094, 'z': 3493, 'level': 0})})).mode).to_be('standard')
        expect(policy(Record({'tile': Record({'x': 2943, 'z': 3590, 'level': 0})})).mode).to_be('standard')
    test('missing and out-of-zone tiles use the standard policy', _fn42)


describe('gatheringCombatPolicy (Wilderness Miner)', _fn35)


def _fn43():
    common = Record({
        'is_miner': True,
        'tile': Record({'x': 3286, 'z': 9415, 'level': 0}),
        'auto_location': False,
        'tick_manip_allow_combat': False,
        'desert_camp_miner': True,
    })

    def _fn44():
        _merged45 = {}
        for _k, _v in (common._fields if isinstance(common, Record) else common).items():
            _merged45[_k] = _v
        for _k, _v in {'incoming_player_attacker': False}.items():
            _merged45[_k] = _v
        expect(gathering_combat_policy(_merged45.get('is_miner'), _merged45.get('tile'), _merged45.get('incoming_player_attacker'), _merged45.get('auto_location'), _merged45.get('tick_manip_allow_combat'), _merged45.get('desert_camp_miner', False))).to_equal(Record({'mode': 'desert-camp-miner-npc', 'allow_gather': True, 'flee': False}))
    test('Cake sustain and the dedicated route own resident NPC combat', _fn44)

    def _fn46():
        _merged47 = {}
        for _k, _v in (common._fields if isinstance(common, Record) else common).items():
            _merged47[_k] = _v
        for _k, _v in {'incoming_player_attacker': True}.items():
            _merged47[_k] = _v
        expect(gathering_combat_policy(_merged47.get('is_miner'), _merged47.get('tile'), _merged47.get('incoming_player_attacker'), _merged47.get('auto_location'), _merged47.get('tick_manip_allow_combat'), _merged47.get('desert_camp_miner', False))).to_equal(Record({'mode': 'desert-camp-miner-player', 'allow_gather': False, 'flee': True}))
    test('a detectable player attack still restores flee behavior', _fn46)


describe('gatheringCombatPolicy (Desert Mining Camp)', _fn43)


def _fn48():
    def _fn49():
        expect(effective_gather_leash(12, 'Use Closest')).to_be(12)
        expect(effective_gather_leash(12, 'Use Start Position')).to_be(12)
        expect(effective_gather_leash(12, 'Use Custom Position')).to_be(12)
        expect(effective_gather_leash(12, 'Auto')).to_be(12)
        expect(effective_gather_leash(18, 'auto')).to_be(18)
        expect(effective_gather_leash(40, 'Use Closest')).to_be(40)
        expect(effective_gather_leash(64, 'Auto')).to_be(64)
    test('freeform keeps the UI setting (Use Closest / Use Start / Use Custom / Auto)', _fn49)

    def _fn50():
        expect(effective_gather_leash(10, 'Catherby')).to_be(NAMED_CAMP_LEASH_FLOOR)
        expect(effective_gather_leash(18, 'Catherby')).to_be(NAMED_CAMP_LEASH_FLOOR)
        expect(effective_gather_leash(12, 'Southwest Varrock Mine')).to_be(NAMED_CAMP_LEASH_FLOOR)
        expect(effective_gather_leash(18, 'Fishing Guild')).to_be(NAMED_CAMP_LEASH_FLOOR)
        expect(effective_gather_leash(40, 'Draynor Village')).to_be(NAMED_CAMP_LEASH_FLOOR)
        expect(effective_gather_leash(64, 'Draynor Village')).to_be(64)
    test('named camps floor to NAMED_CAMP_LEASH_FLOOR (Fishing Guild / Catherby-scale)', _fn50)

    def _fn51():
        expect(effective_gather_leash(10, 'Atlantis')).to_be(NAMED_CAMP_LEASH_FLOOR)
        expect(effective_gather_leash(8, 'Some Unknown Camp')).to_be(NAMED_CAMP_LEASH_FLOOR)
    test('unknown names also floor — start-tile clusters need width', _fn51)


describe('effectiveGatherLeash', _fn48)


def _fn52():
    def _fn53():
        expect(is_auto_location('Use Closest')).to_be(True)
        expect(is_auto_location('Use Start Position')).to_be(True)
        expect(is_auto_location('Use Custom Position')).to_be(True)
        expect(is_auto_location('Auto')).to_be(True)
        expect(is_auto_location(' auto ')).to_be(True)
        expect(is_auto_location('Fishing Guild')).to_be(False)
        expect(is_auto_location('Atlantis')).to_be(False)
    test('Use Closest / Use Start Position / Use Custom Position / Auto are expert freeform (no mob flee)', _fn53)


describe('isAutoLocation', _fn52)


def _fn54():
    def _fn55():
        expect(gather_hunt_radius(18)).to_be(48)
        expect(gather_hunt_radius(28)).to_be(52)
        expect(gather_hunt_radius(40)).to_be(64)
        expect(gather_hunt_radius(NAMED_CAMP_LEASH_FLOOR)).to_be(NAMED_CAMP_LEASH_FLOOR + 24)
    test('extends past freeform leash without a hard 40 cap', _fn55)


describe('gatherHuntRadius', _fn54)


def _fn56():
    def rock(id, dist):
        return (Record({'id': id, 'dist': dist}))

    def _fn57():
        # Dwarven-style: iron 3 tiles away and iron 28 tiles across the tunnel.
        near = rock('near', 3)
        far = rock('far', 28)
        expect(LOCAL_MINE_PREFER_RADIUS).to_be(12)
        expect((pick_nearest_prefer_local([far, near], lambda r: r.dist).id if pick_nearest_prefer_local([far, near], lambda r: r.dist) is not None else None)).to_be('near')
        # Far alone still returns far when nothing local is up.
        expect((pick_nearest_prefer_local([far], lambda r: r.dist).id if pick_nearest_prefer_local([far], lambda r: r.dist) is not None else None)).to_be('far')
    test('prefers local cluster when any rock is within prefer radius', _fn57)

    def _fn58():
        a = rock('a', 5)
        b = rock('b', 2)
        far = rock('far', 40)
        expect((pick_nearest_prefer_local([a, far, b], lambda r: r.dist).id if pick_nearest_prefer_local([a, far, b], lambda r: r.dist) is not None else None)).to_be('b')
    test('among local rocks picks the closest', _fn58)

    def _fn59():
        expect(pick_nearest_prefer_local([], lambda: 0)).to_be(None)
    test('empty candidates → null', _fn59)

    def _fn60():
        near = rock('near', 3)
        far = rock('far', 28)
        expect((pick_nearest_prefer_local([far, near], lambda r: r.dist, 0).id if pick_nearest_prefer_local([far, near], lambda r: r.dist, 0) is not None else None)).to_be('near')
    test('preferRadius 0 falls back to global nearest', _fn60)


describe('pickNearestPreferLocal (mine/chop target pick)', _fn56)


def _fn61():
    def _fn62():
        # Iron respawn ~6t; old always-cooldown 8t sent the bot across the mine.
        expect(should_cooldown_gather_tile(True, True)).to_be(False)
        expect(should_cooldown_gather_tile(True, False)).to_be(False)
    test('does not cooldown after a successful ore/log', _fn62)

    def _fn63():
        expect(should_cooldown_gather_tile(False, True)).to_be(True)
        expect(should_cooldown_gather_tile(False, False)).to_be(False)
    test('cools only failed clicks when other targets exist', _fn63)


describe('shouldCooldownGatherTile (iron respawn thrash)', _fn61)


def _fn64():
    def _fn65():
        expect(should_yield_gathering(True, False, False, False)).to_be(True)
    test('a pending random event interrupts an active gather loop', _fn65)

    def _fn66():
        expect(should_yield_gathering(False, False, False, False)).to_be(False)
    test('an uninterrupted gather loop keeps waiting', _fn66)

    def _fn67():
        expect(should_yield_gathering(False, True, False, False)).to_be(True)
        expect(should_yield_gathering(False, False, True, False)).to_be(True)
        expect(should_yield_gathering(False, False, False, True)).to_be(True)
    test('existing full-pack, dialog, and missing-target exits remain intact', _fn67)

    def _fn68():
        expect(should_yield_gathering(False, False, False, False, True)).to_be(True)
        expect(should_yield_gathering(False, False, False, False, False)).to_be(False)
    test('combat yields so river troll / swarm can be handled', _fn68)

    def _fn69():
        expect(should_yield_gathering(False, False, False, False, True, True)).to_be(False)
        expect(should_yield_gathering(False, False, False, False, True, False)).to_be(True)
        # Non-combat exits still win even when combat is allowed.
        expect(should_yield_gathering(True, False, False, False, True, True)).to_be(True)
        expect(should_yield_gathering(False, True, False, False, True, True)).to_be(True)
        expect(should_yield_gathering(False, False, True, False, True, True)).to_be(True)
        expect(should_yield_gathering(False, False, False, True, True, True)).to_be(True)
    test('allowCombat keeps gathering during retaliate tick-manip (#160)', _fn69)


describe('shouldYieldGathering', _fn64)


def _fn70():
    calm = Record({
        'event_pending': False,
        'inventory_full': False,
        'dialog_pending': False,
        'in_combat': False,
        'allow_combat_gather': False,
        'should_eat_miner_food': False,
        'clicked_tile_hazard': False,
        'no_resource_in_camp': False,
    })

    def _fn71():
        _merged72 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged72[_k] = _v
        for _k, _v in {'clicked_tile_hazard': True}.items():
            _merged72[_k] = _v
        expect(loc_gather_should_yield(_merged72.get('event_pending'), _merged72.get('inventory_full'), _merged72.get('dialog_pending'), _merged72.get('in_combat'), _merged72.get('allow_combat_gather'), _merged72.get('should_eat_miner_food'), _merged72.get('clicked_tile_hazard'), _merged72.get('no_resource_in_camp'))).to_be(True)
        expect(loc_gather_should_yield(calm.event_pending, calm.inventory_full, calm.dialog_pending, calm.in_combat, calm.allow_combat_gather, calm.should_eat_miner_food, calm.clicked_tile_hazard, calm.no_resource_in_camp)).to_be(False)
    test('an Ent on the clicked tile yields even when other trees remain', _fn71)

    def _fn73():
        _merged74 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged74[_k] = _v
        for _k, _v in {'no_resource_in_camp': False, 'clicked_tile_hazard': False}.items():
            _merged74[_k] = _v
        expect(loc_gather_should_yield(_merged74.get('event_pending'), _merged74.get('inventory_full'), _merged74.get('dialog_pending'), _merged74.get('in_combat'), _merged74.get('allow_combat_gather'), _merged74.get('should_eat_miner_food'), _merged74.get('clicked_tile_hazard'), _merged74.get('no_resource_in_camp'))).to_be(False)
        _merged75 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged75[_k] = _v
        for _k, _v in {'no_resource_in_camp': True}.items():
            _merged75[_k] = _v
        expect(loc_gather_should_yield(_merged75.get('event_pending'), _merged75.get('inventory_full'), _merged75.get('dialog_pending'), _merged75.get('in_combat'), _merged75.get('allow_combat_gather'), _merged75.get('should_eat_miner_food'), _merged75.get('clicked_tile_hazard'), _merged75.get('no_resource_in_camp'))).to_be(True)
    test('other trees in camp are not treated as an empty grove', _fn73)


describe('locGatherShouldYield (Ent / smoking rock on the clicked tile)', _fn70)


def _fn76():
    def _fn77():
        expect(ent_abort_action(True, True)).to_be('chop-neighbour')
        expect(ent_abort_action(False, True)).to_be('walk-to-neighbour')
        expect(ent_abort_action(False, False)).to_be('step-off')
    test('chops a neighbour in reach, else walks, else steps off', _fn77)


describe('entAbortAction', _fn76)


def _fn78():
    def _fn79():
        expect(AXE_BAR_FOR.get('Rune axe')).to_be('Runite bar')
        expect(AXE_BAR_FOR.get('Mithril axe')).to_be('Mithril bar')
        expect(len(list(AXE_BAR_FOR.values()))).to_be_greater_than_or_equal(6)
        expect(('Runite bar' in set(list(AXE_BAR_FOR.values())))).to_be(True)
    test('maps every smithable axe to a bar name restock must retain', _fn79)


describe('AXE_BAR_FOR (smith restock keep)', _fn78)


def _fn80():
    calm = Record({
        'event_pending': False,
        'inventory_full': False,
        'dialog_pending': False,
        'in_combat': False,
        'spot_gone': False,
        'spot_moved': False,
        'became_whirlpool': False,
    })

    def _fn81():
        expect(fishing_session_broken(calm.event_pending, calm.inventory_full, calm.dialog_pending, calm.in_combat, calm.spot_gone, calm.spot_moved, calm.became_whirlpool)).to_be(False)
    test('calm session keeps fishing', _fn81)

    def _fn82():
        _merged83 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged83[_k] = _v
        for _k, _v in {'spot_moved': True}.items():
            _merged83[_k] = _v
        expect(fishing_session_broken(_merged83.get('event_pending'), _merged83.get('inventory_full'), _merged83.get('dialog_pending'), _merged83.get('in_combat'), _merged83.get('spot_gone'), _merged83.get('spot_moved'), _merged83.get('became_whirlpool'), _merged83.get('allow_combat', False))).to_be(True)
    test('spot hop ends the session even while animating', _fn82)

    def _fn84():
        _merged85 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged85[_k] = _v
        for _k, _v in {'became_whirlpool': True}.items():
            _merged85[_k] = _v
        expect(fishing_session_broken(_merged85.get('event_pending'), _merged85.get('inventory_full'), _merged85.get('dialog_pending'), _merged85.get('in_combat'), _merged85.get('spot_gone'), _merged85.get('spot_moved'), _merged85.get('became_whirlpool'), _merged85.get('allow_combat', False))).to_be(True)
    test('whirlpool swap ends the session', _fn84)

    def _fn86():
        _merged87 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged87[_k] = _v
        for _k, _v in {'spot_gone': True}.items():
            _merged87[_k] = _v
        expect(fishing_session_broken(_merged87.get('event_pending'), _merged87.get('inventory_full'), _merged87.get('dialog_pending'), _merged87.get('in_combat'), _merged87.get('spot_gone'), _merged87.get('spot_moved'), _merged87.get('became_whirlpool'), _merged87.get('allow_combat', False))).to_be(True)
    test('spot despawn ends the session', _fn86)

    def _fn88():
        _merged89 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged89[_k] = _v
        for _k, _v in {'in_combat': True}.items():
            _merged89[_k] = _v
        expect(fishing_session_broken(_merged89.get('event_pending'), _merged89.get('inventory_full'), _merged89.get('dialog_pending'), _merged89.get('in_combat'), _merged89.get('spot_gone'), _merged89.get('spot_moved'), _merged89.get('became_whirlpool'), _merged89.get('allow_combat', False))).to_be(True)
        _merged90 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged90[_k] = _v
        for _k, _v in {'event_pending': True}.items():
            _merged90[_k] = _v
        expect(fishing_session_broken(_merged90.get('event_pending'), _merged90.get('inventory_full'), _merged90.get('dialog_pending'), _merged90.get('in_combat'), _merged90.get('spot_gone'), _merged90.get('spot_moved'), _merged90.get('became_whirlpool'), _merged90.get('allow_combat', False))).to_be(True)
        _merged91 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged91[_k] = _v
        for _k, _v in {'inventory_full': True}.items():
            _merged91[_k] = _v
        expect(fishing_session_broken(_merged91.get('event_pending'), _merged91.get('inventory_full'), _merged91.get('dialog_pending'), _merged91.get('in_combat'), _merged91.get('spot_gone'), _merged91.get('spot_moved'), _merged91.get('became_whirlpool'), _merged91.get('allow_combat', False))).to_be(True)
        _merged92 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged92[_k] = _v
        for _k, _v in {'dialog_pending': True}.items():
            _merged92[_k] = _v
        expect(fishing_session_broken(_merged92.get('event_pending'), _merged92.get('inventory_full'), _merged92.get('dialog_pending'), _merged92.get('in_combat'), _merged92.get('spot_gone'), _merged92.get('spot_moved'), _merged92.get('became_whirlpool'), _merged92.get('allow_combat', False))).to_be(True)
    test('combat / event / full pack / dialog all break', _fn88)

    def _fn93():
        _merged94 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged94[_k] = _v
        for _k, _v in {'in_combat': True, 'allow_combat': True}.items():
            _merged94[_k] = _v
        expect(fishing_session_broken(_merged94.get('event_pending'), _merged94.get('inventory_full'), _merged94.get('dialog_pending'), _merged94.get('in_combat'), _merged94.get('spot_gone'), _merged94.get('spot_moved'), _merged94.get('became_whirlpool'), _merged94.get('allow_combat', False))).to_be(False)
        _merged95 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged95[_k] = _v
        for _k, _v in {'in_combat': True, 'allow_combat': False}.items():
            _merged95[_k] = _v
        expect(fishing_session_broken(_merged95.get('event_pending'), _merged95.get('inventory_full'), _merged95.get('dialog_pending'), _merged95.get('in_combat'), _merged95.get('spot_gone'), _merged95.get('spot_moved'), _merged95.get('became_whirlpool'), _merged95.get('allow_combat', False))).to_be(True)
        # Spot/event exits still break even when combat is allowed.
        _merged96 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged96[_k] = _v
        for _k, _v in {'in_combat': True, 'allow_combat': True, 'spot_gone': True}.items():
            _merged96[_k] = _v
        expect(fishing_session_broken(_merged96.get('event_pending'), _merged96.get('inventory_full'), _merged96.get('dialog_pending'), _merged96.get('in_combat'), _merged96.get('spot_gone'), _merged96.get('spot_moved'), _merged96.get('became_whirlpool'), _merged96.get('allow_combat', False))).to_be(True)
        _merged97 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged97[_k] = _v
        for _k, _v in {'in_combat': True, 'allow_combat': True, 'event_pending': True}.items():
            _merged97[_k] = _v
        expect(fishing_session_broken(_merged97.get('event_pending'), _merged97.get('inventory_full'), _merged97.get('dialog_pending'), _merged97.get('in_combat'), _merged97.get('spot_gone'), _merged97.get('spot_moved'), _merged97.get('became_whirlpool'), _merged97.get('allow_combat', False))).to_be(True)
        _merged98 = {}
        for _k, _v in (calm._fields if isinstance(calm, Record) else calm).items():
            _merged98[_k] = _v
        for _k, _v in {'in_combat': True, 'allow_combat': True, 'inventory_full': True}.items():
            _merged98[_k] = _v
        expect(fishing_session_broken(_merged98.get('event_pending'), _merged98.get('inventory_full'), _merged98.get('dialog_pending'), _merged98.get('in_combat'), _merged98.get('spot_gone'), _merged98.get('spot_moved'), _merged98.get('became_whirlpool'), _merged98.get('allow_combat', False))).to_be(True)
    test('allowCombat keeps fishing during Tannerfishing / retaliate (#160)', _fn93)


describe('fishingSessionBroken', _fn80)


# Why: Roachey's feathers come back one a tick toward a baseline of 1500, so a full buyout is fifteen minutes of restock and anything sooner takes a partial stack.
def _fn99():

    def _fn100():
        expect(FEATHER_RESTOCK_MINUTES).to_be(15)
    test("the default interval is the shop's own full-recovery time", _fn100)

    def _fn101():
        expect(feather_buyout_due(None, 15, 0)).to_be(True)
    test('the first trip is owed as soon as the run starts', _fn101)

    def _fn102():
        expect(feather_buyout_due(0, 15, 14 * MIN)).to_be(False)
        expect(feather_buyout_due(0, 15, 15 * MIN)).to_be(True)
        expect(feather_buyout_due(0, 15, 40 * MIN)).to_be(True)
    test('waits the interval out between trips', _fn102)

    def _fn103():
        expect(feather_buyout_due(None, 0, 999 * MIN)).to_be(False)
        expect(feather_buyout_due(0, 0, 999 * MIN)).to_be(False)
    test('zero minutes turns it off, first trip included', _fn103)

    def _fn104():
        def due(over=None):
            if over is None:
                over = Record({})
            _merged105 = {}
            for _k, _v in {
            'has_vendor': True,
            'out_of_bait': False,
            'last_at_ms': 0,
            'interval_minutes': 0,
            'now_ms': 999 * MIN,
        }.items():
                _merged105[_k] = _v
            for _k, _v in (over._fields if isinstance(over, Record) else over).items():
                _merged105[_k] = _v
            return bait_trip_due(_merged105.get('has_vendor'), _merged105.get('out_of_bait'), _merged105.get('last_at_ms'), _merged105.get('interval_minutes'), _merged105.get('now_ms'))

        def _fn106():
            expect(due(Record({'has_vendor': False, 'out_of_bait': True, 'last_at_ms': None}))).to_be(False)
            expect(due(Record({'has_vendor': False, 'interval_minutes': 15, 'last_at_ms': None}))).to_be(False)
        test('a camp with no shop never goes, however short it is', _fn106)

        # Why: the bank run at a shop-only camp finds no bait to withdraw and spins on 'bank has no Feather', so running out has to send the trip by itself.
        def _fn107():
            expect(due(Record({'out_of_bait': True}))).to_be(True)
            expect(due(Record({'out_of_bait': False}))).to_be(False)
        test('runs out of bait and goes, even with the clock switched off', _fn107)

        def _fn108():
            expect(due(Record({'out_of_bait': True, 'last_at_ms': 0, 'now_ms': 30000}))).to_be(False)
            expect(due(Record({'out_of_bait': True, 'last_at_ms': 0, 'now_ms': BAIT_RETRY_MINUTES * MIN}))).to_be(True)
        test('a needed trip still waits out the retry, so an empty shelf is not hit every loop', _fn108)

        def _fn109():
            expect(due(Record({'out_of_bait': False, 'interval_minutes': 15, 'last_at_ms': 0, 'now_ms': 15 * MIN}))).to_be(True)
            expect(due(Record({'out_of_bait': False, 'interval_minutes': 15, 'last_at_ms': 0, 'now_ms': 14 * MIN}))).to_be(False)
        test('the clock still sends a trip that holds plenty of bait', _fn109)

        def _fn110():
            expect(due(Record({'interval_minutes': 15, 'last_at_ms': None}))).to_be(True)
            expect(due(Record({'out_of_bait': True, 'last_at_ms': None}))).to_be(True)
        test('the first trip is owed at once on the clock, and at once when out of bait', _fn110)
    describe('the bait trip', _fn104)

    def _fn111():
        expect(feather_buyout_due(0, 5, 5 * MIN)).to_be(True)
        expect(feather_buyout_due(0, 5, 4 * MIN)).to_be(False)
    test('a shorter interval is honoured, since a partial stack still buys', _fn111)


describe('the guild feather buyout', _fn99)


# 'drawing coins for the buyout' waits for the feather buyout's shop pricing (phase 13).


def _feather_draws():
    def _fn1():
        expect(feather_coins_to_draw(0, 5000000, 2)).to_be(FEATHER_BUYOUT_GP)
    test('takes a shelf out of a bank that holds more', _fn1)

    def _fn2():
        expect(feather_coins_to_draw(0, 900, 2)).to_be(900)
    test('takes the whole of a bank that holds less', _fn2)

    def _fn3():
        expect(feather_coins_to_draw(250, 5000000, 2)).to_be(FEATHER_BUYOUT_GP - 250)
    test('counts what is already held against the budget', _fn3)

    def _fn4():
        expect(feather_coins_to_draw(FEATHER_BUYOUT_GP, 5000000, 2)).to_be(0)
        expect(feather_coins_to_draw(FEATHER_BUYOUT_GP + 1, 5000000, 2)).to_be(0)
    test('draws nothing when the pack already covers a shelf', _fn4)

    def _fn5():
        expect(feather_coins_to_draw(0, 0, 2)).to_be(0)
    test('an empty bank asks for nothing', _fn5)


describe('drawing coins for the buyout', _feather_draws)

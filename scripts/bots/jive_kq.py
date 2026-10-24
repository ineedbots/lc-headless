# Four accounts kill the Kalphite Queen together: rs2b0t's JiveKQ (MIT, see thirdparty/rs2b0t). Each banks the same
# dragon mace and magic shortbow loadout at Shantay, the four rope down together on the leader's word, stand west,
# east, north and south of her, pull her onto open ground when the cross doesn't fit, and leave together when one
# runs short. A teammate who dies has its dropped gear picked up by another. rs2b0t's clients talked over a
# BroadcastChannel; here the four are accounts in one process, messaging each other with send_bot_message.

import random
import time

from rs2004.catalogs import Record, sustain
from bots.jivekq.loadout import ARROWS, BOW, FOOD, MACE, RECOIL
from bots.jivekq.loot import LootCollector, step_to
from bots.jivekq.party import Party, normalize_name, parse_roster
from bots.jivekq.policy import SIDES, WAIT_CORNER, QueenTracker, combat_formation, combat_mode, in_lair, in_nest, near, queen_phase, retreat_reason
from bots.jivekq.recovery import DeathReport, RecoveryItem, recovery_drops, tile_message
from bots.jivekq.route import camelot, descend, duel_arena, gate_tile, pass_gate, place_rope, rope_ready, walk
from bots.jivekq.search import QueenSearch, QueenSighting, approach_queen, pull_queen
from bots.jivekq.stats import CombatStats
from bots.jivekq.supply import boost, boosts_ready, doses, drink, eat, equip, provision, send_eat, send_equip, supplies, worn

SETTINGS = {
    'team': SettingDef('string', '', 'Four account names',
                       help='The same comma-separated roster on all four accounts, which run in one client. The first places the ropes; the four stand west, east, north and south'),
}

REQUIREMENTS = [('attack', 60), ('defence', 40), ('ranged', 70), ('hitpoints', 70), ('prayer', 37), ('magic', 45)]
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']
ULTIMATE_STRENGTH = 'Ultimate strength'
INCREDIBLE_REFLEXES = 'Incredible reflexes'
VISITORS = ['genie', 'mysterious old man']
IGNORED_IN_NEST = ['genie', 'drunken dwarf', 'mysterious old man', 'sandwich lady', 'frog', 'strange plant', 'lamp', 'strange box']
VIAL_OF_WATER = 229
RELEASE_MS = 12000


def now_ms():
    return time.time() * 1000


def queen_npc():
    return npcs.query().where(lambda n: queen_phase(n.id) is not None).nearest()


def queen_snapshot(npc):
    return Record({'id': npc.id, 'health': npc.health, 'total_health': npc.max_health}) if npc is not None else None


class JiveKQ(LoopingBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.stage = 'bank'
        self.trip = 0
        self.kills = 0
        self.looted = 0
        self.entries = 0
        self.retreats = 0
        self.restocking = False
        self.trip_kills = 0
        self.stats = CombatStats()
        self.recovered_items = []
        self.last_kill_ms = 0
        self.collector = LootCollector()
        self.loot_counts = {}
        self.party = None
        self.prepared = False
        self.paused = False
        self.release_out = None
        self.entry_at = 0
        self.gate_at = 0
        self.descent = None
        self.walk_tile = None
        self.last_dose = 0
        self.poisoned = False
        self.queen_tracker = QueenTracker()
        self.slot = 0
        self.last_attack = -10
        self.next_eat_tick = 0
        self.pending_food = None
        self.prayer_requests = {}
        self.protection_failures = 0
        self.weapon_request = None
        self.queen_dead = False
        self.blocked = False
        self.lure = None
        self.lure_at = 0
        self.sighting = None
        self.search = QueenSearch()
        self.searching = False
        self.last_kill_tick = 0
        self.lure_attempt = 0
        self.lure_position = None
        self.death = None
        self.last_alive = None
        self.recovery_message = ''
        self.recoveries = {}
        self.spellings = {}
        yield from execution.delay_until(lambda: game.scene_ready(), 0)
        roster = parse_roster(self.settings.str('team', ''))
        me = normalize_name(game.my_name() or '')
        if me not in roster:
            raise RuntimeError('This account is not in the KQ team roster')
        self.slot = roster.index(me)
        for skill, level in REQUIREMENTS:
            if skills.level(skill) < level:
                raise RuntimeError(f'KQ requires {level} {skill}')
        self.started_at = now_ms()
        self.xp_at_start = sum([skills.xp(s) for s in COMBAT_SKILLS])
        session = f'{int(now_ms())}-{random.randint(0, 1000000000)}'
        self.party = Party(roster, me, session, lambda m: self.log(f'team: {m}'))
        self.on('tick', self.watch_tick)
        self.on('chat_message', self.watch_chat)
        game.set_auto_retaliate(False)

        def upkeep_hook():
            self.check_safety()
            if self.stage != 'retreat':
                yield from self.upkeep(True)

        sustain.set(upkeep_hook)
        event_signal.set_interrupt(lambda: self.stage == 'retreat')
        if in_nest(game.tile()):
            self.stage = 'retreat'
        self.heartbeat()

    # The team channel

    def on_bot_message(self, sender, message):
        if self.party is None or not isinstance(message, dict):
            return
        if 'member' in message:
            self.party.receive(message['member'], now_ms())
        if 'release' in message and normalize_name(sender) == self.party.roster[0]:
            self.party.accept(message['release'], now_ms())

    def post(self, message):
        """Sends to the three teammates, trying their name as the roster spells it and with underscores, since an
        account file may spell a space either way."""
        for name in self.party.roster:
            if name == self.party.self_name:
                continue
            known = self.spellings.get(name)
            for spelling in ([known] if known is not None else [name, name.replace(' ', '_')]):
                try:
                    send_bot_message(spelling, message)
                    self.spellings[name] = spelling
                    break
                except ValueError:
                    continue

    def watch_tick(self, *args):
        self.observe_death()
        self.observe_food()
        self.observe_descent()
        self.observe_queen()
        self.observe_stats()
        self.check_safety()
        self.heartbeat()

    def watch_chat(self, line):
        if 'you have been poisoned' in (line.text or '').lower():
            self.poisoned = True

    def heartbeat(self):
        if self.party is None:
            return
        tile = game.tile() if game.ingame() else None
        local = players.local()
        claim = self.collector.claim()
        alive = game.ingame() and skills.effective('hitpoints') > 0
        member = {
            'blocked': self.blocked, 'name': self.party.self_name, 'session': self.party.session, 'trip': self.trip, 'stage': self.stage,
            'tile': tile_message(tile) if tile is not None else None,
            'ready': self.prepared and not self.paused and alive and self.stage != 'retreat',
            'restocking': self.restocking and not self.paused and (alive or self.death is not None),
            'recovery_space': inventory.free() + len([i for i in inventory.items() if i.name == 'Vial']),
            'stats': {'hp': max(0, skills.effective('hitpoints')), 'prayer': prayer.points(), 'food': inventory.count_by_id(FOOD),
                      'damage': self.stats.damage, 'dps': self.stats.dps(), 'kills': self.kills},
        }
        if self.lure is not None:
            member['lure'] = tile_message(self.lure)
        if self.sighting is not None:
            member['queen'] = self.sighting.to_message()
        if local is not None:
            member['player_slot'] = local.index
        if self.death is not None:
            member['death'] = self.death.to_message()
        if claim is not None:
            member['loot'] = claim.to_message()
        reason = 'paused' if self.paused else (self.status if self.stage == 'retreat' else self.recovery_message)
        if reason:
            member['reason'] = reason
        self.party.receive(member, now_ms())
        self.post({'member': member})
        if self.release_out is not None and now_ms() - self.release_out.at < RELEASE_MS:
            self.post({'release': self.release_out.to_message()})

    # Safety

    def retreat(self, reason, restocking=False):
        if self.stage == 'retreat':
            return
        self.log(f"{'restocking' if restocking else 'group retreat'}: {reason}")
        self.restocking = restocking
        self.collector.clear()
        self.stage = 'retreat'
        self.descent = None
        self.status = reason
        self.retreats += 1
        self.heartbeat()
        tile = game.tile()
        if tile is not None and in_nest(tile):
            step_to(tile)

    def observe_death(self):
        if not game.ingame() or not game.scene_ready() or self.death is not None:
            return
        tile = game.tile()
        if tile is None:
            return
        items = [RecoveryItem(i.id, i.count) for i in inventory.items() + equipment.items()]
        ground = [RecoveryItem(g.id, g.count) for g in ground_items.query().results() if near(g.tile(), tile, 0)]
        if skills.effective('hitpoints') > 0:
            self.last_alive = DeathReport(now_ms(), tile, items, ground)
            return
        last = self.last_alive
        same_tile = last is not None and near(last.tile, tile, 0)
        self.death = DeathReport(now_ms(), tile, last.items if last is not None else items, last.ground if same_tile else ground)
        self.restocking = True
        self.prepared = False
        self.retreat('died; teammates can recover my dropped items', True)
        self.heartbeat()

    def check_safety(self):
        if self.stage == 'retreat':
            return True
        if not self.prepared or self.stage == 'bank' or self.party is None or not game.scene_ready():
            return False
        if self.stage == 'fight' and not in_lair(game.tile()):
            self.retreat('left the queen chamber unexpectedly', True)
            return True
        if not in_nest(game.tile()):
            return False
        visitor = npcs.query().within(6).where(lambda n: (n.name or '').lower() in VISITORS and n.targets_me()).nearest()
        if visitor is not None:
            self.retreat(f'{visitor.name} needs attention outside combat', self.stage == 'fight')
            return True
        reason = retreat_reason(supplies())
        if reason is not None:
            self.retreat(reason, self.stage == 'fight')
            return True
        now = now_ms()
        if not self.party.unsafe(self.trip, now):
            return False
        peers = self.party.members(now)
        names = [m.name for m in peers]
        missing = [name for name in self.party.roster if name not in names]
        unready = [m for m in peers if not m.restocking and (not m.ready or m.trip != self.trip or m.stage == 'retreat' or m.stage == 'bank')]
        if missing:
            self.retreat(f"missing heartbeat: {', '.join(missing)}")
        else:
            self.retreat('team not ready: ' + ', '.join([f'{m.name} ({m.reason or m.stage})' for m in unready]))
        return True

    # The queen

    def observe_queen(self):
        if self.stage != 'fight' or not in_lair(game.tile()) or not game.scene_ready():
            return
        queen = queen_npc()
        dead, killed = self.queen_tracker.observe(queen_snapshot(queen), now_ms())
        self.queen_dead = dead
        if queen is not None and not dead:
            peers = [m for m in self.party.members(now_ms()) if m.trip == self.trip and m.stage == 'fight' and not m.restocking]
            engaged = queen.targets_me() or any([m.player_slot is not None and queen.target == ('player', m.player_slot) for m in peers])
            self.sighting = QueenSighting(queen.id, queen.network_tile(), now_ms(), engaged)
            self.searching = False
        if dead or killed:
            self.sighting = None
        if dead or killed or (queen is not None and self.formation(queen) is not None):
            self.blocked = False
            self.lure = None
        elif queen is not None:
            self.blocked = True
        if killed:
            self.kills += 1
            self.trip_kills += 1
            self.last_kill_ms = self.queen_tracker.last_kill_ms
            self.last_kill_tick = game.tick()
            self.search = QueenSearch()
            self.log(f'Kalphite Queen killed ({self.kills})')

    def observe_stats(self):
        fighting = not self.paused and self.stage == 'fight' and self.queen_tracker.started_at > 0 and not self.queen_tracker.killed_at
        self.stats.observe(now_ms(), skills.xp('strength') + skills.xp('ranged'), fighting)

    def leave_rendezvous(self):
        if self.stage == 'surface' or self.stage == 'upper':
            self.stage = 'travel'
            self.heartbeat()

    # Why: rs2b0t sends these without waiting and checks back, so a fight tick is never spent on a toggle; a click
    # gets ten ticks to land before it's sent again, since a second click on a toggle still in flight undoes it.
    def request_prayer(self, name, on):
        tick = game.tick()
        request = self.prayer_requests.get(name)
        if prayer.active(name) == on:
            if name == PROTECT_FROM_MAGIC:
                self.protection_failures = 0
            if request is not None:
                del self.prayer_requests[name]
            return True
        if request is not None and request.on == on and tick < request.retry_tick:
            return False
        if request is not None and request.on == on and name == PROTECT_FROM_MAGIC and on:
            self.protection_failures += 1
        sent = prayer.toggle(name, on)
        self.prayer_requests[name] = Record({'on': on, 'retry_tick': tick + (10 if sent else 1)})
        return False

    def protect(self):
        request = self.prayer_requests.get(PROTECT_FROM_MAGIC)
        if not prayer.active(PROTECT_FROM_MAGIC) and self.protection_failures >= 2 and request is not None and game.tick() >= request.retry_tick:
            self.retreat('could not restore magic protection after retrying', True)
            return False
        return self.request_prayer(PROTECT_FROM_MAGIC, True)

    def clear_prayers(self):
        done = [self.request_prayer(name, False) for name in [PROTECT_FROM_MAGIC, ULTIMATE_STRENGTH, INCREDIBLE_REFLEXES]]
        return all(done)

    def equip_weapon(self, id):
        tick = game.tick()
        previous = self.weapon_request
        waiting = previous is not None and not worn(previous.id) and tick < previous.retry_tick
        if not waiting and worn(id):
            self.weapon_request = None
            return True
        self.status = 'equipping dragon mace' if id == MACE else 'equipping magic shortbow'
        if waiting:
            return False
        if inventory.count_by_id(id) == 0:
            self.retreat('phase weapon missing', True)
            return False
        sent = send_equip(id)
        self.weapon_request = Record({'id': id, 'retry_tick': tick + (10 if sent else 1)})
        return False

    def upkeep(self, walking=False):
        """Eats, sips and boosts between swings. True when it spent the pass."""
        if not game.scene_ready() or self.stage == 'bank':
            return False
        tile = game.tile()
        claim = self.collector.claim()
        if claim is not None and claim.id == ARROWS and not self.waiting_for_respawn():
            if claim.collecting and tile is not None:
                step_to(tile)
            self.collector.clear()
            self.heartbeat()
        moving = walking and tile is not None and tile.level == 2 and self.walk_tile is not None and not near(tile, self.walk_tile, 0)
        if walking:
            self.walk_tile = tile
        self.observe_food()
        hp = skills.effective('hitpoints')
        queen = queen_npc() if self.stage == 'fight' and not self.queen_dead else None
        if queen is not None and hp > 31 and prayer.points() > 0 and not prayer.active(PROTECT_FROM_MAGIC):
            self.protect()
        waiting = self.stage == 'fight' and self.queen_tracker.killed_at > 0 and queen is None and not self.searching
        if waiting:
            self.clear_prayers()
        food = inventory.count_by_id(FOOD)
        tick = game.tick()
        can_consume = tick >= self.next_eat_tick and (self.pending_food is None or tick - self.pending_food[0] >= 4)
        if self.stage == 'fight' and hp > 31 and prayer.points() <= 10 and doses('Prayer potion') > 0:
            if not can_consume:
                return False
            drank = yield from drink('Prayer potion')
            return drank
        if (hp <= 31 or hp <= skills.level('hitpoints') - 20) and food > 0:
            self.leave_rendezvous()
            if not can_consume:
                return False
            if self.stage != 'fight':
                ate = yield from eat()
                return ate
            self.queue_combat_food()
            return False
        if self.stage == 'fight' and not can_consume:
            return False
        if in_nest(game.tile()):
            if prayer.points() <= min(35, prayer.max() - 15) and doses('Prayer potion') > 0:
                self.leave_rendezvous()
                drank = yield from drink('Prayer potion')
                return drank
            dose_due = now_ms() - self.last_dose > 240000 and (self.stage == 'fight' or self.stage == 'upper' or moving)
            if (self.poisoned or dose_due) and doses('Superantipoison') > 0:
                self.leave_rendezvous()
                drank = yield from drink('Superantipoison')
                if drank:
                    self.last_dose = now_ms()
                    self.poisoned = False
                    return True
            if not worn(RECOIL) and inventory.count_by_id(RECOIL) > 0:
                self.leave_rendezvous()
                on = yield from equip(RECOIL)
                return on
            upper = game.tile() is not None and game.tile().level == 2
            if self.stage == 'upper' or self.stage == 'fight' or moving:
                melee = upper or waiting or npcs.query().where(lambda n: n.id == 1158).nearest() is not None
                if self.stage == 'upper' and not boosts_ready():
                    self.leave_rendezvous()
                boosted = yield from boost(melee)
                if boosted:
                    return True
        return False

    def queue_combat_food(self):
        """Sends one Eat between swings without waiting on it, holding the next for three ticks."""
        tick = game.tick()
        count = inventory.count_by_id(FOOD)
        if not count or tick < self.next_eat_tick or (self.pending_food is not None and tick - self.pending_food[0] < 4):
            return False
        sent = send_eat()
        if not sent:
            return False
        self.pending_food = (tick, count)
        self.next_eat_tick = tick + 3
        self.last_attack = -10
        return True

    def observe_food(self):
        if not game.scene_ready() or self.pending_food is None or inventory.count_by_id(FOOD) >= self.pending_food[1]:
            return
        self.next_eat_tick = max(self.next_eat_tick, game.tick() + 2)
        self.pending_food = None

    # The loop

    def loop(self):
        if not game.scene_ready() or self.party is None:
            return
        try:
            yield from self.step()
        except Exception as error:
            reason = str(error)
            self.retreat(reason)
            if in_nest(game.tile()):
                yield from self.escape()
            else:
                self.request_finish(reason)

    def step(self):
        self.observe_death()
        self.observe_descent()
        if skills.effective('hitpoints') <= 0:
            return
        if self.stage == 'retreat' or self.check_safety():
            yield from self.escape()
            return
        entered = yield from self.enter_released_gate()
        if entered:
            return
        spent = yield from self.upkeep()
        if spent:
            return
        if not game.scene_ready() or self.check_safety():
            return
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            return
        if self.stage == 'bank':
            yield from self.bank_stage()
            return
        if in_lair(game.tile()):
            recovered = yield from self.recover_loot()
            if not recovered:
                yield from self.fight()
            return
        if in_nest(game.tile()):
            yield from self.gate('upper')
            return
        through = yield from pass_gate(lambda m: self.log(m))
        if not through:
            return
        yield from self.gate('surface')

    def bank_stage(self):
        party = self.party
        self.status = 'banking the shared KQ loadout'
        if not self.prepared:
            ready = yield from provision(self.slot, lambda m: self.log(m), self.death is not None)
            if not ready:
                if self.death is not None:
                    self.status = 'returning to Shantay; waiting for replacement gear'
                return
            self.prepared = True
        self.status = 'waiting for four supplied players at Shantay bank'
        self.heartbeat()
        now = now_ms()
        release = party.release('bank', max([self.trip] + [m.trip for m in party.members(now)]) + 1, now)
        if release is not None:
            self.release_out = release
            party.accept(release, now)
            self.heartbeat()
        trip = party.departure(self.trip, now_ms())
        if trip is None:
            return
        self.trip = trip
        self.stage = 'travel'
        self.restocking = False
        self.queen_tracker = QueenTracker()
        self.queen_dead = False
        self.blocked = False
        self.lure = None
        self.lure_at = 0
        self.sighting = None
        self.search = QueenSearch()
        self.searching = False
        self.lure_attempt = 0
        self.lure_position = None
        self.death = None
        self.last_alive = None
        self.recoveries = {}
        self.recovery_message = ''
        self.trip_kills = 0
        self.collector.clear()
        self.gate_at = 0
        self.descent = None
        self.log(f'trip {self.trip}: shared loadout ready')
        self.heartbeat()

    def gate(self, gate):
        party = self.party
        target = gate_tile(gate)
        if not near(game.tile(), target, 0):
            self.stage = 'travel'
            self.status = f'walking to {gate} entrance'
            self.walk_tile = game.tile()
            yield from walk(target, 0, lambda m: self.log(m))
            self.walk_tile = None
            return
        if not self.gate_at:
            self.gate_at = now_ms()
        if now_ms() - self.gate_at > 180000:
            self.retreat('party rendezvous timed out')
            return
        if gate == 'upper' and not boosts_ready():
            self.stage = 'travel'
            self.status = 'drinking super potions before entering'
            yield from boost(True)
            return
        if gate == 'upper' and not prayer.active(PROTECT_FROM_MAGIC):
            self.stage = 'travel'
            self.status = 'enabling protection before entering'
            yield from prayer.set(PROTECT_FROM_MAGIC, True)
            return
        if gate == 'upper' and now_ms() - self.last_dose > 240000:
            self.stage = 'travel'
            self.status = 'drinking antipoison before entering'
            drank = yield from drink('Superantipoison')
            if not drank:
                self.retreat('antipoison unavailable')
                return
            self.last_dose = now_ms()
            return
        self.stage = gate
        self.status = f'waiting for four at {gate} entrance'
        self.heartbeat()
        release = party.release(gate, self.trip, now_ms())
        if release is not None and self.together():
            placed = yield from place_rope(gate, lambda m: self.log(m))
            if placed:
                release = party.release(gate, self.trip, now_ms())
                if release is None or not self.together():
                    return
                self.release_out = release
                party.accept(release, now_ms())
                self.heartbeat()
        yield from self.enter_released_gate()

    def together(self):
        """Whether all four stand within eight tiles, as the rope's release needs."""
        visible = set([self.party.self_name] + [normalize_name(p.name or '') for p in players.query().within(8).results()])
        return all([name in visible for name in self.party.roster])

    def enter_released_gate(self):
        for gate in ['surface', 'upper']:
            if not near(game.tile(), gate_tile(gate), 0) or self.party is None or not self.party.released(gate, self.trip, now_ms()) or not rope_ready(gate):
                continue
            self.stage = gate
            self.status = f'descending {gate} entrance with team'
            self.descent = gate
            yield from descend(gate)
            self.observe_descent()
            return True
        return False

    def observe_descent(self):
        if not game.scene_ready():
            return
        gate = self.descent
        here = game.tile()
        landed = (gate == 'surface' and in_nest(here) and here.level == 2) or (gate == 'upper' and in_lair(here))
        if not landed:
            return
        self.descent = None
        if self.check_safety():
            return
        self.log(f'trip {self.trip}: descended {gate}')
        self.stage = 'travel' if gate == 'surface' else 'fight'
        self.gate_at = 0
        self.entry_at = now_ms()
        if gate == 'upper':
            self.entries += 1
        self.heartbeat()

    # The fight

    def fight(self):
        peers = [m for m in self.party.members(now_ms()) if not m.restocking]
        if any([m.stage != 'fight' or not in_lair(m.tile) for m in peers]):
            self.status = 'waiting for the team to finish descending'
            if now_ms() - self.entry_at > 12000:
                self.retreat('the team did not arrive together')
            return
        if self.loot():
            return
        queen = queen_npc()
        sighting = self.latest_sighting()
        if not self.queen_dead and (self.blocked or any([m.blocked for m in peers])) and (queen is None or self.formation(queen) is None):
            self.reposition_queen(queen, sighting)
            return
        self.lure_at = 0
        if queen is None or self.queen_dead:
            if self.queen_tracker.killed_at and game.tick() - self.last_kill_tick <= 120 and sighting is None:
                if not self.clear_prayers():
                    return
                corner = near(game.tile(), WAIT_CORNER, 0)
                self.status = 'stacked near spawn; prayers off' if corner else 'regrouping in the northwest corner'
                if not corner:
                    step_to(WAIT_CORNER)
                    return
                if not self.equip_weapon(MACE):
                    return
                if game.combat_mode() != 1:
                    game.set_combat_mode(1)
            else:
                self.request_prayer(ULTIMATE_STRENGTH, False)
                self.request_prayer(INCREDIBLE_REFLEXES, False)
                if queen is None:
                    self.search_queen(sighting)
            return
        if prayer.points() == 0 and doses('Prayer potion') > 0:
            self.status = 'restoring prayer before attacking'
            return
        if not self.protect():
            if self.stage != 'retreat':
                self.status = 'restoring magic protection'
            return
        if self.check_safety():
            return
        phase = queen_phase(queen.id)
        formation = self.formation(queen)
        if formation is None:
            self.blocked = True
            self.heartbeat()
            self.reposition_queen(queen, sighting)
            return
        tile = formation[self.slot]
        self.status = f'{phase}: {SIDES[self.slot]}'
        if not near(game.tile(), tile, 0):
            step_to(tile)
            return
        melee = phase == 'melee'
        if not self.equip_weapon(MACE if melee else BOW):
            return
        mode = combat_mode(phase, game.combat_styles())
        if mode is None:
            self.retreat('required crush or rapid combat style unavailable')
            return
        if game.combat_mode() != mode:
            game.set_combat_mode(mode)
        if self.check_safety():
            return
        self.request_prayer(ULTIMATE_STRENGTH, melee)
        self.request_prayer(INCREDIBLE_REFLEXES, melee)
        if special.ready('Dragon mace' if melee else 'Magic shortbow'):
            yield from special.arm()
        if game.tick() - self.last_attack >= 4 or game.facing() != ('npc', queen.index):
            if queen.interact('Attack'):
                self.last_attack = game.tick()

    def formation(self, queen):
        return self.formation_at(queen.network_tile(), queen.size, queen_phase(queen.id))

    def formation_at(self, centre, size, phase):
        back = size // 2
        origin = Tile(centre.x - back, centre.z - back, centre.level)
        return combat_formation(centre, size, phase, lambda p: reachability.walkable(p) and reachability.line_of_sight(p, origin, size))

    def latest_sighting(self):
        now = now_ms()
        heard = [m.queen for m in self.party.members(now) if m.trip == self.trip and m.stage == 'fight' and not m.restocking]
        fresh = [s for s in [self.sighting] + heard if s is not None and now - s.at <= 8000 and s.at > self.queen_tracker.killed_at]
        fresh.sort(key=lambda s: -s.at)
        return fresh[0] if fresh else None

    def usable(self, tile):
        return reachability.walkable(tile) and reachability.can_reach(tile, max_steps=2048)

    def search_queen(self, sighting):
        here = game.tile()
        if here is None:
            return
        self.searching = True
        self.blocked = False
        self.lure = None
        if prayer.points() > 0 and not self.protect():
            return
        if self.check_safety():
            return
        target = self.search.next(here, sighting, now_ms(), self.usable)
        self.status = 'searching the last reported queen position' if sighting is not None else 'searching the queen chamber'
        if target is not None:
            step_to(target)

    def body_steps(self, from_, to):
        """Whether the queen's five-wide body can step from from_ to to."""
        for x in range(-2, 3):
            for z in range(-2, 3):
                if not reachability.can_step(Tile(from_.x + x, from_.z + z, from_.level), Tile(to.x + x, to.z + z, to.level)):
                    return False
        return True

    def reposition_queen(self, queen, sighting):
        party = self.party
        controllers = [m for m in party.members(now_ms()) if m.trip == self.trip and m.stage == 'fight' and not m.restocking and m.ready]
        controller = controllers[0] if controllers else None
        leading = controller is None or controller.name == party.self_name
        if not leading and controller.lure is not None and sighting is not None and sighting.engaged:
            self.lure = controller.lure
            self.status = 'following the team pull route'
            step_to(self.lure)
            return
        if queen is None and sighting is not None and sighting.engaged and self.lure is not None and now_ms() - sighting.at < 3000:
            self.status = 'waiting for the queen to follow'
            step_to(self.lure)
            return
        if queen is None or sighting is None:
            self.search_queen(sighting)
            return
        if prayer.points() > 0 and not self.protect():
            return
        if self.check_safety():
            return
        now = now_ms()
        centre = queen.network_tile()
        if leading and (not self.lure_at or not near(self.lure_position, centre, 0)):
            self.lure_position = centre
            self.lure_at = now
        if leading and self.lure_at and now - self.lure_at > 15000:
            self.lure = None
            self.lure_attempt += 1
            self.lure_at = now
        if not sighting.engaged:
            self.lure = None
            self.status = 'approaching and tagging the queen'
            here = game.tile()
            if here is None:
                return
            origin = Tile(centre.x - 2, centre.z - 2, centre.level)
            target = approach_queen(centre, here, lambda p: self.usable(p) and reachability.line_of_sight(p, origin, 5))
            if target is None:
                self.search_queen(None)
                return
            if not near(here, target, 0):
                step_to(target)
                return
            if not self.equip_weapon(BOW):
                return
            if game.combat_mode() != 1:
                game.set_combat_mode(1)
            if game.tick() - self.last_attack >= 4 and queen.interact('Attack'):
                self.last_attack = game.tick()
            return
        if not leading:
            self.lure = None
            self.status = 'waiting for the team pull route'
            return
        if self.lure is None:
            phase = queen_phase(queen.id)
            self.lure = pull_queen(centre, phase, lambda p: self.formation_at(p, 5, phase) is not None, self.body_steps, self.usable, self.lure_attempt)
        if self.lure is None:
            self.search_queen(sighting)
            return
        self.status = 'pulling the queen along an open route'
        self.heartbeat()
        step_to(self.lure)

    # Loot and recovery

    def recover_loot(self):
        party = self.party
        if self.death is not None or not in_lair(game.tile()):
            return False
        deaths = [c for c in party.deaths(self.trip) if c.name != party.self_name and in_lair(c.death.tile)]
        if not deaths:
            return False
        tick = game.tick()
        for c in deaths:
            key = f'{c.name}:{c.session}:{c.death.at}'
            if key not in self.recoveries:
                self.recoveries[key] = Record({'first': tick, 'last': tick, 'done': False})
        casualty = None
        for c in deaths:
            r = self.recoveries[f'{c.name}:{c.session}:{c.death.at}']
            if not r.done and tick - r.first < 60:
                casualty = c
                break
        if casualty is None:
            self.retreat('teammate recovery finished; banking recovered items', True)
            return True
        if inventory.is_full() and inventory.first('Vial') is None:
            self.retreat('no recovery space; banking recovered items', True)
            return True
        collector = None
        for m in party.members(now_ms()):
            if m.trip == self.trip and m.stage == 'fight' and m.ready and m.death is None and (m.recovery_space or 0) > 0 and in_lair(m.tile):
                collector = m
                break
        if collector is None or collector.name != party.self_name:
            return False
        if self.collector.claim() is not None:
            self.collector.clear()
            self.heartbeat()
        recovery = self.recoveries[f'{casualty.name}:{casualty.session}:{casualty.death.at}']
        self.status = f"recovering {casualty.name}'s dropped items"
        if prayer.points() == 0 or not self.protect():
            return True
        if self.check_safety():
            return True
        spot = casualty.death.tile
        if not near(game.tile(), spot, 1):
            step_to(spot)
            return True
        pile = [Record({'id': g.id, 'count': g.count, 'tile': g.tile()}) for g in ground_items.query().results()]
        items = [i for i in recovery_drops(casualty.death, pile) if i.id != VIAL_OF_WATER]
        if not items:
            if tick - recovery.first >= 12 and tick - recovery.last >= 3:
                recovery.done = True
            return True
        recovery.last = tick
        if inventory.is_full():
            vial = inventory.first('Vial')
            if vial is not None:
                vial.interact('Drop')
            else:
                recovery.done = True
            return True
        wanted = items[0].id
        drop = ground_items.query().where(lambda g: g.id == wanted and near(g.tile(), spot, 0)).first()
        if drop is None:
            return True
        before = inventory.count_by_id(drop.id)
        if drop.interact('Take'):
            took = yield from execution.delay_until_ticks(lambda: inventory.count_by_id(wanted) > before, 2)
            if took:
                count = inventory.count_by_id(wanted) - before
                name = drop.name or str(wanted)
                self.recovered_items.append(Record({'owner': casualty.name, 'id': wanted, 'count': count, 'at': now_ms()}))
                key = f'Recovered for {casualty.name}: {name}'
                self.loot_counts[key] = self.loot_counts.get(key, 0) + count
                self.recovery_message = f'recovered {count} {name} for {casualty.name}; banking after recovery'
                self.log(self.recovery_message)
                self.heartbeat()
        return True

    def waiting_for_respawn(self):
        if not self.queen_tracker.killed_at or game.tick() - self.last_kill_tick > 120 or self.latest_sighting() is not None:
            return False
        return npcs.query().where(lambda n: queen_phase(n.id) is not None and (n.health > 0 or n.max_health == 0)).nearest() is None

    def loot(self):
        party = self.party
        previous = self.collector.claim()
        waiting = self.waiting_for_respawn()

        def ready():
            return self.clear_prayers() if waiting else prayer.points() > 0 and self.protect()

        result = self.collector.step(party, self.trip, [c.death.tile for c in party.deaths(self.trip)], ready, self.queue_combat_food, waiting)
        if self.stage == 'retreat':
            return True
        if result.collected is not None:
            self.looted += 1
            name = result.collected.name
            count = result.collected.count
            self.loot_counts[name] = self.loot_counts.get(name, 0) + count
            self.log(f'looted {count} {name}')
        if previous is not self.collector.claim():
            self.heartbeat()
        if result.busy:
            self.last_attack = -10
            claim = self.collector.claim()
            self.status = f"collecting {claim.name if claim is not None else 'queen loot'}"
        return result.busy

    # Leaving

    def back_at_bank(self):
        yield from prayer.clear()
        self.prepared = False
        self.stage = 'bank'
        self.release_out = None
        self.heartbeat()

    def escape(self):
        self.heartbeat()
        if self.death is not None and not in_nest(game.tile()):
            yield from self.back_at_bank()
            return
        here = game.tile()
        if in_nest(here) or (here is not None and here.z < 3117):
            self.status = 'escaping to Camelot'
            yield from self.upkeep()
            if skills.effective('hitpoints') <= max(31, skills.level('hitpoints') - 20) and inventory.count_by_id(FOOD) > 0:
                return
            yield from camelot()
            here = game.tile()
            if in_nest(here) or (here is not None and here.z < 3117):
                return
        if skills.effective('hitpoints') <= 62 and inventory.count_by_id(FOOD) > 0:
            yield from eat()
            return
        if not near(game.tile(), Tile(3315, 3235, 0), 4):
            self.status = 'teleporting to Duel Arena'
            arrived = yield from duel_arena()
            if not arrived:
                return
        yield from self.back_at_bank()

    # Lifecycle and upkeep

    def on_pause(self):
        self.collector.clear()
        self.paused = True
        self.observe_stats()
        self.heartbeat()

    def on_resume(self):
        self.paused = False
        if in_nest(game.tile()):
            self.retreat('resumed after party pause')

    def on_stop(self, reason):
        self.collector.clear()
        self.restocking = self.death is not None
        self.stage = 'retreat'
        if self.party is not None:
            self.heartbeat()
        sustain.set(None)
        event_signal.set_interrupt(None)

    def recovery_anchor(self):
        return None

    def ignored_randoms(self):
        return IGNORED_IN_NEST if in_nest(game.tile()) or self.stage == 'retreat' else []

    def on_progress_report(self):
        minutes = (now_ms() - self.started_at) / 60000
        gained = sum([skills.xp(s) for s in COMBAT_SKILLS]) - self.xp_at_start
        queen = queen_npc()
        report = {
            'Status': self.status,
            'Slot': SIDES[self.slot],
            'Trip': self.trip,
            'Kills': self.kills,
            'Trip kills': self.trip_kills,
            'Retreats': self.retreats,
            'Last kill': f'{round(self.last_kill_ms / 1000)}s' if self.last_kill_ms else '-',
            'DPS': f'{self.stats.dps():.2f}',
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
            'Looted': ', '.join([f'{n} x{c}' for n, c in self.loot_counts.items()]) or '-',
            'Team': ', '.join([f'{m.name} {m.stage}' for m in self.party.members(now_ms())]) if self.party is not None else '-',
        }
        if queen is not None and queen.max_health:
            report['Queen'] = f'{queen_phase(queen.id)} {queen.health}/{queen.max_health}'
        return report


BOT = define_bot(
    name='JiveKQ',
    create=JiveKQ,
    description='Four-player Kalphite Queen trips with a shared dragon mace and magic shortbow loadout, synchronized ropes, a four-point cross, repeated kills and group retreats.',
    category='Combat',
    tags=['combat', 'boss', 'kalphite', 'group', 'banking'],
    settings_schema=SETTINGS,
)

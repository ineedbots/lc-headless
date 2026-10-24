"""The fight on a site: the Fight, Retreat, HoldSafespot and WalkToSpot tasks over a combat host. Ported from
rs2b0t's api/combat/hunting/combat.ts (MIT, see thirdparty/rs2b0t).

The host is the bot, a CombatHost in rs2b0t: what rs2004.hunting.supply needs, and died, target_idx,
count_kill(), count_burial(), hp_fraction(), panic_hp(), retreat_hp(), has_food(), need_eat(), eat_once() (with
yield from), bury_bones(), bone_name(), safespot_index() and set_safespot_index(n). It may have fight (its Fight
task), rotate_spawns(), shield_ready() and arm_special() (with yield from) too."""

import _core
from rs2004 import execution
from rs2004.bot import Task
from rs2004.catalogs.combat import bury_one_in_fight
from rs2004.geometry import Tile
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, facing_player, game, skills
from rs2004.navigation import reachability
from rs2004.traversal import traversal
from rs2004.hunting.logic import SAFESPOT_BLIND_MS, body_origin, chase_mode, engage_range_for, gap_to, hold_due, hurt_on_spot
from rs2004.hunting.logic import next_safespot, note_sighting, retreat_aim, retreat_due, settled
from rs2004.hunting.sites import GUTANOTH_BLUE, HEROES_BLUE, TAVERLEY_BLACK, TAVERLEY_BLUE, hunt_names
from rs2004.hunting.supply import wait_fed, walk_approach

__all__ = ['anchor_for', 'chases_target', 'Fight', 'Retreat', 'HoldSafespot', 'WalkToSpot']

ATTACK = 'Attack'

FIELD_RADIUS = 10
APPROACH_RADIUS = 12

FIGHT_MS = 120000
FIGHT_PASSES = 600
LEASH_MS = 12000
LEASH_PASSES = 60

RE_ENGAGE_MS = 4000
ENGAGE_SETTLE_MS = 1200
KILL_GRACE_MS = 6000
# Why: a dragon standing where the tiles beside it are rock takes the click, walks the bot to the nearest tile it
# can reach and never gets a swing; a minute fired once on a live fight in a dry spell, and ninety seconds is
# thirty swings, one fight in a thousand at a quarter hit chance.
CHASE_STALL_MS = 90000
CHASE_SKIP_MS = 90000

TAKEN_SKIP_MS = 15000
LEASH_SKIP_MS = 20000
PULL_SKIP_MS = 8000
REFUSED_SKIP_MS = 5000

HOP_ATTEMPTS = 4
HOP_MS = 2000
RETURN_MS = 60000
APPROACH_MS = 120000

# A gap this long between two of Fight's own polls is time the bot spent somewhere other than the tile.
HOLD_GAP_MS = 10000
# How often an empty field with adults in the scene is explained, one line, to vlog.
FIELD_DIAG_MS = 10000
FIELD_DIAG_RADIUS = 16

# How long a body must hold its tile before a safespot style clicks it.
SETTLE_MS = 1200
# A stalled target is clicked again every few seconds, so only one line in this many says so.
REISSUE_LOG_EVERY = 10

RETREAT_HOPS = 4
RETREAT_HOP_MS = 3000
RETREAT_RETRY_MS = 5000


def _now():
    return _core.step_time()


def _optional(host, name):
    """One of the host's optional methods, or None."""
    return getattr(host, name, None)


def _vlog(host, message):
    vlog = _optional(host, 'vlog')
    if vlog is not None:
        vlog(message)


def _shield_down(host):
    shield_ready = _optional(host, 'shield_ready')
    return shield_ready is not None and shield_ready() == False


def _arm_special(host):
    arm = _optional(host, 'arm_special')
    if arm is not None:
        yield from arm()


def _interrupt_fight(host):
    fight = _optional(host, 'fight')
    if fight is not None:
        fight.interrupt_watch()


def _fight_has_chase_target(host):
    fight = _optional(host, 'fight')
    return fight is not None and fight.has_chase_target()


def _rotates_spawns(host):
    rotate = _optional(host, 'rotate_spawns')
    return rotate is not None and rotate() == True


# Why: an npc's face target clears between its own attacks, so a dragon another player is mid-fight with reads as
# free for a tick, and "in combat but not facing us" closes that gap.
# Why: our own target is exempt, since its face target flickers the same way and dropping it would churn targets
# every few ticks.
def _taken_by_another(is_ours, in_combat, targets_me, targets_another):
    """Whether a dragon already belongs to someone else's fight."""
    if is_ours:
        return False
    return targets_another or (in_combat and not targets_me)


def anchor_for(site, style, index):
    """The tile a style fights from: the melee anchor, or the safespot at index."""
    if style == 'melee':
        return site.melee_anchor
    # Why: next_safespot holds its index unclamped, so the clamp lives here where the tile is read.
    if len(site.safespots) == 0:
        return site.melee_anchor
    return site.safespots[min(index, len(site.safespots) - 1)]


def _uses_safespot(style):
    return style != 'melee'


_BLUE_SITES = [TAVERLEY_BLUE.key, HEROES_BLUE.key, GUTANOTH_BLUE.key]


def chases_target(site, style):
    """Whether the style walks to its target here rather than holding a tile."""
    return chase_mode(style, site.fire_at_range == True or site.key in _BLUE_SITES)


def _holds_anchor(site, style):
    return not chases_target(site, style)


def _spot_name(style, index):
    return f'safespot {index}' if _uses_safespot(style) else 'the melee anchor'


def _label(site):
    return site.target.lower()


def _at_tile(t):
    here = game.tile()
    return here is not None and here.x == t.x and here.z == t.z and here.level == t.level


def _skipped_until(skip, index):
    until = skip.get(index)
    return until if until is not None else 0


# Why: the server walks an Attack click until it has line of sight, and a safespot sees a body in only some of the
# places it wanders, so a target the tile can't see is a walk off the tile.
def _sighted_from(spot, n):
    """Whether an Attack click from spot at this body fires without the server walking closer."""
    o = body_origin(n.network_tile(), n.size)
    return reachability.line_of_sight(spot, Tile(o.x, o.z, spot.level), n.size)


# Why: the query's name match is exact, so 'Baby blue dragon' never matches 'Blue dragon' and the babies stay
# untargeted.
def _huntable_near(site, name, ours, radius, from_):
    def huntable(n):
        if from_ is None:
            near = n.distance() <= radius and site.in_area(n.tile())
        else:
            near = gap_to(from_, n.network_tile(), n.size) <= radius and site.in_area(n.network_tile()) and _sighted_from(from_, n)
        return near and not _taken_by_another(n.index == ours, n.in_combat, n.targets_me(), n.targets_another_player())

    return npcs.query().name(name).action(ATTACK).where(huntable).results()


# Why: the stand is idle while its dragon respawns, so the filler is taken then and only then, or it would trade the
# drop the trip is for. One already engaged stays in the field though: a greater demon on 87 health dropped the
# moment a dragon respawns heals back before the next lull and is never killed. A filler that's biting us stays in
# too, since losing a metal dragon's aggro is harder than killing it and auto retaliate is already hitting it.
def _adults_near(site, ours, radius, from_):
    """Adults inside radius that no other player is fighting and that from_ can see: the target's own, plus a
    filler already being fought or biting us, and the rest of the filler only when the target isn't up."""
    primary = _huntable_near(site, site.target, ours, radius, from_)
    if not site.also_hunt:
        return primary
    filler = []
    for name in site.also_hunt:
        filler.extend(_huntable_near(site, name, ours, radius, from_))
    if len(primary) == 0:
        return filler
    engaged = [n for n in filler if n.index == ours or n.targets_me()]
    return engaged + primary


# Why: auto retaliate swings the casts to whatever bit us last, and a loop that keeps clicking the dragon it chose
# fights its own client; the face target is the one thing the client says about who we're hitting, so the loop
# follows it and the kill is counted under that dragon.
def _retaliation_target(site):
    """The huntable npc our own character is facing, when auto retaliate has picked one."""
    face = game.facing()
    if face is None or facing_player(face):
        return None
    names = hunt_names(site)
    for n in npcs.all():
        if n.index == face[1] and (n.name or '') in names:
            return n
    return None


def _still_there(idx, name):
    for n in npcs.all():
        if n.index == idx and (n.name or '').lower() == name:
            return True
    return False


def _dying(n):
    return n.health == 0 and n.max_health > 0


def _on_any_safespot(site):
    for spot in site.safespots:
        if _at_tile(spot):
            return True
    return False


def _retreat_needed(host, site):
    """Whether to break off and heal on a safespot rather than where the bot stands."""
    here = game.tile()
    return here is not None and retreat_due(site.in_area(here), _on_any_safespot(site), host.hp_fraction(), host.retreat_hp(),
                                            host.has_food(), len(site.safespots))


def _first(items, test):
    for item in items:
        if test(item):
            return item
    return None


class Fight(Task):
    """Holds the fight tile and kills what the site hunts: the safespot ladder for mage and range, the melee
    anchor or a chase for melee."""

    def __init__(self, host, site):
        Task.__init__(self, label='fight')
        self.host = host
        self.site = site
        self.engaged = None
        self.killed_spawns = {}
        self.kills = 0
        self.loot_target = None
        # What the engaged npc is called, so a site that fills downtime names the thing it killed.
        self.engaged_name = ''
        self.seen_at = 0
        self.engaged_at = 0
        self.engaged_health = -1
        self.last_hp = -1
        self.watched_anchor = None
        self.unattackable_since = None
        self.blind_since = 0
        self.polled_at = 0
        self.diag_at = 0
        self.biter_noted_at = 0
        self.reclicked_at = 0
        # When the engaged dragon last lost health under the loop's eye, or was first engaged.
        self.damaged_at = 0
        self.reissues = 0
        self.skip = {}
        self.seen = {}

    def blocks_loot(self):
        if not game.scene_ready():
            return True
        if self.engaged is not None:
            return True
        if self.loot_target is not None and not _still_there(self.loot_target, self.engaged_name or _label(self.site)):
            self.loot_target = None
        return self.loot_target is not None

    def has_chase_target(self):
        if not chases_target(self.site, self.host.style()):
            return False
        now = _now()
        return _first(self._field(FIELD_RADIUS), lambda n: _skipped_until(self.skip, n.index) < now and not _dying(n)) is not None

    def reset(self):
        self._clear_target()
        self.loot_target = None
        self.interrupt_watch()

    def interrupt_watch(self):
        self.last_hp = -1
        self.watched_anchor = None
        self.unattackable_since = None
        self.blind_since = _now()

    def validate(self):
        if _shield_down(self.host):
            return False
        on_spot = _at_tile(self._anchor())
        self._watch(on_spot)
        if not self.site.in_area(game.tile()) or self.host.hp_fraction() < self.host.panic_hp():
            return False
        if _holds_anchor(self.site, self.host.style()) and not on_spot:
            return False
        return self.engaged is not None or len(self._field(FIELD_RADIUS)) > 0 or self._alternate() is not None or self._blind_due()

    # Why: the blind clock belongs to the tile the bot stands on, and this task is skipped whenever anything above
    # it runs, so a long gap between polls is time spent walking in, looting or banking, not time the tile showed
    # nothing.
    def _watch(self, on_spot):
        """Stamps the poll, restarting the blind clock unless the bot has been on the tile since the last one."""
        now = _now()
        anchor = self._anchor()
        if not on_spot or self.watched_anchor is None or not self.watched_anchor.equals(anchor) or now - self.polled_at > HOLD_GAP_MS:
            self.interrupt_watch()
        self.watched_anchor = anchor if on_spot else None
        self.polled_at = now

    # Why: the ladder only turns inside execute(), so a spot that sees nothing at all would never rotate if an empty
    # field kept the task from running.
    def _blind_due(self):
        """Whether the safespot has gone blind long enough to owe a rotation."""
        return _uses_safespot(self.host.style()) and len(self.site.safespots) > 1 and _now() - self.blind_since >= SAFESPOT_BLIND_MS

    def execute(self):
        host = self.host
        site = self.site
        style = host.style()
        name = _label(site)
        host.set_status(f'fighting {name}s')
        deadline = _now() + FIGHT_MS
        for _ in range(FIGHT_PASSES):
            if _now() >= deadline:
                return
            if not game.scene_ready() or event_signal.pending() or host.died or chat_dialog.can_continue() or _shield_down(host):
                self.interrupt_watch()
                return
            # Why: eating in dragonfire loses the race, so the fight hands the loop back at the retreat line, as the
            # task order puts Retreat above Eat.
            # Why: need_eat is false with an empty pack, so gating on it alone kept a foodless fight running for the
            # 5s that killed a live run.
            if (not host.has_food() or host.need_eat()) and _retreat_needed(host, site):
                return
            # Why: on a site that breathes at the tile an empty pack is hp draining with nothing to stop it, so the
            # fight hands back at once and the bank run above it fires with the hp still there.
            if site.ranged_threat == True and not host.has_food():
                return
            # Why: an eat that never lands means an empty pack, and looping on it burns every pass without pumping
            # sustain or reaching the panic check below.
            if host.need_eat():
                ate = yield from host.eat_once()
                if not ate:
                    return
            if host.hp_fraction() < host.panic_hp():
                return
            step = yield from self._ladder()
            if step == 'stuck':
                return
            if step == 'moved':
                continue
            # Why: a kill yields to the higher-priority loot tasks before another dragon is taken on.
            if self._settle_kill(name):
                return
            if _holds_anchor(site, style) and not _at_tile(self._anchor()):
                back = yield from self._walk_back()
                if not back:
                    return

            if site.key == TAVERLEY_BLUE.key and style == 'range' and self.engaged is not None:
                if _first(self._field(FIELD_RADIUS), lambda n: n.index == self.engaged) is not None:
                    self.unattackable_since = None
                else:
                    if self.unattackable_since is None:
                        self.unattackable_since = _now()
                    if _now() - self.unattackable_since >= SAFESPOT_BLIND_MS:
                        self.skip[self.engaged] = _now() + LEASH_SKIP_MS
                        self._clear_target()
            field = self._field(FIELD_RADIUS)
            # Why: rs2b0t takes the biter only on the blue sites, but Brimhaven is single combat too, and a metal dragon
            # breathing from ten tiles made every click on the chosen one "I'm already under attack!" for the 90s
            # the stall skip takes: one kill in 25 minutes live.
            if (site.key in _BLUE_SITES or site.fire_at_range == True) and style == 'melee':
                dying = _first(field, lambda n: n.index == self.engaged and _dying(n))
                if dying is not None:
                    yield from self._idle()
                    continue
                attacker = _first(field, lambda n: n.index == self.engaged and n.targets_me())
                if attacker is None:
                    attacker = _first(field, lambda n: n.targets_me())
                if attacker is not None and attacker.index != self.engaged:
                    self.skip.pop(attacker.index, None)
                    engaged = yield from self._engage(attacker, name)
                    if engaged:
                        continue
            for n in field:
                self.seen[n.index] = note_sighting(self.seen.get(n.index), n.network_tile() if _uses_safespot(style) else n.tile(), _now())
            facing = _retaliation_target(site)
            # Why: a chase runs with retaliate off, so the face is always its own target, and adopting it took back a
            # dragon the stall skip had dropped.
            if _holds_anchor(site, style) and facing is not None and facing.index != self.engaged:
                gap = gap_to(self._anchor(), facing.network_tile() if _uses_safespot(style) else facing.tile(), facing.size)
                # Why: a biter the field holds is one the loop can fight from the tile; one it doesn't, parked a tile
                # past the radius, walks the bot off if the client is left chasing it, so the engaged dragon is
                # clicked again at once to cancel the walk.
                if _first(field, lambda n: n.index == facing.index) is not None:
                    shown = (facing.name or name).lower()
                    host.log(f'retaliating at {shown} {facing.index} at {facing.tile()} (gap {gap}), so it is the target now')
                    self.engaged_name = shown
                    self.reissues = 0
                    self._set_target(facing.index)
                    self.engaged_health = -1
                else:
                    mine = None if self.engaged is None else _first(field, lambda n: n.index == self.engaged)
                    # Why: a fresh Attack click restarts the swing, and one every pass never let a cast finish: 140
                    # clicks in six minutes landed nothing. The click back waits out the engage cadence.
                    if mine is not None and _now() - self.reclicked_at >= RE_ENGAGE_MS:
                        self.reclicked_at = _now()
                        if _now() - self.biter_noted_at > FIELD_DIAG_MS:
                            self.biter_noted_at = _now()
                            _vlog(host, f'{(facing.name or name).lower()} {facing.index} bites from gap {gap}, beyond reach; '
                                        + f'clicking {self.engaged_name} {mine.index} back')
                        yield from self._engage(mine, name)
                        continue
            live = None
            if self.engaged is not None:
                live = _first(field, lambda n: n.index == self.engaged)
                if live is None and facing is not None and facing.index == self.engaged:
                    live = facing
            if live is not None and live.targets_another_player():
                host.log(f'{name} {live.index} was taken by another player. Finding another.')
                self.skip[live.index] = _now() + TAKEN_SKIP_MS
                self._clear_target()
                continue
            # Why: our own combat bar never lights up while safespotting, so a changing target health is the only
            # proof the attack landed.
            if live is not None:
                if live.health != self.engaged_health:
                    # Why: a click again clears the health it knew and restarts the engage clock, so only a drop the
                    # loop watched counts as damage.
                    if self.engaged_health != -1 and live.health < self.engaged_health:
                        self.damaged_at = _now()
                    self.engaged_health = live.health
                    self.engaged_at = _now()
                if not _holds_anchor(site, style) and _now() - self.damaged_at > CHASE_STALL_MS:
                    here = game.tile()
                    where = f'({here.x}, {here.z})' if here is not None else '(?)'
                    host.log(f'{self.engaged_name or name} {live.index} took no damage for {CHASE_STALL_MS // 1000}s from {where}, so '
                             + f'there is no way in beside it. Skipping it for {CHASE_SKIP_MS // 1000}s.')
                    self.skip[live.index] = _now() + CHASE_SKIP_MS
                    self._clear_target()
                    continue
                if _now() - self.engaged_at < RE_ENGAGE_MS:
                    # Why: the energy comes back mid-fight and only a click used to arm it, so a long fight spent one
                    # special; armed here, the next swing or shot takes it.
                    yield from _arm_special(host)
                    yield from self._idle()
                    continue

            now = _now()
            # Why: with two dragons in view the nearest changes as they shuffle, and a pick that follows it splits the
            # casts between them; the one already engaged keeps the fight until it's down or gone.
            target = None
            if self.engaged is not None:
                target = _first(field, lambda n: n.index == self.engaged and _skipped_until(self.skip, n.index) < now)
            if target is None:
                rotates = _rotates_spawns(host)
                holds = _holds_anchor(site, style)
                choices = [n for n in field if _skipped_until(self.skip, n.index) < now
                           and (not _uses_safespot(style) or self._in_reach(n) or settled(self.seen.get(n.index), now, SETTLE_MS))]

                def rank(n):
                    kills = self.killed_spawns.get(n.index, 0) if rotates else 0
                    reach = (0 if self._in_reach(n) else 1) if holds else 0
                    return (kills, reach, n.distance())

                choices.sort(key=rank)
                target = choices[0] if choices else None
            if target is None:
                self._explain_empty_field(now)
                yield from self._idle()
                return
            if _holds_anchor(site, style) and not self._in_reach(target):
                closed = yield from self._leash(target.index)
                if not closed:
                    self.skip[target.index] = now + LEASH_SKIP_MS
                continue
            engaged = yield from self._engage(target, name)
            if not engaged:
                continue
            if _holds_anchor(site, style) and not _at_tile(self._anchor()):
                self.skip[target.index] = _now() + PULL_SKIP_MS
                host.log(f'{name} {target.index} pulled us off {_spot_name(style, host.safespot_index())}. Skipping it for {PULL_SKIP_MS // 1000}s.')
                self._clear_target()

    def _anchor(self):
        return anchor_for(self.site, self.host.style(), self.host.safespot_index())

    def _alternate(self):
        """On the black dragons' corridor, the index of a safespot with a dragon in reach when this one has none."""
        if self.site.key != TAVERLEY_BLACK.key or self.host.style() != 'range' or not _at_tile(self._anchor()) or self.blocks_loot():
            return None

        def ready(spot):
            now = _now()
            for n in _adults_near(self.site, None, FIELD_RADIUS, spot):
                if gap_to(spot, n.network_tile(), n.size) <= engage_range_for('range') and _skipped_until(self.skip, n.index) < now:
                    return True
            return False

        if ready(self._anchor()):
            return None
        anchor = self._anchor()
        options = []
        for index, spot in enumerate(self.site.safespots):
            if _first(TAVERLEY_BLACK.safespots, lambda existing: existing.equals(spot)) is not None and ready(spot):
                options.append((spot.distance_to(anchor), index))
        options.sort()
        return options[0][1] if options else None

    # Why: the Brimhaven run stood a dragon's breath away from one for two minutes with no engage line, and nothing
    # said which filter was dropping it; the lines are joined so one says it all.
    def _explain_empty_field(self, now):
        """One vlog line naming every adult near the stand and which of the field's filters it fails."""
        if _optional(self.host, 'vlog') is None or now - self.diag_at < FIELD_DIAG_MS:
            return
        self.diag_at = now
        spot = self._anchor()
        names = hunt_names(self.site)
        near = npcs.query().where(lambda n: (n.name or '') in names).within(FIELD_DIAG_RADIUS).results()
        if len(near) == 0:
            return
        yes = lambda b: 'y' if b else 'n'
        rows = []
        for n in near:
            t = n.network_tile() if _uses_safespot(self.host.style()) else n.tile()
            rows.append(f'{n.index}@{t.x},{t.z} gap {gap_to(spot, t, n.size)} sight {yes(_sighted_from(spot, n))} combat {yes(n.in_combat)} '
                        + f'me {yes(n.targets_me())} other {yes(n.targets_another_player())} settled {yes(settled(self.seen.get(n.index), now, SETTLE_MS))} '
                        + f'skip {yes(_skipped_until(self.skip, n.index) > now)}')
        self.host.vlog(f'no target from {spot}: ' + ' | '.join(rows))

    def _field(self, radius):
        style = self.host.style()
        if self.site.key == TAVERLEY_BLUE.key and style == 'range':
            now = _now()
            return [n for n in _adults_near(self.site, self.engaged, min(radius, engage_range_for('range')), self._anchor())
                    if (self.engaged is None or n.index == self.engaged) and _skipped_until(self.skip, n.index) < now]
        reach = 1000000 if _rotates_spawns(self.host) else radius
        adults = _adults_near(self.site, self.engaged, reach, self._anchor() if _uses_safespot(style) else None)
        if style == 'melee':
            if self.site.key == TAVERLEY_BLUE.key:
                names = ['Baby blue dragon']
            elif self.site.key == GUTANOTH_BLUE.key:
                names = ['Blue dragon', 'Greater demon', 'Ogre chieftain']
            else:
                names = []
            hunted = hunt_names(self.site)
            defenders = []
            for other in names:
                if other in hunted:
                    continue
                defenders.extend([n for n in _huntable_near(self.site, other, self.engaged, radius, None) if n.index == self.engaged or n.targets_me()])
            return defenders + adults
        return adults

    def _in_reach(self, n):
        """Whether an Attack click from the anchor lands without the server walking the bot closer."""
        style = self.host.style()
        return gap_to(self._anchor(), n.network_tile() if _uses_safespot(style) else n.tile(), n.size) <= engage_range_for(style)

    def _set_target(self, idx):
        if idx != self.engaged:
            self.damaged_at = _now()
            self.unattackable_since = None
        self.engaged = idx
        self.loot_target = idx
        self.host.target_idx = idx
        self.seen_at = _now()

    def _clear_target(self):
        self.engaged = None
        self.unattackable_since = None
        self.reissues = 0
        self.host.target_idx = None
        self.engaged_health = -1

    # Why: a target index that vanished while the loop was away at the bank is a respawn, not a kill, so a vanish
    # only counts near the last sighting.
    def _settle_kill(self, name):
        """True when the engagement ended, a stale disappearance included."""
        if self.engaged is None:
            return False
        shown = self.engaged_name or name
        if _still_there(self.engaged, shown):
            self.seen_at = _now()
            return False
        if _now() - self.seen_at < KILL_GRACE_MS:
            self.kills += 1
            self.killed_spawns[self.engaged] = self.kills
            if shown in [target.lower() for target in hunt_names(self.site)]:
                self.host.count_kill()
            self.host.log(f'{shown} {self.engaged} down')
        self.reset()
        return True

    # Why: the safespots are derived as melee-proof, so a hit landing there means the derivation missed an angle,
    # and a blind stretch means a dragon body is parked across it.
    def _ladder(self):
        """Advances the safespot ladder, walking onto the new tile when it turns: 'held', 'moved' or 'stuck'."""
        style = self.host.style()
        hp = skills.effective('hitpoints')
        on_spot = _at_tile(self._anchor())
        self._watch(on_spot)
        hurt = hurt_on_spot(self.site.ranged_threat == True, on_spot, self.last_hp, hp)
        self.last_hp = hp if on_spot else -1
        if not _uses_safespot(style):
            return 'held'
        index = self.host.safespot_index()
        alternate = self._alternate()
        if alternate is not None:
            self.host.set_safespot_index(alternate)
            self.blind_since = _now()
            back = yield from self._walk_back()
            return 'moved' if back else 'stuck'
        if not hurt and style == 'range' and self.site.key in [TAVERLEY_BLACK.key, TAVERLEY_BLUE.key] and self.blocks_loot():
            return 'held'
        if _first(self._field(FIELD_RADIUS), lambda n: self._in_reach(n)) is not None:
            self.blind_since = _now()
        blind_ms = _now() - self.blind_since
        following = next_safespot(index, len(self.site.safespots), hurt, blind_ms)
        if following == index:
            return 'held'
        self.host.set_safespot_index(following)
        # Why: resetting the clock with the index stops one rotation from tripping the next on the same pass.
        self.blind_since = _now()
        self.skip = {}
        why = 'a hit landed' if hurt else f'nothing in range for {SAFESPOT_BLIND_MS // 1000}s'
        self.host.log(f'rotating to safespot {following} at {anchor_for(self.site, style, following)} ({why})')
        back = yield from self._walk_back()
        return 'moved' if back else 'stuck'

    # Why: the walker's arrival accepts the closest reachable point, so an exact stand is only proved by reading the
    # position back.
    def _walk_back(self):
        """Hops onto the current anchor. False hands the walk to HoldSafespot."""
        spot = self._anchor()
        if _at_tile(spot):
            return True
        self.interrupt_watch()
        where = _spot_name(self.host.style(), self.host.safespot_index())
        self.host.set_status(f'returning to {where}')
        for _ in range(HOP_ATTEMPTS):
            if _at_tile(spot) or event_signal.pending():
                break
            direct_navigator.walk(spot)
            arrived = yield from wait_fed(lambda: _at_tile(spot), HOP_MS)
            if arrived:
                break
        if _at_tile(spot):
            return True
        self.host.log(f'could not stand on {where} at {spot}. Handing back to the walk-back task.')
        return False

    # Why: clicking Attack from beyond weapon range makes the server walk us into range, which steps off the
    # safespot.
    def _leash(self, idx):
        """Holds the tile while the dragon closes. False means it never did."""
        name = _label(self.site)
        self.host.set_status(f'waiting for {name} {idx} to close')
        # Why: the outline follows what the loop waits on while engaged stays with the dragon we clicked Attack on,
        # so a leash that ends in someone else's kill can't score one.
        self.host.target_idx = idx
        deadline = _now() + LEASH_MS
        for _ in range(LEASH_PASSES):
            if _now() >= deadline:
                break
            if event_signal.pending() or self.host.died or chat_dialog.can_continue():
                return True
            if self.host.need_eat():
                ate = yield from self.host.eat_once()
                if not ate:
                    return True
            if self.host.hp_fraction() < self.host.panic_hp():
                return True
            step = yield from self._ladder()
            if step != 'held':
                return True
            if not _at_tile(self._anchor()):
                back = yield from self._walk_back()
                if not back:
                    return True
            field = self._field(FIELD_RADIUS)
            now = _now()
            if self.engaged is None and _first(field, lambda n: n.index != idx and self._in_reach(n) and _skipped_until(self.skip, n.index) < now) is not None:
                self.host.target_idx = None
                return True
            dragon = _first(field, lambda n: n.index == idx)
            if dragon is None or self._in_reach(dragon):
                return True
            yield from self._idle()
        self.host.target_idx = self.engaged
        return False

    def _current(self, target):
        return _first(self._field(FIELD_RADIUS), lambda n: n.index == target.index and n.id == target.id and n.name == target.name)

    def _engage(self, target, name):
        """Sends the attack and watches for the drag off the safespot. False means the click was refused."""
        host = self.host
        style = host.style()
        if _shield_down(host):
            return False
        if chases_target(self.site, style) and not reachability.can_reach(target.tile()):
            reached = yield from traversal.walk_resilient(target.tile(), radius=1, attempts=3, timeout_ms=APPROACH_MS, log=lambda m: _vlog(host, m))
            if not reached:
                self.skip[target.index] = _now() + CHASE_SKIP_MS
                return False
            current = self._current(target)
            if current is None or current.targets_another_player() or not reachability.can_reach(current.tile()) or event_signal.pending() \
                    or host.died or not host.has_food():
                return False
            target = current
        yield from _arm_special(host)
        if _shield_down(host):
            return False
        current = self._current(target) if _uses_safespot(style) or chases_target(self.site, style) else target
        if current is None or not game.scene_ready() or event_signal.pending() or host.died or current.targets_another_player() \
                or (_uses_safespot(style) and (not _at_tile(self._anchor()) or not self._in_reach(current) or _skipped_until(self.skip, current.index) > _now())):
            yield from self._idle()
            return False
        # Why: a site that fills downtime kills more than one kind of thing, and a line naming the site's target for
        # all of them reads as the dragon being fought when it's the demon.
        shown = (target.name or name).lower()
        self.engaged_name = shown
        # Why: a target whose defence roll dwarfs the attack roll shows no health change for minutes, so the click
        # again runs every few seconds and its line would crowd out everything else.
        if target.index == self.engaged:
            self.reissues += 1
            if self.reissues == 1 or self.reissues % REISSUE_LOG_EVERY == 0:
                host.log(f'{shown} {target.index} stalled. Re-issuing the attack ({self.reissues} so far).')
        else:
            self.reissues = 0
            tile = current.network_tile() if _uses_safespot(style) else current.tile()
            host.log(f'engaging {shown} {target.index} at {tile} (gap {gap_to(self._anchor(), tile, current.size)})')
        if not current.interact(ATTACK):
            self.skip[target.index] = _now() + REFUSED_SKIP_MS
            host.log(f'{name} {target.index} refused the attack click. Skipping it for {REFUSED_SKIP_MS // 1000}s.')
            yield from self._idle()
            return False
        self._set_target(target.index)
        self.engaged_at = _now()
        self.engaged_health = -1
        yield from wait_fed(lambda: (_holds_anchor(self.site, style) and not _at_tile(self._anchor())) or len(self._field(FIELD_RADIUS)) == 0,
                            ENGAGE_SETTLE_MS)
        return True

    # Why: sustain is call-driven and a safespotting bot never walks, so an idle tick that skips it is a tick the
    # bot can't eat on.
    def _idle(self):
        """Spends one idle tick, feeding the sustain hook and burying a bone in the swing cooldown."""
        yield from sustain.run()
        if self.host.bury_bones():
            buried = yield from bury_one_in_fight(self.host.bone_name())
            if buried:
                self.host.count_burial()
                return
        yield from execution.delay_ticks(1)


# Why: this sits above Eat in the task list, since Eat validates until hp reaches its heal line and would otherwise
# hold the loop for every bite of a heal the dragonfire outpaces.
class Retreat(Task):
    """Walks out of the fire onto a safespot, where the heal or the walk to the bank then starts."""

    def __init__(self, host, site):
        Task.__init__(self, label='retreat')
        self.host = host
        self.site = site
        self.retry_at = 0
        self.rotated = None

    def validate(self):
        return _now() >= self.retry_at and _retreat_needed(self.host, self.site)

    def execute(self):
        host = self.host
        _interrupt_fight(host)
        here = game.tile()
        if here is None:
            return
        index, following = retreat_aim(self.rotated, here, self.site.safespots)
        self.rotated = None
        spot = self.site.safespots[index]
        # Why: the ladder reads this to pick the fight tile, so the run resumes on the tile it ran to rather than
        # walking back out to the old one.
        host.set_safespot_index(index)
        host.set_status(f'retreating to safespot {index}')
        empty = '' if host.has_food() else ' with an empty pack'
        host.log(f'retreating to safespot {index} at {spot} from {here.x},{here.z} at {round(host.hp_fraction() * 100)}% hp{empty}')
        # Why: the supervisor pauses the script for a random event, so yielding before the first hop leaves the bot
        # in the fire for all of it. One click goes out, then the loop hands over.
        for _ in range(RETREAT_HOPS):
            if _at_tile(spot):
                break
            if host.died:
                return
            direct_navigator.walk(spot)
            arrived = yield from wait_fed(lambda: _at_tile(spot), RETREAT_HOP_MS)
            if arrived or event_signal.pending():
                return
        if _at_tile(spot):
            return
        # Why: this task outranks Eat, so a tile a dragon body or another player sits on would hold the loop with no
        # bite taken, and the next tile in the ladder is a working fight spot.
        host.set_safespot_index(following)
        self.rotated = following
        self.retry_at = _now() + RETREAT_RETRY_MS
        then = 'Eating where we stand' if host.has_food() else 'Handing to the bank run'
        host.log(f'could not reach safespot {index} at {spot}. {then} and trying {following} in {RETREAT_RETRY_MS // 1000}s.')


class HoldSafespot(Task):
    """Walks back onto the fight tile when the bot is off it."""

    def __init__(self, host, site):
        Task.__init__(self, label='hold safespot')
        self.host = host
        self.site = site

    def validate(self):
        host = self.host
        # Why: a chase stands beside its dragon through the fight's hand-backs, and this task walked it home at
        # every one, a six-second round trip and a restarted swing each time.
        chasing = not _holds_anchor(self.site, host.style()) and host.target_idx is not None
        return self.site.in_area(game.tile()) \
            and not chasing \
            and not _fight_has_chase_target(host) \
            and not _at_tile(self._spot()) \
            and hold_due(_on_any_safespot(self.site), host.has_food()) \
            and host.hp_fraction() >= host.panic_hp()

    def execute(self):
        host = self.host
        _interrupt_fight(host)
        style = host.style()
        index = host.safespot_index()
        spot = self._spot()
        host.set_status(f'returning to {_spot_name(style, index)}')
        yield from traversal.walk_resilient(spot, radius=0, attempts=4, timeout_ms=RETURN_MS, log=lambda m: host.log(f'  {m}'))
        if _at_tile(spot):
            return
        # Why: an occupied or unreachable tile would otherwise be tried forever, and the next tile in the ladder is a
        # working fight spot.
        spots = len(self.site.safespots)
        following = (index + 1) % spots if _uses_safespot(style) and spots > 1 else index
        rotating = '' if following == index else f'. Rotating to {following}'
        host.log(f'{_spot_name(style, index)} at {spot} could not be reached{rotating}.')
        host.set_safespot_index(following)

    def _spot(self):
        return anchor_for(self.site, self.host.style(), self.host.safespot_index())


class WalkToSpot(Task):
    """Walks in from wherever the bot is in the lair to the fight tile."""

    def __init__(self, host, site):
        Task.__init__(self, label='walk to spot')
        self.host = host
        self.site = site

    def validate(self):
        host = self.host
        here = game.tile()
        # Why: a chase stands beside its dragon, tiles off the camp, and this task sits above Fight, so a live target
        # holds it or every pass walked the bot out of its own fight.
        chasing = not _holds_anchor(self.site, host.style()) and host.target_idx is not None
        return here is not None \
            and self.site.in_area(here) \
            and not chasing \
            and not _fight_has_chase_target(host) \
            and host.hp_fraction() >= host.panic_hp() \
            and self._anchor().distance_to(here) > APPROACH_RADIUS

    def execute(self):
        host = self.host
        _interrupt_fight(host)
        host.set_status('walking to the fight spot')
        spot = self._anchor()
        yield from walk_approach(host, self.site, spot)
        yield from traversal.walk_resilient(spot, radius=0, attempts=5, timeout_ms=APPROACH_MS, log=lambda m: host.log(f'  {m}'))
        if not _at_tile(spot):
            host.log(f'the walk in stopped short of {_spot_name(host.style(), host.safespot_index())} at {spot}. Closing the gap from the walk-back task.')

    def _anchor(self):
        return anchor_for(self.site, self.host.style(), self.host.safespot_index())

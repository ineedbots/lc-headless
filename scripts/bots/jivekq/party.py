"""The four-account team: heartbeats, the leader's releases at each rope and at the bank, the loot election and
the deaths: rs2b0t's scripts/JiveKQ/party.ts (MIT, see thirdparty/rs2b0t). Every value received is a teammate's
message, a JSON dict, and is checked before it's believed."""

from bots.jivekq.loot import LootClaim, eligible_loot, loot_priority
from bots.jivekq.policy import BANK, SURFACE, UPPER, in_lair, near
from bots.jivekq.recovery import Casualty, death_report, is_integer, is_number, is_point, to_tile
from bots.jivekq.search import QueenSighting

STAGES = ['bank', 'travel', 'surface', 'upper', 'fight', 'retreat']
FRESH_MS = 6000
RELEASE_MS = 12000


def normalize_name(name):
    return ' '.join(name.strip().lower().replace('_', ' ').split())


def parse_roster(value):
    names = [normalize_name(n) for n in value.split(',')]
    if len(names) != 4 or any([not n or len(n) > 12 for n in names]) or len(set(names)) != 4:
        raise ValueError('Set Team to exactly four distinct account names, separated by commas')
    return names


class MemberStats:
    def __init__(self, hp, prayer, food, damage, dps, kills):
        self.hp = hp
        self.prayer = prayer
        self.food = food
        self.damage = damage
        self.dps = dps
        self.kills = kills


class Member:
    """A teammate's last heartbeat. stage is one of STAGES; the optional fields are None when it didn't say."""

    def __init__(self, name, session, trip, stage, tile, ready):
        self.name = name
        self.session = session
        self.trip = trip
        self.stage = stage
        self.tile = tile
        self.ready = ready
        self.player_slot = None
        self.restocking = False
        self.blocked = False
        self.lure = None
        self.queen = None
        self.death = None
        self.recovery_space = None
        self.loot = None
        self.reason = None
        self.stats = None


class Release:
    def __init__(self, stage, trip, sessions, at):
        self.stage = stage
        self.trip = trip
        self.sessions = sessions
        self.at = at

    def to_message(self):
        return {'stage': self.stage, 'trip': self.trip, 'sessions': list(self.sessions), 'at': self.at}


def _loot_of(loot):
    if not isinstance(loot, dict):
        return None
    id = loot.get('id')
    name = loot.get('name')
    if not is_integer(id) or id <= 0 or id >= 65536 or not isinstance(name, str) or not eligible_loot(name, True):
        return None
    if not is_point(loot.get('tile')) or not in_lair(to_tile(loot['tile'])) or type(loot.get('collecting')) is not bool:
        return None
    return LootClaim(int(id), name, to_tile(loot['tile']), loot['collecting'])


def _queen_of(queen, now):
    if not isinstance(queen, dict) or queen.get('id') not in [1158, 1160] or not is_point(queen.get('tile')):
        return None
    tile = to_tile(queen['tile'])
    at = queen.get('at')
    if not in_lair(tile) or not is_number(at) or at > now + 1000 or now - at > 8000 or type(queen.get('engaged')) is not bool:
        return None
    return QueenSighting(queen['id'], tile, at, queen['engaged'])


def _stats_of(stats):
    keys = ['hp', 'prayer', 'food', 'damage', 'dps', 'kills']
    if not isinstance(stats, dict) or any([not is_number(stats.get(k)) or stats.get(k) < 0 for k in keys]):
        return None
    return MemberStats(stats['hp'], stats['prayer'], stats['food'], stats['damage'], stats['dps'], stats['kills'])


def _same_tile(a, b):
    return near(a, b, 0)


class Party:
    def __init__(self, roster, self_name, session, log=None):
        self.roster = roster
        self.self_name = self_name
        self.session = session
        self._log = log
        self._peers = {}
        self._gates = {}
        self._aborted = set()
        self._casualties = {}
        self.messages = []

    def _report(self, message):
        self.messages.append(message)
        if len(self.messages) > 5:
            self.messages.pop(0)
        if self._log is not None:
            self._log(message)

    def receive(self, value, now):
        if not isinstance(value, dict) or not isinstance(value.get('name'), str) or value['name'] not in self.roster:
            return
        tile = value.get('tile')
        if not isinstance(value.get('session'), str) or not is_integer(value.get('trip')) or value.get('stage') not in STAGES \
                or type(value.get('ready')) is not bool or (tile is not None and not is_point(tile)):
            return
        member = Member(value['name'], value['session'], int(value['trip']), value['stage'], to_tile(tile) if tile is not None else None, value['ready'])
        slot = value.get('player_slot')
        if is_integer(slot) and slot >= 0 and slot < 2048:
            member.player_slot = int(slot)
        space = value.get('recovery_space')
        if is_integer(space) and space >= 0 and space <= 28:
            member.recovery_space = int(space)
        member.restocking = value.get('restocking') == True and (member.stage == 'retreat' or member.stage == 'bank')
        death = death_report(value.get('death'), now)
        if death is not None:
            member.death = death
            key = f'{member.name}:{member.session}:{member.trip}'
            if key not in self._casualties:
                self._report(f'{member.name} died at {death.tile.x},{death.tile.z}; recovering dropped items')
            self._casualties[key] = Casualty(member.name, member.session, member.trip, death)
        member.loot = _loot_of(value.get('loot'))
        member.blocked = value.get('blocked') == True
        if is_point(value.get('lure')):
            member.lure = to_tile(value['lure'])
        member.queen = _queen_of(value.get('queen'), now)
        if isinstance(value.get('reason'), str):
            member.reason = value['reason'][0:120]
        member.stats = _stats_of(value.get('stats'))
        if member.reason == 'paused' or (not member.restocking and (member.stage == 'retreat' or (not member.ready and member.stage != 'bank'))):
            self._aborted.add(member.trip)
        peer = self._peers.get(member.name)
        previous = peer[0] if peer is not None else None
        before = previous.loot if previous is not None else None
        if member.loot is not None and (before is None or before.id != member.loot.id or not _same_tile(before.tile, member.loot.tile)
                                        or before.collecting != member.loot.collecting):
            verb = 'collecting' if member.loot.collecting else 'spotted'
            self._report(f'{member.name} {verb} {member.loot.name} at {member.loot.tile.x},{member.loot.tile.z}')
        elif member.loot is None and before is not None:
            self._report(f'{member.name} released loot claim for {before.name}')
        seen = previous.queen if previous is not None else None
        if member.queen is not None and (seen is None or seen.id != member.queen.id):
            form = 'flying' if member.queen.id == 1160 else 'ground'
            self._report(f'{member.name} spotted the {form} queen at {member.queen.tile.x},{member.queen.tile.z}')
        if previous is None or previous.session != member.session or previous.trip != member.trip or previous.stage != member.stage \
                or previous.ready != member.ready or previous.reason != member.reason or previous.blocked != member.blocked \
                or previous.restocking != member.restocking:
            ready = 'ready' if member.ready else 'not ready'
            restock = ': restocking for next trip' if member.restocking else ''
            reason = f': {member.reason}' if member.reason else ''
            blocked = ': cross blocked' if member.blocked else ''
            self._report(f'{member.name}: {member.stage}, {ready} (trip {member.trip}){restock}{reason}{blocked}')
        self._peers[member.name] = (member, now)

    def members(self, now):
        out = []
        for name in self.roster:
            peer = self._peers.get(name)
            if peer is not None and now - peer[1] <= FRESH_MS:
                out.append(peer[0])
        return out

    def loot_collector(self, trip, now):
        """The one teammate whose claim the team leaves to it: a real drop before Rune arrows, an active collector
        before a spotter, then the drop's priority."""
        eligible = [m for m in self.members(now) if m.trip == trip and m.stage == 'fight' and m.ready and not m.restocking and m.death is None
                    and in_lair(m.tile) and m.loot is not None]
        eligible.sort(key=lambda m: (1 if m.loot.name == 'Rune arrow' else 0, 0 if m.loot.collecting else 1, loot_priority(m.loot.name)))
        return eligible[0] if eligible else None

    def deaths(self, trip):
        return [c for c in self._casualties.values() if c.trip == trip]

    def release(self, stage, trip, now):
        """The leader's go for the four at a rope or the bank, or None while any is missing, unready or elsewhere."""
        members = self.members(now)
        tile = BANK if stage == 'bank' else (SURFACE if stage == 'surface' else UPPER)
        if trip in self._aborted or self.self_name != self.roster[0] or len(members) != 4 \
                or any([m.stage != stage or not m.ready or not near(m.tile, tile, 4) for m in members]):
            return None
        if stage == 'bank':
            if trip != max([m.trip for m in members]) + 1:
                return None
        elif any([m.trip != trip for m in members]):
            return None
        return Release(stage, trip, [m.session for m in members], now)

    def accept(self, value, now):
        """Takes the leader's release message, or a Release this account made."""
        if isinstance(value, Release):
            value = value.to_message()
        if not isinstance(value, dict) or value.get('stage') not in ['surface', 'upper', 'bank'] or not is_number(value.get('trip')) \
                or not is_number(value.get('at')):
            return
        sessions = value.get('sessions')
        if not isinstance(sessions, list) or len(sessions) != 4 or any([not isinstance(s, str) for s in sessions]):
            return
        if sessions[self.roster.index(self.self_name)] != self.session or value['at'] > now + 1000 or now - value['at'] > RELEASE_MS:
            return
        stage = value['stage']
        previous = self._gates.get(stage)
        if previous is None or previous.trip != value['trip'] or any([previous.sessions[i] != sessions[i] for i in range(4)]):
            self._report(f'{self.roster[0]} released {stage}: all four ready (trip {value["trip"]})')
        self._gates[stage] = Release(stage, value['trip'], list(sessions), value['at'])

    def released(self, stage, trip, now):
        gate = self._gates.get(stage)
        members = self.members(now)
        if gate is None or gate.trip != trip or now < gate.at or now - gate.at > RELEASE_MS or self.unsafe(trip, now):
            return False
        for i in range(len(members)):
            if members[i].session != gate.sessions[i]:
                return False
        return True

    def departure(self, current_trip, now):
        """The trip the leader released from the bank, once this account may leave on it."""
        gate = self._gates.get('bank')
        members = self.members(now)
        if gate is None or gate.trip <= current_trip or gate.trip in self._aborted or now < gate.at or now - gate.at > RELEASE_MS or len(members) != 4:
            return None
        for i in range(4):
            m = members[i]
            if not m.ready or m.trip > gate.trip or m.session != gate.sessions[i]:
                return None
        return gate.trip

    def unsafe(self, trip, now):
        """Whether the fight has to stop: the trip was aborted, a living teammate went quiet, or one is on another
        trip, unready or leaving without restocking."""
        members = self.members(now)
        dead = set([c.name for c in self.deaths(trip)])
        names = [m.name for m in members]
        if trip in self._aborted or any([name not in names and name not in dead for name in self.roster]):
            return True
        return any([m.trip != trip or (not m.restocking and (not m.ready or m.stage == 'retreat' or m.stage == 'bank')) for m in members])

"""Same-process quest pairing from rs2b0t's partnerships.ts (MIT, see thirdparty/rs2b0t).

The native bot message bus replaces BroadcastChannel. Peers expire after fifteen seconds.
"""

import json

PARTNER_QUESTS = ['blackarmgang', 'hero']
FRESH_MS = 15000


def normalize(name):
    return ' '.join(name.strip().lower().replace('_', ' ').split())


def established_quest_gang(id, stage):
    if stage is None:
        return None
    if id == 'blackarmgang':
        if stage >= 8 and stage <= 9:
            return 'phoenix'
        if stage >= 21 and stage <= 23:
            return 'blackarm'
    if id == 'hero':
        if stage >= 2 and stage <= 6:
            return 'phoenix'
        if stage >= 7 and stage <= 13:
            return 'blackarm'
    return None


def eligible(peer, quest):
    progress = peer['quests'].get(quest, {})
    stage = progress.get('stage')
    return progress.get('eligible', False) and (stage is None or (stage != 6 and stage < 13 if quest == 'hero' else stage < 30))


def compatible(a, b, quest):
    return a['session'] != b['session'] and normalize(a['name']) != normalize(b['name']) and a['available'] and b['available'] and bool(a['world']) and a['world'] == b['world'] and a['active_quest'] == quest and b['active_quest'] == quest and a['gang'] is not None and b['gang'] is not None and a['gang'] != b['gang'] and eligible(a, quest) and eligible(b, quest) and (not a['overrides'].get(quest) or normalize(a['overrides'][quest]) == normalize(b['name'])) and (not b['overrides'].get(quest) or normalize(b['overrides'][quest]) == normalize(a['name']))


def valid_member(value):
    if not isinstance(value, dict):
        return False
    for key in ['name', 'session', 'world']:
        if not isinstance(value.get(key), str) or not value[key]:
            return False
    if not isinstance(value.get('started_at'), (int, float)) or value.get('gang') not in [None, 'phoenix', 'blackarm']:
        return False
    for key in ['available', 'trade_active']:
        if not isinstance(value.get(key), bool):
            return False
    if value.get('active_quest') is not None and not isinstance(value['active_quest'], str):
        return False
    for key in ['quests', 'claims', 'overrides']:
        if not isinstance(value.get(key), dict):
            return False
    for quest in PARTNER_QUESTS:
        progress = value['quests'].get(quest)
        if progress is not None:
            if not isinstance(progress, dict) or not isinstance(progress.get('eligible'), bool):
                return False
            if progress.get('stage') is not None and not isinstance(progress['stage'], (int, float)):
                return False
            if progress.get('has_key') is not None and not isinstance(progress['has_key'], bool):
                return False
        for key in ['claims', 'overrides']:
            if value[key].get(quest) is not None and not isinstance(value[key][quest], str):
                return False
    return True


class PartnerCoordinator:
    def __init__(self, session, overrides=None, started_at=0):
        self.session = session
        self.overrides = {key: value.strip() for key, value in (overrides or {}).items()}
        self.started_at = started_at
        self.peers = {}
        self.current = None
        self.partners = {}

    def receive(self, value, now):
        if valid_member(value) and value['session'] != self.session:
            self.peers[value['session']] = (json.loads(json.dumps(value)), now)

    def roster(self, now):
        if self.current is None:
            return []
        peers = [self.current] + [value for value, seen in self.peers.values() if now - seen <= FRESH_MS]
        peers.sort(key=lambda value: (-value['started_at'], value['session']))
        seen = set()
        unique = []
        for peer in peers:
            key = peer['world'] + ':' + normalize(peer['name'])
            if key not in seen:
                seen.add(key)
                unique.append(peer)
        unique.sort(key=lambda value: (normalize(value['name']), value['session']))
        return unique

    def match_pairs(self, roster, quest):
        pairs = {}
        for mode in [0, 1, 2]:
            for a in roster:
                if a['session'] in pairs:
                    continue
                for b in roster:
                    if b['session'] in pairs or not compatible(a, b, quest):
                        continue
                    mutual = a['claims'].get(quest) == b['session'] and b['claims'].get(quest) == a['session']
                    claimed = a['claims'].get(quest) == b['session'] or b['claims'].get(quest) == a['session']
                    if mode == 0 and not mutual or mode == 1 and not claimed:
                        continue
                    pairs[a['session']] = b['session']
                    pairs[b['session']] = a['session']
                    break
        return pairs

    def update(self, snapshot, now):
        previous = self.current
        self.current = json.loads(json.dumps(snapshot))
        self.current.update({'session': self.session, 'started_at': self.started_at, 'claims': {key: value for key, value in previous['claims'].items()} if previous else {}, 'overrides': self.overrides})
        roster = self.roster(now)
        for quest in PARTNER_QUESTS:
            if self.current['trade_active'] and self.current['active_quest'] == quest and previous is not None and previous['world'] == self.current['world'] and self.partners.get(quest):
                continue
            matches = self.match_pairs(roster, quest)
            claim = matches.get(self.session)
            if claim:
                self.current['claims'][quest] = claim
            else:
                self.current['claims'].pop(quest, None)
            peer = self.peer(quest, now)
            self.partners[quest] = self.overrides.get(quest) or (peer['name'] if peer else '')
        return json.loads(json.dumps(self.current))

    def partner(self, quest):
        return self.overrides.get(quest) or self.partners.get(quest, '')

    def peer(self, quest, now):
        if self.current is None:
            return None
        for other in self.roster(now):
            if other['session'] == self.current['claims'].get(quest) and compatible(self.current, other, quest) and other['claims'].get(quest) == self.session:
                return other
        return None

    def has_live_partner(self, quest, now):
        return self.peer(quest, now) is not None

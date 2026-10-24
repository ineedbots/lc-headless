"""What a route needs, and what the walker learns on the way: the items a route's hops use and the bank leg that
fetches them, the kit that would open an unreachable route, quest-locked crossings, the talks that unlock a
crossing after its quest, the essence mine's way out, and how sticky a walk follows its route. Mirrors rs2b0t's
event/webwalk/bankPlan.ts, virtualState.ts, gateItems.ts, slashTool.ts, essenceSession.ts, essenceExit.ts,
pathFollowPolicy.ts, exec/questLock.ts, data/postQuestTalks.ts and data/specialCrossings.ts's lookup (MIT, see
thirdparty/rs2b0t). The walker that uses them is traversal.

A route's waypoints are anything with x, z, level and transport, the transport a dict as the core plans it. A
state is world_state()'s dict: members, skills, items, worn, quests, free_slots, can_slash_web and
essence_exit_return.
"""

import json

import _core
from rs2004.geometry import Tile
from rs2004.settings import settings_store

__all__ = [
    'crossings', 'teleports', 'teleport_by_id', 'special_crossing_for_transport', 'pick_choice', 'MissingItem',
    'items_required_by_waypoints', 'missing_items_for_path', 'plan_bank_leg', 'path_has_teleport', 'virtualize_with_items',
    'gate_item_candidates', 'explain_unreachable', 'is_quest_lock_text', 'is_quest_lock_dialogue', 'post_quest_talk_for',
    'essence_session', 'ESSENCE_EXIT_RETURNS', 'essence_return_id_from_tile', 'resolve_path_follow_config', 'is_slash_web_transport',
    'records_have_slash_tool', 'WEB_SLASH_KNIFE_NAME', 'is_entrana_restricted_gear', 'names_have_entrana_restricted_gear', 'meets_requires',
]


class Fields:
    """An answer with its fields as attributes. Why: rs2004.catalogs' Record would import the catalogs, which
    import the walker."""

    def __init__(self, fields):
        self._fields = fields
        for key, value in fields.items():
            setattr(self, key, value)

    def __repr__(self):
        return f'Fields({self._fields})'


def _load(name):
    text = _core.nav_data(name)
    return json.loads(text) if text is not None else []


_crossings = None
_teleports = None


def crossings():
    """rs2b0t's special crossings: tolls, ships, keyed doors and the rest, as dicts in its camelCase."""
    global _crossings
    if _crossings is None:
        _crossings = _load('crossings')
    return _crossings


def teleports():
    """rs2b0t's spell and jewellery teleports, as dicts in its camelCase."""
    global _teleports
    if _teleports is None:
        _teleports = _load('teleports')
    return _teleports


def teleport_by_id(teleport_id):
    for teleport in teleports():
        if teleport['teleportId'] == teleport_id:
            return teleport
    return None


def pick_choice(options, choose):
    """The first option containing any of the wanted texts, without regard to case."""
    wanted = [c.lower() for c in choose]
    for option in options:
        lower = option.lower()
        for want in wanted:
            if want in lower:
                return option
    return None


def _near(tile, x, z, radius):
    return max(abs(tile.x - x), abs(tile.z - z)) <= radius


def _to_tile_matches(crossing, step):
    to = crossing.get('toTile')
    if to is None:
        return True
    return to['x'] == step.x and to['z'] == step.z and (to.get('level') is None or to['level'] == step.level)


def special_crossing_for_transport(transport, approach, step):
    """The special crossing a hop makes, keyed at the tile it leaves, its loc, or the tile it reaches, on
    either level; ones whose landing isn't the hop's are left out. Mirrors rs2b0t's lookup."""
    levels = [approach.level]
    if step is not None and step.level not in levels:
        levels.append(step.level)
    candidates = []
    ranks = []
    for level in levels:
        for crossing in crossings():
            if crossing['level'] != level:
                continue
            rank = None
            if crossing['x'] == approach.x and crossing['z'] == approach.z:
                rank = 0
            elif crossing['x'] == transport['loc_x'] and crossing['z'] == transport['loc_z']:
                rank = 1
            elif step is not None and crossing['x'] == step.x and crossing['z'] == step.z:
                rank = 2
            if rank is None:
                continue
            if crossing in candidates:
                i = candidates.index(crossing)
                ranks[i] = min(ranks[i], rank)
            else:
                candidates.append(crossing)
                ranks.append(rank)
    if not candidates:
        return None
    name = (transport.get('loc_name') or '').lower()
    if name:
        named = [i for i in range(len(candidates)) if candidates[i]['locName'].lower() == name or (candidates[i].get('npc') or '').lower() == name]
        if named:
            candidates = [candidates[i] for i in named]
            ranks = [ranks[i] for i in named]
    if step is not None:
        landing = [i for i in range(len(candidates)) if _to_tile_matches(candidates[i], step)]
        if landing:
            candidates = [candidates[i] for i in landing]
            ranks = [ranks[i] for i in landing]
        elif len([c for c in candidates if c.get('toTile') is not None]) > 0:
            return None
        if len(candidates) > 1:
            for crossing in candidates:
                if crossing.get('toTile') is not None and _to_tile_matches(crossing, step):
                    return crossing
    best = 0
    for i in range(1, len(candidates)):
        if ranks[i] < ranks[best]:
            best = i
    return candidates[best]


# Slashing webs.

WEB_SLASH_KNIFE_NAME = 'Knife'
SLASH_WEAPON_WORDS = ['scimitar', 'longsword', 'sword', 'dagger', 'battleaxe', '2h', 'claws', 'whip', 'scythe', 'halberd', 'machete', 'abyssal',
                      'silverlight', 'excalibur', 'darklight']
THROWN_KNIFE_METALS = ['bronze', 'iron', 'steel', 'black', 'mithril', 'adamant', 'rune', 'dragon']


def _is_word_char(c):
    # Why: pocketpy's str has no isalpha().
    return c.lower() != c.upper() or c in "0123456789'’"


def _words(text):
    """The lower-case words of text, letters, digits and apostrophes, with where each starts and ends."""
    out = []
    word = ''
    start = 0
    for i in range(len(text)):
        c = text[i].lower()
        if _is_word_char(c):
            if word == '':
                start = i
            word += c
        elif word != '':
            out.append((word, start, i))
            word = ''
    if word != '':
        out.append((word, start, len(text)))
    return out


def is_content_knife_name(name):
    return name is not None and name.strip().lower() == 'knife'


def is_slash_weapon_name(name):
    """A weapon that slashes webs: a sword, a scimitar, an axe of war and the rest, but not a thrown knife."""
    if not name or is_content_knife_name(name):
        return False
    words = [w for w, _, _ in _words(name)]
    if len(words) == 2 and words[1] == 'knife' and words[0] in THROWN_KNIFE_METALS:
        return False
    if 'two' in words and 'handed' in words:
        return True
    return len([w for w in words if w in SLASH_WEAPON_WORDS]) > 0


def records_have_slash_tool(items, worn=None):
    """Whether the counts hold a plain knife or a weapon that slashes."""
    for counts in [items, worn or {}]:
        for name, count in counts.items():
            if count > 0 and (is_content_knife_name(name) or is_slash_weapon_name(name)):
                return True
    return False


def is_slash_web_transport(loc_name, action):
    return (action or '').lower() == 'slash' and 'web' in (loc_name or '').lower()


# Entrana's monks turn back anyone carrying weapons or armour: rs2b0t's ENTRANA_RESTRICTED_GEAR_RE as words, since
# pocketpy has no re.
ENTRANA_RESTRICTED_WORDS = [
    'sword', 'dagger', 'scimitar', 'longsword', '2h', 'mace', 'warhammer', 'battleaxe', 'axe', 'pickaxe', 'spear', 'hasta', 'halberd', 'maul',
    'claws', 'whip', 'bow', 'shortbow', 'longbow', 'crossbow', 'javelin', 'dart', 'thrownaxe', 'knife', 'staff', 'wand', 'battlestaff',
    'cannon', 'helmet', 'coif', 'platebody', 'chainbody', 'platelegs', 'plateskirt', 'kiteshield', 'defender', 'chaps', 'vambraces', 'gauntlet',
    'gauntlets', 'gloves', 'shield', 'cape', 'cloak', 'snelm', 'cowl', 'hat', 'hood',
]
ENTRANA_RESTRICTED_PHRASES = [
    ['two', 'handed'], ['full', 'helm'], ['med', 'helm'], ['skirt', 'of'], ['square', 'shield'], ['sq', 'shield'], ['dragon', 'square'],
    ['god', 'cape'], ['fire', 'cape'], ['obsidian', 'cape'],
]


def is_entrana_restricted_gear(name):
    """Whether an item name looks like gear Entrana bans: a weapon, armour, a cape, or a body that isn't a rune."""
    words = [w for w, _, _ in _words(name or '')]
    for i in range(len(words)):
        word = words[i]
        if word in ENTRANA_RESTRICTED_WORDS:
            return True
        # Why: rs2b0t's body(?!\s+rune\b) bans a "body" but not the Body rune.
        if word == 'body' and not (i + 1 < len(words) and words[i + 1] == 'rune'):
            return True
        for phrase in ENTRANA_RESTRICTED_PHRASES:
            if words[i:i + len(phrase)] == phrase:
                return True
    return False


def names_have_entrana_restricted_gear(names):
    return any([len(n) > 0 and is_entrana_restricted_gear(n) for n in names])


_QUEST_RANK = {'not_started': 0, 'unknown': 0, 'started': 1, 'complete': 2}


def meets_requires(requires, state):
    """(ok, reason): whether a catalog entry's requires is met by world_state(). rs2b0t's meetsRequires; an
    unknown quest status fails closed."""
    if not requires:
        return (True, None)
    if requires.get('members') == True and not state.get('members'):
        return (False, 'members-only')
    slots = requires.get('freeSlots')
    if slots is not None and state.get('free_slots', 0) < slots:
        return (False, f"need {slots} free inventory slots (have {state.get('free_slots', 0)})")
    levels = state.get('skills', {})
    for skill in requires.get('skills') or []:
        have = levels.get(skill['name'].lower(), levels.get(skill['name'], 0))
        if have < skill['level']:
            return (False, f"need {skill['name']} {skill['level']} (have {have})")
    held = state.get('items', {})
    worn = state.get('worn', {})
    statuses = state.get('quests', {})
    waives = requires.get('questWaivesItems')
    waived = waives is not None and statuses.get(waives) == 'complete'
    currency = requires.get('currency')
    if currency and not waived and held.get(currency['name'], 0) < currency['amount']:
        return (False, f"need {currency['amount']}x {currency['name']} (have {held.get(currency['name'], 0)})")
    for item in requires.get('items') or []:
        if not waived and held.get(item['name'], 0) < item['count']:
            return (False, f"need {item['count']}x {item['name']} (have {held.get(item['name'], 0)})")
    for item in requires.get('worn') or []:
        if worn.get(item['name'], 0) < item['count']:
            return (False, f"need to wear {item['name']} (have {worn.get(item['name'], 0)})")
    if requires.get('forbidEntranaRestricted') == True and state.get('entrana_restricted_gear'):
        return (False, 'remove weapons/armour before Entrana')
    if requires.get('slashTool') == True and state.get('can_slash_web') == False:
        return (False, 'need Knife or a bladed weapon to slash webs')
    for quest in requires.get('quests') or []:
        name = quest['quest']
        have = statuses.get(name, 'unknown')
        most = quest.get('maxStatus')
        least = quest.get('minStatus')
        if have == 'unknown' and most is not None:
            return (False, f'need known quest status for {name}')
        if most is not None and _QUEST_RANK[have] > _QUEST_RANK[most]:
            return (False, f'need quest {name} at most {most} (have {have})')
        if least is not None and _QUEST_RANK[have] < _QUEST_RANK[least]:
            return (False, f'need quest {name} {least} (have {have})')
    # Why: an essence exit is a session destination, so a known return that doesn't match fails closed, and an
    # unset one fails open.
    exit_return = requires.get('essenceExitReturn')
    live = state.get('essence_exit_return')
    if exit_return is not None and live is not None and live != exit_return:
        return (False, f'essence exit returns to {live}, not {exit_return}')
    return (True, None)


# What a route needs.

# Opening the bank and withdrawing a short list, about 12 ticks, as tiles walked.
WITHDRAW_COST = 24


class MissingItem:
    def __init__(self, name, count):
        self.name = name
        self.count = count

    def __eq__(self, other):
        return isinstance(other, MissingItem) and self.name == other.name and self.count == other.count

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f'{self.count}x {self.name}'


def lookup_item(items, name):
    """A count from a name to count dict, by the name as given, lower-case, or without its spaces."""
    if name in items:
        return items[name]
    lower = name.lower()
    compact = lower.replace(' ', '')
    for key, value in items.items():
        k = key.lower()
        if k == lower or k.replace(' ', '') == compact:
            return value
    return 0


def _quest_status(state, quest):
    statuses = (state or {}).get('quests') or {}
    return statuses.get(quest, 'unknown')


def items_required_by_waypoints(waypoints, state=None):
    """The items a route's hops use, by name: a teleport's runes, a toll's or fare's coins, summed over the
    route, and a key or a knife at the most any hop needs."""
    need = {}

    def bump(name, count):
        if count <= 0:
            return
        # Why: fares are paid at each hop, while a key or a tool is shown and kept.
        if name.lower() == 'coins':
            need[name] = need.get(name, 0) + count
        else:
            need[name] = max(need.get(name, 0), count)

    for i in range(len(waypoints)):
        wp = waypoints[i]
        transport = wp.transport
        if transport is None:
            continue
        teleport_id = transport.get('teleport_id')
        if teleport_id is not None:
            teleport = teleport_by_id(teleport_id)
            requires = (teleport or {}).get('requires') or {}
            for item in requires.get('items', []):
                bump(item['name'], item['count'])
            continue
        # Why: a gate is keyed at its approach stand, which can differ from the loc's tile.
        prev = waypoints[i - 1] if i > 0 else wp
        crossing = special_crossing_for_transport(transport, Tile(prev.x, prev.z, prev.level), Tile(wp.x, wp.z, wp.level))
        if crossing is not None and crossing.get('requires') is not None:
            # A completed waiver quest (Prince Ali Rescue) lifts the toll.
            waiver = crossing.get('questWaivesItems')
            waived = waiver is not None and state is not None and _quest_status(state, waiver) == 'complete'
            if not waived:
                bump(crossing['requires']['item'], crossing['requires']['count'])
        if is_slash_web_transport(transport.get('loc_name'), transport.get('action')):
            bump(WEB_SLASH_KNIFE_NAME, 1)
    return need


def missing_items_for_path(waypoints, state):
    """What the route uses that the account doesn't hold enough of, as MissingItems."""
    missing = []
    for name, count in items_required_by_waypoints(waypoints, state).items():
        # A held slash tool means no knife.
        if name == WEB_SLASH_KNIFE_NAME and state.get('can_slash_web') is True:
            continue
        have = lookup_item(state.get('items') or {}, name)
        if have < count:
            missing.append(MissingItem(name, count - have))
    return missing


def plan_bank_leg(direct_cost, direct_has_teleport, to_bank_cost, bank_to_dest_cost, missing):
    """Whether a bank leg beats walking direct: action 'skip' and reason, or action 'bank', missing
    and estimated_cost, as Fields. A direct cost of None is a route the account can't fund."""
    if direct_has_teleport:
        return Fields({'action': 'skip', 'reason': 'direct path already uses teleport'})
    if len(missing) == 0:
        return Fields({'action': 'skip', 'reason': 'no missing items on virtual path'})
    via = to_bank_cost + WITHDRAW_COST + bank_to_dest_cost
    if direct_cost is not None and via >= direct_cost:
        return Fields({'action': 'skip', 'reason': f'bank route cost {via} >= direct {direct_cost}'})
    return Fields({'action': 'bank', 'missing': missing, 'estimated_cost': via})


def path_has_teleport(waypoints):
    return len([w for w in waypoints if w.transport is not None and (w.transport.get('teleport_id') is not None or w.transport.get('kind') == 'teleport')]) > 0


def virtualize_with_items(state, add):
    """A copy of the state holding the add counts too, as if they'd been withdrawn."""
    items = {}
    for name, count in (state.get('items') or {}).items():
        items[name] = count
    for name, count in add.items():
        if count <= 0:
            continue
        total = lookup_item(items, name) + count
        items[name] = total
        # Keep a loose match under another spelling in step.
        for key in list(items.keys()):
            if key != name and key.lower().replace(' ', '') == name.lower().replace(' ', ''):
                items[key] = total
    out = {}
    for key, value in state.items():
        out[key] = value
    out['items'] = items
    worn = state.get('worn') or {}
    # A knife from the bank opens the webs.
    out['can_slash_web'] = state.get('can_slash_web') is True or records_have_slash_tool(items, worn)
    return out


def gate_item_candidates():
    """Every item a special crossing can ask for, at the most any one asks for, and a knife."""
    out = {WEB_SLASH_KNIFE_NAME: 1}
    for crossing in crossings():
        needs = crossing.get('requires')
        if needs is None:
            continue
        out[needs['item']] = max(out.get(needs['item'], 0), needs['count'])
    return out


def explain_unreachable(probe, state, to_waypoints):
    """The items that would turn an unreachable route into one. probe(state) plans the same route with another
    state; to_waypoints turns its answer into waypoints. Empty when the kit doesn't help, so the destination
    is off the graph."""
    with_kit = probe(virtualize_with_items(state, gate_item_candidates()))
    if not with_kit['ok']:
        return []
    return missing_items_for_path(to_waypoints(with_kit), state)


# Quest-locked crossings: a door that answers with a lock phrase won't open now, so the walk avoids it.

def _has_sequence(words, sequence):
    """Whether words holds sequence's words in a row, each a word or a list of choices."""
    for i in range(len(words) - len(sequence) + 1):
        ok = True
        for j in range(len(sequence)):
            want = sequence[j]
            have = words[i + j][0]
            if (have not in want) if isinstance(want, list) else (have != want):
                ok = False
                break
        if ok:
            return True
    return False


def _within(text, words, firsts, seconds, gap, second_whole=True):
    """Whether a word from firsts is followed within gap characters by one from seconds, which needn't start a
    word, and when second_whole must end one."""
    for word, _, end in words:
        if word not in firsts:
            continue
        for second in seconds:
            at = text.find(second, end)
            while at != -1 and at - end <= gap:
                after = at + len(second)
                if not second_whole or after >= len(text) or not _is_word_char(text[after]):
                    return True
                at = text.find(second, at + 1)
    return False


# Why: rs2b0t's list has no won't, but the 289 doors say "The door won't open".
CANT = ["can't", 'cant', 'cannot', "don't", 'dont', 'can’t', 'don’t', "won't", 'wont', 'won’t']
PASS_VERBS = ['open', 'go', 'pass', 'enter']


def is_quest_lock_text(line):
    """Whether a line of dialogue says the crossing won't open for you now: locked, needs a key or a quest,
    members only, come back later, or nothing interesting happens."""
    text = line.strip().lower()
    if len(text) < 4:
        return False
    words = _words(text)
    plain = [w for w, _, _ in words]
    if len([w for w in plain if w in ('lock', 'locked', 'locks')]) > 0:
        return True
    if _has_sequence(words, [['need', 'needs'], 'a', ['key', 'quest']]):
        return True
    if _has_sequence(words, [CANT, PASS_VERBS]) or _has_sequence(words, ['do', 'not', PASS_VERBS]):
        return True
    if _has_sequence(words, [['members', "members'", 'members’'], ['only', 'area', 'content']]):
        return True
    if _within(text, words, ['complete', 'finish', 'start'], ['quest'], 40):
        return True
    if _within(text, words, ['quest'], ['complete', 'finish', 'required', 'before'], 40):
        return True
    for i in range(len(words) - 1):
        if words[i][0] != 'you':
            continue
        if words[i + 1][0] == 'must' and _within(text, [words[i + 1]], ['must'], ['quest', 'key', 'level'], 30):
            return True
        if i + 2 < len(words) and words[i + 1][0] in ('need', 'have') and words[i + 2][0] == 'to' and _within(text, [words[i + 2]], ['to'], ['quest', 'key', 'level'], 30):
            return True
    if _has_sequence(words, ['nothing', 'interesting', 'happens']):
        return True
    if _has_sequence(words, ['you', 'are', 'not', ['worthy', 'allowed', 'ready']]):
        return True
    return _has_sequence(words, ['come', 'back', ['when', 'after']])


def is_quest_lock_dialogue(texts):
    return len([t for t in texts if is_quest_lock_text(t)]) > 0


# Talks that unlock a crossing whose quest the journal already shows complete. Why: the walker can't see the
# server's finer stage, so it talks only after the crossing refuses.

POST_QUEST_TALKS = [
    {
        # Drezel sets the stage within 20 tiles of the barrier; this is the Mort Myre unlock's stand.
        'loc_x': 3440, 'loc_z': 9886, 'level': 0, 'require_complete': 'Priest in Peril', 'npc': 'Drezel',
        'stand': Tile(3439, 9895, 0), 'choose': [], 'talks': 2, 'label': 'Salve barrier access (Drezel, post Priest in Peril)',
    },
]


def post_quest_talk_for(loc_x, loc_z, level):
    for talk in POST_QUEST_TALKS:
        if talk['loc_x'] == loc_x and talk['loc_z'] == loc_z and talk['level'] == level:
            return talk
    return None


# The essence mine. Why: the entry wizard keeps the way back in a varp the server never sends, so the walker
# remembers which wizard it came through, and the planner takes the portal that leads there.

def _lc(text):
    level, mx, mz, lx, lz = [int(p) for p in text.split('_')]
    return Tile(mx * 64 + lx, mz * 64 + lz, level)


ESSENCE_EXIT_RETURNS = {
    'aubury': _lc('0_50_53_53_9'),
    'sedridor': _lc('0_48_149_34_36'),
    'distentor': _lc('0_40_48_31_14'),
    'brimstail': _lc('0_37_153_22_18'),
    'cromperty': _lc('0_41_51_60_58'),
}

NPC_TO_RETURN = {
    'aubury': 'aubury', 'sedridor': 'sedridor', 'wizard distentor': 'distentor', 'distentor': 'distentor', 'wizard cromperty': 'cromperty',
    'cromperty': 'cromperty', 'brimstail': 'brimstail',
}


def essence_return_id_from_tile(tile):
    """The wizard whose stand is within 3 tiles of tile, or None."""
    best = None
    best_distance = 4
    for return_id, stand in ESSENCE_EXIT_RETURNS.items():
        if stand.level != tile.level:
            continue
        distance = max(abs(stand.x - tile.x), abs(stand.z - tile.z))
        if distance < best_distance:
            best_distance = distance
            best = return_id
    return best


class _EssenceSession:
    """Which wizard the essence mine's portal leads back to, once a walk has gone in through one."""

    def __init__(self):
        self._return = None
        self._override = None

    def get_return_id(self):
        return self._override if self._override is not None else self._return

    def note_entry(self, return_id):
        self._return = return_id

    def note_entry_from_npc(self, name):
        """From a wizard's name, such as Aubury or Wizard Cromperty."""
        if not name:
            return None
        found = NPC_TO_RETURN.get(name.strip().lower())
        if found is not None:
            self._return = found
        return found

    def note_entry_from_transport(self, transport):
        """From a hop taken: the entry hops are a wizard's Teleport, by name or by its surface stand."""
        if (transport.get('action') or '').lower() != 'teleport':
            return None
        found = self.note_entry_from_npc(transport.get('loc_name'))
        if found is not None:
            return found
        if transport.get('loc_x') is not None and transport.get('loc_z') is not None:
            at = essence_return_id_from_tile(Tile(transport['loc_x'], transport['loc_z'], 0))
            if at is not None:
                self._return = at
                return at
        return None

    def note_entry_from_crossing_label(self, label):
        """From a special crossing's label, such as 'Aubury -> essence mine'."""
        if not label or 'essence' not in label.lower() or 'mine' not in label.lower():
            return None
        head = label.replace('→', '->').split('->')[0].strip()
        return self.note_entry_from_npc(head)

    def set_harness_override(self, return_id):
        """For a test that teleports into the mine without a wizard."""
        self._override = return_id

    def clear_harness_override(self):
        self._override = None

    def clear(self):
        self._return = None
        self._override = None


essence_session = _EssenceSession()


# How sticky a walk follows its route: plan once, then plan again only on a stall, a step off it, or a request.

DEFAULT_PATH_STALL_TICKS = 5
DEFAULT_PATH_DEVIATION_CHEBYSHEV = 10
# Why: route progress counts a tile reached from this far, so a hop trigger below it never fires.
PATH_CORRIDOR = 3
DEFAULT_TRANSPORT_APPROACH_CHEBYSHEV = 4
# Why: the server moves a player the tick after it reads a click, so the step through a door that's just opened
# waits a tick; 0 steps on the frame it opens.
DEFAULT_DOOR_STEP_TICKS = 1


def resolve_path_follow_config(overrides=None):
    """The walk's follow settings, Fields of stall_ticks, deviation_chebyshev, transport_approach_chebyshev and
    door_step_ticks: from overrides, a dict of those keys, then the Global nav_path_stall_ticks and
    nav_path_deviation, then the defaults."""
    over = overrides or {}
    bag = settings_store.global_bag()
    stall = over.get('stall_ticks')
    deviation = over.get('deviation_chebyshev')
    approach = over.get('transport_approach_chebyshev')
    door = over.get('door_step_ticks')
    return Fields({
        'stall_ticks': max(1, int(stall if stall is not None else bag.num('nav_path_stall_ticks', DEFAULT_PATH_STALL_TICKS))),
        'deviation_chebyshev': max(1, int(deviation if deviation is not None else bag.num('nav_path_deviation', DEFAULT_PATH_DEVIATION_CHEBYSHEV))),
        # Never below the corridor, or the walker can pass a hop without taking it.
        'transport_approach_chebyshev': max(PATH_CORRIDOR, int(approach if approach is not None else DEFAULT_TRANSPORT_APPROACH_CHEBYSHEV)),
        'door_step_ticks': max(0, int(door if door is not None else DEFAULT_DOOR_STEP_TICKS)),
    })

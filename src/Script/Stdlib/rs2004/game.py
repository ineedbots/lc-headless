"""You and the game: game, skills, reader, chat, friends, ignores and direct_navigator. Mirrors rs2b0t's
api/game/Game.ts, api/skills/Skills.ts and event/webwalk/DirectNavigator.ts (MIT, see third_party/rs2b0t);
chat, friends and ignores are this client's own."""

import _core
from rs2004 import execution
from rs2004.entities import local_tile
from rs2004.events import SKILL_NAMES
from rs2004.geometry import Tile
from rs2004.tabs import COM_MODE_VARP, RETALIATE_VARP, _select_button, combat_styles, parse_combat_style
from rs2004.tabs import resolve_combat_style, spell_button, teleport_button, try_parse_combat_style

__all__ = ['game', 'skills', 'reader', 'chat', 'friends', 'ignores', 'direct_navigator']

_SKILL_INDEXES = {name: index for index, name in SKILL_NAMES.items()}
HITPOINTS_INDEX = 3


class _Game:
    """Your position, energy, combat and pacing."""

    def ingame(self):
        """Logged in and placed in the world, so the map is built and actions are taken."""
        return _core.is_placed()

    def tile(self):
        """Your tile, or None before you're placed."""
        if not _core.is_placed():
            return None
        return local_tile()

    def energy(self):
        """Run energy, 0 to 100."""
        return _core.get_run_energy()

    def run_enabled(self):
        return _core.is_running()

    def set_run(self, on):
        """Turns run mode on or off."""
        return _core.set_run(on)

    def weight(self):
        """Carried weight in kg."""
        return _core.get_weight()

    def in_combat(self):
        """You were hit within the last 8 ticks; 2004 has no combat-state packet."""
        return _core.in_combat()

    def appearance_screen_open(self):
        """Whether the character design screen is open, as on a new account."""
        return _core.is_appearance_screen_open()

    def set_appearance(self, female, kits, colours):
        """Saves a character design: the 7 body kits (head, jaw, torso, arms, hands, legs, feet; idk ids) and
        the 5 colours (hair, torso, legs, feet, skin). False when the design screen isn't open. The server
        checks the design and ignores one it doesn't allow."""
        return _core.set_appearance(female, kits, colours)

    def animating(self):
        return _core.get_local_player().animation != -1

    def moving(self):
        return _core.is_moving()

    def tick(self):
        """Server ticks since login."""
        return _core.get_tick()

    def my_name(self):
        return _core.get_name()

    def combat_level(self):
        return _core.get_combat_level()

    # Combat

    def combat_mode(self):
        """The combat tab's selected mode, the varp its style buttons set."""
        return _core.get_varp(COM_MODE_VARP)

    def combat_styles(self):
        """The wielded weapon's style buttons as (mode, label), such as (0, '(Accurate)'). None before the
        combat tab is sent."""
        return combat_styles()

    def combat_style_resolution(self, style):
        """How the weapon trains style ('attack', 'strength', 'controlled' or 'defence'): a
        CombatStyleResolution, falling back to its last defensive style, or None."""
        offered = combat_styles()
        if offered is None:
            return None
        return resolve_combat_style(parse_combat_style(style), offered)

    def combat_style_mode(self, style):
        resolution = self.combat_style_resolution(style)
        return resolution.mode if resolution is not None else None

    def has_combat_style(self, style):
        mode = self.combat_style_mode(style)
        return mode is not None and self.combat_mode() == mode

    def set_combat_style(self, style):
        """Selects the style, by training style or interface label ('aggressive'), or by mode number."""
        if isinstance(style, int) and not isinstance(style, bool):
            return self.set_combat_mode(style)
        if try_parse_combat_style(style) is None:
            raise ValueError(f'{repr(style)} is not a combat style; use attack, strength, controlled or defence')
        mode = self.combat_style_mode(style)
        return mode is not None and self.set_combat_mode(mode)

    def set_combat_mode(self, mode):
        """Clicks the combat tab's button for the mode, as ranged styles are set."""
        button = _select_button(COM_MODE_VARP, mode)
        return button is not None and _core.click_component(button.id)

    def auto_retaliate_on(self):
        return _core.get_varp(RETALIATE_VARP) == 0

    def set_auto_retaliate(self, on):
        button = _select_button(RETALIATE_VARP, 0 if on else 1)
        return button is not None and _core.click_component(button.id)

    def attacked_by_player(self):
        """In combat and facing a player: one who attacked, since a bot that doesn't start fights only
        faces players by retaliating."""
        target = _core.get_local_player().target
        return _core.in_combat() and target is not None and target[0] == 'player'

    # Magic

    def _spell(self, spell):
        com = spell_button(spell)
        if com == -1:
            return None
        return com

    def cast_on_npc(self, spell, npc):
        """Casts the spell, by name ('Wind strike'), on the NPC. False when the spellbook has no such spell."""
        com = self._spell(spell)
        return com is not None and _core.cast_on_npc(com, npc)

    def cast_on_player(self, spell, player):
        com = self._spell(spell)
        return com is not None and _core.cast_on_player(com, player)

    def cast_on_loc(self, spell, loc):
        com = self._spell(spell)
        if com is None:
            return False
        _core.cast_on_loc(com, loc.id, loc._x, loc._z)
        return True

    def cast_on_ground_item(self, spell, item):
        com = self._spell(spell)
        return com is not None and _core.cast_on_ground_item(com, item)

    def cast_on_item(self, spell, item):
        """Casts the spell on a backpack item, as Superheat Item and the alchemy spells are cast."""
        com = self._spell(spell)
        return com is not None and _core.cast_on_item(com, item)

    def teleport(self, name):
        """Casts a teleport by name, 'Varrock' or 'Varrock teleport'. True when the click is sent; check the
        arrival yourself."""
        com = teleport_button(name)
        return com != -1 and _core.click_component(com)


def _skill_index(name):
    index = _SKILL_INDEXES.get(name.strip().lower())
    if index is None:
        raise ValueError(f'{repr(name)} is not a skill; the skills are {", ".join(_SKILL_INDEXES.keys())}')
    return index


class _Skills:
    """Levels and experience, by lower-case name: 'attack', 'woodcutting' and so on."""

    def index(self, name):
        """The skill's index, or -1 for a name that isn't one."""
        return _SKILL_INDEXES.get(name.strip().lower(), -1)

    def level(self, name):
        """The base level, unboosted."""
        return _core.get_max_stat(_skill_index(name))

    def effective(self, name):
        """The current level, boosted or drained."""
        return _core.get_current_stat(_skill_index(name))

    def xp(self, name):
        return _core.get_experience(_skill_index(name))

    def hp_fraction(self):
        """Current over base hitpoints; 1 while they aren't known."""
        base = _core.get_max_stat(HITPOINTS_INDEX)
        if base <= 0:
            return 1
        return _core.get_current_stat(HITPOINTS_INDEX) / base


class _Reader:
    """Raw reads, for what no facade covers yet."""

    def varp(self, id):
        return _core.get_varp(id)

    def pid(self):
        return _core.get_pid()

    def main_modal(self):
        return _core.get_main_modal()

    def side_modal(self):
        return _core.get_side_modal()

    def chat_modal(self):
        return _core.get_chat_modal()

    def interface_open(self, id):
        return _core.is_interface_open(id)

    def component_text(self, com):
        return _core.get_component_text(com)

    def count_dialog_open(self):
        return _core.is_count_dialog_open()

    def inventory(self, com):
        """The InvItems of any inventory the server sends, such as BANK."""
        return _core.get_inventory(com)

    def npc_type(self, id):
        return _core.get_npc_type(id)

    def item_type(self, id):
        return _core.get_item_type(id)

    def loc_type(self, id):
        return _core.get_loc_type(id)

    def item_ids(self, name):
        """The ids of the items with that name in the cache, without regard to case."""
        return _core.find_type_ids('item', name)

    def npc_ids(self, name):
        return _core.find_type_ids('npc', name)

    def loc_ids(self, name):
        return _core.find_type_ids('loc', name)


class _Chat:
    def say(self, text):
        return _core.say(text)

    def send_pm(self, name, text):
        return _core.send_pm(name, text)

    def command(self, text):
        """A ::command, for staff accounts."""
        return _core.command(text)


class _Friends:
    def list(self):
        """[(name, world)], world 0 when offline."""
        return _core.get_friends()

    def add(self, name):
        return _core.add_friend(name)

    def remove(self, name):
        return _core.remove_friend(name)


class _Ignores:
    def list(self):
        return _core.get_ignores()

    def add(self, name):
        return _core.add_ignore(name)

    def remove(self, name):
        return _core.remove_ignore(name)


def _as_tile(dest):
    """A Tile, or (x, z) on your level."""
    if isinstance(dest, (tuple, list)) and len(dest) == 2:
        return Tile(dest[0], dest[1], _core.get_level())
    return Tile.from_tile(dest)


# rs2b0t re-clicks a walk that hasn't moved, or every 2.4 seconds.
RECLICK_MS = 2400


class _DirectNavigator:
    """Walking within the area the server has loaded, routed around obstacles as the webclient does.
    last_outcome says how the last walk_to ended: 'arrived', 'unreachable' or 'timeout'."""

    last_outcome = None

    def walk(self, dest, run=False):
        """One walk toward the tile. False when it's in view but can't be reached."""
        tile = _as_tile(dest)
        return _core.walk_to(tile.x, tile.z, run)

    def walk_to(self, dest, radius=2, timeout_ms=45000, run=False):
        """Walks until within radius tiles of dest, clicking again when the walk stalls. Use with yield from;
        True on arrival, False at the timeout."""
        tile = _as_tile(dest)
        deadline = _core.step_time() + timeout_ms
        last_click = None
        last_tile = None
        while _core.step_time() < deadline:
            here = local_tile()
            if here.distance_to(tile) <= radius:
                self.last_outcome = 'arrived'
                return True
            stalled = last_tile is not None and here == last_tile
            if last_click is None or stalled or _core.step_time() - last_click > RECLICK_MS:
                if not _core.walk_to(tile.x, tile.z, run):
                    self.last_outcome = 'unreachable'
                    return False
                last_click = _core.step_time()
            last_tile = here
            yield from execution.delay_ticks(2)
        self.last_outcome = 'timeout'
        return False

    def walk_path(self, points, run=False):
        """Walks through up to 25 (x, z) waypoints, each leg in a straight line, without routing."""
        return _core.walk_path(points, run)

    def reachable(self, dest):
        """Whether a walk can end on the tile."""
        tile = _as_tile(dest)
        return _core.is_reachable(tile.x, tile.z)

    def path(self, dest):
        """The waypoints a walk to the tile would send, as Tiles, or None without a route."""
        tile = _as_tile(dest)
        waypoints = _core.find_path(tile.x, tile.z)
        if waypoints is None:
            return None
        return [Tile(x, z, tile.level) for x, z in waypoints]

    def destination(self):
        """Where the last walk is heading, until it ends."""
        point = _core.get_walk_destination()
        if point is None:
            return None
        return Tile(point[0], point[1], _core.get_level())


game = _Game()
skills = _Skills()
reader = _Reader()
chat = _Chat()
friends = _Friends()
ignores = _Ignores()
direct_navigator = _DirectNavigator()

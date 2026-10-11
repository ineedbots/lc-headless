"""The side tabs: quests, prayer, the special attack bar, combat styles, spells and autocast. Mirrors rs2b0t's
api/ui/questlog/Quests.ts, api/prayer/Prayer.ts, api/combat/Special.ts, CombatStyle.ts and CombatStyleLogic.ts,
api/magic/Autocast.ts and the combat and magic parts of api/game/Game.ts (MIT, see thirdparty/rs2b0t).

Everything is found in the tab's interface by what it is, so a weapon swap that changes the combat tab just
works: prayers are the prayer tab's Toggle buttons, combat styles the Select buttons that set the combat mode
with the label beside each, spells the magic tab's Target buttons by the spell they name.
"""

import _core
from rs2004 import execution
from rs2004.items import equipment

__all__ = [
    'Quest', 'CombatStyleResolution', 'quests', 'prayer', 'special', 'autocast', 'parse_combat_style',
    'try_parse_combat_style', 'parse_interface_combat_style', 'resolve_combat_style', 'parse_range_style',
    'COMBAT_STYLE_OPTIONS', 'RANGE_STYLE_OPTIONS', 'PRAYER_NAMES', 'AUTOCAST_SPELLS', 'SA_MAX_ENERGY',
]

COMBAT_TAB = 0
QUEST_TAB = 2
PRAYER_TAB = 5
MAGIC_TAB = 6

COM_MODE_VARP = 43
QUEST_POINTS_VARP = 101
ATTACKSTYLE_MAGIC_VARP = 108
# option_nodef, inverted: 0 is auto-retaliate on.
RETALIATE_VARP = 172
SA_ENERGY_VARP = 300
SA_ARMED_VARP = 301
SA_MAX_ENERGY = 1000
AUTOCAST_CHOSEN = 2
AUTOCAST_ARMED = 3
PRAYER_STAT = 5
WEAPON_SLOT = 3

TOGGLE_TIMEOUT_MS = 2000
JOURNAL_TIMEOUT_MS = 5000
AUTOCAST_STEP_MS = 3000
ARM_TICKS = 2


def clean_text(text):
    """Text without colour tags such as @gre@, and with runs of spaces as one."""
    out = ''
    i = 0
    while i < len(text):
        if text[i] == '@' and i + 4 < len(text) and text[i + 4] == '@':
            out += ' '
            i += 5
            continue
        out += text[i]
        i += 1
    return ' '.join(out.split())


def _tab(tab):
    return _core.get_tab_interface(tab)


def _components(tab):
    root = _tab(tab)
    return _core.get_interface(root) if root >= 0 else []


def _select_button(varp, value):
    """The visible Select button in an open interface that sets varp to value, or None."""
    for root in _core.get_open_interfaces():
        for component in _core.get_interface(root):
            if component.button == 'select' and component.varp == varp and component.value == value and component.visible:
                return component
    return None


# Quests

class Quest:
    """A row of the quest list: name, status ('not_started', 'in_progress', 'complete' or 'unknown') and com,
    the row's button."""

    def __init__(self, name, status, com):
        self.name = name
        self.status = status
        self.com = com

    def __repr__(self):
        return f'Quest({repr(self.name)}, {repr(self.status)})'


def quest_status(colour):
    """The status the quest list's colour shows: red, yellow or green."""
    red = (colour >> 16) & 0xFF
    green = (colour >> 8) & 0xFF
    if red >= 0x80 and green < 0x80:
        return 'not_started'
    if red >= 0x80 and green >= 0x80:
        return 'in_progress'
    if green >= 0x80 and red < 0x80:
        return 'complete'
    return 'unknown'


class _Quests:
    """The quest list. Only the list's colours, the quest points and the journals are on the wire."""

    def all(self):
        return [Quest(clean_text(c.text), quest_status(c.colour), c.id) for c in _components(QUEST_TAB) if c.type == 'text' and c.button == 'ok' and c.text]

    def _find(self, name):
        wanted = name.strip().lower()
        for quest in self.all():
            if quest.name.lower() == wanted:
                return quest
        return None

    def status(self, name):
        quest = self._find(name)
        return quest.status if quest is not None else 'unknown'

    def points(self):
        return _core.get_varp(QUEST_POINTS_VARP)

    def journal(self, name):
        """Opens the quest's journal and gives its lines. Use with yield from."""
        quest = self._find(name)
        if quest is None:
            return []
        before = _core.get_main_modal()
        if not _core.click_component(quest.com):
            return []
        opened = yield from execution.delay_until(lambda: _core.get_main_modal() not in (-1, before), JOURNAL_TIMEOUT_MS)
        return _core.get_texts(_core.get_main_modal()) if opened else []


# Prayer

PRAYER_NAMES = [
    'thick skin', 'burst of strength', 'clarity of thought', 'rock skin', 'superhuman strength',
    'improved reflexes', 'rapid restore', 'rapid heal', 'protect item', 'steel skin', 'ultimate strength',
    'incredible reflexes', 'protect from magic', 'protect from missiles', 'protect from melee',
]
PRAYER_LEVELS = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43]


def _prayer_index(name):
    wanted = name.strip().lower()
    for i in range(len(PRAYER_NAMES)):
        if PRAYER_NAMES[i] == wanted:
            return i
    return -1


class _Prayer:
    """Prayer points and the prayers, by name: 'protect from melee' and so on. A prayer's button is its place
    among the prayer tab's toggles, in prayer.if's order, and whether it's on is the varp its button reads."""

    def points(self):
        return _core.get_current_stat(PRAYER_STAT)

    def max(self):
        return _core.get_max_stat(PRAYER_STAT)

    def full(self):
        top = self.max()
        return top > 0 and self.points() >= top

    def known(self, name):
        return _prayer_index(name) != -1

    def available(self, name):
        """Your level is high enough and points remain."""
        i = _prayer_index(name)
        return i != -1 and self.max() >= PRAYER_LEVELS[i] and self.points() > 0

    def _button(self, name):
        i = _prayer_index(name)
        if i == -1:
            return None
        toggles = [c for c in _components(PRAYER_TAB) if c.button == 'toggle']
        return toggles[i] if i < len(toggles) else None

    def active(self, name):
        button = self._button(name)
        return button is not None and button.varp is not None and _core.get_varp(button.varp) == 1

    def set(self, name, on):
        """Turns the prayer on or off, and waits for the server to agree. Use with yield from."""
        button = self._button(name)
        if button is None:
            return False
        if self.active(name) == on:
            return True
        if on and not self.available(name):
            return False
        if not _core.click_component(button.id):
            return False
        done = yield from execution.delay_until(lambda: self.active(name) == on, TOGGLE_TIMEOUT_MS)
        return done

    def clear(self):
        """Turns off every prayer that's on."""
        for name in PRAYER_NAMES:
            if self.active(name):
                yield from self.set(name, False)


# The special attack

SPEC_COST = {
    'dragon dagger': 250, 'dragon dagger(p)': 250, 'dragon longsword': 250, 'dragon mace': 250,
    'dragon spear': 250, 'dragon spear(p)': 250, 'dragon spear(kp)': 250, 'dragon halberd': 300,
    'rune claws': 250, 'rune thrownaxe': 100, 'magic shortbow': 350, 'magic longbow': 350,
}


class _Special:
    """Weapon special attacks. Arming is one-shot: the bar arms the next attack, which spends it."""

    def energy(self):
        """0 to 1000."""
        return _core.get_varp(SA_ENERGY_VARP)

    def armed(self):
        return _core.get_varp(SA_ARMED_VARP) == 1

    def wielded(self):
        """The wielded weapon's name, or '' with empty hands."""
        for item in equipment.items():
            if item.slot == WEAPON_SLOT:
                return item.name or ''
        return ''

    def cost(self, weapon_name):
        """The energy the weapon's special costs, or None for one without."""
        return SPEC_COST.get(weapon_name.strip().lower())

    def ready(self, weapon_name):
        cost = self.cost(weapon_name)
        return cost is not None and self.energy() >= cost

    def bar_component(self):
        """The special attack bar in the combat tab, or -1 when the weapon has none."""
        for component in _components(COMBAT_TAB):
            if component.button == 'ok' and component.visible and 'special attack' in clean_text(component.button_text or '').lower():
                return component.id
        return -1

    def arm(self):
        """Arms the next attack; an armed one is left alone. Use with yield from."""
        if self.armed():
            return True
        bar = self.bar_component()
        if bar == -1 or not _core.click_component(bar):
            return False
        armed = yield from execution.delay_until_ticks(lambda: self.armed(), ARM_TICKS)
        return armed


# Combat styles

COMBAT_STYLE_OPTIONS = ['attack', 'strength', 'controlled', 'defence']
_COMBAT_STYLES = {
    'attack': 'attack', 'accurate': 'attack', 'strength': 'strength', 'aggressive': 'strength',
    'controlled': 'controlled', 'shared': 'controlled', 'defence': 'defence', 'defense': 'defence',
    'defensive': 'defence',
}
_INTERFACE_STYLES = {'accurate': 'attack', 'aggressive': 'strength', 'controlled': 'controlled', 'defensive': 'defence'}
RANGE_STYLE_OPTIONS = ['accurate', 'rapid', 'longrange']
_RANGE_MODES = {'accurate': 0, 'rapid': 1, 'longrange': 2, 'long range': 2, 'long-range': 2}


def parse_combat_style(name):
    """A melee training style, 'strength' for one it doesn't know."""
    return _COMBAT_STYLES.get(name.strip().lower(), 'strength')


def try_parse_combat_style(name):
    return _COMBAT_STYLES.get(name.strip().lower())


def parse_interface_combat_style(label):
    """The training style a combat tab's label names, such as 'attack' for '(Accurate)', or None."""
    key = label.strip()
    if key.startswith('('):
        key = key[1:]
    if key.endswith(')'):
        key = key[:-1]
    return _INTERFACE_STYLES.get(key.strip().lower())


def parse_range_style(name):
    """The combat mode of a ranged style: 0 accurate, 1 rapid, 2 long range."""
    return _RANGE_MODES.get(name.strip().lower(), 1)


class CombatStyleResolution:
    """requested, the style asked for; effective, the one the weapon gives; and mode, the button's mode."""

    def __init__(self, requested, effective, mode):
        self.requested = requested
        self.effective = effective
        self.mode = mode

    def __repr__(self):
        return f'CombatStyleResolution({repr(self.requested)}, {repr(self.effective)}, {self.mode})'


def resolve_combat_style(style, offered):
    """The mode that trains style among the offered (mode, label) pairs: the matching label, else the last
    defensive one. None when neither is offered."""
    modes = []
    seen = []
    for mode, label in offered:
        effective = parse_interface_combat_style(label)
        if effective is None or mode in seen:
            continue
        seen.append(mode)
        modes.append((mode, effective))
    for mode, effective in modes:
        if effective == style:
            return CombatStyleResolution(style, effective, mode)
    fallback = None
    for mode, effective in modes:
        if effective == 'defence':
            fallback = CombatStyleResolution(style, effective, mode)
    return fallback


def combat_styles():
    """The combat tab's style buttons as (mode, label), top to bottom: each Select button that sets the
    combat mode, with the label drawn level with it in its layer. None before the tab is sent."""
    components = _components(COMBAT_TAB)
    if not components:
        return None
    labels = [c for c in components if c.type == 'text' and parse_interface_combat_style(c.text) is not None]
    buttons = [c for c in components if c.button == 'select' and c.varp == COM_MODE_VARP and c.value is not None]
    buttons.sort(key=lambda c: (c.y, c.x, c.id))
    offered = []
    for button in buttons:
        best = None
        for label in labels:
            centre = label.y + label.height // 2
            if label.layer != button.layer or centre < button.y or centre > button.y + button.height:
                continue
            distance = abs(centre - (button.y + button.height // 2))
            if best is None or distance < best[0]:
                best = (distance, label.text)
        if best is not None:
            offered.append((button.value, best[1]))
    return offered


# Spells

AUTOCAST_SPELLS = [
    'wind strike', 'water strike', 'earth strike', 'fire strike', 'wind bolt', 'water bolt', 'earth bolt',
    'fire bolt', 'wind blast', 'water blast', 'earth blast', 'fire blast', 'wind wave', 'water wave',
    'earth wave', 'fire wave',
]


def spell_button(spell):
    """The magic tab's Target button for the spell, by the name it gives, or -1."""
    wanted = spell.strip().lower()
    for component in _components(MAGIC_TAB):
        if component.button == 'target' and component.target_name is not None and component.target_name.lower() == wanted:
            return component.id
    return -1


def teleport_button(name):
    """The magic tab's button for a teleport, such as 'Varrock' or 'Varrock teleport', or -1."""
    key = clean_text(name).lower()
    if key.startswith('cast '):
        key = key[5:]
    if key.endswith(' teleport'):
        key = key[:-9]
    wanted = f'cast {key.strip()} teleport'
    for component in _components(MAGIC_TAB):
        if component.button == 'ok' and clean_text(component.button_text or '').lower() == wanted:
            return component.id
    return -1


class _Autocast:
    """Autocasting from a staff's combat tab."""

    def armed(self):
        return _core.get_varp(ATTACKSTYLE_MAGIC_VARP) == AUTOCAST_ARMED

    def staff_tab_attached(self):
        """The combat tab is a staff's, with its Choose Spell button."""
        root = _tab(COMBAT_TAB)
        return root >= 0 and 'Choose' in _core.get_texts(root)

    def arm(self, spell, log=None):
        """Chooses the spell to autocast and turns autocasting on. Use with yield from."""
        def say(message):
            if log is not None:
                log(message)

        wanted = spell.strip().lower()
        if wanted not in AUTOCAST_SPELLS:
            say(f'{repr(spell)} is not an autocast spell')
            return False
        if not self.staff_tab_attached():
            say('the combat tab is not a staff\'s: is a staff wielded?')
            return False
        staff_tab = _tab(COMBAT_TAB)
        if not _core.click_text('Choose', staff_tab):
            return False
        opened = yield from execution.delay_until(lambda: _tab(COMBAT_TAB) != staff_tab, AUTOCAST_STEP_MS)
        if not opened:
            say('the spell chooser did not open')
            return False
        choices = [c for c in _components(COMBAT_TAB) if c.button == 'ok']
        index = AUTOCAST_SPELLS.index(wanted)
        if index >= len(choices) or not _core.click_component(choices[index].id):
            return False
        chosen = yield from execution.delay_until(lambda: _core.get_varp(ATTACKSTYLE_MAGIC_VARP) == AUTOCAST_CHOSEN, AUTOCAST_STEP_MS)
        if not chosen:
            say(f'choosing {spell} did not take: is your Magic level too low?')
            return False
        toggle = _select_button_reading(ATTACKSTYLE_MAGIC_VARP)
        if toggle is None or not _core.click_component(toggle.id):
            return False
        armed = yield from execution.delay_until(lambda: self.armed(), AUTOCAST_STEP_MS)
        if armed:
            say(f'autocast armed: {spell}')
        return armed


def _select_button_reading(varp):
    for component in _components(COMBAT_TAB):
        if component.button == 'select' and component.varp == varp:
            return component
    return None


quests = _Quests()
prayer = _Prayer()
special = _Special()
autocast = _Autocast()

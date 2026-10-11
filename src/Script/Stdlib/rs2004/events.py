"""The event bus. Every event has one name, used by events.on(name, callback), bot.on(name, callback) and a
hook named on_<name>. The events rs2b0t has (api/events/EventBus.ts, MIT, see thirdparty/rs2b0t) pass one
payload object with its fields; the rest pass their values as arguments."""

__all__ = ['events', 'Event']

SKILL_NAMES = {
    0: 'attack', 1: 'defence', 2: 'strength', 3: 'hitpoints', 4: 'ranged', 5: 'prayer', 6: 'magic',
    7: 'cooking', 8: 'woodcutting', 9: 'fletching', 10: 'fishing', 11: 'firemaking', 12: 'crafting',
    13: 'smithing', 14: 'mining', 15: 'herblore', 16: 'agility', 17: 'thieving', 20: 'runecraft',
}


class Event:
    """An event's payload: one attribute per field."""

    def __init__(self, fields):
        self._fields = fields
        for key, value in fields.items():
            setattr(self, key, value)

    def __repr__(self):
        parts = [f'{key}={repr(value)}' for key, value in self._fields.items()]
        return 'Event(' + ', '.join(parts) + ')'


def _skill_name(skill):
    return SKILL_NAMES.get(skill)


# Events whose callbacks get one Event, built from the values the host passes.
PAYLOADS = {
    'tick': lambda tick: {'tick': tick},
    'chat_message': lambda type, username, text: {'type': type, 'username': username, 'text': text},
    'skill_xp': lambda skill, xp, delta: {'skill': skill, 'name': _skill_name(skill), 'xp': xp, 'delta': delta},
    'skill_level': lambda skill, level, previous: {'skill': skill, 'name': _skill_name(skill), 'level': level, 'previous': previous},
    'inventory_changed': lambda slot, id, name, count, previous_id, previous_count: {
        'slot': slot, 'id': id, 'name': name, 'count': count, 'previous_id': previous_id, 'previous_count': previous_count,
    },
    'varp_changed': lambda index, value, previous: {'index': index, 'value': value, 'previous': previous},
    'script_finish': lambda reason: {'reason': reason},
}

# Events whose callbacks get the values themselves.
POSITIONAL = (
    'server_message', 'private_message', 'trade_request', 'duel_request',
    'npc_spawned', 'npc_despawned', 'npc_damaged',
    'player_spawned', 'player_despawned', 'player_damaged', 'damaged',
    'ground_item_spawned', 'ground_item_despawned', 'ground_item_changed',
    'loc_changed', 'interface_changed', 'system_update',
    'disconnect', 'reconnect', 'kill_signal', 'bot_message',
    'death', 'npc_say', 'projectile',
)

# A bot's lifecycle, which has hooks but no subscribers.
LIFECYCLE = ('start', 'stop', 'progress_report')

EVENT_NAMES = tuple(list(PAYLOADS.keys()) + list(POSITIONAL))
HOOK_NAMES = tuple(list(EVENT_NAMES) + list(LIFECYCLE))

# The names something listens to, by hook or subscription. The host reads it to skip events nobody wants,
# so it's only ever changed in place.
listening = {}
_hooks = []


def make_args(name, args):
    """The arguments callbacks of this event get."""
    build = PAYLOADS.get(name)
    if build is None:
        return args
    return (Event(build(*args)),)


class EventBus:
    """Subscriptions to events, by name."""

    def __init__(self):
        self._subscribers = {}

    def on(self, event, callback):
        """Calls callback each time the event happens, until the returned function is called."""
        if event not in EVENT_NAMES:
            raise ValueError(f'{repr(event)} is not an event; the events are {", ".join(EVENT_NAMES)}')
        if not callable(callback):
            raise TypeError('an event callback must be callable')

        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)
        _refresh()

        def unsubscribe():
            self.off(event, callback)

        return unsubscribe

    def off(self, event, callback):
        callbacks = self._subscribers.get(event)
        if callbacks is None:
            return
        for i in range(len(callbacks)):
            if callbacks[i] is callback:
                callbacks.pop(i)
                break
        if not callbacks:
            del self._subscribers[event]
        _refresh()

    def subscribers(self, event):
        return list(self._subscribers.get(event, []))

    def clear(self):
        self._subscribers = {}
        _refresh()


events = EventBus()


def set_hooks(names):
    """The event names the bot has hooks for."""
    global _hooks
    _hooks = list(names)
    _refresh()


def _refresh():
    listening.clear()
    for name in _hooks:
        listening[name] = True
    for name in events._subscribers:
        listening[name] = True

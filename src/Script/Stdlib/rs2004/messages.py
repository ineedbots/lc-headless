"""Game messages since a mark, to tell what the server said after an action. Mirrors rs2b0t's
api/chatbox/gameMessages.ts (MIT, see third_party/rs2b0t), over the last 100 messages the client keeps.

    mark = game_messages.mark()
    loc.interact('Open')
    yield from execution.delay_until(lambda: game_messages.saw_since(mark, CANT_REACH), 3000)

A pattern is text, matched as part of the message without regard to case, or a callable given the text.
"""

import _core

__all__ = ['game_messages', 'CANT_REACH', 'WRONG_SIDE']

CANT_REACH = "i can't reach that"


def WRONG_SIDE(text):
    """The op reached the loc and the server refused the side it came from: "You can't do that from here."
    or "You cannot do that from here."."""
    lower = text.lower()
    return "can't do that from here" in lower or 'cannot do that from here' in lower


def _matches(pattern, text):
    if callable(pattern):
        return pattern(text)
    return pattern.lower() in text.lower()


class GameMessage:
    """seq, the message's place in the order they came, and text."""

    def __init__(self, seq, text):
        self.seq = seq
        self.text = text

    def __repr__(self):
        return f'GameMessage({self.seq}, {repr(self.text)})'


class _GameMessages:
    def mark(self):
        """A mark: messages after now come after it."""
        return _core.message_mark()

    def since(self, mark):
        return [GameMessage(seq, text) for seq, text in _core.game_messages_since(mark)]

    def saw_since(self, mark, pattern):
        return self.first_since(mark, pattern) is not None

    def first_since(self, mark, pattern):
        for message in self.since(mark):
            if _matches(pattern, message.text):
                return message
        return None

    def recent(self, limit=8):
        """The newest messages, newest first."""
        messages = self.since(0)
        messages.reverse()
        return messages[:limit]


game_messages = _GameMessages()

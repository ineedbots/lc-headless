"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/verdict.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.messages import CANT_REACH, WRONG_SIDE, game_messages

__all__ = ['verdict_since', 'said_since']

# Why: every obstacle in the pass announces its outcome in the chatbox in the tick the op resolves, so waiting on a tile instead costs a refusal the full crossing timeout, the settle and the reachability poll. The op's own words are the fastest oracle.
REFUSED = [
    CANT_REACH,
    WRONG_SIDE,
    'is being used',
    'blocked by a grill',
    'cannot open the grill from this side',
    'need a thieving level',
]
FAILED = [
    'but you slip back down',
    'you fail to pick the lock',
    'and fall off it',
    'you fall in to the rat pit',
    'but you slip and tumble into the darkness',
    'you try to swing but fall in to the darkness',
    'and fail, activating the trap',
]
CROSSING = [
    'and step down the other side',
    'you manage to pick the lock',
    'you walk through',
    'you crawl through the pipe',
    'you skillfully swing across',
    'and make it.',
    'you manage to cross safely',
    'and quickly walk over',
    'and succeed, you quickly walk past',
]
CLASSES = [['refused', REFUSED], ['failed', FAILED], ['crossing', CROSSING]]


def _says(text, pattern):
    return pattern(text) if callable(pattern) else pattern in text.lower()


def verdict_since(mark):
    """What the obstacle said since `mark`, or null while it has said nothing. Why: the last verdict. One attempt loop keeps one mark across 4 rolls, so a seam that slipped then landed has both a failure and a crossing in the ring, and the last one says where you are now."""
    said = game_messages.since(mark)
    for i in range(len(said) - 1, -1, -1):
        text = said[i].text
        for verdict, patterns in CLASSES:
            if any([_says(text, p) for p in patterns]):
                return verdict
    return None


def said_since(mark, count, separator=' / '):
    """The last count messages since the mark, on one line."""
    texts = [message.text for message in game_messages.since(mark)]
    return separator.join(texts[-count:])

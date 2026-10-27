"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/config.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record


__all__ = ['arrav_config', 'hash_name', 'resolve_gang']

arrav_config = Record({'gang': 'random', 'partner': '', 'cert_target': 2})


# Why: the gang has to come out the same on every run of one character, and nothing durable stores the choice.
def hash_name(name):
    hash_ = 0x811c9dc5
    for ch in name.lower():
        if ch in 'abcdefghijklmnopqrstuvwxyz0123456789':
            hash_ = ((hash_ ^ ord(ch)) * 0x01000193) & 0xffffffff
    return hash_


def resolve_gang(setting, player_name):
    if setting != 'random':
        return setting
    # Why: the name lands a few ticks after login, and guessing blackarm before then commits to a key no partner has been asked for.
    if not player_name:
        return 'phoenix'
    return ('phoenix' if (hash_name(player_name) & 1) == 0 else 'blackarm')

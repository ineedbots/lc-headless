"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/config.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.quests.defs.shieldofarrav.config import arrav_config, resolve_gang

__all__ = ['hero_config', 'hero_gang', 'reset_hero_gang_cache', 'partner_configured']

hero_config = Record({'partner': ''})
cached = None
cached_for = ''


# Why: Grip refuses a Black Arm attacker and Katrine a Phoenix candlestick, so the gang here is the one
# the character joined for Shield of Arrav rather than a second roll.
# Why: the name lands a few ticks after login, so re-resolving every tick would flip the gang mid-run.
def hero_gang():
    global cached, cached_for
    _v1 = game.my_name()
    name = (_v1 if _v1 is not None else '')
    fingerprint = f'{arrav_config.gang}|{name}'
    if cached is None or (cached_for != fingerprint and len(name) > 0):
        cached = resolve_gang(arrav_config.gang, (name if len(name) > 0 else None))
        cached_for = fingerprint
    return cached


def reset_hero_gang_cache():
    """Test seam: the gang is memoised for the process, and a test that changes the setting has to clear it."""
    global cached, cached_for
    cached = None
    cached_for = ''


def partner_configured():
    return len(hero_config.partner.strip()) > 0

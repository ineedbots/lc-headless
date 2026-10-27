"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.engine.types import banked_id, held_id
from rs2004.quests.engine.types import QuestModule
from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import held_id
from rs2004.quests.defs.shieldofarrav.areas import SOA_HOPS, SOA_ID
from rs2004.quests.defs.shieldofarrav.blackarm import blackarm_step
from rs2004.quests.defs.shieldofarrav.certs import cert_step, certs_banked, certs_held, curator_step
from rs2004.quests.defs.shieldofarrav.config import arrav_config, resolve_gang
from rs2004.quests.defs.shieldofarrav.journal import read_shield_of_arrav_progress, SOA_STAGE
from rs2004.quests.defs.shieldofarrav.partner import arrav_handoff_state, decide_handoff, handoff_step
from rs2004.quests.defs.shieldofarrav.phoenix import phoenix_step
from rs2004.quests.defs.shieldofarrav.state import other_half, own_half
from rs2004.game import game

__all__ = ['reset_gang_cache', 'decide', 'shieldofarrav']

cached_gang = None
cached_for = ''


# Why: the character name lands a few ticks after login, and re-resolving every tick would flip the gang mid-run.
def gang():
    global cached_gang, cached_for
    _v1 = game.my_name()
    name = (_v1 if _v1 is not None else '')
    fingerprint = f'{arrav_config.gang}|{name}'
    if cached_gang is None or (cached_for != fingerprint and len(name) > 0):
        cached_gang = resolve_gang(arrav_config.gang, (name if len(name) > 0 else None))
        cached_for = fingerprint
    return cached_gang


def reset_gang_cache():
    global cached_gang, cached_for
    """Test seam: the gang is memoised for the process, and a test that changes the setting has to clear it."""
    cached_gang = None
    cached_for = ''


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v2 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v2 if _v2 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    mine = gang()
    # Why: `ownsInventory` skips the engine's provisioning, so nothing else opens a booth and a banked certificate or traded store key stays invisible until one read.
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    # Why: minting outranks every trade; a bot holding both halves must never hand one back.
    curator = curator_step(snap, mine)
    if curator:
        return curator
    handoff = decide_handoff(Record({
        'gang': mine,
        'stage': stage,
        'has_key': held_id(snap, SOA_ID.STORE_KEY) > 0,
        'has_own_half': held_id(snap, own_half(mine)) > 0,
        'has_other_half': held_id(snap, other_half(mine)) > 0,
        'certs': certs_held(snap) + certs_banked(snap),
        'certs_held': certs_held(snap),
        'cert_target': arrav_config.cert_target,
        'partner_configured': len(arrav_config.partner.strip()) > 0,
        'halves_given': arrav_handoff_state.halves_given,
        'gave_cert': arrav_handoff_state.gave_cert,
    }))
    if handoff:
        return handoff_step(handoff, mine)
    certs = cert_step(snap, mine)
    if certs:
        return certs
    # Why: one half and no way to a second is the dead end `warnReadiness` names; only a `wait` parks it, a failing `custom` step never does.
    if len(arrav_config.partner.strip()) == 0 and certs_held(snap) + certs_banked(snap) == 0 and held_id(snap, own_half(mine)) > 0:
        return Record({
            'kind': 'wait',
            'reason': "own half held, no partner and no banked certificate: the other gang's half is out of reach alone",
        })
    return (phoenix_step(snap) if mine == 'phoenix' else blackarm_step(snap))


shieldofarrav = QuestModule(**{
    'record': ([r for r in QUESTS if r.id == 'blackarmgang'] or [None])[0],
    'bank': 'nearest',
    'owns_inventory': True,
    'hops': list(SOA_HOPS),
    'grind': ['Jonny the beard', 'Weaponsmaster'],
    'tools': ['coins', 'broken shield', 'certificate', 'key', 'scroll', 'phoenix crossbow', 'book'],
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'read_progress': read_shield_of_arrav_progress,
    'warn_readiness': lambda: (None if len(arrav_config.partner.strip()) > 0 else 'Shield of Arrav needs a partner or a banked certificate — it cannot be finished alone'),
    'decide': decide,
})

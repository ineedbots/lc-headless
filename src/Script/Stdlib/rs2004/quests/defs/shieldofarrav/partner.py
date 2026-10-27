"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/partner.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.partner_handoff import run_handoff as run_partner_handoff
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID, SOA_TILE
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
from rs2004.quests.defs.shieldofarrav.state import other_half, own_half

__all__ = ['arrav_handoff_state', 'decide_handoff', 'run_handoff', 'handoff_step']

# Why: before farming a half and after giving one away the snapshot is the same (joined, no half, no certificate); the cupboard re-arms once the half leaves the pack, so nothing durable tells them apart.
# Why: a count, because a stockpile needs one half per 2 certificates and a flag would stop the supplier after the first.
# Why: session scope is enough; a restart farms another half, which is correct work.
arrav_handoff_state = Record({'halves_given': 0, 'gave_cert': False})


def decide_handoff(state):
    gang = state.gang
    stage = state.stage
    has_key = state.has_key
    has_own_half = state.has_own_half
    has_other_half = state.has_other_half
    certs = state.certs
    certs_held = state.certs_held
    cert_target = state.cert_target
    partner_configured = state.partner_configured
    halves_given = state.halves_given
    gave_cert = state.gave_cert
    """Who owes whom. The phoenix bot mints by convention, since it reaches Straven and the curator without being given anything first."""
    if not partner_configured:
        return None
    target = max(1, cert_target)
    if gang == 'phoenix':
        # Why: Straven re-issues the key whenever obj_gettotal reads zero, so giving it away costs nothing.
        if stage >= SOA_STAGE.PHOENIX_JOINED and stage < SOA_STAGE.COMPLETE and has_key:
            return 'give-key'
        if has_own_half and has_other_half:
            return None
        # Why: count the pack; a stockpile in the bank can't be offered, and the withdraw that fixes that is the certificate step's job.
        if not gave_cert and certs_held >= 2 and certs >= target:
            return 'give-cert'
        if has_own_half:
            return 'take-half'
        return None
    if stage == SOA_STAGE.KATRINE_TASK and not has_key:
        return 'take-key'
    if has_own_half:
        return 'give-half'
    # Why: each half buys 2 certificates, so the supplier keeps farming until the target is covered; asking before the cupboard leg has run waits on a certificate only its own half can buy.
    covered = halves_given * 2 >= max(1, cert_target)
    if stage == SOA_STAGE.BLACKARM_JOINED and certs == 0 and covered:
        return 'take-cert'
    return None


def item_for(handoff, gang):
    """What each handoff moves, and in which direction."""
    if handoff == 'give-key':
        return Record({'id': SOA_ID.STORE_KEY, 'name': 'Key', 'giving': True})
    elif handoff == 'take-key':
        return Record({'id': SOA_ID.STORE_KEY, 'name': 'Key', 'giving': False})
    elif handoff == 'give-half':
        return Record({'id': own_half(gang), 'name': 'Broken shield', 'giving': True})
    elif handoff == 'take-half':
        return Record({'id': other_half(gang), 'name': 'Broken shield', 'giving': False})
    elif handoff == 'give-cert':
        return Record({'id': SOA_ID.CERTIFICATE, 'name': 'Certificate', 'giving': True})
    elif handoff == 'take-cert':
        return Record({'id': SOA_ID.CERTIFICATE, 'name': 'Certificate', 'giving': False})


def run_handoff(handoff, gang, log):
    want = item_for(handoff, gang)
    moved = yield from run_partner_handoff(Record({
        'partner': arrav_config.partner,
        'rendezvous': SOA_TILE.RENDEZVOUS,
        'id': want.id,
        'name': want.name,
        'giving': want.giving,
        'label': handoff,
        'log': log,
    }))
    if not moved:
        return False
    if handoff == 'give-half':
        arrav_handoff_state.halves_given += 1
    if handoff == 'give-cert':
        arrav_handoff_state.gave_cert = True
    return True


def handoff_step(handoff, gang):
    return Record({
        'kind': 'custom',
        'name': f'{handoff} with {arrav_config.partner}',
        'run': lambda log: run_handoff(handoff, gang, log),
    })

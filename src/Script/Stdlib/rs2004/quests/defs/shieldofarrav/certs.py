"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/certs.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import banked_id, held_id
from rs2004.quests.defs.shieldofarrav.areas import CURATOR, ROALD, SOA_ID
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.exec.legs import talk_until
from rs2004.quests.defs.shieldofarrav.partner import arrav_handoff_state
from rs2004.quests.defs.shieldofarrav.state import other_half, own_half
from rs2004.items import inventory

__all__ = ['mint_certificates', 'redeem_certificate', 'SUSTAIN_KEEP', 'CERT_KEEP_IDS', 'certs_held', 'certs_banked', 'curator_step', 'cert_step']

# Why: both conversations run through `~mesbox` / `~objbox`, which build a main modal no chat driver can see.
def mint_certificates(log):
    """Hand both halves over for 2 certificates."""
    before = inventory.count_by_id(SOA_ID.CERTIFICATE)
    _result1 = yield from talk_until(CURATOR, [], lambda: inventory.count_by_id(SOA_ID.CERTIFICATE) > before, log)
    return _result1


def redeem_certificate(log):
    """Redeem one certificate with the king; that completes the quest."""
    before = inventory.count_by_id(SOA_ID.CERTIFICATE)
    _result2 = yield from talk_until(ROALD, [], lambda: inventory.count_by_id(SOA_ID.CERTIFICATE) < before, log)
    return _result2


SUSTAIN_KEEP = ['lobster', 'swordfish', 'tuna', 'trout', 'salmon']
CERT_KEEP_IDS = [SOA_ID.CERTIFICATE, SOA_ID.SHIELD_PHOENIX, SOA_ID.SHIELD_BLACKARM, SOA_ID.STORE_KEY, SOA_ID.COINS]


def certs_held(snap):
    return held_id(snap, SOA_ID.CERTIFICATE)


def certs_banked(snap):
    return banked_id(snap, SOA_ID.CERTIFICATE)


def curator_step(snap, gang):
    """Join both halves with the curator before any partner handoff."""
    pair = [own_half(gang), other_half(gang)]
    # Why: test the total across pack and bank; a predicate that flips as the halves move makes a withdraw and a deposit undo each other every tick.
    if any([held_id(snap, id) + banked_id(snap, id) == 0 for id in pair]):
        return None
    short = [id for id in pair if held_id(snap, id) == 0]
    if len(short) > 0:
        return Record({
            'kind': 'withdraw',
            'items': [({'name': 'Broken shield', 'qty': 1, 'id': id}) for id in short],
        })
    # Why: he mints 2 per pair and stops once either varp goes complete, so this is the only window.
    return Record({'kind': 'custom', 'name': 'mint two certificates at the curator', 'run': mint_certificates})


# Why: this runs after the handoffs, so the partner is paid before this bot spends the last certificate it holds.
def cert_step(snap, gang):
    """Redeeming, withdrawing and banking the surplus; null when nothing is due."""
    held = certs_held(snap)
    banked = certs_banked(snap)
    target = max(1, arrav_config.cert_target)
    # Why: only the phoenix bot reaches Straven and the curator unaided, so only it mints and only it is held to the stockpile target.
    # Why: Solo accounts cannot produce a second certificate, so do not wait for partner stock.
    minting = gang == 'phoenix' and len(arrav_config.partner.strip()) > 0
    # Why: test the total across pack and bank; a predicate that flips as certificates move makes the deposit and the withdraw undo each other every tick.
    # Why: handing the partner its certificate ends minting whatever the total reads, since giving one away drops it below target again.
    done_minting = not minting or arrav_handoff_state.gave_cert or held + banked >= target
    if done_minting:
        if held > 0:
            return Record({'kind': 'custom', 'name': 'claim the reward from King Roald', 'run': redeem_certificate})
        if banked > 0:
            # Why: withdraw 2 while a partner is owed one: redeem one, trade the other, and a trade can only offer from the pack.
            owed = len(arrav_config.partner.strip()) > 0 and not arrav_handoff_state.gave_cert and gang == 'phoenix'
            qty = (min(2, banked) if owed else 1)
            return Record({
                'kind': 'withdraw',
                'items': [{'name': 'Certificate', 'qty': qty, 'id': SOA_ID.CERTIFICATE}],
            })
        return None
    # Why: a spare half can't be banked (the chest and cupboard re-check the bank), so only the certificate stockpiles.
    if held >= 2:
        return Record({
            'kind': 'deposit',
            'keep': list(SUSTAIN_KEEP),
            'keep_ids': [id for id in CERT_KEEP_IDS if id != SOA_ID.CERTIFICATE],
        })
    return None

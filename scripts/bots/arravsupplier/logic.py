"""Ported from rs2b0t's src/bot/scripts/ArravSupplier/ArravSupplierLogic.ts (MIT, see thirdparty/rs2b0t)."""



__all__ = ['supplier_phase']

# Why: the journal is blank for a dual-gang character, so every field here is an item count or a door's own refusal.
# Why: it must never redeem. The king sets %phoenixgang complete, which seals the chest and stops the curator for good.
def supplier_phase(s):
    """The supplier's one decision."""
    if s.in_black_arm and s.in_phoenix:
        if s.certs_banked >= s.cert_target:
            return 'done'
        if s.phoenix_half > 0 and s.blackarm_half > 0:
            return 'mint'
        return ('take-blackarm-half' if s.phoenix_half > 0 else 'take-phoenix-half')
    if s.in_black_arm:
        # Why: [opnpcu,straven] is missing the black-arm guard that [opnpc1,straven] and the hideout door both carry, so using the report joins the second gang.
        return ('join-phoenix' if s.has_report else 'kill-jonny')
    if s.crossbows >= 2:
        return 'join-blackarm'
    if s.has_key:
        return 'raid-store'
    # Why: only Straven issues the store key, so the bootstrap key has to be traded in.
    return 'await-key'

"""Who to trade with, and what to do on the trade screen, for mule and runner bots. Ported from rs2b0t's
api/trade/PartnerTrade.ts (MIT, see thirdparty/rs2b0t). The trade itself is rs2004.trade's."""

DEFAULT_TRADE_RANGE = 2
MULE_MODE_OPTIONS = ['Off', 'Gatherer', 'Mule', 'Cooker', 'Supplier']


def parse_partner_list(raw):
    """Partner names from a comma-separated setting."""
    return [name.strip() for name in raw.split(',') if name.strip()]


def names_match(a, b):
    return a.strip().lower() == b.strip().lower()


def is_configured_partner(name, partners):
    if name is None or not name.strip() or not partners:
        return False
    wanted = name.strip().lower()
    return len([p for p in partners if p.strip().lower() == wanted]) > 0


def count_offer_by_name(items, item_name):
    """The count of offered items with that name; an item's count is at least 1."""
    wanted = item_name.strip().lower()
    return sum([max(1, i.count) for i in items if (i.name or '').strip().lower() == wanted])


def count_offer_matching(items, test):
    return sum([max(1, i.count) for i in items if i.name is not None and test(i.name)])


def decide_receiver_offer_screen(partner_header, partners, my_offer_slots, their_product_count):
    """On the first screen, receiving: ('wait-header',), ('decline', reason), ('wait-offer',) or ('accept',)."""
    if partner_header is None:
        return ('wait-header',)
    if not is_configured_partner(partner_header, partners):
        return ('decline', f'not a configured partner ({partner_header})')
    if my_offer_slots > 0:
        return ('decline', 'safety: own offer not empty')
    if their_product_count <= 0:
        return ('wait-offer',)
    return ('accept',)


def decide_giver_offer_screen(my_offer_slots):
    """On the first screen, giving: 'offer' the haul, then 'accept'."""
    return 'offer' if my_offer_slots <= 0 else 'accept'


def parse_mule_mode(raw):
    mode = raw.strip().lower()
    return mode if mode in ['gatherer', 'mule', 'cooker', 'supplier'] else 'off'


def mule_gatherer_handoff_active(mode, partners, power_mode):
    return mode == 'gatherer' and len(partners) > 0 and not power_mode


def mule_receiver_active(mode, partners):
    return mode == 'mule' and len(partners) > 0


def mule_cooker_active(mode, partners):
    return mode == 'cooker' and len(partners) > 0


def mule_supplier_active(mode, partners, power_mode):
    return mode == 'supplier' and len(partners) > 0 and not power_mode


def mule_non_gatherer_active(mode, partners):
    return mule_receiver_active(mode, partners) or mule_cooker_active(mode, partners) or (mode == 'supplier' and len(partners) > 0)

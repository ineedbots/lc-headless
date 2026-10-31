"""Nature Spirit's departures from rs2b0t, each found live."""

from rs2004.quests.defs.druidspirit import decide
from rs2004.quests.defs.druidspirit.areas import NS_ID, NS_STAGE
from rs2004.quests.defs.druidspirit.supplies import SILVER_MINING, SILVER_SMITHING, sickle_step
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot

BRONZE_PICKAXE = 1265


def snap(inv_ids, bank_ids=None):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv_ids': inv_ids,
        'bank_ids': bank_ids if bank_ids is not None else {},
        'bank_known': True,
        'stage': NS_STAGE.FULL_TRANSFORM,
        'progress': QuestProgress(NS_STAGE.FULL_TRANSFORM, set()),
    })


def waits_below_silver():
    step = sickle_step(snap({NS_ID.MOULD: 1, BRONZE_PICKAXE: 1}), SILVER_MINING - 1, SILVER_SMITHING)
    expect(step.kind).to_be('wait')
    expect(step.reason).to_contain(f'Mining {SILVER_MINING}')


test('below the silver rock\'s Mining level the chain waits with the reason, not a silent mine', waits_below_silver)


def waits_below_smelting():
    for inv in [{NS_ID.MOULD: 1, NS_ID.SILVER_ORE: 1}, {NS_ID.MOULD: 1, BRONZE_PICKAXE: 1}]:
        step = sickle_step(snap(inv), SILVER_MINING, SILVER_SMITHING - 1)
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain(f'Smithing {SILVER_SMITHING}')


test('below the silver bar\'s Smithing level the chain neither smelts nor mines ore it can\'t smelt', waits_below_smelting)


def mines_at_silver():
    step = sickle_step(snap({NS_ID.MOULD: 1, BRONZE_PICKAXE: 1}), SILVER_MINING, SILVER_SMITHING)
    expect(step.kind).to_be('mine_rock')


test('at the silver rock\'s Mining level it mines', mines_at_silver)


def bar_needs_no_skills():
    step = sickle_step(snap({NS_ID.MOULD: 1}, {NS_ID.SILVER_BAR: 1}), 1, 1)
    expect(step.kind).to_be('withdraw')


test('a banked silver bar needs neither Mining nor Smithing', bar_needs_no_skills)


def ghast_snap(worn, inv, bank, bank_known=True):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': inv,
        'inv_ids': {NS_ID.SICKLE_BLESSED: 1, NS_ID.POUCH: 3},
        'worn': worn,
        'worn_ids': set([NS_ID.GHOSTSPEAK]),
        'bank': bank,
        'bank_known': bank_known,
        'stage': NS_STAGE.ADDED_POUCH,
        'progress': QuestProgress(NS_STAGE.ADDED_POUCH, set()),
        'prayer': 40,
    })


def draws_melee_over_a_bow():
    step = decide(ghast_snap(set(['yew shortbow', 'rune chainbody']), {}, {'rune scimitar': 1, 'rune kiteshield': 1}))
    expect(step.kind).to_be('withdraw')
    expect([item['name'] for item in step.items]).to_equal(['Rune scimitar', 'Rune kiteshield'])


test('a bow left on from another quest is swapped for the banked melee kit before the ghasts', draws_melee_over_a_bow)


def wears_carried_kit():
    step = decide(ghast_snap(set(['yew shortbow']), {'rune scimitar': 1}, {}))
    expect(step.kind).to_be('custom')
    expect(step.name).to_be('wear Rune scimitar')


test('a carried melee weapon is worn before the ghasts', wears_carried_kit)


def armed_hunts():
    step = decide(ghast_snap(set(['rune scimitar', 'rune chainbody', 'rune platelegs', 'rune full helm', 'rune kiteshield']), {}, {}))
    expect(step.name).to_be('kill a ghast')


test('an armed account goes straight to the ghasts', armed_hunts)


def scans_unread_bank():
    step = decide(ghast_snap(set(['yew shortbow']), {}, {}, False))
    expect(step.kind).to_be('scan_bank')


test('after a restart an unread bank is scanned before the ghasts are fought bare-handed', scans_unread_bank)


def no_kit_anywhere():
    step = decide(ghast_snap(set(['yew shortbow']), {}, {}))
    expect(step.name).to_be('kill a ghast')


test('with no melee kit in the bank either, the hunt goes on', no_kit_anywhere)

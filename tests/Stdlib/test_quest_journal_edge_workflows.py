"""Journal readers preserve unavailable state and handle terminal quest-list statuses."""

import rs2004.quests.defs.ernest.journal as ernest
import rs2004.quests.defs.knightssword.journal as knight
import rs2004.quests.defs.princeali.journal as prince
import rs2004.quests.defs.shieldofarrav.journal as arrav
import rs2004.quests.defs.romeojuliet as romeo
import rs2004.quests.defs.doric as doric
import rs2004.quests.defs.princeali as pa
import rs2004.quests.defs.shieldofarrav.certs as certs
import rs2004.quests.defs.shieldofarrav.partner as partner
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_journal_readers_return_terminal_or_unknown_status_without_opening_scroll():
    readers = [(ernest, ernest.read_ernest_progress, 3), (knight, knight.read_knights_sword_progress, 7),
               (prince, prince.read_prince_progress, 110), (arrav, arrav.read_shield_of_arrav_progress, 30),
               (romeo, romeo.read_romeo_juliet_stage, 100), (doric, doric.read_doric_stage, 100)]
    for module, read, complete in readers:
        for status, expected in [('complete', complete), ('not_started', 0), ('unknown', None)]:
            with QuestWorld() as w:
                w.patch(module, 'quests', FakeModule(status=lambda name: status))
                result = w.run(read())
                assert (result.stage if hasattr(result, 'stage') else result) == expected, (module, status, result)


def test_romeo_journal_closes_scroll_and_supports_name_only_snapshots():
    with QuestWorld() as w:
        w.patch(romeo, 'quests', FakeModule(status=lambda n: 'in_progress',
                                          journal=lambda n: w.reply(['I should find Father Lawrence'])))
        w.pages = [('main', [])]
        assert w.run(romeo.read_romeo_juliet_stage()) == 30
        assert not w.pages
    item = romeo.ROMEO_JULIET_ITEM['BERRIES']
    snap = QuestSnapshot(inv={'cadava berries': 1}, bank={'cadava berries': 2})
    assert romeo._held(snap, item) and romeo._banked(snap, item) == 2


def test_prince_journal_retries_empty_scroll_instead_of_inventing_a_stage():
    with QuestWorld() as w:
        w.patch(prince, 'quests', FakeModule(status=lambda n: 'in_progress', journal=lambda n: w.reply([])))
        w.patch(prince, 'reader', FakeModule(modals=lambda: FakeModule(main=-1)))
        assert w.run(prince.read_prince_progress()) is None
        assert len(w.waits) == 6
    assert arrav.parse_shield_of_arrav_journal(['unrelated text']) is None


def test_doric_name_snapshot_preserves_materials_picks_and_nearest_bank():
    snap = QuestSnapshot(inv={'clay': 6, 'bronze pickaxe': 1}, worn={'bronze pickaxe'},
                         bank={'clay': 2, 'bronze pickaxe': 1}, tile=Tile(2946, 3369))
    assert doric.held_count(snap, doric.DORIC_ITEM.CLAY) == 6
    assert doric.banked_count(snap, doric.DORIC_ITEM.CLAY) == 2
    assert doric.pick_held(snap, doric.DORIC_PICKAXES[-1])
    assert doric.pick_banked(snap, doric.DORIC_PICKAXES[-1])
    assert not doric.has_depositable_item(snap)
    assert doric.nearest_bank(snap) == doric.BANKS[0]


def test_prince_leela_handover_propagates_dialogue_and_unknown_stage():
    for reached, talked in [(False, False), (True, False), (True, True)]:
        with QuestWorld() as w:
            w.patch(pa, 'goto_npc', lambda *a: w.reply(reached))
            w.patch(pa, 'talk_strict', lambda *a: w.reply(talked))
            assert w.run(pa.leela_handover(w.logs.append)) == (reached and talked)
    assert pa.decide(QuestSnapshot(journal='in_progress', stage=99, bank_known=True)).kind == 'wait'
    with QuestWorld() as w:
        w.patch(pa, 'PREP', [])
        snap = QuestSnapshot(journal='in_progress', stage=pa.PRINCE_STAGE.SPOKEN_OSMAN,
                             bank_known=True, inv={'coins': 5000}, inv_ids={995: 5000})
        assert 'disguise or key' in pa.decide(snap).reason


def test_arrav_certificate_actions_wait_for_counts_in_opposite_directions():
    with QuestWorld() as w:
        w.install(certs)
        def talk(stop, prefer, expect, log):
            yield from w.reply()
            w.pack = [QuestObject(w, 'Certificate', certs.SOA_ID.CERTIFICATE)] if stop == certs.CURATOR else []
            return expect()
        w.patch(certs, 'talk_until', talk)
        assert w.run(certs.mint_certificates(w.logs.append))
        assert w.run(certs.redeem_certificate(w.logs.append))


def test_arrav_partner_handoffs_move_exact_ids_and_update_only_proven_state():
    with QuestWorld() as w:
        w.patch(partner, 'arrav_handoff_state', FakeModule(halves_given=0, gave_cert=False))
        requests = []
        def handoff(spec):
            requests.append(spec)
            yield from w.reply()
            return spec.partner != 'failed'
        w.patch(partner, 'run_partner_handoff', handoff)
        w.patch(partner, 'arrav_config', FakeModule(partner='friend'))
        for name in ['give-key', 'take-key', 'give-half', 'take-half', 'give-cert', 'take-cert']:
            assert w.run(partner.run_handoff(name, 'phoenix', w.logs.append))
        assert partner.arrav_handoff_state.halves_given == 1 and partner.arrav_handoff_state.gave_cert
        assert requests[0].giving and not requests[1].giving
        w.patch(partner, 'arrav_config', FakeModule(partner='failed'))
        assert not w.run(partner.run_handoff('give-half', 'phoenix', w.logs.append))
        assert partner.arrav_handoff_state.halves_given == 1

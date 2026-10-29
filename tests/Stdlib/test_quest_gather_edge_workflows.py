"""Quest collection and hand-ins require the expected world or inventory update."""

import rs2004.quests.defs.blackknight as bk
import rs2004.quests.defs.hetty as hetty
import rs2004.quests.defs.romeojuliet as rj
import rs2004.quests.defs.impcatcher as imp
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_fortress_listens_once_then_uses_cabbage_on_upper_floor_hole():
    with QuestWorld() as w:
        w.install(bk)
        w.patch(bk, 'bkf_state', bk._BkfState())
        assert w.run(bk.infiltrate(w.logs.append))
        cabbage = QuestObject(w, 'Cabbage', effect=lambda: setattr(w, 'pack', []))
        w.pack = [cabbage]
        assert w.run(bk.pick_cabbage(w.logs.append))
        for status in ['unreachable', 'failed', 'done']:
            w.patch(bk, 'reach', FakeModule(loc_op=lambda *a, **kw: w.reply(status)))
            if status == 'done':
                w.pages = [('continue', ['A sinister plot'])]
            assert w.run(bk.infiltrate(w.logs.append)) is False
            assert bk.bkf_state.listened == (status == 'done')
        w.scene = [QuestObject(w, 'Hole', at=bk.HOLE)]
        assert w.run(bk.infiltrate(w.logs.append)) is False
        assert not w.pack and w.walks[-1] == bk.HOLE
        w.position = bk.GRILL
        assert bk._grill_answered()
        w.position = None
        assert not bk._near_tile(bk.GRILL, 1)


def test_fortress_cabbage_gatherer_drives_reach_and_returns_a_custom_step():
    with QuestWorld() as w:
        w.install(bk)
        calls = []
        def pick(name, op, tile, expect, **kw):
            calls.append((name, op))
            yield from w.reply()
            w.pack = [QuestObject(w, 'Cabbage')]
            assert expect()
            return 'done'
        w.patch(bk, 'reach', FakeModule(loc_op=pick))
        step = bk._gather_cabbage(QuestSnapshot())
        assert not w.run(step.run(w.logs.append))
        assert calls == [('Cabbage', 'Pick')]


def test_hetty_tail_pickup_and_rat_attack_failures():
    with QuestWorld() as w:
        w.install(hetty)
        w.patch(hetty, 'game', FakeModule(tile=lambda: w.position, set_combat_style=lambda style: w.actions.append(style)))
        tail = QuestObject(w, hetty.RATS_TAIL, effect=lambda: w.pack.append(QuestObject(w, hetty.RATS_TAIL)))
        w.scene = [tail]
        tail.accept = False
        assert not w.run(hetty.kill_rat_grab_tail(w.logs.append))
        tail.accept = True
        assert w.run(hetty.kill_rat_grab_tail(w.logs.append))
        assert w.run(hetty.kill_rat_grab_tail(w.logs.append))
        w.pack = []
        w.scene = []
        w.can_walk = False
        assert not w.run(hetty.kill_rat_grab_tail(w.logs.append))
        w.can_walk = True
        assert not w.run(hetty.kill_rat_grab_tail(w.logs.append))
        rat = QuestObject(w, 'Rat', ops=['Attack'], at=hetty.RATS)
        rat.in_combat = False
        w.scene = [rat]
        rat.accept = False
        assert not w.run(hetty.kill_rat_grab_tail(w.logs.append))
        rat.accept = True
        rat.effect = lambda: setattr(w, 'scene', [])
        assert not w.run(hetty.kill_rat_grab_tail(w.logs.append))
        assert 'strength' in w.actions and ('Rat', 'Attack') in w.actions


def test_hetty_meat_cooks_or_burns_only_after_server_response():
    for mode in ['held', 'walk_failed', 'missing_meat', 'missing_range', 'refused', 'silent', 'burnt', 'make_menu']:
        with QuestWorld() as w:
            w.install(hetty)
            w.can_walk = mode != 'walk_failed'
            meat = QuestObject(w, 'Raw beef', effect=lambda: setattr(w, 'pack', [QuestObject(w, 'Burnt meat')]))
            meat.accept = mode != 'refused'
            w.respond = mode != 'silent'
            if mode == 'held':
                w.pack = [QuestObject(w, 'Burnt meat')]
            elif mode != 'missing_meat':
                w.pack = [meat]
            if mode != 'missing_range':
                w.scene = [QuestObject(w, 'Range', at=hetty.RANGE)]
            state = FakeModule(menu=mode == 'make_menu')
            burnt = lambda: setattr(w, 'pack', [QuestObject(w, 'Burnt meat')])
            def make(name=None):
                yield from w.reply()
                if name is None:
                    burnt()
                return name is None
            w.patch(hetty, 'chat_dialog', FakeModule(is_make_menu=lambda: state.menu, make=make))
            # A silent use is retried twelve times, so bound its simulated time through the normal update clock.
            assert w.run(hetty.burn_meat(w.logs.append)) == (mode in ['held', 'burnt', 'make_menu'])


def test_hetty_handin_requires_arrival_and_an_accepted_cauldron_action():
    for mode in ['unreached', 'walk_failed', 'missing', 'refused', 'done']:
        with QuestWorld() as w:
            w.install(hetty)
            w.patch(hetty, 'goto_npc', lambda *a: w.reply(mode != 'unreached'))
            w.patch(hetty, 'talk_through', lambda *a: w.reply())
            w.can_walk = mode != 'walk_failed'
            pot = QuestObject(w, 'Cauldron', ops=['Drink From'], at=hetty.CAULDRON)
            pot.accept = mode != 'refused'
            w.scene = [] if mode == 'missing' else [pot]
            assert w.run(hetty.hand_in_and_drink(w.logs.append)) == (mode == 'done')
    assert hetty._gather_for('unknown', QuestSnapshot()).kind == 'wait'


def test_romeo_stage_talk_reports_unreachable_refused_and_completed_dialogue():
    for reached, talked in [(False, False), (True, False), (True, True)]:
        with QuestWorld() as w:
            w.patch(rj, 'goto_npc', lambda *a: w.reply(reached))
            w.patch(rj, 'talk_strict', lambda *a: w.reply(talked))
            step = rj.decide(QuestSnapshot(journal='in_progress', stage=30))
            assert w.run(step.run(w.logs.append)) == (reached and talked)


def test_romeo_berry_collection_handles_respawn_loss_rejection_and_acknowledgement():
    for mode in ['full', 'walk_failed', 'empty', 'refused', 'silent', 'taken', 'respawn']:
        with QuestWorld() as w:
            w.install(rj)
            w.position = rj.BERRY_ANCHOR
            berry = QuestObject(w, 'Cadava berries', 753, effect=lambda: w.pack.append(QuestObject(w, 'Cadava berries', 753)))
            berry.accept = mode != 'refused'
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            if mode == 'full':
                w.pack = [QuestObject(w, 'Junk') for i in range(28)]
            if mode in ['refused', 'silent', 'taken']:
                w.scene = [berry]
            if mode == 'respawn':
                w.on_update = lambda: setattr(w, 'scene', [berry]) if w.now >= 1500 else None
            assert w.run(rj.pick_berries(w.logs.append)) == (mode in ['taken', 'respawn'])
            if mode in ['taken', 'respawn']:
                assert w.count_by_id(753) == 1


def test_imp_bead_pickup_requeries_after_walking_and_requires_inventory_gain():
    for mode in ['full', 'walk_failed', 'lost', 'refused', 'silent', 'taken']:
        with QuestWorld() as w:
            w.install(imp)
            drop = QuestObject(w, 'Red bead', 1470, at=Tile(3010, 3000),
                               effect=lambda: w.pack.append(QuestObject(w, 'Red bead', 1470)))
            drop.accept = mode != 'refused'
            w.scene = [] if mode == 'lost' else [drop]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            if mode == 'full':
                w.pack = [QuestObject(w, 'Junk') for i in range(28)]
            assert w.run(imp.take_bead(drop, w.logs.append)) == (mode == 'taken')


def test_imp_combat_tracks_death_teleport_competition_and_timeout():
    for mode in ['walk_failed', 'lost', 'refused', 'event', 'dead', 'teleport', 'contested', 'timeout']:
        with QuestWorld() as w:
            w.install(imp)
            w.patch(imp, '_core', w)
            w.patch(imp, 'sustain', FakeModule(run=lambda: w.reply()))
            npc = QuestObject(w, 'Imp', ops=['Attack'])
            npc.targets_another_player = lambda: mode == 'contested'
            npc.accept = mode != 'refused'
            w.scene = [] if mode == 'lost' else [npc]
            w.interrupted = mode == 'event'
            if mode == 'walk_failed':
                npc.at = Tile(3010, 3000)
                w.can_walk = False
            if mode == 'dead':
                npc.effect = lambda: setattr(w, 'scene', [])
            if mode == 'teleport':
                npc.effect = lambda: setattr(npc, 'at', Tile(3020, 3000))
            assert w.run(imp.kill_imp(npc, w.logs.append)) == (mode == 'dead')


def test_imp_farming_handles_finished_pack_drop_and_empty_field_search():
    with QuestWorld() as w:
        w.install(imp)
        w.pack = [QuestObject(w, b.name, b.id) for b in imp.IMP_BEADS]
        assert w.run(imp.farm_beads(w.logs.append))
        w.pack = []
        drop = QuestObject(w, 'Red bead', 1470, effect=lambda: w.pack.append(QuestObject(w, 'Red bead', 1470)))
        w.scene = [drop]
        assert w.run(imp.farm_beads(w.logs.append))
        w.scene = []
        assert w.run(imp.farm_beads(w.logs.append)) and w.walks[-1] == imp.IMP_STAND
        assert w.run(imp.farm_beads(w.logs.append)) and len(w.walks) == 2

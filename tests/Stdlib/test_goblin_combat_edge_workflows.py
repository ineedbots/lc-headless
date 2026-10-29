"""Goblin mail gathering releases stale locks and never steals another player's target."""

import rs2004.quests.defs.goblindiplomacy as gd
from rs2004 import execution
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_goblin_mail_combat_handles_rejection_competition_death_and_disengagement():
    for mode in ['empty', 'drop_refused', 'drop', 'dead', 'lost', 'contested', 'disengaged',
                 'attack_refused', 'no_combat', 'stolen', 'killed', 'throttled']:
        with QuestWorld() as w:
            w.install(gd)
            w.patch(gd, '_core', w)
            w.patch(gd, 'sustain', FakeModule(run=lambda: w.reply()))
            w.position = gd.GOBLIN_FARM
            w.now = 10000
            w.patch(gd, 'game', FakeModule(my_name=lambda: 'Tester', tile=lambda: w.position, in_combat=lambda: w.fighting))
            for name, value in [('goblin_mail_owner', 'Tester'), ('goblin_mail_target_index', None),
                ('goblin_mail_target_engaged', False), ('goblin_mail_last_attack_at', 0),
                ('goblin_mail_disengaged_at', 0), ('goblin_mail_rejected_target_index', None),
                ('goblin_mail_rejected_until', 0)]:
                w.patch(gd, name, value)
            npc = QuestObject(w, 'Goblin', 100, ['Attack'])
            npc.accept = mode != 'attack_refused'
            w.scene = [] if mode in ['empty', 'lost'] else [npc]
            if mode in ['drop', 'drop_refused']:
                drop = QuestObject(w, 'Goblin mail', effect=lambda: w.hold('Goblin mail'))
                drop.accept = mode != 'drop_refused'
                w.scene = [drop]
            if mode in ['dead', 'lost', 'contested', 'disengaged', 'throttled']:
                gd.goblin_mail_target_index = npc.index
                gd.goblin_mail_target_engaged = mode in ['lost', 'disengaged']
            if mode == 'dead':
                npc.alive = False
            if mode == 'contested':
                npc.contested = True
            if mode == 'disengaged':
                gd.goblin_mail_disengaged_at = 1
            if mode == 'throttled':
                gd.goblin_mail_last_attack_at = w.now
            if mode == 'stolen':
                npc.effect = lambda: setattr(npc, 'contested', True)
            elif mode == 'killed':
                npc.effect = lambda: setattr(w, 'scene', [])
            result = w.run(gd._farm_goblin_mail_tick(w.logs.append))
            assert result == (mode == 'drop'), (mode, w.logs)
            if mode in ['attack_refused', 'no_combat', 'stolen', 'contested', 'disengaged']:
                assert gd.goblin_mail_rejected_target_index == npc.index
            if mode in ['dead', 'lost', 'killed']:
                assert gd.goblin_mail_target_index is None


def test_goblin_mail_farm_yields_to_randoms_and_reports_timeout_without_mail():
    with QuestWorld() as w:
        w.install(gd)
        w.patch(gd, '_core', w)
        w.patch(gd, 'sustain', FakeModule(run=lambda: w.reply()))
        w.patch(execution, 'event_signal', FakeModule(pending=lambda: w.interrupted))
        w.patch(gd, '_farm_goblin_mail_tick', lambda log: w.reply(False))
        w.interrupted = True
        assert not w.run(gd.farm_goblin_mail(w.logs.append))
        w.interrupted = False
        assert not w.run(gd.farm_goblin_mail(w.logs.append)) and w.now >= 90000

"""Demon Slayer's key collection and incantation follow server state."""

import rs2004.quests.defs.demonslayer as demon
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestSnapshot
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_demon_bones_pickup_and_goblin_kill_are_incremental():
    for mode in ['held', 'combat', 'drop_refused', 'drop', 'missing', 'attack_refused', 'kill']:
        with QuestWorld() as w:
            w.install(demon)
            w.position = demon.GOBLIN_ANCHOR
            if mode == 'held':
                w.hold('Bones', 25)
            w.fighting = mode == 'combat'
            if mode in ['drop', 'drop_refused']:
                drop = QuestObject(w, 'Bones', demon.BONES_ID, effect=lambda: w.hold('Bones'))
                drop.accept = mode != 'drop_refused'
                w.scene = [drop]
            elif mode in ['kill', 'attack_refused']:
                npc = QuestObject(w, 'Goblin', demon.GOBLIN_ID, ['Attack'])
                npc.accept = mode != 'attack_refused'
                npc.effect = lambda: setattr(npc, 'alive', False)
                w.scene = [npc]
            assert w.run(demon.grind_goblins(w.logs.append)) == (mode == 'held')
            if mode == 'drop':
                assert w.count('Bones') == 1
            if mode == 'kill':
                assert not npc.valid()


def test_drain_surface_fills_bucket_pours_water_and_opens_manhole():
    with QuestWorld() as w:
        w.install(demon)
        w.hold('Bucket', effect=lambda: setattr(w, 'pack', [QuestObject(w, 'Bucket of water')]))
        w.scene = [QuestObject(w, 'Sink', at=demon.SINK_TILE)]
        assert not w.run(demon.drain_leg(w.logs.append))
        water = w.first('Bucket of water')
        water.effect = lambda: setattr(w, 'pack', [])
        hole = QuestObject(w, 'Manhole', ops=['Open'], at=demon.MANHOLE_TILE)
        descend = lambda: setattr(w, 'position', demon.SEWER_LAND)
        def opened():
            hole.ops = ['Climb down']
            hole.effect = descend
        hole.effect = opened
        w.scene = [QuestObject(w, 'Drain', at=demon.DRAIN_TILE), hole]
        assert not w.run(demon.drain_leg(w.logs.append))
        assert w.position == demon.SEWER_LAND and not w.pack


def test_drain_sewer_picks_key_and_climbs_out_before_reporting_success():
    for mode in ['walk_failed', 'no_key', 'no_exit', 'collected']:
        with QuestWorld() as w:
            w.install(demon)
            w.position = demon.SEWER_KEY
            w.can_walk = mode != 'walk_failed'
            key = QuestObject(w, 'Key', demon.DRAIN_KEY_ID, at=demon.SEWER_KEY,
                              effect=lambda: w.hold('Key', id=demon.DRAIN_KEY_ID))
            exit = QuestObject(w, 'Manhole', ops=['Climb-up'], at=demon.SEWER_LAND,
                               effect=lambda: setattr(w, 'position', demon.MANHOLE_TILE))
            w.scene = ([] if mode == 'no_key' else [key]) + ([] if mode == 'no_exit' else [exit])
            assert not w.run(demon.drain_leg(w.logs.append))
            if mode == 'collected':
                assert w.position == demon.MANHOLE_TILE
                assert w.run(demon.drain_leg(w.logs.append))
    with QuestWorld() as w:
        w.install(demon)
        w.position = None
        assert not w.run(demon.drain_leg(w.logs.append))


def test_drain_surface_failure_paths_preserve_bucket_and_retry_purchase():
    for held in ['Bucket', 'Bucket of water', None]:
        for walk_ok in [True, False]:
            with QuestWorld() as w:
                w.install(demon)
                w.can_walk = walk_ok
                if held:
                    w.hold(held)
                calls = []
                def execute(step, hops, log):
                    calls.append(step.item)
                    yield from w.reply(False)
                w.patch(demon, 'execute_step', execute)
                assert not w.run(demon.drain_leg(w.logs.append))
                if held is None:
                    assert calls == ['Bucket']


def test_key_hunt_collects_rovin_and_delivers_three_keys_to_prysin():
    for mode in ['missing_position', 'unreachable', 'rovin', 'silverlight']:
        with QuestWorld() as w:
            w.install(demon)
            if mode == 'missing_position':
                w.position = None
            if mode == 'silverlight':
                for id in [demon.ROVIN_KEY_ID, demon.TRAIBORN_KEY_ID, demon.DRAIN_KEY_ID]:
                    w.hold('Key', id=id)
            w.patch(demon, 'goto_npc', lambda *a: w.reply(mode != 'unreachable'))
            def talk(name, prefer, log):
                yield from w.reply()
                if name == 'Captain Rovin':
                    w.hold('Key', id=demon.ROVIN_KEY_ID)
                elif mode == 'silverlight':
                    w.hold('Silverlight')
                return True
            w.patch(demon, 'talk_through', talk)
            assert w.run(demon.key_hunt(w.logs.append)) == (mode in ['rovin', 'silverlight'])


def test_traiborn_key_hunt_climbs_tower_and_drives_ritual_boxes():
    for mode in ['climb_down', 'grind', 'climb_up', 'unreachable', 'key', 'ritual_stalled']:
        with QuestWorld() as w:
            w.install(demon)
            w.hold('Key', id=demon.ROVIN_KEY_ID)
            w.position = Tile(3112, 3162, 1 if mode in ['climb_down', 'unreachable', 'key', 'ritual_stalled'] else 0)
            if mode not in ['climb_down', 'grind']:
                w.hold('Bones', 25)
            w.patch(demon, 'reach', FakeModule(loc_op=lambda *a, **kw: w.reply('unreachable'),
                                              npc_dialog=lambda *a, **kw: w.reply('failed' if mode == 'unreachable' else 'done')))
            w.patch(demon, 'talk_through', lambda *a: w.reply(True))
            got = lambda: w.hold('Key', id=demon.TRAIBORN_KEY_ID)
            w.patch(demon, 'drive_boxes', lambda *a: w.reply(mode == 'key', got if mode == 'key' else None))
            assert w.run(demon.key_hunt(w.logs.append)) == (mode == 'key')


def test_delrith_equips_silverlight_then_selects_incantation_and_waits_for_completion():
    for mode in ['no_sword', 'equip', 'walk_failed', 'missing', 'complete', 'timeout']:
        with QuestWorld() as w:
            w.install(demon)
            w.patch(demon, '_core', w)
            state = FakeModule(complete=False)
            w.patch(demon, 'quests', FakeModule(status=lambda n: 'complete' if state.complete else 'in_progress'))
            w.patch(demon, 'equipment', FakeModule(contains=lambda n: mode not in ['no_sword', 'equip'],
                                                   equip=lambda n: w.reply()))
            if mode == 'equip':
                w.hold('Silverlight')
            w.can_walk = mode != 'walk_failed'
            npc = QuestObject(w, 'Delrith', ops=['Attack'], at=demon.DELRITH_TILE)
            w.scene = [] if mode == 'missing' else [npc]
            if mode == 'complete':
                npc.effect = lambda: setattr(w, 'pages', [('continue', ['He is weakened!']), ('options', ['Wrong words', demon.INCANTATION])])
                w.on_update = lambda: setattr(state, 'complete', True) if 111 in w.clicks else None
            assert w.run(demon.fight_delrith(w.logs.append)) == (mode == 'complete')
            if mode == 'complete':
                assert 111 in w.clicks


def test_demon_decisions_and_bucket_source_keep_equipment_and_exact_keys_distinct():
    for status, kind in [('complete', 'done'), ('unknown', 'wait'), ('not_started', 'talk'), ('in_progress', 'custom')]:
        assert demon.decide(QuestSnapshot(journal=status)).kind == kind
    assert demon.decide(QuestSnapshot(journal='in_progress', worn={'silverlight'})).kind == 'custom'
    assert demon.decide(QuestSnapshot(journal='in_progress', inv={'silverlight': 1})).kind == 'equip'
    assert demon.fill_bucket(QuestSnapshot(inv={'bucket': 1})).kind == 'use_on'
    assert demon.fill_bucket(QuestSnapshot()).kind == 'wait'
    assert demon.fill_bucket(QuestSnapshot(bank_coins=100)).kind == 'buy'


def test_traiborn_partial_ritual_waits_for_consumed_bones_to_settle():
    with QuestWorld() as w:
        w.install(demon)
        w.position = Tile(3112, 3162, 1)
        w.hold('Key', id=demon.ROVIN_KEY_ID)
        bones = w.hold('Bones', 25)
        w.patch(demon, 'reach', FakeModule(npc_dialog=lambda *a, **kw: w.reply('done')))
        consumed = lambda: setattr(bones, 'count', 24)
        w.patch(demon, 'talk_through', lambda *a: w.reply(True, consumed))
        w.patch(demon, 'drive_boxes', lambda *a: w.reply(False))
        assert not w.run(demon.key_hunt(w.logs.append))
        assert w.count('Bones') == 24 and len(w.waits) >= 10

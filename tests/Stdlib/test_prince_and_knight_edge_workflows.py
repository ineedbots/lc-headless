"""Disguises, prison escapes and the knight's supplies over delayed world updates."""

import rs2004.quests.defs.princeali.disguise as disguise
import rs2004.quests.defs.princeali.jailbreak as jail
import rs2004.quests.defs.princeali.key as key
import rs2004.quests.defs.princeali.supplies as supplies
import rs2004.quests.defs.knightssword.supplies as ks
import rs2004.quests.defs.knightssword.portrait as portrait
import rs2004.quests.defs.knightssword.dungeon as dungeon
from rs2004 import execution
from rs2004.geometry import Tile
from helpers import FakeModule, raises
from quest_world import QuestWorld, QuestObject


def test_prince_item_on_npc_requires_arrival_target_and_consumption():
    for mode in ['held', 'walk_failed', 'missing_npc', 'missing_item', 'refused', 'silent', 'done']:
        with QuestWorld() as w:
            w.install(disguise)
            w.install(supplies)
            onion = QuestObject(w, 'Onion', disguise.PA_ITEM.ONION.id,
                                effect=lambda: w.pack.append(QuestObject(w, 'Yellow dye', disguise.PA_ITEM.YELLOW_DYE.id)))
            onion.accept = mode != 'refused'
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            w.pack = [] if mode == 'missing_item' else [onion]
            w.scene = [] if mode == 'missing_npc' else [QuestObject(w, disguise.PA_NPC.AGGIE, at=disguise.PA_TILE.AGGIE)]
            if mode == 'held':
                w.pack.append(QuestObject(w, 'Yellow dye', disguise.PA_ITEM.YELLOW_DYE.id))
            assert w.run(disguise.make_yellow_dye(w.logs.append)) == (mode in ['held', 'done'])


def test_prince_dyeing_requires_both_parts_and_a_blond_wig_response():
    for mode in ['held', 'missing', 'refused', 'silent', 'done']:
        with QuestWorld() as w:
            w.install(supplies)
            dye = QuestObject(w, 'Yellow dye', disguise.PA_ITEM.YELLOW_DYE.id,
                              effect=lambda: w.pack.append(QuestObject(w, 'Wig', disguise.PA_ITEM.BLOND_WIG.id)))
            dye.accept = mode != 'refused'
            w.pack = [] if mode == 'missing' else [dye, QuestObject(w, 'Wig', disguise.PA_ITEM.PLAIN_WIG.id)]
            if mode == 'held':
                w.pack.append(QuestObject(w, 'Wig', disguise.PA_ITEM.BLOND_WIG.id))
            w.respond = mode != 'silent'
            assert w.run(disguise.dye_wig(w.logs.append)) == (mode in ['held', 'done'])


def test_prince_ashes_waits_for_the_fire_then_takes_its_drop():
    for mode in ['held', 'missing', 'walk_failed', 'refused', 'no_ashes', 'take_refused', 'done']:
        with QuestWorld() as w:
            w.install(disguise)
            w.install(supplies)
            w.patch(disguise, 'bank', FakeModule(is_open=lambda: True, close=lambda: w.reply()))
            ash = QuestObject(w, 'Ashes', disguise.PA_ITEM.ASHES.id, at=disguise.PA_TILE.LOGS_SPAWN,
                              effect=lambda: w.pack.append(QuestObject(w, 'Ashes', disguise.PA_ITEM.ASHES.id)))
            ash.accept = mode != 'take_refused'
            tinder = QuestObject(w, 'Tinderbox', disguise.PA_ITEM.TINDERBOX.id,
                                 effect=lambda: setattr(w, 'scene', [ash]))
            tinder.accept = mode != 'refused'
            w.pack = [] if mode == 'missing' else [tinder, QuestObject(w, 'Logs', disguise.PA_ITEM.LOGS.id)]
            if mode == 'held':
                w.pack.append(QuestObject(w, 'Ashes', disguise.PA_ITEM.ASHES.id))
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'no_ashes'
            assert w.run(disguise.burn_logs(w.logs.append)) == (mode in ['held', 'done'])


def test_keli_tying_requires_rope_a_live_target_and_disappearance():
    for mode in ['absent', 'no_rope', 'walk_failed', 'lost', 'refused', 'silent', 'done']:
        with QuestWorld() as w:
            w.install(jail)
            w.install(supplies)
            keli = QuestObject(w, jail.PA_NPC.KELI)
            rope = QuestObject(w, 'Rope', jail.PA_ITEM.ROPE.id, effect=lambda: setattr(w, 'scene', []))
            rope.accept = mode != 'refused'
            w.scene = [] if mode == 'absent' else [keli]
            w.pack = [] if mode == 'no_rope' else [rope]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            if mode == 'lost':
                w.on_walk = lambda: setattr(w, 'scene', [])
            assert w.run(jail.tie_keli(w.logs.append)) == (mode in ['absent', 'done'])


def test_prison_unlock_proves_crossing_and_prince_receives_disguise():
    for mode in ['inside', 'walk_failed', 'missing', 'refused', 'silent', 'done']:
        with QuestWorld() as w:
            w.install(jail)
            w.install(supplies)
            w.position = jail.PA_TILE.CELL if mode == 'inside' else Tile(3000, 3300)
            w.can_walk = mode != 'walk_failed'
            key_item = QuestObject(w, 'Key', jail.PA_ITEM.PRINCE_KEY.id,
                                   effect=lambda: setattr(w, 'position', jail.PA_TILE.CELL))
            key_item.accept = mode != 'refused'
            w.pack = [key_item]
            w.scene = [] if mode == 'missing' else [QuestObject(w, jail.PA_LOC.PRISON_DOOR, at=jail.PA_TILE.DOOR_STAND)]
            w.respond = mode != 'silent'
            assert w.run(jail.unlock_cell(w.logs.append)) == (mode in ['inside', 'done'])
    with QuestWorld() as w:
        w.install(jail)
        w.install(supplies)
        w.position = jail.PA_TILE.CELL
        w.pack = [QuestObject(w, 'Wig', jail.PA_ITEM.BLOND_WIG.id)]
        w.patch(jail, 'talk_strict', lambda *a: w.reply(False, lambda: None))
        assert not w.run(jail.break_out(w.logs.append))
        handed = lambda: setattr(w, 'pack', [])
        w.patch(jail, 'talk_strict', lambda *a: w.reply(True, handed))
        assert w.run(jail.break_out(w.logs.append))


def test_forged_key_collects_from_leela_even_when_osman_keeps_the_print():
    for mode in ['held', 'unreachable', 'silent', 'done']:
        with QuestWorld() as w:
            w.install(supplies)
            item = QuestObject(w, 'Key', key.PA_ITEM.PRINCE_KEY.id)
            w.pack = [item] if mode == 'held' else [QuestObject(w, 'Key print', key.PA_ITEM.KEY_PRINT.id)]
            def goto(stop, hops, log):
                yield from w.reply()
                return mode != 'unreachable'
            received = lambda: w.pack.append(item)
            def talk(name, prefer, log):
                yield from w.reply()
                if name == key.LEELA_STOP.npc and mode == 'done':
                    received()
                return True
            w.patch(key, 'goto_npc', goto)
            w.patch(key, 'talk_strict', talk)
            assert w.run(key.forge_and_collect(w.logs.append)) == (mode in ['held', 'done'])


def test_knight_pastry_and_burnt_dish_require_real_products():
    for mode in ['missing', 'refused', 'silent', 'done']:
        with QuestWorld() as w:
            w.install(ks)
            flour = QuestObject(w, ks.KS_NAME.POT_OF_FLOUR, ks.KS_ID.POT_OF_FLOUR,
                                effect=lambda: w.pack.append(QuestObject(w, 'Pastry dough', ks.KS_ID.PASTRY_DOUGH)))
            flour.accept = mode != 'refused'
            w.pack = [] if mode == 'missing' else [flour, QuestObject(w, ks.KS_NAME.BUCKET_OF_WATER)]
            w.respond = mode != 'silent'
            assert w.run(ks.mix_dough(w.logs.append)) == (mode == 'done')
            burnt = QuestObject(w, ks.KS_NAME.BURNT_PIE, ks.KS_ID.BURNT_PIE,
                                effect=lambda: w.pack.append(QuestObject(w, 'Pie dish', ks.KS_ID.PIE_DISH)))
            burnt.accept = mode != 'refused'
            w.pack = [] if mode == 'missing' else [burnt]
            assert w.run(ks.empty_burnt_pie(w.logs.append)) == (mode in ['missing', 'done'])


def test_knight_smelting_handles_missing_menu_wrong_product_and_lost_batch():
    for mode in ['walk_failed', 'missing', 'refused', 'no_menu', 'wrong_product', 'no_bars', 'done']:
        with QuestWorld() as w:
            w.install(ks)
            state = FakeModule(menu=False)
            furnace = QuestObject(w, 'Furnace', ops=['Smelt'], at=ks.KS_TILE.FURNACE,
                                  effect=lambda: setattr(state, 'menu', mode != 'no_menu'))
            furnace.accept = mode != 'refused'
            w.scene = [] if mode == 'missing' else [furnace]
            w.can_walk = mode != 'walk_failed'
            def make_x(name, count):
                assert name == 'Iron' and count == ks.ORE_PER_TRIP
                yield from w.reply()
                if mode == 'done':
                    w.pack = [QuestObject(w, 'Iron bar', ks.KS_ID.IRON_BAR)]
                return mode != 'wrong_product'
            w.patch(ks, 'chat_dialog', FakeModule(is_make_menu=lambda: state.menu, make_x=make_x,
                                                 make_products=lambda: ['Bronze']))
            assert w.run(ks.smelt_iron(w.logs.append)) == (mode == 'done')


def test_portrait_search_opens_cupboard_waits_for_vyvin_and_proves_pickup():
    with QuestWorld() as w:
        w.install(portrait)
        w.can_walk = False
        assert not w.run(portrait.fetch_portrait(w.logs.append))
        w.can_walk = True
        cupboard = QuestObject(w, 'Cupboard', ops=['Open'], at=portrait.VYVIN_APPROACHES[0])
        found = lambda: w.pack.append(QuestObject(w, 'Portrait', portrait.KS_ID.PORTRAIT))
        def open_cupboard():
            cupboard.ops = ['Search']
            cupboard.effect = found
        cupboard.effect = open_cupboard
        w.scene = [cupboard, QuestObject(w, 'Sir Vyvin', at=portrait.VYVIN_APPROACHES[0])]
        w.pages = [('continue', ['You cannot search that!'])]
        assert w.run(portrait.fetch_portrait(w.logs.append))
        assert ('Cupboard', 'Open') in w.actions and ('Cupboard', 'Search') in w.actions
        assert w.run(portrait.fetch_portrait(w.logs.append))


def test_portrait_search_retries_refusals_and_retreats_with_a_bounded_failure():
    with QuestWorld() as w:
        w.install(portrait)
        w.patch(portrait, 'ATTEMPTS', 8)
        cupboard = QuestObject(w, 'Cupboard', ops=['Search'], at=portrait.VYVIN_APPROACHES[0])
        w.scene = [cupboard]
        assert not w.run(portrait.fetch_portrait(w.logs.append))
        assert portrait.KS_TILE.VYVIN_RETREAT in w.walks
        assert 'search did not land' in ' '.join(w.logs)
        w.scene = []
        assert not w.run(portrait.fetch_portrait(w.logs.append))
        assert 'no Cupboard' in ' '.join(w.logs)


def test_blurite_mining_restores_retaliation_on_success_failure_and_exception():
    for mode in ['held', 'walk_failed', 'no_path', 'no_scene', 'mined', 'timeout', 'exception']:
        with QuestWorld() as w:
            w.install(dungeon)
            switches = []
            w.patch(dungeon, 'game', FakeModule(tile=lambda: w.position, set_auto_retaliate=switches.append))
            w.patch(dungeon, 'navigator', FakeModule(find_path=lambda *a: FakeModule(ok=mode != 'no_path')))
            def sustain():
                if mode == 'exception':
                    raise ValueError('sustain failed')
                yield execution.Ticks(1)
            w.patch(dungeon, 'sustain', FakeModule(run=sustain))
            w.patch(dungeon, 'MINE_ATTEMPTS', 2)
            w.can_walk = mode not in ['walk_failed', 'no_scene']
            w.position = Tile(3000, 9000) if mode == 'no_scene' else Tile(3000, 3000)
            ore = QuestObject(w, 'Blurite ore', dungeon.KS_ID.BLURITE_ORE)
            if mode == 'held':
                w.pack = [ore]
            if mode in ['mined', 'timeout']:
                w.scene = [QuestObject(w, 'Blurite rocks', list(dungeon.BLURITE_IDS)[0], ['Mine'],
                                      at=dungeon.BLURITE_ROCKS[0], effect=lambda: w.pack.append(ore))]
                w.respond = mode == 'mined'
                w.on_walk = lambda: setattr(w, 'position', dungeon.BLURITE_ROCKS[0])
            if mode == 'exception':
                raises(ValueError, lambda: w.run(dungeon.mine_blurite(w.logs.append)))
            else:
                assert w.run(dungeon.mine_blurite(w.logs.append)) == (mode in ['held', 'mined'])
            assert switches == ([] if mode == 'held' else [False, True])


def test_blurite_waits_for_scene_and_rechecks_ore_after_upkeep():
    with QuestWorld() as w:
        w.install(dungeon)
        w.patch(dungeon, 'navigator', FakeModule(find_path=lambda *a: FakeModule(ok=True)))
        w.patch(dungeon, 'sustain', FakeModule(run=lambda: w.reply()))
        w.patch(dungeon, 'MINE_ATTEMPTS', 2)
        w.position = None
        assert w.run(dungeon.nearest_reachable_rock(w.logs.append)) is None
        w.position = Tile(3000, 9000)
        assert not w.run(dungeon.run(w.logs.append))
        w.hold('Blurite ore', id=dungeon.KS_ID.BLURITE_ORE)
        assert w.run(dungeon.run(w.logs.append))

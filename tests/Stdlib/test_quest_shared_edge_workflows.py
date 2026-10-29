"""Quest upkeep, dialogue and value boundaries exercise the real shared services."""

import rs2004.quests.prayer as qp
import rs2004.quests.strike as strike
import rs2004.quests.weapons as weapons
import rs2004.quests.exec.primitives as primitives
import rs2004.quests.exec.garlic as garlic
import rs2004.quests.exec.wool as wool
import rs2004.quests.defs as defs
import rs2004.quests.data as data
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot, QuestSustain, flag_value
from rs2004.quests.engine.queue import queue_rows
from rs2004.quests.types import SkillReq
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_quest_values_unknown_records_and_malformed_flags():
    assert SkillReq('attack', 10) == SkillReq('attack', 10)
    assert SkillReq('attack', 10) != SkillReq('attack', 11)
    assert SkillReq() != None
    assert flag_value(None, 'count') is None
    assert flag_value(QuestProgress(flags={'count:oops'}), 'count') is None
    assert QuestSustain(['Lobster'], .6).eat_below_hp == .6
    assert data.quest_record('missing') is None
    assert defs.def_by_id('missing') is None
    assert defs.record_by_id('missing') is None
    assert defs.record_by_id('doric').id == 'doric'
    rows = queue_rows(['unknown'], {'unknown'}, {}, set(), None)
    assert rows[0].status == 'UNKNOWN' and 'unknown' in repr(rows[0])


def test_strike_preparation_requires_magic_and_makes_space_without_losing_runes():
    assert strike.prepare_strikes(QuestSnapshot(magic=0)).kind == 'wait'
    for inv, kind in [({'junk': 1}, 'deposit'), ({'coins': 1}, 'wait')]:
        step = strike.prepare_strikes(QuestSnapshot(magic=1, inv=inv, bank_known=True, free_slots=0))
        assert step.kind == kind
        if kind == 'deposit':
            assert 'mind rune' in step.keep and step.exact_keep


def test_weapon_readers_choose_live_pack_and_worn_weapons():
    with QuestWorld() as w:
        w.install(weapons)
        weapon = weapons.MELEE_WEAPONS[-1]
        w.pack = [QuestObject(w, weapon.name, weapon.id)]
        snap = QuestSnapshot(inv_ids={weapon.id: 1}, worn_ids={weapon.id}, attack=99)
        assert weapons.pack_weapon(snap).id == weapon.id
        assert weapons.wielded_weapon(snap).id == weapon.id
        assert weapons.live_best_weapon().id == weapon.id
        assert weapon.name in repr(weapon)


def test_prayer_upkeep_warns_once_then_drinks_raises_and_drops():
    with QuestWorld() as w:
        w.install(qp)
        w.patch(qp, 'quest_prayer_state', qp._QuestPrayerState())
        state = FakeModule(level=1, points=10, active=False, combat=True)
        sets = []
        def set_prayer(name, on):
            sets.append(on)
            yield from w.reply()
            state.active = on
            return True
        w.patch(qp, 'prayer', FakeModule(max=lambda: state.level, points=lambda: state.points,
                                      active=lambda n: state.active, available=lambda n: True, set=set_prayer))
        w.fighting = True
        qp.set_quest_prayer({'protect': 'melee'}, w.logs.append)
        assert not w.run(qp.prayer_upkeep())
        assert not w.run(qp.prayer_upkeep()) and len(w.logs) == 1
        state.level = 50
        potion = QuestObject(w, 'Prayer potion(1)', 143, ['Drink'], effect=lambda: setattr(state, 'points', 40))
        w.pack = [potion]
        assert w.run(qp.prayer_upkeep()) and state.points == 40
        assert w.run(qp.prayer_upkeep()) and sets == [True]
        assert not w.run(qp.prayer_upkeep())
        w.fighting = False
        assert w.run(qp.prayer_upkeep()) and sets == [True, False]
        qp.set_quest_prayer(None, None)
        assert not w.run(qp.prayer_upkeep())


def test_strict_dialogue_uses_last_spoken_line_before_options():
    with QuestWorld() as w:
        w.install(primitives)
        w.pages = [('continue', ['The magic words are silver light']), ('options', ['Leave', 'Silver light!'])]
        rules = [primitives.LineRule('magic words', 'silver')]
        assert w.run(primitives.talk_choosing_by('Wizard', rules, [], w.logs.append))
        assert w.clicks == ['continue', 111]
        w.pages = [('options', ['Attack', 'Leave'])]
        assert not w.run(primitives.talk_strict('Wizard', ['Help'], w.logs.append))
        assert 'no rule' in w.logs[-1]
        w.interrupted = True
        assert not w.run(primitives.talk_strict('Wizard', [], w.logs.append))


def test_strict_dialogue_missing_npc_and_lull_remain_bounded():
    with QuestWorld() as w:
        w.install(primitives)
        assert not w.run(primitives.talk_strict('Absent', [], w.logs.append))
        w.pages = [('waiting', ['Loading'])]
        w.on_update = lambda: setattr(w, 'pages', [])
        assert w.run(primitives.talk_strict('Wizard', [], w.logs.append))


def test_lenient_dialogue_falls_back_to_last_option():
    with QuestWorld() as w:
        w.install(primitives)
        w.pages = [('options', ['Attack', 'Leave'])]
        assert w.run(primitives.drive_dialog(['Help'], w.logs.append))
        assert w.clicks == [111] and 'WARN' in w.logs[0]


def test_walk_with_hops_requires_position_and_acknowledged_ladder():
    with QuestWorld() as w:
        w.install(primitives)
        target = Tile(3000, 9400)
        w.position = None
        assert not w.run(primitives.walk_with_hops(target, 1, [], w.logs.append))
        assert not w.run(primitives.goto_npc(primitives.NpcStop('Wizard', target, 5, []), [], w.logs.append))
        w.position = Tile(3000, 3000)
        hop = primitives.LadderHop(w.position, 'Trapdoor', 'Climb-down', target, open='Open')
        assert not w.run(primitives.walk_with_hops(target, 1, [hop], w.logs.append))
        door = QuestObject(w, 'Trapdoor', ops=['Open'])
        door.effect = lambda: setattr(door, 'ops', ['Climb-down'])
        w.scene = [door]
        assert not w.run(primitives.walk_with_hops(target, 1, [hop], w.logs.append))
        door.effect = lambda: setattr(w, 'position', target)
        assert w.run(primitives.walk_with_hops(target, 1, [hop], w.logs.append))
        assert w.run(primitives.walk_with_hops(Tile(3010, 9400), 1, [], w.logs.append))


def test_garlic_failure_paths_do_not_claim_a_clove():
    with QuestWorld() as w:
        w.install(garlic)
        w.can_walk = False
        assert not w.run(garlic.take_garlic(w.logs.append))
        w.can_walk = True
        assert not w.run(garlic.take_garlic(w.logs.append))
        w.position = garlic.GARLIC_CUPBOARD
        w.can_walk = False
        assert not w.run(garlic.take_garlic(w.logs.append))
        w.can_walk = True
        assert not w.run(garlic.take_garlic(w.logs.append))
        cupboard = QuestObject(w, 'Cupboard', garlic.CUPBOARD_OPEN, ['Search'], at=garlic.GARLIC_CUPBOARD)
        cupboard.accept = False
        w.scene = [cupboard]
        assert not w.run(garlic.take_garlic(w.logs.append))


def test_shearing_needs_a_reachable_sheep_shears_and_server_wool():
    with QuestWorld() as w:
        w.install(wool)
        pen = w.position
        assert not w.run(wool.shear_one(pen, w.logs.append)) and w.walks == [pen]
        w.scene = [QuestObject(w, 'Sheep', wool.UNSHEARED_SHEEP_ID)]
        assert not w.run(wool.shear_one(pen, w.logs.append))
        shears = QuestObject(w, 'Shears', effect=lambda: w.pack.append(QuestObject(w, 'Wool')))
        w.pack = [shears]
        assert w.run(wool.shear_one(pen, w.logs.append)) and w.count('Wool') == 1
        shears.accept = False
        assert not w.run(wool.shear_one(pen, w.logs.append))


def test_spinning_retries_missing_wheel_menu_and_unacknowledged_products():
    for outcome in ['missing', 'refused', 'silent', 'no_product', 'stalled', 'spun']:
        with QuestWorld() as w:
            w.install(wool)
            state = FakeModule(menu=False)
            spun = lambda: setattr(w, 'pack', [QuestObject(w, 'Ball of wool')])
            def make_x(name, count):
                if outcome == 'spun':
                    w.effects.append(spun)
                yield from w.reply()
                return outcome != 'no_product'
            w.patch(wool, 'chat_dialog', FakeModule(is_make_menu=lambda: state.menu, make_x=make_x,
                                                    make_products=lambda: ['Wrong product']))
            w.pack = [QuestObject(w, 'Wool')]
            wheel = QuestObject(w, 'Spinning wheel', ops=['Spin'],
                                effect=lambda: setattr(state, 'menu', outcome != 'silent'))
            wheel.accept = outcome != 'refused'
            w.scene = [] if outcome == 'missing' else [wheel]
            assert w.run(wool.spin_all_wool(w.position, w.logs.append)) == (outcome == 'spun')
            if outcome == 'spun':
                assert w.count('Ball of wool') == 1

"""Regressions from the concurrent 289 Heroes, Regicide and Legends deaths."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.geometry import Tile
from rs2004.quests.defs.legends import viyeldi
from rs2004.quests.defs.legends.fight import fight_loop
from rs2004.quests.defs.trollstronghold import combat
from rs2004.quests.defs.regicide import decide, outfit
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.prayer import potion_step
from rs2004.tabs import prayer


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def fall_past_ledge():
    scene = Scene(Tile(2388, 4728, 0))
    state = Record({'pocket': 'descent_four'})
    patch(viyeldi, 'pocket', lambda: state.pocket)

    def fall(opts, log):
        state.pocket = 'viyeldi_main'
        expect(opts.expect()).to_be(True)
        return False
        yield

    prompt = spy_on(viyeldi, 'prompt_loc', impl=fall)
    expect(run_wait(viyeldi.climb(viyeldi.LEDGES[4], 'down', scene.log))).to_be(True)
    expect(len(prompt.calls)).to_be(1)
    expect(len(scene.walks)).to_be(1)


test('falling to the Viyeldi floor inside a climb does not retry an unreachable ledge', fall_past_ledge)


def restores_prayer_without_food():
    scene = Scene(Tile(2407, 4699, 0))
    state = Record({'points': 0})
    spy_on(skills, 'level', returns=85)
    spy_on(skills, 'effective', returns=30)
    spy_on(prayer, 'active', returns=True)
    spy_on(prayer, 'points', impl=lambda: state.points)

    def drink(op):
        state.points = 30

    scene.item(139, 'Prayer potion(3)', actions=['Drink'], effect=drink)
    plan = Record({'npc': 'Ranalph Devere', 'done': lambda: state.points > 0, 'ms': 10000})
    expect(run_wait(fight_loop(plan, True, scene.log))).to_be(True)
    expect(state.points).to_be(30)


test('an injured guardian fighter with no food still drinks its prayer potion', restores_prayer_without_food)


def empty_food_still_attacks():
    scene = Scene(Tile(2865, 9955, 0))
    state = Record({'won': False})
    spy_on(combat, 'hungry', returns=True)
    spy_on(combat.event_signal, 'pending', returns=False)
    spy_on(combat.game, 'set_auto_retaliate', returns=None)

    def hit(op):
        state.won = True

    enemy = scene.npc('Ice Queen', ['Attack'], effect=hit)
    plan = Record({'what': 'Ice Queen', 'target': lambda: enemy, 'won': lambda: state.won, 'guard': 5})
    guard = Record({'usable': False, 'arms': 0})
    expect(run_wait(combat.fight_rounds(plan, guard, scene.log))).to_be(True)
    expect(state.won).to_be(True)


test('an empty food pack does not stall Ice Queen attacks in the eating branch', empty_food_still_attacks)


def retargets_after_retaliation():
    scene = Scene(Tile(2865, 9955, 0))
    scene.fighting = True
    state = Record({'attacks': 0})
    spy_on(combat.game, 'facing', returns=('npc', 999))
    spy_on(combat, 'hungry', returns=False)
    spy_on(combat.event_signal, 'pending', returns=False)
    spy_on(combat.game, 'set_auto_retaliate', returns=None)

    def hit(op):
        state.attacks += 1

    enemy = scene.npc('Ice Queen', ['Attack'], effect=hit)
    plan = Record({'what': 'Ice Queen', 'target': lambda: enemy, 'won': lambda: state.attacks == 2, 'guard': 5})
    guard = Record({'usable': False, 'arms': 0})
    expect(run_wait(combat.fight_rounds(plan, guard, scene.log))).to_be(True)
    expect(state.attacks).to_be(2)


test('combat with another aggressor does not suppress renewing the quest target', retargets_after_retaliation)


def provisions_and_armour():
    snap = QuestSnapshot(inv_ids={}, bank_ids={139: 100}, bank_known=True, bank={}, inv={}, worn=set(), worn_ids=set(), free_slots=20)
    step = potion_step(snap, 2)
    expect(step.items[0]['id']).to_be(139)
    expect(step.items[0]['qty']).to_be(2)
    snap.inv_ids = {141: 1, 143: 1}
    expect(potion_step(snap, 2)).to_be_null()
    snap.bank = {'rune chainbody': 1, 'rune platelegs': 1}
    snap.defence = 75
    snap.attack = 75
    step = outfit(snap, 'mainland')
    expect(step.kind).to_be('withdraw')
    expect([item['name'] for item in step.items]).to_contain('Rune chainbody')
    expect([item['name'] for item in step.items]).to_contain('Rune platelegs')
    scene = Scene(Tile(2655, 3283, 0))
    scene.wear('Rune longsword', id=1303)
    scene.item(1113, 'Rune chainbody')
    scene.item(1079, 'Rune platelegs')
    snap.tile = scene.at
    snap.stage = 2
    snap.journal = 'in_progress'
    snap.worn = set(['rune longsword'])
    snap.inv = {'rune chainbody': 1, 'rune platelegs': 1}
    step = decide(snap)
    expect(step.kind).to_be('custom')
    expect(run_wait(step.run(scene.log))).to_be(True)
    expect([item.name for item in scene.worn]).to_contain('Rune chainbody')
    expect([item.name for item in scene.worn]).to_contain('Rune platelegs')


test('owned-inventory quests accept partial prayer flasks and Regicide draws banked armour', provisions_and_armour)

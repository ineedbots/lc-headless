"""Viyeldi descent, guardian crystals, source demon and the complete climb back out."""

from rs2004.game import game
from rs2004.quests.defs.legends import viyeldi as cave
from rs2004.quests.defs.legends.areas import HEROES, LQ_ID, LQ_LOC, LQ_NPC, LQ_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def world(pocket='viyeldi_ledge'):
    scene = Scene(LQ_TILE.SOURCE_STAND)
    scene.pocket = pocket
    scene.area = 'viyeldi_caves'
    patch(cave, 'pocket', lambda: scene.pocket)
    patch(cave, 'legends_area', lambda tile: scene.area)
    patch(cave, 'legends_pocket', lambda tile: scene.pocket)
    return scene


def climbs():
    scene = world()
    ledge = cave.LEDGES[0]
    scene.pocket = ledge.down.to
    expect(run_wait(cave.climb(ledge, 'down', scene.log))).to_be(True)
    scene.pocket = 'viyeldi_main'
    expect(run_wait(cave.climb(ledge, 'down', scene.log))).to_be(True)
    scene.pocket = 'viyeldi_ledge'
    expect(run_wait(cave.climb(ledge, 'up', scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(cave.climb(ledge, 'down', scene.log))).to_be(False)
    scene.walk_ok = True
    prompt = spy_on(cave, 'prompt_loc', impl=answer(False))
    expect(run_wait(cave.climb(ledge, 'down', scene.log))).to_be(False)
    expect(len(prompt.calls)).to_be(8)

    def cross(opts, log):
        expect(opts.id).to_be(ledge.id)
        scene.pocket = ledge.down.to
        expect(opts.expect()).to_be(True)
        return True
        yield

    prompt.mock_implementation(cross)
    expect(run_wait(cave.climb(ledge, 'down', scene.log))).to_be(True)


test('a ledge retries agility failures eight times and accepts an overshoot to the floor', climbs)


def descent():
    scene = world()
    scene.area = 'surface'
    expect(run_wait(cave.descend_ledges(scene.log))).to_be(False)
    scene.area = 'viyeldi_caves'
    climb = spy_on(cave, 'climb', impl=answer(False))
    expect(run_wait(cave.descend_ledges(scene.log))).to_be(False)
    scene.pocket = None
    expect(run_wait(cave.descend_ledges(scene.log))).to_be(False)
    expect(scene.logged('trying the next ledge')).to_be(True)

    def down(ledge, dir, log):
        expect(dir).to_be('down')
        scene.pocket = ledge.down.to
        return True
        yield

    climb.mock_implementation(down)
    scene.pocket = 'descent_two'
    before = len(climb.calls)
    expect(run_wait(cave.descend_ledges(scene.log))).to_be(True)
    expect(len(climb.calls) - before).to_be(4)
    scene.pocket = 'viyeldi_source'
    expect(run_wait(cave.descend_ledges(scene.log))).to_be(True)


test('the Viyeldi descent resumes below fallen ledges and probes uncovered fall tiles', descent)


def ascent():
    scene = world('viyeldi_main')
    scene.area = 'surface'
    expect(run_wait(cave.climb_ledges(scene.log))).to_be(True)
    scene.area = 'viyeldi_caves'
    barrier = spy_on(cave, 'recross_barrier', impl=answer(False))
    expect(run_wait(cave.climb_ledges(scene.log))).to_be(False)
    barrier.mock_implementation(answer(True))
    climb = spy_on(cave, 'climb', impl=answer(False))
    expect(run_wait(cave.climb_ledges(scene.log))).to_be(False)

    def up(ledge, dir, log):
        expect(dir).to_be('up')
        scene.pocket = ledge.up.to
        return True
        yield

    climb.mock_implementation(up)
    expect(run_wait(cave.climb_ledges(scene.log))).to_be(True)
    expect(scene.pocket).to_be('viyeldi_ledge')
    expect(run_wait(cave.climb_ledges(scene.log))).to_be(True)


test('the climb out reverses all six ledges after recrossing the barrier', ascent)


def guardians():
    scene = world('viyeldi_main')
    expect(run_wait(cave.find_guardian('Guardian', scene.log))).to_be_null()
    scene.walk_ok = False
    expect(run_wait(cave.fight_guardian('Guardian', 123, scene.log))).to_be(False)
    guardian = scene.npc('Guardian', ['Attack'])
    expect(cave.guardian_here('Guardian')).to_be(guardian)
    expect(run_wait(cave.fight_guardian('Guardian', 123, scene.log))).to_be(False)
    scene.walk_ok = True

    def won(plan, log):
        expect(plan.npc).to_be('Guardian')
        expect(plan.done()).to_be(False)
        scene.item(123, 'Section')
        expect(plan.done()).to_be(True)
        return True
        yield

    spy_on(cave, 'fight', impl=won)
    expect(run_wait(cave.fight_guardian('Guardian', 123, scene.log))).to_be(True)
    expect(run_wait(cave.fight_guardian('Guardian', 123, scene.log))).to_be(True)
    expect(run_wait(cave.smelt_section(456, scene.log))).to_be(True)

    def smelt(id, opts, prefer, goal, log):
        expect(id).to_be(123)
        scene.take(id)
        return goal()
        yield

    spy_on(cave, 'use_on_loc', impl=smelt)
    expect(run_wait(cave.smelt_section(123, scene.log))).to_be(True)


test('guardians are found in the current pocket and their sections feed the lava furnace', guardians)


def heart_crystal():
    scene = world('viyeldi_main')
    down = spy_on(cave, 'descend_ledges', impl=answer(False))
    expect(run_wait(cave.forge_heart_crystal(scene.log))).to_be(False)
    down.mock_implementation(answer(True))
    fight = spy_on(cave, 'fight_guardian', impl=answer(False))
    expect(run_wait(cave.forge_heart_crystal(scene.log))).to_be(False)
    for hero in HEROES:
        scene.item(hero.section, 'Section')
    smelt = spy_on(cave, 'smelt_section', impl=answer(False))
    expect(run_wait(cave.forge_heart_crystal(scene.log))).to_be(False)
    fused = []

    def fuse(id, log):
        fused.append(id)
        scene.take(id)
        if len(fused) == 3:
            scene.item(LQ_ID.HEART_CRYSTAL, 'Heart')
        return True
        yield

    smelt.mock_implementation(fuse)
    expect(run_wait(cave.forge_heart_crystal(scene.log))).to_be(True)
    expect(len(fused)).to_be(3)
    expect(run_wait(cave.forge_heart_crystal(scene.log))).to_be(True)
    scene.pack = []
    scene.item(HEROES[0].section, 'Section')

    def early(id, log):
        scene.item(LQ_ID.HEART_CRYSTAL, 'Heart')
        return True
        yield

    smelt.mock_implementation(early)
    expect(run_wait(cave.forge_heart_crystal(scene.log))).to_be(True)


test('the heart is forged from all three sections and a completed heart ends a resumed sweep', heart_crystal)


def charge_and_recess():
    scene = world()
    down = spy_on(cave, 'descend_ledges', impl=answer(False))
    expect(run_wait(cave.charge_heart_crystal(scene.log))).to_be(False)
    expect(run_wait(cave.fill_recess(scene.log))).to_be(False)
    down.mock_implementation(answer(True))

    def charge(id, opts, prefer, goal, log):
        if id == LQ_ID.HEART_CRYSTAL:
            scene.item(LQ_ID.HEART_CRYSTAL_GLOW, 'Glowing heart')
        else:
            expect(id).to_be(LQ_ID.HEART_CRYSTAL_GLOW)
            scene.take(id)
        return goal()
        yield

    spy_on(cave, 'use_on_loc', impl=charge)
    expect(run_wait(cave.charge_heart_crystal(scene.log))).to_be(True)
    expect(run_wait(cave.charge_heart_crystal(scene.log))).to_be(True)
    expect(run_wait(cave.fill_recess(scene.log))).to_be(True)
    scene.loc(LQ_LOC.RECESS_FULL, ['Look'])
    expect(run_wait(cave.fill_recess(scene.log))).to_be(True)


test('the heart glows at the dragon eye and is consumed by the recess', charge_and_recess)


def barrier():
    scene = world('viyeldi_main')
    down = spy_on(cave, 'descend_ledges', impl=answer(False))
    expect(run_wait(cave.cross_barrier(scene.log))).to_be(False)
    down.mock_implementation(answer(True))

    def cross(opts, log):
        scene.pocket = 'viyeldi_main' if scene.pocket == 'viyeldi_source' else 'viyeldi_source'
        return opts.expect()
        yield

    spy_on(cave, 'prompt_loc', impl=cross)
    expect(run_wait(cave.cross_barrier(scene.log))).to_be(True)
    expect(run_wait(cave.cross_barrier(scene.log))).to_be(True)
    expect(run_wait(cave.recross_barrier(scene.log))).to_be(True)
    expect(run_wait(cave.recross_barrier(scene.log))).to_be(True)


test('the shimmering field is crossed in either direction only after reaching its floor', barrier)


def boulder_and_dagger():
    scene = world('viyeldi_source')
    cross = spy_on(cave, 'cross_barrier', impl=answer(False))
    expect(run_wait(cave.push_source_boulder(scene.log))).to_be(False)
    expect(run_wait(cave.take_black_dagger(scene.log))).to_be(False)
    cross.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(cave.push_source_boulder(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(cave.push_source_boulder(scene.log))).to_be(False)
    scene.npc(LQ_NPC.BOULDER, ['Push'])
    expect(run_wait(cave.push_source_boulder(scene.log))).to_be(True)
    scene.npc(LQ_NPC.ECHNED)
    scene.later(lambda: scene.item(LQ_ID.DEATH_DAGGER, 'Dagger'))
    expect(run_wait(cave.take_black_dagger(scene.log))).to_be(True)
    expect(run_wait(cave.take_black_dagger(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(cave.trade_dagger_for_spell(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(cave.trade_dagger_for_spell(scene.log))).to_be(False)
    scene.npc(LQ_NPC.UNGADULU)
    offer = spy_on(cave, 'offer_to', impl=answer(False))
    expect(run_wait(cave.trade_dagger_for_spell(scene.log))).to_be(False)
    offer.mock_implementation(answer(True))
    scene.later(lambda: scene.item(LQ_ID.HOLY_FORCE, 'Spell'))
    expect(run_wait(cave.trade_dagger_for_spell(scene.log))).to_be(True)
    expect(run_wait(cave.trade_dagger_for_spell(scene.log))).to_be(True)


test('the source boulder summons Echned and his dagger is traded to Ungadulu for Holy Force', boulder_and_dagger)


def source_demon():
    scene = world('viyeldi_source')
    cross = spy_on(cave, 'cross_barrier', impl=answer(False))
    expect(run_wait(cave.banish_source_demon(scene.log))).to_be(False)
    cross.mock_implementation(answer(True))
    push = spy_on(cave, 'push_source_boulder', impl=answer(False))
    expect(run_wait(cave.banish_source_demon(scene.log))).to_be(False)
    push.mock_implementation(answer(True))
    scene.npc(LQ_NPC.ECHNED)
    expect(run_wait(cave.banish_source_demon(scene.log))).to_be(False)
    scene.item(LQ_ID.HOLY_FORCE, 'Spell', effect=lambda op: False)
    expect(run_wait(cave.banish_source_demon(scene.log))).to_be(False)
    scene.pack = []
    scene.item(LQ_ID.HOLY_FORCE, 'Spell', effect=lambda op: scene.npc(LQ_NPC.NEZIKCHENED, ['Attack']))

    def fight(plan, log):
        expect(plan.done()).to_be(False)
        scene.npcs = []
        return plan.done()
        yield

    spy_on(cave, 'fight', impl=fight)
    expect(run_wait(cave.banish_source_demon(scene.log))).to_be(True)


test('Holy Force uses Cast Spell and victory requires the source demon to disappear', source_demon)


def source_water():
    scene = world('viyeldi_source')
    expect(run_wait(cave.collect_sacred_water(scene.log))).to_be(False)
    scene.item(LQ_ID.GOLD_BOWL_BLESSED, 'Bowl')
    cross = spy_on(cave, 'cross_barrier', impl=answer(False))
    expect(run_wait(cave.collect_sacred_water(scene.log))).to_be(False)
    cross.mock_implementation(answer(True))
    push = spy_on(cave, 'push_source_boulder', impl=answer(False))
    expect(run_wait(cave.collect_sacred_water(scene.log))).to_be(False)
    push.mock_implementation(answer(True))
    use = spy_on(cave, 'use_on_loc', impl=answer(False))
    expect(run_wait(cave.collect_sacred_water(scene.log))).to_be(False)
    expect(len(use.calls)).to_be(4)
    scene.loc(LQ_LOC.SOURCE_POOL, ['Look'])

    def fill(id, opts, prefer, goal, log):
        expect(id).to_be(LQ_ID.GOLD_BOWL_BLESSED)
        scene.item(LQ_ID.GOLD_BOWL_BLESSED_PURE, 'Water')
        return goal()
        yield

    use.mock_implementation(fill)
    expect(run_wait(cave.collect_sacred_water(scene.log))).to_be(True)
    expect(run_wait(cave.collect_sacred_water(scene.log))).to_be(True)


test('source water needs an empty blessed bowl and the temporary pool is retried four times', source_water)


def cave_escape():
    scene = world()
    scene.pocket = None
    scene.area = 'surface'
    expect(run_wait(cave.leave_caves(scene.log))).to_be(True)
    scene.area = 'viyeldi_caves'
    for name in ['climb_ledges', 'leave_octagram', 'climb_out_of_trials', 'leave_shaman_cave']:
        step = spy_on(cave, name, impl=answer(False))
        expect(run_wait(cave.leave_caves(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    expect(run_wait(cave.leave_caves(scene.log))).to_be(True)


test('leaving the caves completes every ascent before a mainland walk can start', cave_escape)

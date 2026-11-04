"""Ungadulu, Gujuo's blessing, the bowl, flames and Yommi seeds."""

from rs2004.game import skills
from rs2004.quests.defs.legends import shaman
from rs2004.quests.defs.legends.areas import LQ_ID, LQ_LOC, LQ_NPC, LQ_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def world():
    scene = Scene(LQ_TILE.MOSSY_ROCKS)
    scene.area = 'jungle'
    patch(shaman, 'here', lambda: scene.area)
    return scene


def cave_entry():
    scene = world()
    enter = spy_on(shaman, 'enter_jungle', impl=answer(False))
    expect(run_wait(shaman.enter_shaman_cave(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(shaman.enter_shaman_cave(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(shaman.enter_shaman_cave(scene.log))).to_be(False)
    scene.loc('Rock', ['Search'], id=shaman.ROCK_IDS[0], effect=lambda op: False)
    expect(run_wait(shaman.enter_shaman_cave(scene.log))).to_be(False)
    scene.locs = []

    def crawl(op):
        scene.area = 'shaman_caves'

    scene.loc('Rock', ['Search'], id=shaman.ROCK_IDS[0], effect=crawl)
    expect(run_wait(shaman.enter_shaman_cave(scene.log))).to_be(True)
    expect(run_wait(shaman.enter_shaman_cave(scene.log))).to_be(True)


test('the shaman cave retries agility rolls but requires a searchable cave-mouth rock', cave_entry)


def through_flames():
    scene = world()
    inside = spy_on(shaman, 'in_octagram', returns=True)
    leave = spy_on(shaman, 'leave_octagram', impl=answer(False))
    expect(run_wait(shaman.speak_to_ungadulu(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    enter = spy_on(shaman, 'enter_shaman_cave', impl=answer(False))
    expect(run_wait(shaman.speak_to_ungadulu(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(shaman.speak_to_ungadulu(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(shaman.speak_to_ungadulu(scene.log))).to_be(False)
    scene.loc(LQ_LOC.FIRE_WALL, ['Investigate'], effect=lambda op: False)
    expect(run_wait(shaman.speak_to_ungadulu(scene.log))).to_be(False)
    scene.locs = []
    scene.loc(LQ_LOC.FIRE_WALL, ['Investigate'])
    expect(run_wait(shaman.speak_to_ungadulu(scene.log))).to_be(False)
    scene.chat.pages = ['continue', ['Who are you?']]
    expect(run_wait(shaman.speak_to_ungadulu(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Who are you?'])


test('Ungadulu must be spoken to outside the flames and asked who he is', through_flames)


def prayer_and_blessing():
    scene = world()
    expect(run_wait(shaman.top_up_prayer(scene.log))).to_be(True)
    scene.stats['prayer'] = 20
    drink = spy_on(shaman, 'drink_prayer', impl=answer(False))
    expect(run_wait(shaman.top_up_prayer(scene.log))).to_be(False)
    drink.mock_implementation(answer(True))
    expect(run_wait(shaman.top_up_prayer(scene.log))).to_be(True)
    summoned = spy_on(shaman, 'summon_gujuo', impl=answer(False))
    expect(run_wait(shaman.bless_bowl(scene.log))).to_be(False)
    summoned.mock_implementation(answer(True))
    expect(run_wait(shaman.bless_bowl(scene.log))).to_be(False)
    scene.npc(LQ_NPC.GUJUO)
    drink.mock_implementation(answer(False))
    expect(run_wait(shaman.bless_bowl(scene.log))).to_be(False)
    scene.stats['prayer'] = 42
    offer = spy_on(shaman, 'offer_to', impl=answer(False))
    expect(run_wait(shaman.bless_bowl(scene.log))).to_be(False)
    expect(scene.logged('never blessed')).to_be(True)
    offer.mock_implementation(answer(True))
    trance = spy_on(shaman, 'drive_blessing', impl=answer('refused'))
    expect(run_wait(shaman.bless_bowl(scene.log))).to_be(False)
    expect(len(drink.calls) > 1).to_be(True)
    trance.mock_implementation(answer('blessed'))
    expect(run_wait(shaman.bless_bowl(scene.log))).to_be(True)
    scene.item(LQ_ID.GOLD_BOWL_BLESSED, 'Blessed bowl')
    expect(run_wait(shaman.bless_bowl(scene.log))).to_be(True)


test('Gujuo blessing restores prayer, retries refusals and stops at an explicit blessing', prayer_and_blessing)


def trance_outcomes():
    scene = world()
    expect(run_wait(shaman.drive_blessing(lambda: True))).to_be('blessed')
    expect(run_wait(shaman.drive_blessing(lambda: False))).to_be('quiet')
    scene.chat.shown = ['not in a deep enough trance']
    scene.chat.pages = ['continue']
    expect(run_wait(shaman.drive_blessing(lambda: False))).to_be('missed')
    scene.chat.shown = ['too inexperienced']
    scene.chat.pages = ['continue']
    expect(run_wait(shaman.drive_blessing(lambda: False))).to_be('refused')


test('the trance preserves failure text even after the dialogue closes', trance_outcomes)


def bowl_forging():
    scene = world()
    leave = spy_on(shaman, 'leave_jungle', impl=answer(False))
    expect(run_wait(shaman.make_golden_bowl(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    expect(run_wait(shaman.make_golden_bowl(scene.log))).to_be(False)
    scene.item(LQ_ID.GOLD_BAR, 'Gold bar', count=2)
    use = spy_on(shaman, 'use_on_loc', impl=answer(False))
    expect(run_wait(shaman.make_golden_bowl(scene.log))).to_be(False)
    expect(len(use.calls)).to_be(6)

    def forged(id, opts, prefer, goal, log):
        expect(id).to_be(LQ_ID.GOLD_BAR)
        scene.item(LQ_ID.GOLD_BOWL, 'Bowl')
        return goal()
        yield

    use.mock_implementation(forged)
    expect(run_wait(shaman.make_golden_bowl(scene.log))).to_be(True)
    expect(run_wait(shaman.make_golden_bowl(scene.log))).to_be(True)


test('forging a golden bowl needs two bars and retries the crafting roll', bowl_forging)


def reed_and_water():
    scene = world()
    enter = spy_on(shaman, 'enter_jungle', impl=answer(False))
    expect(run_wait(shaman.cut_reed(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))

    def used(id, opts, prefer, goal, log):
        if id in [LQ_ID.KNIFE, LQ_ID.MACHETE]:
            scene.item(LQ_ID.HOLLOW_REED, 'Reed')
        else:
            scene.item(LQ_ID.GOLD_BOWL_BLESSED_PURE, 'Pure water')
        return goal()
        yield

    use = spy_on(shaman, 'use_on_loc', impl=used)
    expect(run_wait(shaman.cut_reed(scene.log))).to_be(True)
    expect(run_wait(shaman.cut_reed(scene.log))).to_be(True)
    expect(run_wait(shaman.fill_bowl_from_pool(scene.log))).to_be(True)
    expect(run_wait(shaman.fill_bowl_from_pool(scene.log))).to_be(True)
    scene.pack = []
    scene.item(LQ_ID.KNIFE, 'Knife')
    expect(run_wait(shaman.cut_reed(scene.log))).to_be(True)
    cut = spy_on(shaman, 'cut_reed', impl=answer(False))
    expect(run_wait(shaman.fill_bowl_from_pool(scene.log))).to_be(False)
    expect(run_wait(shaman.find_pool_dried(scene.log))).to_be(False)
    cut.mock_implementation(answer(True))
    use.mock_implementation(answer(False))
    expect(run_wait(shaman.find_pool_dried(scene.log))).to_be(False)
    scene.loc(LQ_LOC.POLLUTED_WATER, ['Look'])
    expect(run_wait(shaman.find_pool_dried(scene.log))).to_be(True)


test('a knife or machete cuts a reed and the pool reports whether its water is dried', reed_and_water)


def octagram():
    scene = world()
    inside = spy_on(shaman, 'in_octagram', returns=True)
    expect(run_wait(shaman.enter_octagram(scene.log))).to_be(True)
    inside.mock_return_value(False)
    for name in ['climb_out_of_trials', 'enter_shaman_cave']:
        step = spy_on(shaman, name, impl=answer(False))
        expect(run_wait(shaman.enter_octagram(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(shaman.enter_octagram(scene.log))).to_be(False)
    scene.walk_ok = True
    touch = spy_on(shaman, 'prompt_loc', impl=answer(False))
    expect(run_wait(shaman.enter_octagram(scene.log))).to_be(False)
    touch.mock_implementation(answer(True))
    expect(run_wait(shaman.enter_octagram(scene.log))).to_be(True)
    scene.item(LQ_ID.GOLD_BOWL_BLESSED_PURE, 'Water')
    splash = spy_on(shaman, 'use_on_loc', impl=answer(True))
    expect(run_wait(shaman.enter_octagram(scene.log))).to_be(True)
    expect(splash.calls[-1][0]).to_be(LQ_ID.GOLD_BOWL_BLESSED_PURE)


test('octagram entry tries pure water and the post-demon Touch crossing', octagram)


def demon_and_seeds():
    scene = world()
    enter = spy_on(shaman, 'enter_octagram', impl=answer(False))
    expect(run_wait(shaman.summon_demon(scene.log))).to_be(False)
    expect(run_wait(shaman.ask_for_seeds(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(shaman.summon_demon(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(shaman.summon_demon(scene.log))).to_be(False)
    scene.npc(LQ_NPC.UNGADULU)
    offer = spy_on(shaman, 'offer_to', impl=answer(False))
    expect(run_wait(shaman.summon_demon(scene.log))).to_be(False)
    offer.mock_implementation(answer(True))
    scene.later(lambda: scene.npc(LQ_NPC.NEZIKCHENED))
    expect(run_wait(shaman.summon_demon(scene.log))).to_be(True)
    scene.talk_status = 'unreachable'
    expect(run_wait(shaman.ask_for_seeds(scene.log))).to_be(False)
    scene.talk_status = 'done'
    scene.later(lambda: scene.item(LQ_ID.YOMMI_SEEDS, 'Seeds'))
    expect(run_wait(shaman.ask_for_seeds(scene.log))).to_be(True)
    expect(run_wait(shaman.ask_for_seeds(scene.log))).to_be(True)
    expect(run_wait(shaman.germinate_seeds(scene.log))).to_be(False)
    scene.item(LQ_ID.GOLD_BOWL_BLESSED_PURE, 'Bowl')
    expect(run_wait(shaman.germinate_seeds(scene.log))).to_be(False)
    scene.take(LQ_ID.YOMMI_SEEDS)
    scene.item(LQ_ID.YOMMI_SEEDS, 'Seeds', on_use=lambda target: False)
    expect(run_wait(shaman.germinate_seeds(scene.log))).to_be(False)
    scene.take(LQ_ID.YOMMI_SEEDS)
    scene.item(LQ_ID.YOMMI_SEEDS, 'Seeds', on_use=lambda target: scene.item(LQ_ID.YOMMI_SEEDS_GERM, 'Germinated'))
    scene.chat.pages = ['continue']
    expect(run_wait(shaman.germinate_seeds(scene.log))).to_be(True)
    expect(run_wait(shaman.germinate_seeds(scene.log))).to_be(True)


test('the binding book summons the demon and seeds germinate only after the final chat is closed', demon_and_seeds)

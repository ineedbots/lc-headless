"""Gertrude's Cat's yard routes, supplies, handovers, crate search and brothers against Scene facades."""

import rs2004.quests.defs.gertrudescat as cat
from rs2004.game import direct_navigator
from rs2004.reach import reach
from rs2004.tabs import quests


def answer(value):
    return value
    yield


def move(scene, tile):
    def effect(*args):
        scene.at = tile
        return True
    return effect


def world(at=None):
    scene = Scene(at if at is not None else cat.YARD_HUB)
    scene.direct_ok = True

    def step(dest, radius, timeout_ms):
        if scene.direct_ok:
            scene.at = dest
        return scene.direct_ok
        yield

    spy_on(direct_navigator, 'walk_to', impl=step)
    return scene


def journal_status():
    scene = world()
    for status, stage in [('complete', cat.FLUFFS_STAGE.COMPLETE), ('not_started', cat.FLUFFS_STAGE.NOT_STARTED)]:
        scene.status = status
        expect(run_wait(cat.read_gertrudes_cat_progress()).stage).to_be(stage)
    scene.status = 'unknown'
    expect(run_wait(cat.read_gertrudes_cat_progress())).to_be_null()
    scene.status = 'in_progress'
    spy_on(quests, 'journal', impl=lambda name: answer(['I gave Fluffs her kitten back']))
    scene.main_modal = 123
    expect(run_wait(cat.read_gertrudes_cat_progress()).stage).to_be(cat.FLUFFS_STAGE.RESCUED)
    expect(scene.main_modal).to_be(-1)
    expect(scene.ticks).to_be(1)
    expect(run_wait(cat.read_gertrudes_cat_progress()).stage).to_be(cat.FLUFFS_STAGE.RESCUED)
    expect(scene.ticks).to_be(1)
    spy_on(quests, 'journal', impl=lambda name: answer(['unrecognized journal']))
    expect(run_wait(cat.read_gertrudes_cat_progress())).to_be_null()


test('Gertrude journal reading handles status shortcuts and closes the parsed page', journal_status)


def yard_routes():
    scene = world()
    expect(run_wait(cat.enter_yard(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene.at = cat.GERTRUDE.anchor
    scene.no_walk = [cat.YARD_ENTRY]
    expect(run_wait(cat.enter_yard(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cat.enter_yard(scene.log))).to_be(True)
    expect(scene.at).to_equal(cat.YARD_ENTRY)
    expect(run_wait(cat.leave_yard(scene.log))).to_be(True)
    expect(scene.walks[-2:]).to_equal(cat.YARD_EXIT)
    scene.no_walk = [cat.YARD_HUB]
    expect(run_wait(cat.walk_via([cat.YARD_HUB], scene.log))).to_be(True)
    expect(scene.at).to_equal(cat.YARD_HUB)
    expect(scene.logged('walking there directly')).to_be(True)
    scene.direct_ok = False
    expect(run_wait(cat.walk_via(cat.YARD_EXIT, scene.log))).to_be(False)
    expect(scene.walks[-1]).to_equal(cat.YARD_HUB)
    scene = world(cat.CAT_STAND)
    expect(run_wait(cat.enter_yard(scene.log))).to_be(False)
    expect(run_wait(cat.leave_yard(scene.log))).to_be(False)


test('Gertrude yard routes use the fence and fall back to direct walking when planning fails', yard_routes)


def ladders():
    scene = world()
    scene.walk_ok = False
    scene.direct_ok = False
    expect(run_wait(cat.climb_to_cat(scene.log))).to_be(False)
    scene.walk_ok = True
    scene.no_walk = [cat.LADDER_BASE]
    expect(run_wait(cat.climb_to_cat(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cat.climb_to_cat(scene.log))).to_be(False)
    expect(scene.logged('no ladder up')).to_be(True)
    ladder = scene.loc('Ladder', ['Climb-up'], effect=lambda op: False)
    expect(run_wait(cat.climb_to_cat(scene.log))).to_be(False)
    ladder._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(cat.climb_to_cat(scene.log))).to_be(False)
    expect(scene.clock - before >= 10000).to_be(True)
    ladder._fields['interact'] = move(scene, cat.LADDER_TOP)
    expect(run_wait(cat.climb_to_cat(scene.log))).to_be(True)
    expect(cat.on_platform()).to_be(True)
    walks = len(scene.walks)
    expect(run_wait(cat.climb_to_cat(scene.log))).to_be(True)
    expect(len(scene.walks)).to_be(walks)
    scene.no_walk = [cat.LADDER_TOP]
    expect(run_wait(cat.climb_down_to_yard(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cat.climb_down_to_yard(scene.log))).to_be(False)
    expect(scene.logged('no ladder down')).to_be(True)
    ladder = scene.loc('Ladder', ['Climb-down'], effect=lambda op: False)
    expect(run_wait(cat.climb_down_to_yard(scene.log))).to_be(False)
    ladder._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(cat.climb_down_to_yard(scene.log))).to_be(False)
    expect(scene.clock - before).to_be(10000)
    ladder._fields['interact'] = move(scene, cat.LADDER_BASE)
    ticks = scene.ticks
    expect(run_wait(cat.climb_down_to_yard(scene.log))).to_be(True)
    expect(cat.on_platform()).to_be(False)
    expect(scene.ticks - ticks).to_be(2)


test('Gertrude ladders verify arrival and propagate missing, refused and stalled climbs', ladders)


def seasoning():
    scene = world()
    expect(run_wait(cat.season_sardine(scene.log))).to_be(False)
    expect(scene.logged('no doogle leaves or no raw sardine')).to_be(True)
    leaves = scene.item(cat.FLUFFS_OBJ.doogle_leaves, 'Doogle leaves', on_use=lambda target: False)
    expect(run_wait(cat.season_sardine(scene.log))).to_be(False)
    raw = scene.item(cat.FLUFFS_OBJ.raw_sardine, 'Raw sardine')
    expect(run_wait(cat.season_sardine(scene.log))).to_be(False)
    uses = []

    def rub(target):
        expect(target).to_be(raw)
        expect(scene.main_modal).to_be(-1)
        uses.append(target.id)
        if len(uses) == 2:
            scene.take(cat.FLUFFS_OBJ.doogle_leaves)
            scene.take(cat.FLUFFS_OBJ.raw_sardine)
            scene.item(cat.FLUFFS_OBJ.seasoned_sardine, 'Seasoned sardine')
        return True

    leaves._fields['use_on'] = rub
    scene.main_modal = 123
    expect(run_wait(cat.season_sardine(scene.log))).to_be(True)
    expect(len(uses)).to_be(2)
    expect(scene.has(cat.FLUFFS_OBJ.seasoned_sardine)).to_be(True)
    expect(scene.has(cat.FLUFFS_OBJ.raw_sardine)).to_be(False)
    expect(run_wait(cat.season_sardine(scene.log))).to_be(True)
    expect(len(uses)).to_be(2)

    scene = world()
    scene.item(cat.FLUFFS_OBJ.raw_sardine, 'Raw sardine')
    attempts = []

    def ignored(target):
        attempts.append(target.id)
        return True

    scene.item(cat.FLUFFS_OBJ.doogle_leaves, 'Doogle leaves', on_use=ignored)
    expect(run_wait(cat.season_sardine(scene.log))).to_be(False)
    expect(len(attempts)).to_be(cat.SEASON_ATTEMPTS)
    expect(scene.clock >= cat.SEASON_ATTEMPTS * 8000).to_be(True)


test('Gertrude seasoning closes the shop modal, retries dropped uses and confirms the product', seasoning)


def handovers():
    for id, what in [(cat.FLUFFS_OBJ.bucket_of_milk, 'milk'), (cat.FLUFFS_OBJ.seasoned_sardine, 'sardine'), (cat.FLUFFS_OBJ.kitten, 'kitten')]:
        scene = world(cat.CAT_STAND)
        offer = cat.offer_to_cat(id, what)
        expect(run_wait(offer(scene.log))).to_be(True)
        expect(scene.walks).to_equal([])
        item = scene.item(id, what, on_use=lambda target: False)
        expect(run_wait(offer(scene.log))).to_be(False)
        expect(scene.logged('no Fluffs in reach')).to_be(True)
        fluffs = scene.npc('Fluffs', id=cat.CAT_NPC)
        scene.npc('Fluffs', id=999, dist=0)
        expect(run_wait(offer(scene.log))).to_be(False)
        attempts = []

        def give(target):
            expect(target).to_be(fluffs)
            attempts.append(target.id)
            if len(attempts) == 2:
                scene.take(id)
                scene.main_modal = 123
                scene.chat.pages = ['continue']
            return True

        item._fields['use_on'] = give
        ticks = scene.ticks
        expect(run_wait(offer(scene.log))).to_be(True)
        expect(len(attempts)).to_be(2)
        expect(scene.has(id)).to_be(False)
        expect(scene.ticks - ticks >= cat.CUTSCENE_TICKS).to_be(True)
        expect(scene.main_modal).to_be(-1)
        expect(scene.chat.pages).to_equal([])

    scene = world()
    scene.item(cat.FLUFFS_OBJ.kitten, 'Kitten')
    expect(run_wait(cat.offer_to_cat(cat.FLUFFS_OBJ.kitten, 'kitten')(scene.log))).to_be(False)
    scene = world(cat.CAT_STAND)
    scene.npc('Fluffs', id=cat.CAT_NPC)
    attempts = []

    def ignored(target):
        attempts.append(target.id)
        return True

    scene.item(cat.FLUFFS_OBJ.kitten, 'Kitten', on_use=ignored)
    expect(run_wait(cat.offer_to_cat(cat.FLUFFS_OBJ.kitten, 'kitten')(scene.log))).to_be(False)
    expect(len(attempts)).to_be(cat.OFFER_ATTEMPTS)
    expect(scene.has(cat.FLUFFS_OBJ.kitten)).to_be(True)


test('Gertrude handovers use Fluffs by id, retry dropped uses and finish the cutscene', handovers)


def crate_search():
    scene = world()
    spot = cat.CRATES[0].tile
    found = lambda: scene.has(cat.FLUFFS_OBJ.kitten)
    run_wait(cat.search_crate(spot, found, scene.log))
    expect(scene.logged('no crate standing')).to_be(True)
    scene.npc('Crate', ['Search'], id=cat.CRATE_NPC, tile=cat.CRATES[1].tile)
    run_wait(cat.search_crate(spot, found, scene.log))
    expect(scene.clock).to_be(0)
    crate = scene.npc('Crate', ['Search'], id=cat.CRATE_NPC, tile=spot, effect=lambda op: False)
    run_wait(cat.search_crate(spot, found, scene.log))
    expect(scene.clock).to_be(0)
    crate._fields['interact'] = lambda op: True
    scene.say('You find nothing.')
    run_wait(cat.search_crate(spot, found, scene.log))
    expect(scene.clock >= cat.CRATE_SEARCH_MS).to_be(True)

    def empty(op):
        expect(op).to_be('Search')
        scene.say('You find nothing.')
        return True

    crate._fields['interact'] = empty
    before = scene.clock
    run_wait(cat.search_crate(spot, found, scene.log))
    expect(scene.clock - before).to_be(0)

    def rescue(op):
        scene.item(cat.FLUFFS_OBJ.kitten, "Fluffs' kitten")
        return True

    crate._fields['interact'] = rescue
    run_wait(cat.search_crate(spot, found, scene.log))
    expect(found()).to_be(True)


test('Gertrude searches the crate at its exact tile and ignores stale empty-search messages', crate_search)


def kitten_in(scene, spot):
    def rescue(op):
        expect(op).to_be('Search')
        scene.item(cat.FLUFFS_OBJ.kitten, "Fluffs' kitten")
        return True
    scene.npc('Crate', ['Search'], id=cat.CRATE_NPC, tile=spot, effect=rescue)


def search_yard():
    scene = world(cat.CAT_STAND)
    expect(run_wait(cat.search_crates_for_kitten(scene.log))).to_be(False)
    scene = world()
    expect(run_wait(cat.search_crates_for_kitten(scene.log))).to_be(False)
    expect(scene.logged('none of the six crates')).to_be(True)
    expect(scene.walks).to_equal(cat.NW_CORNER_IN + cat.NW_CORNER_OUT)
    scene = world()
    kitten_in(scene, cat.CRATES[0].tile)
    expect(run_wait(cat.search_crates_for_kitten(scene.log))).to_be(True)
    expect(scene.walks).to_equal(cat.NW_CORNER_IN + cat.NW_CORNER_OUT)
    before = len(scene.walks)
    expect(run_wait(cat.search_crates_for_kitten(scene.log))).to_be(True)
    expect(len(scene.walks)).to_be(before)
    scene = world()
    scene.no_walk = [cat.NW_CORNER_IN[1]]
    scene.direct_ok = False
    kitten_in(scene, cat.CRATES[1].tile)
    expect(run_wait(cat.search_crates_for_kitten(scene.log))).to_be(True)
    expect(scene.has(cat.FLUFFS_OBJ.kitten)).to_be(True)


test('Gertrude searches all six crates, follows corner waypoints and skips a blocked corner', search_yard)


def brothers_world():
    scene = world(cat.MARKET)
    spy_on(cat._core, 'line_of_sight', returns=True)
    scene.npc('Shilop', ['Talk-to'], tile=cat.MARKET)
    scene.npc('Wilough', ['Talk-to'], tile=cat.MARKET)
    scene.coins = scene.item(995, 'Coins', count=1000)
    scene.pay = True
    scene.open_ok = True
    scene.opened = 0

    def dialogue(*args, **kwargs):
        scene.opened += 1
        if scene.open_ok:
            scene.chat.pages = [['What will make you tell me?'], ["I'll pay"]]
        return 'done' if scene.open_ok else 'missing'
        yield

    def choose(text):
        if text == "I'll pay" and scene.pay:
            scene.coins._fields['count'] -= cat.BOY_PAYMENT

    scene.chat.on_choose = choose
    spy_on(reach, 'entity_op', impl=dialogue)
    return scene


def paying_brothers():
    scene = brothers_world()
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(True)
    expect(scene.coins.count).to_be(900)
    expect(scene.chat.chosen).to_equal(cat.PAY_PREFER)
    expect(scene.opened).to_be(1)
    scene = brothers_world()
    scene.pay = False
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(False)
    expect(scene.opened).to_be(cat.PAY_ATTEMPTS)
    expect(scene.coins.count).to_be(1000)
    expect(scene.logged('dialogue ended without paying')).to_be(True)
    scene = brothers_world()
    scene.open_ok = False
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(False)
    expect(scene.opened).to_be(cat.PAY_ATTEMPTS)
    scene = brothers_world()
    scene.npcs = []
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(False)
    expect(scene.opened).to_be(0)
    expect(scene.clock >= cat.PAY_ATTEMPTS * 60000).to_be(True)
    scene = brothers_world()
    scene.npcs[1]._fields['tile'] = lambda: cat.YARD_HUB
    scene.npcs[1]._fields['network_tile'] = lambda: cat.YARD_HUB
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(False)
    expect(scene.logged('never wandered within earshot')).to_be(True)
    expect(scene.opened).to_be(0)
    scene = brothers_world()
    scene.walk_ok = False
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(False)
    expect(scene.opened).to_be(0)


def brothers_within_server_range():
    scene = brothers_world()
    scene.npcs[1]._fields['network_tile'] = lambda: Tile(cat.MARKET.x + 3, cat.MARKET.z, 0)
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(True)
    scene = brothers_world()
    spy_on(cat._core, 'line_of_sight', returns=False)
    expect(run_wait(cat.pay_brothers(scene.log))).to_be(False)
    expect(scene.opened).to_be(0)


test('the brothers can be three tiles apart with line of sight but cannot hear through a wall', brothers_within_server_range)


test('Gertrude pays only paired brothers and verifies the coin debit, with bounded retries', paying_brothers)


def reporting():
    scene = world(cat.CAT_STAND)
    expect(run_wait(cat.report_to_gertrude(scene.log))).to_be(False)
    scene = world(cat.GERTRUDE.anchor)
    scene.walk_ok = False
    scene.at = cat.MARKET
    expect(run_wait(cat.report_to_gertrude(scene.log))).to_be(False)
    scene.walk_ok = True
    scene.npc('Gertrude', ['Talk-to'])
    spy_on(reach, 'entity_op', impl=lambda *args, **kwargs: answer('missing'))
    expect(run_wait(cat.report_to_gertrude(scene.log))).to_be(False)
    spy_on(reach, 'entity_op', impl=lambda *args, **kwargs: answer('done'))
    scene.at = cat.YARD_HUB
    expect(run_wait(cat.report_to_gertrude(scene.log))).to_be(True)
    expect(scene.walks[-3:]).to_equal(cat.YARD_EXIT + [cat.GERTRUDE.anchor])


test('Gertrude reporting escapes the yard before approaching and talking to Gertrude', reporting)


def banked_kitten():
    scene = world(cat.CAT_STAND)
    execute = spy_on(cat, 'execute_step', impl=lambda *args: answer(True))
    expect(run_wait(cat.recover_banked_kitten(scene.log))).to_be(False)
    expect(execute.calls).to_equal([])
    scene = world(cat.YARD_HUB)
    execute = spy_on(cat, 'execute_step', impl=lambda *args: answer(False))
    expect(run_wait(cat.recover_banked_kitten(scene.log))).to_be(False)
    step = execute.calls[0][0]
    expect(step.kind).to_be('withdraw')
    expect(step.bank).to_equal(cat.QUEST_BANK)
    expect(step.items).to_equal([{'name': "Fluffs' kitten", 'id': cat.FLUFFS_OBJ.kitten, 'qty': 1}])
    expect(scene.at).to_equal(cat.YARD_ENTRY)
    scene.at = cat.GERTRUDE.anchor
    execute.mock_implementation(lambda *args: answer(True))
    expect(run_wait(cat.recover_banked_kitten(scene.log))).to_be(True)


test('Gertrude bank recovery escapes the yard and requests one kitten by exact id', banked_kitten)

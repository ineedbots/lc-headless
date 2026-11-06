"""Boss combat recovery restores toggles and distinguishes interrupted, missing and defeated targets."""

from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.familycrest import chronozon as crest
from rs2004.quests.defs.fightarena import fights as arena
from rs2004.quests.defs.horror import fight as horror
from rs2004.quests.defs import lostcity_combat as spirit
from rs2004.tabs import prayer


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def chronozon_approach():
    scene = Scene(crest.SAFESPOT)
    stub(crest, last_drink=-crest.IMMUNITY_MS)
    expect(run_wait(crest.drink_antipoison(scene.log))).to_be(False)
    dose_id = list(crest.ANTIPOISON_IDS)[0]
    scene.item(dose_id, 'Antipoison', effect=lambda op: False)
    expect(run_wait(crest.drink_antipoison(scene.log))).to_be(False)
    scene.pack = []
    scene.item(dose_id, 'Antipoison')
    expect(run_wait(crest.drink_antipoison(scene.log))).to_be(True)
    expect(run_wait(crest.drink_antipoison(scene.log))).to_be(True)
    expect(run_wait(crest.take_safespot(scene.log))).to_be(True)
    scene.at = Tile(3000, 3000, 0)
    scene.walk_ok = False
    expect(run_wait(crest.take_safespot(scene.log))).to_be(False)
    expect(run_wait(crest.walk_to_chronozon(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(crest.take_safespot(scene.log))).to_be(True)
    expect(run_wait(crest.walk_to_chronozon(scene.log))).to_be(False)
    demon = scene.npc('Chronozon', ['Attack'], id=667)
    spy_on(crest, 'chronozon', returns=demon)
    expect(crest.demon_in_reach()).to_be(True)
    expect(run_wait(crest.walk_to_chronozon(scene.log))).to_be(True)
    spy_on(crest, 'clear_attacker', impl=answer(False))
    state = Record({'safespot': True})
    scene.at = Tile(3000, 3000, 0)
    spy_on(game, 'cast_on_npc', returns=False)
    expect(run_wait(crest._cast_blast('Fire blast', state, scene.log))).to_be('nospell')
    spy_on(crest, 'chronozon', returns=None)
    expect(run_wait(crest._cast_blast('Fire blast', state, scene.log))).to_be('gone')


test('Chronozon approach checks respawns, safespot reach and antipoison immunity', chronozon_approach)


def chronozon_finish():
    scene = Scene(crest.SAFESPOT)
    auto = spy_on(game, 'set_auto_retaliate', returns=None)
    spy_on(game, 'cast_on_npc', returns=False)
    spy_on(crest, 'clear_attacker', impl=answer(False))
    spy_on(crest, 'take_safespot', impl=answer(True))
    walk = spy_on(crest, 'walk_to_chronozon', impl=answer(False))
    blast = spy_on(crest, '_cast_blast', impl=answer('landed'))
    spy_on(crest, 'chronozon', returns=None)
    expect(run_wait(crest.fight_chronozon(scene.log))).to_be(False)
    walk.mock_implementation(answer(True))
    target = scene.npc('Chronozon', ['Attack'], id=667)
    spy_on(crest, 'chronozon', returns=target)
    scene.at = Tile(3000, 3000, 0)
    expect(run_wait(crest.fight_chronozon(scene.log))).to_be(False)
    expect(auto.calls[-1]).to_equal((True,))
    scene.on_ground(crest.FC_ID.CREST_FROM_CHRONOZON, crest.FC_ITEM.CREST_PART, effect=lambda op: False)
    expect(run_wait(crest.fight_chronozon(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(crest.FC_ID.CREST_FROM_CHRONOZON, crest.FC_ITEM.CREST_PART)
    expect(run_wait(crest.fight_chronozon(scene.log))).to_be(True)
    scene.pack = []

    def broken(*args):
        raise RuntimeError('interrupted fight')
        yield

    blast.mock_implementation(broken)
    try:
        run_wait(crest.fight_chronozon(scene.log))
        expect(False).to_be(True)
    except RuntimeError:
        expect(auto.calls[-1]).to_equal((True,))


test('Chronozon retries absent drops and restores auto-retaliate even when the fight raises', chronozon_finish)


def arena_recovery():
    scene = Scene(arena.ARENA_COVER)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(prayer, 'points', returns=50)
    active = spy_on(prayer, 'active', returns=False)
    spy_on(prayer, 'set', impl=answer(True))
    spy_on(arena, 'ready_strikes', impl=answer(False))
    plan = Record({'what': 'test beast', 'npc_id': 999, 'guard': 4, 'cover': arena.ARENA_COVER})
    expect(run_wait(arena.fight_rounds(plan, scene.log))).to_be('stuck')
    spy_on(arena, 'ready_strikes', impl=answer(True))
    spy_on(arena, 'take_strike_cover', impl=answer(True))
    expect(run_wait(arena.fight_rounds(plan, scene.log))).to_be('stuck')
    active.mock_return_value(True)
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(arena.fight_rounds(plan, scene.log))).to_be('stuck')
    pending.mock_return_value(False)
    target = scene.npc('Beast', ['Attack'], id=999)
    stub(target, network_tile=lambda: scene.at)
    spy_on(arena, 'at_cover', returns=False)
    expect(run_wait(arena.fight_rounds(plan, scene.log))).to_be('stuck')
    spy_on(arena, 'at_cover', returns=True)
    spy_on(arena, 'cast_strike', impl=answer(True))
    scene.ticks = 50
    expect(run_wait(arena.fight_rounds(plan, scene.log))).to_be('stuck')
    expect(scene.logged('hp=')).to_be(True)
    chat = spy_on(chat_dialog, 'can_continue', returns=True)

    def continued():
        chat.mock_return_value(False)
        return True
        yield

    spy_on(chat_dialog, 'continue_', impl=continued)
    run_wait(arena.drain_win_dialogue())
    spy_on(chat_dialog, 'is_open', returns=True)
    run_wait(arena.drain_win_dialogue())

    def broken(*args):
        raise RuntimeError('interrupted arena')
        yield

    spy_on(arena, 'fight_rounds', impl=broken)
    clear = spy_on(arena, 'drop_prayer', impl=answer(True))
    try:
        run_wait(arena.run_fight(plan, scene.log))
        expect(False).to_be(True)
    except RuntimeError:
        expect(len(clear.calls)).to_be(1)


test('arena fights yield for events, handle prayer setup and clean up after interrupted rounds', arena_recovery)


def dagannoth_recovery():
    scene = Scene(Tile(2500, 9900, 0))
    spy_on(game, 'open_side_tab', impl=answer(True))
    auto = spy_on(game, 'set_auto_retaliate', returns=None)
    spy_on(prayer, 'points', returns=0)
    spy_on(prayer, 'active', returns=False)
    spy_on(prayer, 'set', impl=answer(True))
    expect(horror.mother()).to_be_null()
    expect(horror.junior()).to_be_null()
    scene.item(horror.PRAYER_POTION_IDS[0], 'Prayer potion')
    expect(horror.low_on_prayer_dose() is not None).to_be(True)
    target = scene.npc('Dagannoth', ['Attack'], id=horror.DAGANNOTH_JR)
    plan = Fake(what='test', protect='melee', guard=2, target=lambda: target,
                won=lambda: False, melee=None, element=lambda target: None, summon_delay=1)
    expect(run_wait(horror.fight_loop(plan, scene.log))).to_be(False)
    scene.pack = []
    spy_on(horror, 'hungry', returns=True)
    expect(run_wait(horror.fight_loop(plan, scene.log))).to_be(False)

    def broken(*args):
        raise RuntimeError('interrupted dagannoth')
        yield

    spy_on(horror, '_fight_rounds', impl=broken)
    try:
        run_wait(horror.fight_loop(plan, scene.log))
        expect(False).to_be(True)
    except RuntimeError:
        expect(auto.calls[-1]).to_equal((True,))
    expect(horror._mother_won()).to_be(False)
    scene.item(horror.HD_ID.CASKET, 'Casket')
    expect(horror._mother_won()).to_be(True)


test('Dagannoth combat drinks low prayer, eats between casts and restores toggles on exceptions', dagannoth_recovery)


def tree_spirit_recovery():
    scene = Scene(Tile(1, 1, 0))
    spy_on(event_signal, 'pending', returns=False)
    spy_on(game, 'cast_on_npc', returns=True)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(game, 'set_auto_retaliate', returns=None)
    from rs2004.game import direct_navigator
    spy_on(direct_navigator, 'walk', returns=False)
    target = Fake(id=655)
    cast = spirit.PendingCast()
    expect(run_wait(spirit.settle_cast('Wind strike', target, cast, scene.log))).to_be(False)
    expect(cast.pending).to_be(True)
    spy_on(spirit, 'spirit', returns=target)
    spy_on(spirit, 'take_cover', impl=answer(True))
    expect(run_wait(spirit.defeat_tree_spirit(scene.log, answer(False)))).to_be(False)
    expect(scene.logged('safespot changed')).to_be(True)
    scene.at = spirit.TREE_SPIRIT_SAFESPOT
    spy_on(spirit, 'trapped', returns=True)
    spy_on(spirit, 'strike', returns='Wind strike')

    def broken(*args):
        raise RuntimeError('interrupted spirit cast')
        yield

    spy_on(spirit, 'settle_cast', impl=broken)
    try:
        run_wait(spirit.defeat_tree_spirit(scene.log, answer(False)))
        expect(False).to_be(True)
    except RuntimeError:
        expect(True).to_be(True)


test('Tree Spirit casts retreat when displaced and preserve cleanup when a cast raises', tree_spirit_recovery)

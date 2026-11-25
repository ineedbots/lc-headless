"""An ogre closing Grew's dialogue must not trigger another rope/shop circuit."""

from rs2004.geometry import Tile
from rs2004.quests.defs.watchtower import tribes
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_TILE
from rs2004.quests.engine.types import QuestProgress


def answer(value):
    return value
    yield


def island():
    scene = Scene(WT_TILE.GREW)
    scene.flags = set()
    scene.conversations = 0
    scene.kills = 0
    spy_on(tribes, 'watchtower_area', impl=lambda tile: 'grewIsland')
    spy_on(tribes.event_signal, 'pending', returns=False)
    spy_on(tribes.game, 'facing', returns=None)
    spy_on(tribes.game, 'in_combat', impl=lambda: any([npc.targets_me() for npc in scene.npcs]))
    spy_on(tribes.game, 'set_auto_retaliate', returns=True)
    spy_on(tribes, 'prayer_upkeep', impl=lambda: answer(False))
    spy_on(tribes, 'read_watchtower_progress', impl=lambda: answer(QuestProgress(2, set(scene.flags))))
    return scene


def aggressor(scene):
    def defeat(op):
        scene.kills += 1
        scene.npcs = [npc for npc in scene.npcs if not npc.targets_me()]
        return True

    ogre = scene.npc('Ogre', ['Attack'], targets_me=True, effect=defeat)
    ogre._fields['max_health'] = 60
    ogre._fields['health'] = 60
    return ogre


def interrupted():
    scene = island()

    def talk(*args):
        scene.conversations += 1
        if scene.conversations == 1:
            aggressor(scene)
        else:
            scene.flags.add('spoken-grew')
        # The shared helper returns True whenever a hit closes the dialogue.
        return True
        yield

    spy_on(tribes, 'talk_strict', impl=talk)
    expect(run_wait(tribes.talk_to_grew(scene.log))).to_be(True)
    expect(scene.conversations).to_be(2)
    expect(scene.kills).to_be(1)
    expect(scene.walks).to_equal([])
    expect(scene.at).to_equal(WT_TILE.GREW)


test('an interrupted Grew introduction clears its attacker and retries without leaving', interrupted)


def tooth_hand_in():
    scene = island()
    scene.flags.add('spoken-grew')
    scene.item(WT_ITEM.OGRE_TOOTH.id, 'Ogre tooth')

    def talk(*args):
        scene.conversations += 1
        if scene.conversations == 2:
            scene.take(WT_ITEM.OGRE_TOOTH.id)
            scene.flags.add('helped-grew')
        return True
        yield

    spy_on(tribes, 'talk_strict', impl=talk)
    expect(run_wait(tribes.talk_to_grew(scene.log))).to_be(True)
    expect(scene.conversations).to_be(2)
    expect(scene.has(WT_ITEM.OGRE_TOOTH.id)).to_be(False)


test('already speaking to Grew does not prove an interrupted tooth hand-in succeeded', tooth_hand_in)


def lost_crystal():
    scene = island()
    scene.flags.add('helped-grew')

    def talk(*args):
        scene.conversations += 1
        if scene.conversations == 2:
            scene.item(WT_ITEM.CRYSTAL1.id, 'Crystal')
        return True
        yield

    spy_on(tribes, 'talk_strict', impl=talk)
    expect(run_wait(tribes.talk_to_grew(scene.log))).to_be(True)
    expect(scene.conversations).to_be(2)


test('a replacement reward needs an actual item increase', lost_crystal)


def bounded():
    scene = island()
    spy_on(tribes, 'talk_strict', impl=lambda *args: answer(True))
    expect(run_wait(tribes.talk_to_grew(scene.log))).to_be(False)
    expect(scene.clock >= 240000).to_be(True)
    expect(scene.walks).to_equal([])


test('permanently interrupted Grew dialogue stops at the local retry budget', bounded)


def unsafe():
    scene = island()
    aggressor(scene)
    spy_on(tribes.skills, 'level', returns=85)
    spy_on(tribes.skills, 'effective', returns=20)
    expect(run_wait(tribes.talk_to_grew(scene.log))).to_be(False)
    expect(scene.kills).to_be(0)
    spy_on(tribes.event_signal, 'pending', returns=True)
    expect(run_wait(tribes.quiet_grew_island(scene.clock + 10000, scene.log))).to_be(False)


test('low health without food and pending random events stop island combat', unsafe)

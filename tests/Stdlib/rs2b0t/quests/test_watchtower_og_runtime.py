"""Og must finish his request or hand over a reward despite hostile ogres."""

from rs2004.geometry import Tile
from rs2004.quests.defs.watchtower import tribes
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_TILE
from rs2004.quests.engine.types import QuestProgress


def answer(value):
    return value
    yield


def camp():
    scene = Scene(WT_TILE.OG)
    scene.flags = set()
    scene.conversations = []
    scene.kills = 0
    spy_on(tribes, 'watchtower_area', returns='yanille')
    spy_on(tribes.event_signal, 'pending', returns=False)
    spy_on(tribes.game, 'facing', returns=None)
    spy_on(tribes.game, 'in_combat', impl=lambda: any([npc.targets_me() for npc in scene.npcs]))
    spy_on(tribes.game, 'set_auto_retaliate', returns=True)
    spy_on(tribes, 'prayer_upkeep', impl=lambda: answer(False))
    spy_on(tribes, 'read_watchtower_progress', impl=lambda: answer(QuestProgress(2, set(scene.flags))))
    return scene


def attacker(scene):
    def defeat(op):
        scene.kills += 1
        scene.npcs = [npc for npc in scene.npcs if not npc.targets_me()]
        return True

    ogre = scene.npc('Ogre', ['Attack'], targets_me=True, effect=defeat)
    ogre._fields['size'] = 2
    ogre._fields['health'] = 60
    ogre._fields['max_health'] = 60


def introduction():
    scene = camp()
    bystander = scene.npc('Ogre', ['Attack'], others=True)

    def talk(name, prefer, log):
        scene.conversations.append(prefer)
        if len(scene.conversations) == 1:
            attacker(scene)
        else:
            scene.flags.add('spoken-og')
            scene.item(WT_ITEM.TOBAN_KEY.id, 'Toban key')
        return True
        yield

    spy_on(tribes, 'talk_strict', impl=talk)
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(True)
    expect(len(scene.conversations)).to_be(2)
    expect(scene.kills).to_be(1)
    expect(scene.npcs).to_equal([bystander])
    expect(scene.has(WT_ITEM.TOBAN_KEY.id)).to_be(True)
    expect(scene.walks).to_equal([WT_TILE.OG])


test('Og clears the interrupting attacker and finishes the introduction locally', introduction)


def gold_hand_in():
    scene = camp()
    scene.flags.add('spoken-og')
    scene.item(WT_ITEM.STOLEN_GOLD.id, 'Gold')

    def talk(name, prefer, log):
        scene.conversations.append(prefer)
        if len(scene.conversations) == 2:
            scene.flags.add('helped-og')
            scene.take(WT_ITEM.STOLEN_GOLD.id)
            scene.item(WT_ITEM.RELIC_PART1.id, 'Relic part 1')
        return True
        yield

    spy_on(tribes, 'talk_strict', impl=talk)
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(True)
    expect(len(scene.conversations)).to_be(2)
    expect(scene.conversations[0]).to_equal(['I have your gold.'])
    expect(scene.has(WT_ITEM.RELIC_PART1.id)).to_be(True)


test('already speaking to Og does not prove an interrupted gold hand-in succeeded', gold_hand_in)


def replacements():
    for helped in [False, True]:
        scene = camp()
        scene.flags.add('helped-og' if helped else 'spoken-og')
        reward = WT_ITEM.RELIC_PART1 if helped else WT_ITEM.TOBAN_KEY

        def talk(name, prefer, log):
            scene.conversations.append(prefer)
            if len(scene.conversations) == 2:
                scene.item(reward.id, reward.name)
            return True
            yield

        spy_on(tribes, 'talk_strict', impl=talk)
        expect(run_wait(tribes.talk_to_og(scene.log))).to_be(True)
        expect(len(scene.conversations)).to_be(2)
        expect(scene.conversations[0]).to_equal(['I have lost the relic part you gave me.'] if helped else ['I have lost the key!'])
        expect(scene.has(reward.id)).to_be(True)
        restore_all()


test('Og replacement requests choose the right menu option and require an actual reward', replacements)


def bounded_and_safe():
    scene = camp()
    spy_on(tribes, 'talk_strict', impl=lambda *args: answer(True))
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(False)
    expect(scene.clock >= 240000).to_be(True)
    expect(scene.walks).to_equal([WT_TILE.OG])
    attacker(scene)
    spy_on(tribes.skills, 'effective', returns=20)
    spy_on(tribes.skills, 'level', returns=85)
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(False)
    expect(scene.kills).to_be(0)
    spy_on(tribes.event_signal, 'pending', returns=True)
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(False)


test('Og retries have a deadline and stop for unsafe health or interruptions', bounded_and_safe)


def stand():
    scene = camp()
    og = scene.npc('Og', ['Talk-to'], tile=WT_TILE.OG)
    og._fields['size'] = 2
    ogre = scene.npc('Ogre', ['Attack'], tile=Tile(2503, 3115, 0))
    ogre._fields['size'] = 2
    spy_on(tribes.reachability, 'can_reach', returns=True)
    chosen = tribes.ogre_dialogue_stand('Og', WT_TILE.OG, 'yanille')
    expect(chosen).to_equal(Tile(2508, 3117, 0))
    spy_on(tribes.reachability, 'can_reach', returns=False)
    expect(tribes.ogre_dialogue_stand('Og', WT_TILE.OG, 'yanille')).to_be(None)


test('Og selects a reachable side away from the surrounding ogres', stand)


def failed_approaches():
    scene = camp()
    scene.walk_ok = False
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(False)
    expect(scene.walks).to_equal([WT_TILE.OG])
    scene.walk_ok = True
    og = scene.npc('Og', ['Talk-to'], tile=WT_TILE.OG)
    og._fields['size'] = 2
    spy_on(tribes.reachability, 'can_reach', returns=False)
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(False)
    spy_on(tribes.reachability, 'can_reach', returns=True)
    destination = tribes.ogre_dialogue_stand('Og', WT_TILE.OG, 'yanille')
    scene.no_walk = [destination]
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(False)
    expect(scene.walks[-1]).to_equal(destination)
    expect(scene.conversations).to_equal([])


test('Og stops when the camp or the selected conversation tile cannot be reached', failed_approaches)


def journal_not_ready():
    scene = camp()
    reads = []

    def progress():
        reads.append(True)
        return None if len(reads) == 1 else QuestProgress(2, set(scene.flags))
        yield

    def talk(name, prefer, log):
        scene.conversations.append(prefer)
        scene.flags.add('spoken-og')
        scene.item(WT_ITEM.TOBAN_KEY.id, 'Toban key')
        return True
        yield

    spy_on(tribes, 'read_watchtower_progress', impl=progress)
    spy_on(tribes, 'talk_strict', impl=talk)
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(True)
    expect(len(reads)).to_be(3)
    expect(len(scene.conversations)).to_be(1)
    expect(scene.has(WT_ITEM.TOBAN_KEY.id)).to_be(True)


test('Og waits for an unavailable journal before beginning the conversation', journal_not_ready)


def interrupted_by_event():
    scene = camp()
    pending = []

    def talk(name, prefer, log):
        pending.append(True)
        return True
        yield

    spy_on(tribes.event_signal, 'pending', impl=lambda: bool(pending))
    spy_on(tribes, 'talk_strict', impl=talk)
    expect(run_wait(tribes.talk_to_og(scene.log))).to_be(False)
    expect(scene.has(WT_ITEM.TOBAN_KEY.id)).to_be(False)


test('a random event arriving during Og dialogue stops the local retry', interrupted_by_event)

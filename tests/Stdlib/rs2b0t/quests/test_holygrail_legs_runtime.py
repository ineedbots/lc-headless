"""Holy Grail's legs against spied facades: Merlin's door, the whistles, the crossing, the Titan, the bell, the realm's
one step, Sir Percival and the Grail, each through its success and its failures."""

from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment
from rs2004.quests.defs.holygrail import legs
from rs2004.quests.defs.holygrail.areas import FISHERMAN, GRAIL_TILE, ITEM, MERLIN_ID, TITAN_ID, WHISTLE_DOOR_ID
from rs2004.quests.defs.holygrail.armour import unwearable
from rs2004.tabs import prayer
from rs2004.traversal import traversal


def reset():
    event_signal.set_interrupt(None)
    legs.inside_castle = False


after_each(reset)

CAMELOT = Tile(2757, 3477, 0)
LANDING = GRAIL_TILE.CASTLE_LANDING


def run(gen):
    return run_wait(gen)


def chats(scene, pages):
    def effect(op):
        scene.chat.pages = list(pages)
    return effect


def moves_to(scene, tile):
    def effect(op):
        scene.at = tile
    return effect


def good_talk(*args, **kwargs):
    return True
    yield


def bad_talk(*args, **kwargs):
    return False
    yield


def walking():
    scene = Scene(CAMELOT)
    expect(run(legs.walk_to(CAMELOT, 1, scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)
    above = Tile(CAMELOT.x, CAMELOT.z, 1)
    expect(run(legs.walk_to(above, 1, scene.log))).to_be(True)
    expect(scene.walks).to_equal([above])
    expect(legs.chebyshev(CAMELOT, Tile(CAMELOT.x + 3, CAMELOT.z + 1, 0))).to_be(3)
    expect(legs.chebyshev(CAMELOT, above)).to_be(float('inf'))


test('walking is skipped only on the same level, and another level is infinitely far', walking)


def draining():
    scene = Scene(CAMELOT)
    scene.chat.pages = ['continue', 'continue']
    scene.main_modal = 5
    run(legs.drain())
    expect(scene.chat.pages).to_have_length(0)
    expect(scene.main_modal).to_be(-1)

    # Options are left to the caller.
    scene = Scene(CAMELOT)
    scene.chat.pages = [['Yes']]
    scene.main_modal = 5
    run(legs.drain())
    expect(scene.chat.pages).to_have_length(1)
    expect(scene.main_modal).to_be(5)

    # A dialogue open with nothing pressable runs out its twenty ticks.
    scene = Scene(CAMELOT)
    spy_on(chat_dialog, 'is_open', returns=True)
    run(legs.drain())
    expect(scene.ticks).to_be(20)


test('draining clicks pages and boxes through, and leaves an option list alone', draining)


def climbing():
    stand = GRAIL_TILE.CASTLE_STAIR
    scene = Scene(stand)
    scene.loc('Staircase', ['Climb-up'], effect=moves_to(scene, Tile(stand.x, stand.z, 1)))
    expect(run(legs.climb_at(stand, 'Climb-up', scene.log))).to_be(True)

    scene = Scene(CAMELOT)
    scene.walk_ok = False
    expect(run(legs.climb_at(stand, 'Climb-up', scene.log))).to_be(False)

    scene = Scene(stand)
    expect(run(legs.climb_at(stand, 'Climb-up', scene.log))).to_be(False)
    expect(scene.logged("no Staircase offering 'Climb-up'")).to_be(True)

    scene = Scene(stand)
    scene.loc('Staircase', ['Climb-up'], effect=lambda op: False)
    expect(run(legs.climb_at(stand, 'Climb-up', scene.log))).to_be(False)

    # The click lands and the level stays.
    scene = Scene(stand)
    scene.loc('Staircase', ['Climb-up'])
    expect(run(legs.climb_at(stand, 'Climb-up', scene.log))).to_be(False)


test('a climb is proved by the level changing', climbing)


def merlin_scene(effect=None):
    scene = Scene(GRAIL_TILE.MERLIN_WORKSHOP)
    scene.npc('Merlin', ['Talk-to'], id=MERLIN_ID, effect=effect)
    return scene


def merlin():
    scene = merlin_scene()
    scene.npcs = []
    scene.npc('Merlin', ['Talk-to'], id=MERLIN_ID, effect=chats(scene, [['Thank you for the advice.']]))
    expect(run(legs.merlin_leg(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Thank you for the advice.'])

    scene = merlin_scene()
    scene.at = CAMELOT
    scene.walk_ok = False
    expect(run(legs.merlin_leg(scene.log))).to_be(False)

    scene = merlin_scene(lambda op: False)
    expect(run(legs.merlin_leg(scene.log))).to_be(False)

    # He never answers.
    scene = merlin_scene()
    expect(run(legs.merlin_leg(scene.log))).to_be(False)


test('Merlin is talked to in the workshop', merlin)


def merlin_needs_the_door():
    # The other Merlin, Crystal's, carries no Grail dialogue, and the door spawns the right one.
    scene = Scene(GRAIL_TILE.MERLIN_WORKSHOP)
    scene.npc('Merlin', ['Talk-to'], id=MERLIN_ID + 1, effect=lambda op: expect(op).to_be('never'))
    opened = []
    scene.loc('Door', ['Open'], effect=lambda op: opened.append(op))
    expect(run(legs.merlin_leg(scene.log))).to_be(False)
    expect(opened).to_equal(['Open'])
    expect(scene.logged('no Merlin in the workshop')).to_be(True)

    scene = Scene(GRAIL_TILE.MERLIN_WORKSHOP)
    expect(run(legs.merlin_leg(scene.log))).to_be(False)
    expect(scene.ticks).to_be(0)


test('with only the wrong Merlin about, the door is opened and the leg retried', merlin_needs_the_door)


def stripping():
    scene = Scene(CAMELOT)
    expect(run(legs.unequip_all(scene.log))).to_be(True)

    scene = Scene(CAMELOT)
    scene.wear('Rune platebody')
    scene.wear('Rune platelegs')
    expect(run(legs.unequip_all(scene.log))).to_be(True)
    expect(scene.worn).to_have_length(0)

    def stuck(name):
        return False
        yield

    scene = Scene(CAMELOT)
    scene.wear('Cursed amulet')
    spy_on(equipment, 'unequip', impl=stuck)
    expect(run(legs.unequip_all(scene.log))).to_be(False)
    expect(scene.logged('could not remove Cursed amulet')).to_be(True)


test('everything comes off for the monk, or the leg says what would not', stripping)


def wearing():
    unwearable.clear()
    scene = Scene(CAMELOT)
    scene.wear('Rune helm')
    scene.item(1, 'Rune platebody')
    expect(run(legs.wear_armour(['Rune helm', 'Rune platebody', 'Dragon square shield'], scene.log))).to_be(True)
    expect(len(scene.worn)).to_be(2)
    expect(scene.logged('cannot wear Dragon square shield')).to_be(True)
    expect('dragon square shield' in unwearable).to_be(True)
    unwearable.clear()


test('armour that will not go on is remembered and left behind', wearing)


def whistle_scene():
    scene = Scene(GRAIL_TILE.WHISTLE_STAND)
    scene.item(1, ITEM.NAPKIN)
    return scene


def whistle_drops(scene):
    """A door that drops whistles; each Take moves one to the pack."""
    def take(op):
        scene.item(2, ITEM.WHISTLE)

    def door(op):
        scene.on_ground(70, ITEM.WHISTLE, effect=take)

    return door


def whistles():
    scene = whistle_scene()
    scene.item(2, ITEM.WHISTLE)
    expect(run(legs.draynor_whistles(1, scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = whistle_scene()
    scene.loc('Door', ['Open'], id=WHISTLE_DOOR_ID, effect=whistle_drops(scene))
    expect(run(legs.draynor_whistles(2, scene.log))).to_be(True)
    expect(scene.logged('Draynor Manor gave')).to_be(False)


test('the door drops whistles, which are all taken in one step', whistles)


def whistle_failures():
    scene = Scene(GRAIL_TILE.WHISTLE_STAND)
    expect(run(legs.draynor_whistles(1, scene.log))).to_be(False)
    expect(scene.logged('no Holy table napkin')).to_be(True)

    scene = whistle_scene()
    scene.at = CAMELOT
    scene.walk_ok = False
    expect(run(legs.draynor_whistles(1, scene.log))).to_be(False)

    # No door and nothing on the ground.
    scene = whistle_scene()
    expect(run(legs.draynor_whistles(2, scene.log))).to_be(False)
    expect(scene.logged('Draynor Manor gave 0 of 2')).to_be(True)

    scene = whistle_scene()
    scene.on_ground(70, ITEM.WHISTLE, effect=lambda op: False)
    expect(run(legs.draynor_whistles(1, scene.log))).to_be(False)


test('the whistles fail with no napkin, no way up, or none that can be taken', whistle_failures)


def blowing():
    scene = Scene(GRAIL_TILE.SIX_HEADS)
    expect(run(legs.blow(scene.log))).to_be(False)
    expect(scene.logged('no Magic whistle')).to_be(True)

    scene = Scene(GRAIL_TILE.SIX_HEADS)
    scene.item(2, ITEM.WHISTLE, effect=lambda op: False)
    expect(run(legs.blow(scene.log))).to_be(False)

    scene = Scene(GRAIL_TILE.SIX_HEADS)
    scene.item(2, ITEM.WHISTLE)
    expect(run(legs.blow(scene.log))).to_be(False)


test('blowing needs a whistle, a click, and a move', blowing)


def crossing_in():
    scene = Scene(GRAIL_TILE.SIX_HEADS)
    scene.item(2, ITEM.WHISTLE, effect=moves_to(scene, GRAIL_TILE.REALM_ARRIVAL))
    expect(run(legs.whistle_in(scene.log))).to_be(True)

    scene = Scene(CAMELOT)
    scene.walk_ok = False
    expect(run(legs.whistle_in(scene.log))).to_be(False)

    scene = Scene(GRAIL_TILE.SIX_HEADS)
    expect(run(legs.whistle_in(scene.log))).to_be(False)

    # Moved, but not into the realm.
    scene = Scene(GRAIL_TILE.SIX_HEADS)
    scene.item(2, ITEM.WHISTLE, effect=moves_to(scene, CAMELOT))
    expect(run(legs.whistle_in(scene.log))).to_be(False)


test('the whistle takes the player from the six heads into the realm', crossing_in)


def crossing_out():
    legs.inside_castle = True
    scene = Scene(GRAIL_TILE.REALM_ARRIVAL)
    scene.item(2, ITEM.WHISTLE, effect=moves_to(scene, GRAIL_TILE.SIX_HEADS))
    expect(run(legs.whistle_out(scene.log))).to_be(True)
    expect(legs.inside_castle).to_be(False)

    scene = Scene(GRAIL_TILE.REALM_ARRIVAL)
    expect(run(legs.whistle_out(scene.log))).to_be(False)

    # Moved within the realm: still in it.
    scene = Scene(GRAIL_TILE.REALM_ARRIVAL)
    scene.item(2, ITEM.WHISTLE, effect=moves_to(scene, GRAIL_TILE.TITAN_STAND))
    expect(run(legs.whistle_out(scene.log))).to_be(False)


test('blowing it out of the realm forgets the castle', crossing_out)


def protection_rules():
    expect(legs.should_protect(legs.PROTECT_LEVEL, 10, False)).to_be(True)
    expect(legs.should_protect(legs.PROTECT_LEVEL - 1, 10, False)).to_be(False)
    expect(legs.should_protect(legs.PROTECT_LEVEL, 0, False)).to_be(False)
    expect(legs.should_protect(legs.PROTECT_LEVEL, 10, True)).to_be(False)

    scene = Scene(CAMELOT)
    scene.stats['hitpoints'] = 50
    expect(legs.hungry()).to_be(False)
    spy_on(skills, 'effective', returns=50 - legs.EAT_AT_MISSING)
    expect(legs.hungry()).to_be(True)
    scene.stats['hitpoints'] = 0
    expect(legs.hungry()).to_be(False)


test('melee protection and food are decided by their thresholds', protection_rules)


def titan_scene(points=30, level=99):
    scene = Scene(GRAIL_TILE.TITAN_STAND)
    scene.wear(ITEM.EXCALIBUR)
    scene.stats['prayer'] = level
    scene.prayers = {}
    scene.points = points
    spy_on(game, 'set_auto_retaliate', returns=True)
    spy_on(game, 'set_combat_style', returns=True)
    spy_on(game, 'facing', returns=None)
    spy_on(prayer, 'points', impl=lambda: scene.points)
    spy_on(prayer, 'active', impl=lambda name: scene.prayers.get(name, False))
    spy_on(prayer, 'set', impl=lambda name, on: set_prayer(scene, name, on))
    return scene


def set_prayer(scene, name, on):
    scene.prayers[name] = on
    return True
    yield


def titan_kill():
    scene = titan_scene()
    scene.npc('Titan', ['Attack'], id=TITAN_ID, effect=moves_to(scene, GRAIL_TILE.TITAN_WEST))
    expect(run(legs.fight_titan(scene.log))).to_be(True)
    expect(scene.logged('teleported past his crossing')).to_be(True)
    # The prayer is dropped once he can't reach us.
    expect(scene.prayers[legs.PROTECT_MELEE]).to_be(False)


test('the win teleports past him, and the prayer comes down afterwards', titan_kill)


def titan_gates():
    scene = Scene(GRAIL_TILE.TITAN_STAND)
    expect(run(legs.fight_titan(scene.log))).to_be(False)
    expect(scene.logged('refusing to fight the titan')).to_be(True)

    scene = titan_scene()
    scene.at = CAMELOT
    scene.walk_ok = False
    expect(run(legs.fight_titan(scene.log))).to_be(False)


test('no Excalibur, no fight', titan_gates)


def titan_with_low_prayer():
    scene = titan_scene(level=legs.PROTECT_LEVEL - 1)
    scene.npc('Titan', ['Attack'], id=TITAN_ID, effect=moves_to(scene, GRAIL_TILE.TITAN_WEST))
    expect(run(legs.fight_titan(scene.log))).to_be(True)
    expect(scene.logged(f'prayer below {legs.PROTECT_LEVEL}')).to_be(True)
    expect(scene.prayers.get(legs.PROTECT_MELEE)).to_be_null()


test('below Protect from Melee the fight goes on and says so', titan_with_low_prayer)


def titan_yields():
    scene = titan_scene()
    scene.prayers[legs.PROTECT_MELEE] = True
    event_signal.set_interrupt(lambda: True)
    expect(run(legs.fight_titan(scene.log))).to_be(False)
    expect(scene.logged('yielding to a runtime event')).to_be(True)
    # Still out of combat, so the prayer may come down.
    expect(scene.prayers[legs.PROTECT_MELEE]).to_be(False)
    event_signal.set_interrupt(None)

    # In combat the prayer stays up, since he is still swinging.
    scene = titan_scene()
    scene.fighting = True
    scene.prayers[legs.PROTECT_MELEE] = True
    event_signal.set_interrupt(lambda: True)
    expect(run(legs.fight_titan(scene.log))).to_be(False)
    expect(scene.prayers[legs.PROTECT_MELEE]).to_be(True)


test('a runtime event leaves the fight, and the prayer up while he still swings', titan_yields)


def titan_gives_up_with_nobody_there():
    scene = titan_scene(points=0)
    expect(run(legs.fight_titan(scene.log))).to_be(False)
    expect(scene.logged(f'gave up after {legs.TITAN_GUARD_TICKS} ticks (0 attacks)')).to_be(True)


test('no titan for the whole guard gives up', titan_gives_up_with_nobody_there)


def titan_round_orders():
    # Hungry: the sustain runs instead of a swing, until the move past him.
    scene = titan_scene(points=0)
    scene.stats['hitpoints'] = 50
    spy_on(skills, 'effective', returns=30)
    upkeep = {'runs': 0}

    def eats():
        upkeep['runs'] += 1
        if upkeep['runs'] == 3:
            scene.at = GRAIL_TILE.TITAN_WEST
        return None
        yield

    spy_on(sustain, 'run', impl=eats)
    expect(run(legs._titan_rounds(scene.log))).to_be(True)
    expect(upkeep['runs']).to_be(3)

    # A dialogue box is drained before anything else.
    scene = titan_scene(points=0)
    scene.chat.pages = ['continue']
    scene.later(moves_to_later(scene))
    expect(run(legs._titan_rounds(scene.log))).to_be(True)
    expect(scene.chat.pages).to_have_length(0)


def moves_to_later(scene):
    def effect():
        scene.at = GRAIL_TILE.TITAN_WEST
    return effect


test('the order is pray, eat, swing, with any box drained first', titan_round_orders)


def titan_keeps_swinging():
    # Once attacking and facing him, melee keeps swinging on its own.
    scene = titan_scene(points=0)
    clicks = []

    def click(op):
        clicks.append(op)

    titan = scene.npc('Titan', ['Attack'], id=TITAN_ID, effect=click)
    spy_on(game, 'facing', returns=('npc', titan.index))
    expect(run(legs._titan_rounds(scene.log))).to_be(False)
    expect(clicks).to_have_length(1)
    expect(scene.logged('(1 attacks)')).to_be(True)
    expect(scene.logged('titan: hp=')).to_be(True)

    # A refused click is not counted.
    scene = titan_scene(points=0)
    scene.npc('Titan', ['Attack'], id=TITAN_ID, effect=lambda op: False)
    expect(run(legs._titan_rounds(scene.log))).to_be(False)
    expect(scene.logged('(0 attacks)')).to_be(True)


test('a swing in progress is not clicked again', titan_keeps_swinging)


def titan_exception_drops_the_prayer():
    scene = titan_scene()
    scene.prayers[legs.PROTECT_MELEE] = True

    def boom(log):
        raise ValueError('boom')
        yield

    spy_on(legs, '_titan_rounds', impl=boom)
    try:
        run(legs.fight_titan(scene.log))
        raised = False
    except ValueError:
        raised = True
    expect(raised).to_be(True)
    expect(scene.prayers[legs.PROTECT_MELEE]).to_be(False)


test('an error in the fight still drops the prayer, then goes on up', titan_exception_drops_the_prayer)


def ring_scene():
    scene = Scene(GRAIL_TILE.RING_STAND)
    scene.npc('Grail Maiden', tile=GRAIL_TILE.RING_STAND)
    return scene


def ringing():
    scene = ring_scene()
    scene.item(3, ITEM.BELL, effect=moves_to(scene, LANDING))
    expect(run(legs.ring_bell(scene.log))).to_be(True)
    expect(legs.inside_castle).to_be(True)


test('ringing beside a maiden lands the player in the castle', ringing)


def already_inside_bell():
    scene = ring_scene()
    scene.walk_ok = False
    scene.at = CAMELOT
    traversal.last_outcome = 'unreachable'
    expect(run(legs.ring_bell(scene.log))).to_be(True)
    expect(legs.inside_castle).to_be(True)
    traversal.last_outcome = None

    legs.inside_castle = False
    scene = ring_scene()
    scene.walk_ok = False
    scene.at = CAMELOT
    traversal.last_outcome = 'failed'
    expect(run(legs.ring_bell(scene.log))).to_be(False)
    expect(legs.inside_castle).to_be(False)
    traversal.last_outcome = None


test('an unreachable ring stand means the player is already inside', already_inside_bell)


def ring_failures():
    # No bell.
    scene = ring_scene()
    expect(run(legs.ring_bell(scene.log))).to_be(False)
    expect(scene.logged('no Grail bell in the pack')).to_be(True)

    scene = ring_scene()
    scene.item(3, ITEM.BELL, effect=lambda op: False)
    expect(run(legs.ring_bell(scene.log))).to_be(False)

    # A maiden too far off, each try.
    scene = Scene(GRAIL_TILE.RING_STAND)
    scene.npc('Grail Maiden', tile=Tile(GRAIL_TILE.RING_STAND.x + 5, GRAIL_TILE.RING_STAND.z, 0))
    scene.item(3, ITEM.BELL, effect=lambda op: expect(op).to_be('never'))
    expect(run(legs.ring_bell(scene.log))).to_be(False)
    expect(scene.logged('no Grail Maiden came within four tiles')).to_be(True)
    expect(scene.ticks).to_be(legs.RING_ATTEMPTS * 2)

    # The bell rings and nobody answers. From the stand's far corner, as most of the tiles the walk can stop on are
    # already within the landing's two tiles.
    scene = ring_scene()
    scene.at = Tile(GRAIL_TILE.RING_STAND.x + 1, GRAIL_TILE.RING_STAND.z + 1, 0)
    scene.item(3, ITEM.BELL)
    expect(run(legs.ring_bell(scene.log))).to_be(False)
    expect(scene.logged('no Grail Maiden came within four tiles')).to_be(True)


test('the bell needs itself, a click, a maiden near, and an answer', ring_failures)


def taking_the_bell():
    scene = Scene(GRAIL_TILE.BELL_SPAWN)
    scene.item(3, ITEM.BELL)
    expect(run(legs.take_bell(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(GRAIL_TILE.RING_STAND)
    scene.on_ground(3, ITEM.BELL)
    expect(run(legs.take_bell(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    # Not in view until the walk there.
    scene = Scene(GRAIL_TILE.CASTLE_STAIR)
    spawned = {'done': False}

    def walk(dest, radius=0, attempts=0, timeout_ms=0, log=None):
        scene.at = dest
        scene.on_ground(3, ITEM.BELL)
        spawned['done'] = True
        return True
        yield

    spy_on(traversal, 'walk_resilient', impl=walk)
    expect(run(legs.take_bell(scene.log))).to_be(True)
    expect(spawned['done']).to_be(True)


test('the bell is taken from the ground, walking there when out of view', taking_the_bell)


def bell_failures():
    scene = Scene(GRAIL_TILE.CASTLE_STAIR)
    scene.walk_ok = False
    expect(run(legs.take_bell(scene.log))).to_be(False)

    scene = Scene(GRAIL_TILE.CASTLE_STAIR)
    expect(run(legs.take_bell(scene.log))).to_be(False)
    expect(scene.logged('no Grail bell on the ground')).to_be(True)

    scene = Scene(GRAIL_TILE.BELL_SPAWN)
    scene.on_ground(3, ITEM.BELL, effect=lambda op: False)
    expect(run(legs.take_bell(scene.log))).to_be(False)

    # Take goes through and the bell stays down.
    scene = Scene(GRAIL_TILE.BELL_SPAWN)
    scene.on_ground(3, ITEM.BELL, effect=lambda op: True)
    expect(run(legs.take_bell(scene.log))).to_be(False)


test('taking the bell fails at each of its steps', bell_failures)


# The realm's one step.

def realm_outside():
    legs.inside_castle = True
    scene = Scene(CAMELOT)
    expect(run(legs.realm_leg(scene.log))).to_be(False)
    expect(legs.inside_castle).to_be(False)
    expect(scene.logged('not in the Realm')).to_be(True)


test('outside the realm the leg stops and forgets the castle', realm_outside)


def realm_routes_to_the_titan():
    scene = Scene(GRAIL_TILE.REALM_ARRIVAL)
    expect(run(legs.realm_leg(scene.log))).to_be(False)
    expect(scene.logged('refusing to fight the titan')).to_be(True)


test('on the landing side, the titan comes next', realm_routes_to_the_titan)


def realm_upstairs():
    upstairs = GRAIL_TILE.FISHER_KING_DOOR
    scene = Scene(upstairs)
    patch(legs, 'talk_through', good_talk)
    expect(run(legs.realm_leg(scene.log))).to_be(True)
    expect(legs.inside_castle).to_be(True)

    legs.inside_castle = False
    scene = Scene(Tile(upstairs.x + 8, upstairs.z, 1))
    scene.walk_ok = False
    expect(run(legs.realm_leg(scene.log))).to_be(False)
    expect(legs.inside_castle).to_be(True)


test('upstairs, the player is known to be in the castle and goes to the Fisher King', realm_upstairs)


def realm_climbs():
    legs.inside_castle = True
    stair = GRAIL_TILE.CASTLE_STAIR
    scene = Scene(stair)
    scene.loc('Staircase', ['Climb-up'], effect=moves_to(scene, Tile(stair.x, stair.z, 1)))
    expect(run(legs.realm_leg(scene.log))).to_be(True)


test('inside the castle on the ground floor, the stairs come first', realm_climbs)


def realm_bell_route():
    # Nothing yet: the Fisherman spawns the bell, then it is taken and rung.
    scene = Scene(FISHERMAN.anchor)
    talked = []

    def land(op):
        scene.at = LANDING

    def ring_ready(op):
        scene.item(3, ITEM.BELL, effect=land)
        scene.ground = []

    def fisherman(npc, prefer, log):
        talked.append(npc)
        scene.on_ground(3, ITEM.BELL, tile=GRAIL_TILE.BELL_SPAWN, effect=ring_ready)
        return True
        yield

    patch(legs, 'talk_through', fisherman)
    scene.npc('Grail Maiden', tile=GRAIL_TILE.RING_STAND)
    expect(run(legs.realm_leg(scene.log))).to_be(True)
    expect(talked).to_equal([FISHERMAN.npc])
    expect(legs.inside_castle).to_be(True)


test('from the castle grounds, the Fisherman, the bell and the ring lead in', realm_bell_route)


def realm_bell_failures():
    scene = Scene(GRAIL_TILE.BELL_SPAWN)
    scene.walk_ok = False
    expect(run(legs.realm_leg(scene.log))).to_be(False)

    scene = Scene(FISHERMAN.anchor)
    patch(legs, 'talk_through', bad_talk)
    expect(run(legs.realm_leg(scene.log))).to_be(False)

    # The Fisherman talks and the bell never appears.
    scene = Scene(FISHERMAN.anchor)
    patch(legs, 'talk_through', good_talk)
    expect(run(legs.realm_leg(scene.log))).to_be(False)
    expect(scene.logged('no Grail bell on the ground')).to_be(True)


test('the way to the bell fails at each of its steps', realm_bell_failures)


# Sir Percival and the Grail.

def percival():
    scene = Scene(GRAIL_TILE.SACKS_STAND)
    expect(run(legs.free_percival(scene.log))).to_be(False)
    expect(scene.logged('no Magic whistle')).to_be(True)

    scene = Scene(CAMELOT)
    scene.item(2, ITEM.WHISTLE)
    scene.walk_ok = False
    expect(run(legs.free_percival(scene.log))).to_be(False)

    # Already out of the sacks.
    scene = Scene(GRAIL_TILE.SACKS_STAND)
    scene.item(2, ITEM.WHISTLE)
    scene.npc('Sir Percival', ['Talk-to'])
    patch(legs, 'talk_through', good_talk)
    expect(run(legs.free_percival(scene.log))).to_be(True)

    scene = Scene(GRAIL_TILE.SACKS_STAND)
    scene.item(2, ITEM.WHISTLE)
    expect(run(legs.free_percival(scene.log))).to_be(False)
    expect(scene.logged('no Sacks to Open')).to_be(True)

    scene = Scene(GRAIL_TILE.SACKS_STAND)
    scene.item(2, ITEM.WHISTLE)
    scene.loc('Sacks', ['Open'], effect=lambda op: False)
    expect(run(legs.free_percival(scene.log))).to_be(False)

    # The sacks are opened and say nothing.
    scene = Scene(GRAIL_TILE.SACKS_STAND)
    scene.item(2, ITEM.WHISTLE)
    scene.loc('Sacks', ['Open'])
    expect(run(legs.free_percival(scene.log))).to_be(False)

    scene = Scene(GRAIL_TILE.SACKS_STAND)
    scene.item(2, ITEM.WHISTLE)
    scene.loc('Sacks', ['Open'], effect=chats(scene, [['Your father wishes to speak to you.']]))
    expect(run(legs.free_percival(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Your father wishes to speak to you.'])


test('Sir Percival is freed from the sacks and handed a whistle', percival)


def the_grail():
    scene = Scene(GRAIL_TILE.GRAIL_STAND)
    scene.item(4, ITEM.GRAIL)
    expect(run(legs.take_grail(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(GRAIL_TILE.GRAIL_STAND)
    scene.on_ground(4, ITEM.GRAIL)
    expect(run(legs.take_grail(scene.log))).to_be(True)

    scene = Scene(CAMELOT)
    scene.walk_ok = False
    expect(run(legs.take_grail(scene.log))).to_be(False)

    scene = Scene(GRAIL_TILE.GRAIL_STAND)
    expect(run(legs.take_grail(scene.log))).to_be(False)
    expect(scene.logged('no Holy grail on the table')).to_be(True)

    scene = Scene(GRAIL_TILE.GRAIL_STAND)
    scene.on_ground(4, ITEM.GRAIL, effect=lambda op: False)
    expect(run(legs.take_grail(scene.log))).to_be(False)

    scene = Scene(GRAIL_TILE.GRAIL_STAND)
    scene.on_ground(4, ITEM.GRAIL, effect=lambda op: True)
    expect(run(legs.take_grail(scene.log))).to_be(False)


test('the Grail is lifted from the table, once', the_grail)

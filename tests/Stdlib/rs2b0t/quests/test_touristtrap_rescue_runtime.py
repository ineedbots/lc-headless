"""Tourist Trap's rescue against spied facades: the barrels, the mine carts, the lift, the driver and the surface
checkpoint, then what decide()'s helpers source, and from where, as the pack and the bank change."""

import rs2004.quests.defs.touristtrap as tt
from rs2004.bank import bank, banking
from rs2004.execution import event_signal
from rs2004.game import skills
from rs2004.geometry import Tile
from rs2004.quests.defs.touristtrap import ITEM, LOC, NPC, TOURIST_TRAP_STAGE as STAGE
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.food import quest_food


def reset():
    event_signal.set_interrupt(None)
    quest_food.name = None


after_each(reset)

CAMP = Tile(3290, 3025, 0)
UPPER = Tile(3290, 3033, 1)
DESERT = Tile(3260, 3050, 0)
MINE_IN = Tile(3278, 9420, 0)
LOWER = Tile(3303, 9416, 0)
DEEP = tt.DEEP_CART
TENT = Tile(3170, 3048, 0)
BEDABIN = tt.BEDABIN_TENT_APPROACH
MAINLAND = Tile(3200, 3200, 0)
ANA = 7
BARREL = 8


def run(gen):
    return run_wait(gen)


def moves_to(scene, tile):
    def effect(op):
        scene.at = tile
    return effect


def answered_moves_to(scene, tile, option):
    def choose(text):
        scene.at = tile
        scene.chat.on_choose = None

    def effect(op):
        scene.chat.pages = [[option]]
        scene.chat.on_choose = choose
    return effect


def chats(scene, pages):
    def effect(op):
        scene.chat.pages = list(pages)
    return effect


def lower_barrel(scene, effect):
    scene.loc('Barrel', ['Search'], tile=tt.LOWER_BARREL, id=LOC.EMPTY_BARREL, effect=effect)


def gives(scene, id, name, option):
    """A click that asks one question, and answering it gives an item."""
    def choose(text):
        scene.item(id, name)
        scene.chat.on_choose = None

    def effect(op):
        scene.chat.pages = [[option]]
        scene.chat.on_choose = choose
    return effect


# Kebabs.

def kebabs_bought():
    scene = Scene(tt.KEBAB_SELLER)
    scene.item(1, ITEM.COINS, count=10)
    scene.npc('Kebab seller', ['Talk-to'], effect=gives(scene, 2, ITEM.KEBAB, 'Yes please.'))
    expect(run(tt.buy_kebabs(2, scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Yes please.', 'Yes please.'])


test('Kebabs are bought one conversation at a time up to the target', kebabs_bought)


def kebab_failures():
    def seller_scene(effect=None, coins=10):
        scene = Scene(tt.KEBAB_SELLER)
        if coins > 0:
            scene.item(1, ITEM.COINS, count=coins)
        scene.npc('Kebab seller', ['Talk-to'], effect=effect)
        return scene

    scene = seller_scene()
    event_signal.set_interrupt(lambda: True)
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)
    event_signal.set_interrupt(None)

    # The event arrives after the walk.
    scene = seller_scene()
    state = {'calls': 0}

    def second_call():
        state['calls'] += 1
        return state['calls'] > 1

    event_signal.set_interrupt(second_call)
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)
    event_signal.set_interrupt(None)

    scene = seller_scene()
    scene.at = MAINLAND
    scene.walk_ok = False
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)

    scene = seller_scene(coins=0)
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)

    scene = seller_scene()
    for n in range(27):
        scene.item(9, 'Junk')
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)

    scene = seller_scene()
    scene.npcs = []
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)

    scene = seller_scene(lambda op: False)
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)

    # Nothing opens.
    scene = seller_scene()
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)

    scene = Scene(tt.KEBAB_SELLER)
    scene.item(1, ITEM.COINS, count=10)
    scene.npc('Kebab seller', ['Talk-to'], effect=chats(scene, [['Unknown']]))
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)

    # The dialogue ends and no Kebab comes.
    scene = Scene(tt.KEBAB_SELLER)
    scene.item(1, ITEM.COINS, count=10)
    scene.npc('Kebab seller', ['Talk-to'], effect=chats(scene, ['continue']))
    expect(run(tt.buy_kebabs(1, scene.log))).to_be(False)


test('buying a Kebab fails at each of its steps', kebab_failures)


# Freeing a slot.

def fill(scene, count):
    for n in range(count):
        scene.item(999, 'Key thing')


def slot_freed():
    scene = Scene(LOWER)
    expect(run(tt.free_one_rescue_slot(scene.log))).to_be(True)

    scene = Scene(LOWER)
    fill(scene, 27)
    scene.item(1, ITEM.HAMMER, effect=lambda op: scene.take(1))
    expect(run(tt.free_one_rescue_slot(scene.log))).to_be(True)
    expect(scene.has(1)).to_be(False)

    scene = Scene(LOWER)
    fill(scene, 27)
    scene.item(1, ITEM.HAMMER, effect=lambda op: False)
    expect(run(tt.free_one_rescue_slot(scene.log))).to_be(False)

    # A drop that does not land moves on to the next expendable.
    scene = Scene(LOWER)
    fill(scene, 26)
    scene.item(1, ITEM.HAMMER)
    scene.item(2, ITEM.BAR, effect=lambda op: scene.take(2))
    expect(run(tt.free_one_rescue_slot(scene.log))).to_be(True)
    expect(scene.has(1)).to_be(True)

    scene = Scene(LOWER)
    fill(scene, 28)
    expect(run(tt.free_one_rescue_slot(scene.log))).to_be(False)
    expect(scene.logged('no safe expendable item')).to_be(True)


test('a rescue slot comes only from what the prototype left over', slot_freed)


# The barrels.

def lower_barrel_takes_one():
    scene = Scene(LOWER)
    lower_barrel(scene, gives(scene, BARREL, ITEM.BARREL, 'Yeah, cool!'))
    expect(run(tt.search_lower_barrel(True, scene.log))).to_be(True)
    expect(scene.has(BARREL)).to_be(True)


test('the lower barrel gives an empty one when asked', lower_barrel_takes_one)


def lower_barrel_returns_ana():
    scene = Scene(LOWER)
    lower_barrel(scene, gives(scene, ANA, ITEM.ANA_BARREL, 'No thanks.'))
    expect(run(tt.search_lower_barrel(False, scene.log))).to_be(True)
    expect(scene.has(ANA)).to_be(True)


test('the lower barrel hands back Ana even when turned down', lower_barrel_returns_ana)


def lower_barrel_declined():
    scene = Scene(LOWER)

    def choose(text):
        scene.say('You decide not to take the barrel.')

    scene.chat.on_choose = choose
    lower_barrel(scene, chats(scene, [['No thanks.']]))
    expect(run(tt.search_lower_barrel(False, scene.log))).to_be(True)
    expect(scene.has(BARREL)).to_be(False)


test("turning a barrel down is proved by the game's message", lower_barrel_declined)


def lower_barrel_failures():
    scene = Scene(LOWER)
    fill(scene, 28)
    lower_barrel(scene, None)
    expect(run(tt.search_lower_barrel(True, scene.log))).to_be(False)
    expect(scene.logged('no safe expendable item')).to_be(True)

    scene = Scene(LOWER)
    lower_barrel(scene, None)

    def says(text):
        scene.say('Something else entirely')

    scene.chat.on_choose = says
    scene.locs = []
    lower_barrel(scene, chats(scene, [['Yeah, cool!']]))
    expect(run(tt.search_lower_barrel(True, scene.log))).to_be(False)
    expect(scene.logged('without its authoritative result; observed=[Something else entirely]')).to_be(True)


test('a barrel with no result is logged with what was said', lower_barrel_failures)


def surface_barrel_scene(effect=None):
    scene = Scene(tt.SURFACE_BARREL_APPROACH)
    scene.loc('Barrel', ['Search'], tile=Tile(3278, 3017, 0), id=LOC.FULL_BARREL, effect=effect)
    return scene


def surface_barrel():
    scene = surface_barrel_scene()
    scene.locs = []
    scene.loc('Barrel', ['Search'], tile=Tile(3278, 3017, 0), id=LOC.FULL_BARREL, effect=lambda op: scene.item(ANA, ITEM.ANA_BARREL) and None)
    expect(run(tt.search_surface_barrel(scene.log))).to_be(True)

    # Ana climbs in through a dialogue.
    scene = surface_barrel_scene()
    scene.locs = []

    def ana_lands():
        scene.item(ANA, ITEM.ANA_BARREL)

    def page(op):
        scene.chat.pages = ['continue']
        scene.later(ana_lands)

    scene.loc('Barrel', ['Search'], tile=Tile(3278, 3017, 0), id=LOC.FULL_BARREL, effect=page)
    expect(run(tt.search_surface_barrel(scene.log))).to_be(True)


test('the top barrel returns Ana, with or without her dialogue', surface_barrel)


def surface_barrel_failures():
    scene = Scene(CAMP)
    scene.walk_ok = False
    expect(run(tt.search_surface_barrel(scene.log))).to_be(False)

    scene = Scene(tt.SURFACE_BARREL_APPROACH)
    expect(run(tt.search_surface_barrel(scene.log))).to_be(False)
    expect(scene.logged('did not expose its Search action')).to_be(True)

    scene = surface_barrel_scene(lambda op: False)
    expect(run(tt.search_surface_barrel(scene.log))).to_be(False)
    expect(scene.logged('Search action was not dispatched')).to_be(True)

    scene = surface_barrel_scene()
    expect(run(tt.search_surface_barrel(scene.log))).to_be(False)
    expect(scene.logged('contained no Ana response')).to_be(True)

    scene = Scene(tt.SURFACE_BARREL_APPROACH)
    scene.loc('Barrel', ['Search'], tile=Tile(3278, 3017, 0), id=LOC.FULL_BARREL, effect=chats(scene, [['Unknown']]))
    expect(run(tt.search_surface_barrel(scene.log))).to_be(False)
    expect(scene.logged('did not reach the inventory award')).to_be(True)


test('the top barrel fails at each of its steps', surface_barrel_failures)


# The mine carts.

def cart_scene(start, anchor, effect=None):
    scene = Scene(start)
    scene.loc('Cart', ['Search'], tile=anchor, id=LOC.MINE_CART, effect=effect)
    return scene


def cart_rides():
    scene = Scene(LOWER)
    scene.loc('Cart', ['Search'], tile=tt.LOWER_CART, id=LOC.MINE_CART, effect=answered_moves_to(scene, DEEP, 'Yes, of course.'))
    expect(run(tt.ride_mine_cart(tt.LOWER_CART, scene.log))).to_be(True)
    expect(scene.logged('mine-cart transit reached the deep mine')).to_be(True)

    scene = Scene(DEEP)
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART, effect=answered_moves_to(scene, LOWER, 'Yes, of course.'))
    expect(run(tt.ride_mine_cart(DEEP, scene.log))).to_be(True)
    expect(scene.logged('mine-cart transit reached the lower mine')).to_be(True)


test('the cart rides either way', cart_rides)


def cart_failures():
    scene = Scene(LOWER)
    event_signal.set_interrupt(lambda: True)
    expect(run(tt.ride_mine_cart(tt.LOWER_CART, scene.log))).to_be(False)
    expect(scene.lines).to_have_length(0)
    event_signal.set_interrupt(None)

    # No cart, so the interaction does not complete.
    scene = Scene(LOWER)
    expect(run(tt.ride_mine_cart(tt.LOWER_CART, scene.log))).to_be(False)
    expect(scene.logged('did not complete at the lower mine')).to_be(True)

    # The Agility roll fails: the player stays and eats.
    scene = Scene(LOWER)
    scene.loc('Cart', ['Search'], tile=tt.LOWER_CART, id=LOC.MINE_CART, effect=chats(scene, [['Yes, of course.']]))
    expect(run(tt.ride_mine_cart(tt.LOWER_CART, scene.log))).to_be(False)
    expect(scene.logged('Agility roll failed at the lower mine')).to_be(True)

    # Somewhere else entirely.
    scene = Scene(LOWER)
    scene.loc('Cart', ['Search'], tile=tt.LOWER_CART, id=LOC.MINE_CART, effect=answered_moves_to(scene, CAMP, 'Yes, of course.'))
    expect(run(tt.ride_mine_cart(tt.LOWER_CART, scene.log))).to_be(False)
    expect(scene.logged('transit unresolved; current area=campSurface')).to_be(True)


test('a failed roll is told from a lost ride', cart_failures)


# Catching Ana.

def catching():
    scene = Scene(tt.ANA_TILE)
    scene.item(ANA, ITEM.ANA_BARREL)
    expect(run(tt.catch_ana_in_barrel(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(tt.ANA_TILE)
    scene.npc('Ana', id=NPC.ANA)

    def squeeze(target):
        scene.take(BARREL)
        scene.item(ANA, ITEM.ANA_BARREL)
        scene.chat.pages = ['continue']
        scene.chat.shown = ['You manage to squeeze Ana into the barrel.']

    scene.item(BARREL, ITEM.BARREL, on_use=squeeze)
    expect(run(tt.catch_ana_in_barrel(scene.log))).to_be(True)

    # A barrel with no Ana in it, whatever the dialogue says.
    scene = Scene(tt.ANA_TILE)
    expect(run(tt.catch_ana_in_barrel(scene.log))).to_be(False)


test('Ana is caught with the empty barrel, proved by what she says and by the pack', catching)


def full_recapture_scene(start):
    """Ana in the deep mine, the barrel beside the lower cart, and the carts each way."""
    scene = Scene(start)
    scene.npc('Ana', id=NPC.ANA)
    lower_barrel(scene, gives(scene, BARREL, ITEM.BARREL, 'Yeah, cool!'))
    scene.loc('Cart', ['Search'], tile=tt.LOWER_CART, id=LOC.MINE_CART, effect=answered_moves_to(scene, DEEP, 'Yes, of course.'))
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART, effect=answered_moves_to(scene, LOWER, 'Yes, of course.'))

    def squeeze(target):
        scene.take(BARREL)
        scene.item(ANA, ITEM.ANA_BARREL)
        scene.chat.pages = ['continue']
        scene.chat.shown = ['I djont fit in dis bawwel']

    scene.squeeze = squeeze
    return scene


def recapture_from_camp():
    scene = Scene(CAMP)
    for name in tt.SLAVE_OUTFIT:
        scene.wear(name)
    scene.npc('Ana', id=NPC.ANA)
    scene.loc('Door', ['Open'], tile=tt.MINE_ENTRANCE, id=LOC.SURFACE_MINE_DOOR[0], effect=moves_to(scene, MINE_IN))
    scene.loc('Cave', ['Walk through'], tile=tt.CAVE_OUTER_LANDING, id=LOC.MINE_CAVE[0], effect=moves_to(scene, tt.CAVE_INNER_LANDING))
    # Once past the cave, the barrel gives Ana straight back.
    lower_barrel(scene, gives(scene, ANA, ITEM.ANA_BARREL, 'Yeah, cool!'))
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(True)
    expect(scene.logged('recovered Ana directly from the lower transport barrel')).to_be(True)


test('from the camp the recapture goes through the mine to the lower barrel', recapture_from_camp)


def recapture_from_deep_without_barrel():
    scene = full_recapture_scene(DEEP)
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(False)
    expect(scene.logged('mine-cart transit reached the lower mine')).to_be(True)
    expect(scene.logged('mine-cart transit reached the deep mine')).to_be(True)
    expect(scene.logged('using the empty barrel on Ana did not complete')).to_be(True)


test('from the deep mine with no barrel, the player rides back for one', recapture_from_deep_without_barrel)


def recapture_with_barrel():
    scene = full_recapture_scene(DEEP)
    scene.item(BARREL, ITEM.BARREL, on_use=scene.squeeze)
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(True)
    expect(scene.logged('Ana secured in the barrel')).to_be(True)


test('at Ana with a barrel, she is caught there', recapture_with_barrel)


def recapture_failures():
    scene = Scene(CAMP)
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(False)

    scene = Scene(MINE_IN)
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(False)

    scene = Scene(DEEP)
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(False)

    scene = Scene(LOWER)
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(False)

    # The barrel is taken and the cart fails its roll.
    scene = Scene(LOWER)
    lower_barrel(scene, gives(scene, BARREL, ITEM.BARREL, 'Yeah, cool!'))
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(False)

    scene = Scene(DESERT)
    expect(run(tt.reach_and_catch_ana(scene.log))).to_be(False)
    expect(scene.logged('did not reach Ana; current area=desert')).to_be(True)


test('the recapture fails at each of its steps', recapture_failures)


# The checkpoints.

def deep_checkpoint():
    # Ana rides first, then the player, and the lower barrel hands her back.
    scene = Scene(DEEP)
    scene.item(ANA, ITEM.ANA_BARREL, on_use=lambda target: scene.take(ANA))
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART, effect=answered_moves_to(scene, LOWER, 'Yes, of course.'))
    lower_barrel(scene, gives(scene, ANA, ITEM.ANA_BARREL, 'No thanks.'))
    expect(run(tt.deep_to_lower_checkpoint(scene.log))).to_be(True)
    expect(scene.has(ANA)).to_be(True)

    scene = Scene(DEEP)
    scene.item(ANA, ITEM.ANA_BARREL)
    expect(run(tt.deep_to_lower_checkpoint(scene.log))).to_be(False)

    scene = Scene(DEEP)
    scene.item(ANA, ITEM.ANA_BARREL)
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART)
    expect(run(tt.deep_to_lower_checkpoint(scene.log))).to_be(False)

    scene = Scene(DEEP)
    expect(run(tt.deep_to_lower_checkpoint(scene.log))).to_be(False)

    # At the lower mine with no barrel to search.
    scene = Scene(DEEP)
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART, effect=answered_moves_to(scene, LOWER, 'Yes, of course.'))
    expect(run(tt.deep_to_lower_checkpoint(scene.log))).to_be(False)


test('the deep-to-lower checkpoint sends Ana ahead and follows her', deep_checkpoint)


def winch(scene, effect):
    scene.loc('Winch', ['Use'], tile=Tile(3279, 3017, 0), id=LOC.SURFACE_WINCH, effect=effect)


def surface_lift_scene():
    scene = Scene(tt.SURFACE_WINCH_APPROACH)

    def winds(op):
        scene.chat.pages = ['continue']
        scene.chat.shown = ['A barrel coming to the surface']

    winch(scene, winds)
    scene.loc('Barrel', ['Search'], tile=Tile(3278, 3017, 0), id=LOC.FULL_BARREL, effect=lambda op: scene.item(ANA, ITEM.ANA_BARREL) and None)
    return scene


def lift_works():
    scene = surface_lift_scene()
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(True)
    expect(scene.logged('recovered Ana from the top barrel')).to_be(True)

    # An empty lift says so; the top barrel is still tried, and has no Ana.
    scene = Scene(tt.SURFACE_WINCH_APPROACH)
    winch(scene, lambda op: scene.say('A heavy barrel filled with stone comes to the surface'))
    scene.loc('Barrel', ['Search'], tile=Tile(3278, 3017, 0), id=LOC.FULL_BARREL)
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('top barrel did not contain Ana')).to_be(True)


test('the winch and the top barrel bring Ana up, or show the lift was empty', lift_works)


def lift_from_below():
    scene = Scene(LOWER)
    for name in tt.SLAVE_OUTFIT:
        scene.wear(name)
    scene.loc('Bucket', tile=tt.LIFT_BUCKET, id=LOC.LIFT_BUCKET)

    def bucket(target):
        scene.take(ANA)

    scene.item(ANA, ITEM.ANA_BARREL, on_use=bucket)
    scene.loc('Cave', ['Walk through'], tile=tt.CAVE_INNER_LANDING, id=LOC.MINE_CAVE[0], effect=moves_to(scene, tt.CAVE_OUTER_LANDING))
    scene.loc('Door', ['Open'], tile=tt.MINE_EXIT_DOOR, id=LOC.UNDERGROUND_MINE_DOOR[0], effect=moves_to(scene, tt.SURFACE_WINCH_APPROACH))
    winch(scene, lambda op: scene.say('A heavy barrel filled with stone comes to the surface'))
    scene.loc('Barrel', ['Search'], tile=Tile(3278, 3017, 0), id=LOC.FULL_BARREL, effect=lambda op: scene.item(ANA, ITEM.ANA_BARREL) and None)
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(True)
    expect(scene.logged('placing Ana on the underground lift')).to_be(True)


test('from below, Ana goes on the lift and the player goes up to meet her', lift_from_below)


def lift_failures():
    # No bucket.
    scene = Scene(LOWER)
    scene.item(ANA, ITEM.ANA_BARREL)
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('underground lift interaction did not complete')).to_be(True)

    # The way up is shut.
    scene = Scene(LOWER)
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('could not reach the surface machinery')).to_be(True)

    scene = Scene(DESERT)
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('surface probe unavailable from area=desert')).to_be(True)

    scene = Scene(tt.SURFACE_WINCH_APPROACH)
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('surface winch interaction could not be dispatched')).to_be(True)

    # The winch answers nothing.
    scene = Scene(tt.SURFACE_WINCH_APPROACH)
    winch(scene, None)
    scene.say('Earlier line')
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('follow-up timed out; messages=[] modal=[]')).to_be(True)

    # The winch's dialogue asks something unknown.
    scene = Scene(tt.SURFACE_WINCH_APPROACH)

    def asks(op):
        scene.chat.pages = [['Unknown']]
        scene.chat.shown = ['get me out of here']

    winch(scene, asks)
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)

    # A pack with nothing it can drop for Ana.
    scene = Scene(tt.SURFACE_WINCH_APPROACH)
    fill(scene, 28)
    winch(scene, lambda op: scene.say('A heavy barrel filled with stone comes to the surface'))
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('no safe expendable item')).to_be(True)


test('the lift fails at each of its steps', lift_failures)


def lift_keeps_ana_in_the_pack():
    scene = Scene(LOWER)
    scene.loc('Bucket', tile=tt.LIFT_BUCKET, id=LOC.LIFT_BUCKET)
    scene.item(ANA, ITEM.ANA_BARREL, on_use=lambda target: None)
    spy_on(tt, 'drain_interaction_dialog', impl=lambda prefer, log, until=None: drained())
    expect(run(tt.retrieve_from_surface_lift(scene.log))).to_be(False)
    expect(scene.logged('Ana remained in the backpack')).to_be(True)


def drained():
    return True
    yield


test('Ana still in the pack after the lift is reported', lift_keeps_ana_in_the_pack)


# The driver and the surface cart.

def cart_at_surface(scene, search=None):
    scene.loc('Cart', ['Search'], tile=tt.SURFACE_CART_APPROACH, id=LOC.SURFACE_CART, effect=search)


def boards_with_ana(scene):
    def choose(text):
        scene.at = DESERT
        scene.chat.on_choose = None

    def effect(op):
        scene.chat.pages = [["Yes, I'll get on."]]
        scene.chat.on_choose = choose
    return effect


def carrying_ana(scene):
    def return_ana(target):
        return None

    scene.item(ANA, ITEM.ANA_BARREL, on_use=return_ana)


def boards_ready():
    # Paid before a restart: Ana is on the cart and Search boards for free.
    scene = Scene(tt.SURFACE_CART_APPROACH)
    scene.item(ANA, ITEM.ANA_BARREL)
    cart_at_surface(scene, boards_with_ana(scene))
    spy_on(tt, 'use_item_on_loc', impl=lambda *args: drained())
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(False)
    expect(scene.logged('Ana remained in the backpack after the cart interaction')).to_be(True)

    scene = Scene(tt.SURFACE_CART_APPROACH)
    cart_at_surface(scene, boards_with_ana(scene))
    scene.item(ANA, ITEM.ANA_BARREL, on_use=lambda target: None)
    scene.pack = []

    def ana_returns(text):
        scene.at = DESERT
        scene.item(ANA, ITEM.ANA_BARREL)
        scene.chat.on_choose = None

    scene.locs = []
    cart_at_surface(scene, chats(scene, [["Yes, I'll get on."]]))
    scene.chat.on_choose = ana_returns
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(True)
    expect(scene.logged('ready-state boarding reached the desert with Ana')).to_be(True)


test('a cart already paid for boards free, and Ana must really leave the pack first', boards_ready)


def bribes_the_driver():
    scene = Scene(tt.SURFACE_CART_APPROACH)
    scene.item(1, ITEM.COINS, count=250)
    searches = []

    def search(op):
        searches.append(op)
        scene.chat.pages = [["Yes, I'll get on."]]

    def boarded(text):
        if len(searches) == 2:
            scene.at = DESERT
            scene.item(ANA, ITEM.ANA_BARREL)

    def bribe(op):
        scene.chat.pages = [[tt.DRIVER_DIALOG[0]], ['A hundred it is!']]
        scene.take(1)
        scene.item(1, ITEM.COINS, count=150)

    scene.chat.on_choose = boarded
    cart_at_surface(scene, search)
    scene.npc('Driver', ['Talk-to'], id=NPC.MINE_CART_DRIVER, effect=bribe)
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(True)
    expect(scene.logged('driver sequence reached the desert with Ana')).to_be(True)
    expect(scene.logged('coins>=100=yes')).to_be(True)


test('the driver takes his hundred coins and the cart boards', bribes_the_driver)


def appeals_without_coins():
    scene = Scene(tt.SURFACE_CART_APPROACH)
    searches = []

    def search(op):
        searches.append(op)
        scene.chat.pages = [["Yes, I'll get on."]]

    def boarded(text):
        if len(searches) == 2:
            scene.at = DESERT
            scene.item(ANA, ITEM.ANA_BARREL)

    scene.chat.on_choose = boarded
    cart_at_surface(scene, search)
    scene.npc('Driver', ['Talk-to'], id=NPC.MINE_CART_DRIVER, effect=chats(scene, [[tt.DRIVER_NO_COIN_DIALOG[6]]]))
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(True)
    expect(scene.logged('coins>=100=no')).to_be(True)


test('with no coins, the prison-riot appeal does the same', appeals_without_coins)


def driver_failures():
    scene = Scene(tt.SURFACE_CART_APPROACH)
    scene.item(ANA, ITEM.ANA_BARREL)
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(False)
    expect(scene.logged('placing Ana in the cart did not complete')).to_be(True)

    # Neither cart nor driver.
    scene = Scene(tt.SURFACE_CART_APPROACH)
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(False)
    expect(scene.logged('ready-state boarding was not available')).to_be(True)
    expect(scene.logged('driver dialogue did not complete')).to_be(True)

    # The driver talks and takes nothing.
    scene = Scene(tt.SURFACE_CART_APPROACH)
    scene.item(1, ITEM.COINS, count=250)
    scene.npc('Driver', ['Talk-to'], id=NPC.MINE_CART_DRIVER, effect=chats(scene, ['continue']))
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(False)
    expect(scene.logged('ended without the 100-Coin bribe')).to_be(True)

    # Paid, and the cart then cannot be boarded.
    scene = Scene(tt.SURFACE_CART_APPROACH)
    scene.npc('Driver', ['Talk-to'], id=NPC.MINE_CART_DRIVER, effect=chats(scene, ['continue']))
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(False)
    expect(scene.logged('boarding interaction did not complete')).to_be(True)

    # Boards, and the ride never gets there.
    scene = Scene(tt.SURFACE_CART_APPROACH)
    cart_at_surface(scene, chats(scene, [["Yes, I'll get on."]]))
    scene.npc('Driver', ['Talk-to'], id=NPC.MINE_CART_DRIVER, effect=chats(scene, ['continue']))
    expect(run(tt.bribe_driver_and_escape(scene.log))).to_be(False)
    expect(scene.logged('boarding did not reach the desert with Ana')).to_be(True)


test('the driver sequence fails at each of its steps', driver_failures)


def lower_checkpoint():
    # An empty barrel means a failed roll: retry beside the cart.
    scene = Scene(LOWER)
    scene.item(BARREL, ITEM.BARREL)
    scene.loc('Cart', ['Search'], tile=tt.LOWER_CART, id=LOC.MINE_CART, effect=answered_moves_to(scene, DEEP, 'Yes, of course.'))
    expect(run(tt.lower_rescue_checkpoint(scene.log))).to_be(True)
    expect(scene.logged('empty barrel ready after a failed cart roll')).to_be(True)

    # The barrel hands Ana back.
    scene = Scene(LOWER)
    lower_barrel(scene, gives(scene, ANA, ITEM.ANA_BARREL, 'No thanks.'))
    expect(run(tt.lower_rescue_checkpoint(scene.log))).to_be(True)

    scene = Scene(LOWER)
    expect(run(tt.lower_rescue_checkpoint(scene.log))).to_be(False)

    # Holding Ana skips the barrel for the lift.
    scene = Scene(LOWER)
    scene.item(ANA, ITEM.ANA_BARREL)
    expect(run(tt.lower_rescue_checkpoint(scene.log))).to_be(False)
    expect(scene.logged('placing Ana on the underground lift')).to_be(True)


test('the lower checkpoint tells a failed roll from a lift still to do', lower_checkpoint)


def operations(has_ana=False, lift=False, cart=None, recapture=False, area='campSurface'):
    calls = {'lift': 0, 'cart': 0, 'recapture': 0, 'upkeep': 0, 'waits': 0}
    outcomes = list(cart) if cart is not None else []

    def retrieve(log):
        calls['lift'] += 1
        return lift
        yield

    def escape(log):
        calls['cart'] += 1
        return outcomes.pop(0) if len(outcomes) > 0 else False
        yield

    def recaptured(log):
        calls['recapture'] += 1
        return recapture
        yield

    def upkeep():
        calls['upkeep'] += 1
        return None
        yield

    def wait():
        calls['waits'] += 1
        return None
        yield

    return Fake(calls=calls, has_ana_barrel=lambda: has_ana, retrieve_lift=retrieve, escape_by_cart=escape, recapture_ana=recaptured, current_area=lambda: area, maintain_survival=upkeep, wait_between_attempts=wait)


def surface_checkpoint_paths():
    lines = []

    ops = operations(lift=True)
    expect(run(tt.run_surface_rescue_checkpoint(ops, lines.append))).to_be(True)
    expect(ops.calls['cart']).to_be(0)

    # The lift is empty and the third cart attempt works.
    ops = operations(cart=[False, False, True])
    expect(run(tt.run_surface_rescue_checkpoint(ops, lines.append))).to_be(True)
    expect(ops.calls['cart']).to_be(3)
    expect(ops.calls['waits']).to_be(2)

    # Holding Ana, three failures stay here rather than going underground.
    ops = operations(has_ana=True)
    expect(run(tt.run_surface_rescue_checkpoint(ops, lines.append))).to_be(False)
    expect(ops.calls['lift']).to_be(0)
    expect(ops.calls['recapture']).to_be(0)

    # Everything clear: back to the deep mine.
    ops = operations(recapture=True)
    expect(run(tt.run_surface_rescue_checkpoint(ops, lines.append))).to_be(True)
    expect(ops.calls['recapture']).to_be(1)

    lines.clear()
    ops = operations(area='mineLower')
    expect(run(tt.run_surface_rescue_checkpoint(ops, lines.append))).to_be(False)
    expect(lines[-1]).to_contain('current area=mineLower')


test('the surface checkpoint tries the lift, the cart three times, then the replay', surface_checkpoint_paths)


def surface_checkpoint_yields():
    # The event comes on each later check in turn, so every stop is met.
    for calls_before in range(9):
        state = {'left': calls_before}

        def pending():
            state['left'] -= 1
            return state['left'] < 0

        event_signal.set_interrupt(pending)
        ops = operations()
        expect(run(tt.run_surface_rescue_checkpoint(ops, lambda line: None))).to_be(False)
        expect(ops.calls['recapture']).to_be(0)
        event_signal.set_interrupt(None)


test('a runtime event stops the surface checkpoint at any of its checks', surface_checkpoint_yields)


def surface_checkpoint_wired():
    scene = Scene(tt.SURFACE_WINCH_APPROACH)
    scene.item(1, ITEM.COINS, count=50)
    expect(run(tt.surface_rescue_checkpoint(scene.log))).to_be(False)
    expect(scene.logged('rescue checkpoint: area=campSurface; empty barrel=no; Ana barrel=no; slave outfit=missing')).to_be(True)
    expect(scene.logged('deep-mine recapture did not complete')).to_be(True)


test('the live checkpoint reports what it starts from', surface_checkpoint_wired)


def irena_ends_it():
    scene = Scene(tt.IRENA)
    scene.npc('Irena', ['Talk-to'], id=NPC.IRENA, effect=chats(scene, [['Agility.'], ['Agility.']]))
    expect(run(tt.claim_reward(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Agility.', 'Agility.'])

    scene = Scene(tt.IRENA)

    def choose(text):
        scene.take(ANA)

    scene.chat.on_choose = choose
    scene.item(ANA, ITEM.ANA_BARREL)
    scene.npc('Irena', ['Talk-to'], id=NPC.IRENA, effect=chats(scene, [['Agility.']]))
    expect(run(tt.return_ana_to_irena(scene.log))).to_be(True)

    scene = Scene(tt.IRENA)
    expect(run(tt.return_ana_to_irena(scene.log))).to_be(False)


test('Irena takes Ana and pays in Agility', irena_ends_it)


# Reading the stage.

def stage_reader():
    from rs2004.tabs import quests
    scene = Scene(DESERT)
    scene.status = 'complete'
    expect(run(tt.read_tourist_trap_stage())).to_be(STAGE.COMPLETE)

    scene.status = 'not_started'
    expect(run(tt.read_tourist_trap_stage())).to_be(STAGE.NOT_STARTED)

    scene.status = 'unknown'
    expect(run(tt.read_tourist_trap_stage())).to_be_null()

    def journal(name):
        scene.main_modal = 5
        return ['I must head into the desert to search for Ana']
        yield

    scene.status = 'in_progress'
    spy_on(quests, 'journal', impl=journal)
    expect(run(tt.read_tourist_trap_stage())).to_be(STAGE.STARTED)
    expect(scene.main_modal).to_be(-1)


test('the stage reads from the quest list, then the journal, which it shuts', stage_reader)


# Banking food away.

def banking_scene():
    scene = Scene(tt.DRAYNOR_BANK)
    quest_food.name = 'Trout'
    spy_on(banking, 'open', impl=lambda log=None: drained())
    spy_on(bank, 'close', impl=lambda: drained())
    return scene


def trout_scene(count, moves=True):
    scene = banking_scene()
    for n in range(count):
        scene.item(1, 'Trout')

    def deposit(name):
        if not moves:
            return True
        scene.pack.pop()
        return True

    spy_on(bank, 'deposit', impl=deposit)
    return scene


def food_banked():
    scene = trout_scene(3)
    expect(run(tt.bank_food_down_to(1, scene.log))).to_be(True)
    expect(scene.pack).to_have_length(1)

    scene = trout_scene(1)
    expect(run(tt.bank_food_down_to(1, scene.log))).to_be(True)

    def closed(log=None):
        return False
        yield

    scene = trout_scene(3)
    spy_on(banking, 'open', impl=closed)
    expect(run(tt.bank_food_down_to(1, scene.log))).to_be(False)

    scene = trout_scene(3)
    spy_on(bank, 'deposit', returns=False)
    expect(run(tt.bank_food_down_to(1, scene.log))).to_be(False)

    scene = trout_scene(3, moves=False)
    expect(run(tt.bank_food_down_to(1, scene.log))).to_be(False)


test('food is banked one at a time down to the count', food_banked)


# What decide's helpers source. Each snapshot is the pack and bank named; the area is the tile's.

def snap(tile=None, inv=None, worn=None, bank=None, known=True, free=8, stage=None):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {name.lower(): count for name, count in (inv or {}).items()},
        'worn': set([name.lower() for name in (worn or [])]),
        'bank': {name.lower(): count for name, count in (bank or {}).items()},
        'bank_known': known,
        'tile': tile if tile is not None else MAINLAND,
        'free_slots': free,
        'stage': stage if stage is not None else STAGE.STARTED,
    })


def withdraws(step, name, qty):
    expect(step.kind).to_be('withdraw')
    expect(step.items[0]['name']).to_be(name)
    expect(step.items[0]['qty']).to_be(qty)


def is_custom(step, text):
    expect(step.kind).to_be('custom')
    expect(step.name).to_contain(text)


def space_steps():
    expect(tt.make_preparation_space(snap(free=None), 3)).to_be_null()
    expect(tt.make_preparation_space(snap(free=3), 3)).to_be_null()
    expect(tt.make_preparation_space(snap(inv={'Lobster': 1}, free=0), 1).kind).to_be('deposit')
    expect(tt.make_preparation_space(snap(free=0), 1).reason).to_contain('need 1 free inventory slot for')
    expect(tt.make_preparation_space(snap(free=0), 2).reason).to_contain('need 2 free inventory slots for')

    expect(tt.make_rescue_space(snap(free=None), 3)).to_be_null()
    expect(tt.make_rescue_space(snap(inv={'Lobster': 1}, free=0), 1).kind).to_be('deposit')
    expect(tt.make_rescue_space(snap(free=0), 2).reason).to_contain('need 2 free inventory slots for Tourist Trap survival')


test('room in the pack comes from anything spare, or the leg waits', space_steps)


def snapshot_counts():
    quest_food.name = 'Trout'
    shot = snap(inv={'Waterskin(4)': 1, 'Waterskin(1)': 2, 'Trout': 2, ITEM.DESERT_SHIRT: 1}, worn=[ITEM.DESERT_ROBE, ITEM.DESERT_BOOTS], bank={'Trout': 3})
    expect(tt.waterskin_doses(shot)).to_be(6)
    expect(tt.waterskin_containers(shot)).to_be(3)
    expect(tt.configured_food_count(shot)).to_be(2)
    expect(tt.banked_configured_food_count(shot)).to_be(3)
    expect(tt.has_outfit(shot, tt.DESERT_OUTFIT)).to_be(True)
    expect(tt.has_outfit(shot, tt.SLAVE_OUTFIT)).to_be(False)
    expect(tt.outfit_copies(shot, tt.DESERT_OUTFIT)).to_be(1)

    quest_food.name = '   '
    expect(tt.configured_food_name()).to_be_null()
    expect(tt.configured_food_forms()).to_equal([])


test('the snapshot counts water doses, food and clothes held or worn', snapshot_counts)


def shortage_withdrawals():
    expect(tt.withdraw_banked_shortage(snap(inv={ITEM.BAR: 1}), ITEM.BAR, 1)).to_be_null()
    expect(tt.withdraw_banked_shortage(snap(), ITEM.BAR, 1)).to_be_null()
    withdraws(tt.withdraw_banked_shortage(snap(bank={ITEM.BAR: 5}), ITEM.BAR, 3), ITEM.BAR, 3)
    withdraws(tt.withdraw_banked_shortage(snap(bank={ITEM.BAR: 2}), ITEM.BAR, 3), ITEM.BAR, 2)
    # A stack already held needs no slot.
    withdraws(tt.withdraw_banked_shortage(snap(inv={ITEM.COINS: 5}, bank={ITEM.COINS: 50}, free=0), ITEM.COINS, 20), ITEM.COINS, 15)
    expect(tt.withdraw_banked_shortage(snap(bank={ITEM.COINS: 50}, free=0), ITEM.COINS, 20).kind).to_be('wait')


test('a banked shortage is withdrawn, up to what is there and what fits', shortage_withdrawals)


def food_withdrawal():
    expect(tt.configured_food_withdrawal(snap(), 1, 2, tt.make_rescue_space)).to_be_null()
    quest_food.name = 'Trout'
    expect(tt.configured_food_withdrawal(snap(inv={'Trout': 2}), 1, 2, tt.make_rescue_space)).to_be_null()
    expect(tt.configured_food_withdrawal(snap(known=False), 1, 2, tt.make_rescue_space).kind).to_be('scan_bank')
    expect(tt.configured_food_withdrawal(snap(), 1, 2, tt.make_rescue_space).reason).to_contain("configured Tourist Trap food 'Trout' unavailable")
    withdraws(tt.configured_food_withdrawal(snap(bank={'Trout': 5}), 1, 2, tt.make_rescue_space), 'Trout', 2)
    expect(tt.configured_food_withdrawal(snap(bank={'Trout': 5}, free=1), 1, 2, tt.make_rescue_space).kind).to_be('wait')


test('configured food comes from the bank, or the quest waits for it', food_withdrawal)


FULL_KIT = {ITEM.COINS: 1000, ITEM.PICKAXE: 1, ITEM.KEBAB: 16, ITEM.DESERT_SHIRT: 1, ITEM.DESERT_ROBE: 1, ITEM.DESERT_BOOTS: 1, 'Waterskin(4)': 4, ITEM.PASS: 1}


def kit_without(*names):
    return {name: count for name, count in FULL_KIT.items() if name not in names}


def preparation_order():
    step = tt.preparation_acquisition_step
    expect(step(snap(known=False)).kind).to_be('scan_bank')
    expect(step(snap(inv={'Lobster': 1})).kind).to_be('deposit')
    withdraws(step(snap(bank={ITEM.COINS: 2000})), ITEM.COINS, 1000)
    expect(step(snap()).name).to_contain('earn 1000 gp')

    withdraws(step(snap(inv=kit_without(ITEM.PICKAXE), bank={ITEM.PICKAXE: 1})), ITEM.PICKAXE, 1)
    expect(step(snap(inv=kit_without(ITEM.PICKAXE))).item).to_be(ITEM.PICKAXE)
    expect(step(snap(inv=kit_without(ITEM.PICKAXE), free=0)).kind).to_be('wait')

    is_custom(step(snap(inv=kit_without(ITEM.KEBAB), free=16)), 'buy 16 Kebabs')

    expect(step(snap(inv=kit_without(ITEM.DESERT_SHIRT))).item).to_be(ITEM.DESERT_SHIRT)
    withdraws(step(snap(inv=kit_without(ITEM.DESERT_SHIRT), bank={ITEM.DESERT_SHIRT: 2})), ITEM.DESERT_SHIRT, 1)
    expect(step(snap(inv=kit_without(ITEM.DESERT_SHIRT), free=0)).kind).to_be('wait')
    expect(step(snap(inv=kit_without('Waterskin(4)'))).item).to_be(ITEM.WATERSKIN)
    expect(step(snap(inv=kit_without(ITEM.PASS))).item).to_be(ITEM.PASS)
    expect(step(snap(inv=FULL_KIT))).to_be_null()


test('preparation buys each thing in its order, from the bank first', preparation_order)


def preparation_with_configured_food():
    quest_food.name = 'Trout'
    kit = kit_without(ITEM.KEBAB)
    kit['Trout'] = 16
    expect(tt.preparation_acquisition_step(snap(inv=kit))).to_be_null()
    withdraws(tt.preparation_acquisition_step(snap(inv=kit_without(ITEM.KEBAB), bank={'Trout': 20}, free=16)), 'Trout', 16)


test('with food configured, preparation banks that rather than buying Kebabs', preparation_with_configured_food)


def preparation_in_the_desert():
    south = snap(tile=DESERT, inv=kit_without(ITEM.PASS, ITEM.COINS))
    expect(tt.preparation_acquisition_step(south)).to_be_null()
    expect(tt.preparation_step(south)).to_be_null()
    is_custom(tt.preparation_step(snap(tile=DESERT, inv=kit_without(ITEM.PASS, ITEM.PICKAXE))), 'cross the Shantay Pass north')
    expect(tt.preparation_step(snap(inv=kit_without(ITEM.PICKAXE))).item).to_be(ITEM.PICKAXE)


test('south of the pass another pass is not wanted, and shortages go back north', preparation_in_the_desert)


def recovery_routes():
    expect(tt.safe_recovery_route('desert')).to_be_null()
    for area, name in [('bedabinTent', 'prototype tent'), ('campUpper', 'climb down'), ('campSurface', 'leave the camp'), ('mineEntrance', 'leave the mine'), ('mineLower', 'leave the mine'), ('mineDeep', 'ride back')]:
        is_custom(tt.safe_recovery_route(area), name)


test('each sealed area has its way out for item recovery', recovery_routes)


def critical_space():
    expect(tt.make_critical_item_space(snap(free=None))).to_be_null()
    expect(tt.make_critical_item_space(snap(free=1))).to_be_null()
    is_custom(tt.make_critical_item_space(snap(tile=CAMP, free=0)), 'leave the camp')
    is_custom(tt.make_critical_item_space(snap(tile=DESERT, free=0)), 'cross the Shantay Pass north')
    expect(tt.make_critical_item_space(snap(inv={'Lobster': 1}, free=0)).kind).to_be('deposit')
    expect(tt.make_critical_item_space(snap(free=0)).reason).to_contain('need 1 safe inventory slot')

    quest_food.name = 'Trout'
    step = tt.make_critical_item_space(snap(inv={'Trout': 14}, free=0), 2)
    is_custom(step, 'bank food down to 12')
    expect(tt.make_critical_item_space(snap(inv={'Trout': tt.FOOD_ENTRY_FLOOR}, free=0), 2).kind).to_be('wait')


test('critical room comes from a safe place, then spillover, then spare food', critical_space)


def critical_recovery():
    again = Fake(kind='custom', name='again')
    expect(tt.recover_critical(snap(inv={ITEM.PLANS: 1}), ITEM.PLANS, again)).to_be_null()
    is_custom(tt.recover_critical(snap(tile=CAMP), ITEM.PLANS, again), 'leave the camp')
    expect(tt.recover_critical(snap(free=0), ITEM.PLANS, again).kind).to_be('wait')
    is_custom(tt.recover_critical(snap(tile=DESERT, known=False), ITEM.PLANS, again), 'cross the Shantay Pass north')
    is_custom(tt.recover_critical(snap(tile=DESERT, bank={ITEM.PLANS: 1}), ITEM.PLANS, again), 'cross the Shantay Pass north')
    expect(tt.recover_critical(snap(known=False), ITEM.PLANS, again).kind).to_be('scan_bank')
    withdraws(tt.recover_critical(snap(bank={ITEM.PLANS: 1}), ITEM.PLANS, again), ITEM.PLANS, 1)
    expect(tt.recover_critical(snap(), ITEM.PLANS, again)).to_be(again)


test('a lost quest item comes from the bank, or from its own source', critical_recovery)


def consumables():
    src = tt.source_consumable
    expect(src(snap(inv={ITEM.BAR: 1}), ITEM.BAR, 1)).to_be_null()
    is_custom(src(snap(tile=CAMP), ITEM.BAR, 1), 'leave the camp')
    is_custom(src(snap(tile=DESERT), ITEM.BAR, 1), 'cross the Shantay Pass north')
    expect(src(snap(known=False), ITEM.BAR, 1).kind).to_be('scan_bank')
    expect(src(snap(free=0), ITEM.BAR, 1).kind).to_be('wait')
    withdraws(src(snap(bank={ITEM.BAR: 3}), ITEM.BAR, 1), ITEM.BAR, 1)
    expect(src(snap(), 'Gold bar', 1).reason).to_contain("cannot naturally replace 'Gold bar'")
    expect(src(snap(), ITEM.BAR, 1).name).to_contain('earn')
    expect(src(snap(inv={ITEM.COINS: 100}), ITEM.BAR, 1).item).to_be(ITEM.BAR)
    # Some feathers held: the stack needs no slot.
    expect(src(snap(inv={ITEM.COINS: 100, ITEM.FEATHER: 4}, free=0), ITEM.FEATHER, 10).qty).to_be(6)


test('a used-up material comes from the bank, then the shop, then money', consumables)


def water():
    src = tt.source_water_doses
    space = tt.make_rescue_space
    expect(src(snap(inv={'Waterskin(4)': 4}), 12, 16, space)).to_be_null()
    is_custom(src(snap(tile=CAMP), 12, 16, space), 'leave the camp')
    is_custom(src(snap(tile=DESERT), 12, 16, space), 'cross the Shantay Pass north')
    expect(src(snap(known=False), 12, 16, space).kind).to_be('scan_bank')
    # Partly used skins are banked so they can be swapped for full ones.
    step = src(snap(inv={'Waterskin(2)': 1}), 12, 16, space)
    expect(step.kind).to_be('deposit')
    expect('waterskin(2)' in step.keep).to_be(False)
    withdraws(src(snap(bank={ITEM.WATERSKIN: 9}), 12, 16, space), ITEM.WATERSKIN, 4)
    expect(src(snap(), 12, 16, space).name).to_contain('earn')
    expect(src(snap(inv={ITEM.COINS: 500}, free=0), 12, 16, space).kind).to_be('wait')
    step = src(snap(inv={ITEM.COINS: 500}), 12, 16, space)
    expect(step.item).to_be(ITEM.WATERSKIN)
    expect(step.qty).to_be(4)


test('water tops up from full skins in the bank, then the shop', water)


def survival_food():
    quest_food.name = 'Trout'
    src = tt.source_configured_survival_food
    is_custom(src(snap(tile=CAMP)), 'leave the camp')
    is_custom(src(snap(tile=DESERT)), 'cross the Shantay Pass north')
    expect(src(snap(inv={'Trout': tt.FOOD_ENTRY_FLOOR}))).to_be_null()
    withdraws(src(snap(inv={'Trout': 2}, bank={'Trout': 20}, free=14)), 'Trout', 14)


test('survival food is sourced from somewhere safe', survival_food)


def coins():
    src = tt.source_coins
    expect(src(snap(inv={ITEM.COINS: 50}), 50, 'x')).to_be_null()
    is_custom(src(snap(tile=CAMP), 50, 'x'), 'leave the camp')
    is_custom(src(snap(tile=DESERT), 50, 'x'), 'cross the Shantay Pass north')
    expect(src(snap(known=False), 50, 'x').kind).to_be('scan_bank')
    withdraws(src(snap(bank={ITEM.COINS: 500}), 50, 'x'), ITEM.COINS, 40)
    withdraws(src(snap(inv={ITEM.COINS: 45}, bank={ITEM.COINS: 500}), 50, 'x'), ITEM.COINS, 5)
    expect(src(snap(), 50, 'x').name).to_contain('earn 50 gp')
    expect(tt.source_rescue_coins(snap(inv={ITEM.COINS: tt.RESCUE_COIN_FLOOR}))).to_be_null()
    expect(tt.source_rescue_coins(snap()).name).to_contain(f'earn {tt.RESCUE_COIN_TARGET} gp')


test('coins come from the bank in small amounts, or are earned', coins)


def route_south_steps():
    expect(tt.route_south(snap(tile=DESERT))).to_be_null()
    water = {'Waterskin(4)': 4}
    expect(tt.route_south(snap(known=False)).kind).to_be('scan_bank')
    expect(tt.route_south(snap(inv=water, known=False)).kind).to_be('scan_bank')
    expect(tt.route_south(snap(inv={'Waterskin(4)': 4, 'Lobster': 1}, free=0)).kind).to_be('deposit')
    withdraws(tt.route_south(snap(inv=water, bank={ITEM.PASS: 2})), ITEM.PASS, 1)
    expect(tt.route_south(snap(inv=water)).name).to_contain('earn 6 gp')
    expect(tt.route_south(snap(inv={'Waterskin(4)': 4, ITEM.COINS: 6})).item).to_be(ITEM.PASS)
    is_custom(tt.route_south(snap(inv={'Waterskin(4)': 4, ITEM.PASS: 1})), 'cross the Shantay Pass')


test('going south needs water, then a pass', route_south_steps)


def desert_copies():
    src = tt.source_desert_outfit_copies
    one = {ITEM.DESERT_SHIRT: 1, ITEM.DESERT_ROBE: 1, ITEM.DESERT_BOOTS: 1}
    expect(src(snap(inv=one), 1)).to_be_null()
    is_custom(src(snap(tile=CAMP), 1), 'leave the camp')
    is_custom(src(snap(tile=DESERT), 1), 'cross the Shantay Pass north')
    expect(src(snap(known=False), 1).kind).to_be('scan_bank')
    withdraws(src(snap(bank={ITEM.DESERT_SHIRT: 3}), 1), ITEM.DESERT_SHIRT, 1)
    expect(src(snap(bank={ITEM.DESERT_SHIRT: 3}, free=0), 1).kind).to_be('wait')
    expect(src(snap(), 1).name).to_contain('earn')
    expect(src(snap(inv={ITEM.COINS: 500}), 1).item).to_be(ITEM.DESERT_SHIRT)
    # The first copy goes on to make room for the second.
    is_custom(src(snap(inv=one, free=0), 2), 'wear the first desert outfit')
    expect(src(snap(worn=list(one.keys()), free=0), 2).kind).to_be('wait')


test('desert clothes come from the bank, then Shantay, and a first copy can be worn for room', desert_copies)


def pickaxes():
    src = tt.source_pickaxe
    expect(src(snap(worn=[ITEM.PICKAXE]))).to_be_null()
    is_custom(src(snap(tile=CAMP)), 'leave the camp')
    is_custom(src(snap(tile=DESERT)), 'cross the Shantay Pass north')
    expect(src(snap(known=False)).kind).to_be('scan_bank')
    expect(src(snap(free=0)).kind).to_be('wait')
    withdraws(src(snap(bank={ITEM.PICKAXE: 1})), ITEM.PICKAXE, 1)
    expect(src(snap()).name).to_contain('earn 2 gp')
    expect(src(snap(inv={ITEM.COINS: 2})).item).to_be(ITEM.PICKAXE)


test('a lost pickaxe comes from the bank or Bob', pickaxes)


def exterior():
    src = tt.ensure_desert_exterior_loadout
    outfit = [ITEM.DESERT_SHIRT, ITEM.DESERT_ROBE, ITEM.DESERT_BOOTS]
    expect(src(snap(known=False)).kind).to_be('scan_bank')
    expect(src(snap(worn=outfit, known=False)).kind).to_be('scan_bank')
    expect(src(snap(worn=outfit + [ITEM.PICKAXE], known=False)).kind).to_be('scan_bank')
    is_custom(src(snap(tile=DESERT, inv={ITEM.PICKAXE: 1}, worn=outfit)), 'wear the camp-safe')
    expect(src(snap(tile=DESERT, worn=outfit + [ITEM.PICKAXE]))).to_be_null()


test('outside the camp the desert loadout comes first', exterior)


def kebab_sources():
    src = tt.source_kebabs
    expect(src(snap(inv={ITEM.KEBAB: 8}))).to_be_null()
    is_custom(src(snap(tile=CAMP)), 'leave the camp')
    is_custom(src(snap(tile=DESERT)), 'cross the Shantay Pass north')
    expect(src(snap(known=False)).kind).to_be('scan_bank')
    withdraws(src(snap(bank={ITEM.KEBAB: 8})), ITEM.KEBAB, 8)
    expect(src(snap()).name).to_contain('earn 8 gp')
    expect(src(snap(inv={ITEM.COINS: 8}, free=1)).kind).to_be('wait')
    is_custom(src(snap(inv={ITEM.COINS: 8})), 'buy 8 Kebabs')


def kebab_step_runs():
    scene = Scene(tt.KEBAB_SELLER)
    scene.item(1, ITEM.COINS, count=8)
    scene.item(2, ITEM.KEBAB, count=8)
    step = tt.source_kebabs(snap(inv={ITEM.COINS: 8}))
    expect(run(step.run(scene.log))).to_be(True)


test('Kebabs come from the bank or the seller', kebab_sources)
test('the Kebab step runs the purchase', kebab_step_runs)


def camp_surface():
    src = tt.ensure_camp_surface
    outfit = [ITEM.DESERT_SHIRT, ITEM.DESERT_ROBE, ITEM.DESERT_BOOTS]
    expect(src(snap(tile=CAMP))).to_be_null()
    is_custom(src(snap(tile=UPPER)), 'climb down')
    is_custom(src(snap(tile=MINE_IN)), 'leave the underground mine')
    is_custom(src(snap(tile=DEEP)), 'ride back')
    is_custom(src(snap(tile=DESERT, known=False)), 'cross the Shantay Pass north')
    expect(src(snap(known=False)).kind).to_be('scan_bank')
    withdraws(src(snap(bank={ITEM.METAL_KEY: 1})), ITEM.METAL_KEY, 1)
    expect(src(snap(bank={ITEM.METAL_KEY: 1}, free=0)).kind).to_be('wait')
    worn_kit = outfit + [ITEM.PICKAXE]
    is_custom(src(snap(tile=DESERT, worn=worn_kit)), 'replace the mining-camp Metal key')
    is_custom(src(snap(tile=DESERT, worn=worn_kit, inv={ITEM.METAL_KEY: 1})), 'unlock the desert mining camp')
    # Dressed wrongly, the loadout comes first.
    is_custom(src(snap(tile=DESERT, inv={ITEM.METAL_KEY: 1, ITEM.PICKAXE: 1, ITEM.DESERT_SHIRT: 1, ITEM.DESERT_ROBE: 1, ITEM.DESERT_BOOTS: 1})), 'wear the camp-safe')


test('the camp is reached through its key and the right clothes', camp_surface)


def mine_entrance():
    src = tt.ensure_mine_entrance
    outfit = list(tt.SLAVE_OUTFIT)
    is_custom(src(snap(tile=MINE_IN, inv={name: 1 for name in outfit})), 'wear the slave disguise')
    expect(src(snap(tile=MINE_IN, worn=outfit))).to_be_null()
    is_custom(src(snap(tile=LOWER, worn=outfit)), 'cross back to the cave guards')
    is_custom(src(snap(tile=DEEP)), 'ride back')
    is_custom(src(snap(tile=CAMP)), 'leave the camp')
    is_custom(src(snap(tile=DESERT, worn=[ITEM.PICKAXE])), 'cross the Shantay Pass north')
    is_custom(src(snap(tile=CAMP, worn=[ITEM.PICKAXE, ITEM.DESERT_SHIRT, ITEM.DESERT_ROBE, ITEM.DESERT_BOOTS])), 'replace the slave disguise')
    is_custom(src(snap(tile=CAMP, inv={name: 1 for name in outfit}, worn=[ITEM.PICKAXE])), 'wear the slave disguise')
    is_custom(src(snap(tile=CAMP, worn=outfit + [ITEM.PICKAXE])), 'open the slave-only mine doors')


test('the mine entrance needs a pickaxe, the disguise and the doors', mine_entrance)


def mine_lower():
    src = tt.ensure_mine_lower
    outfit = list(tt.SLAVE_OUTFIT)
    expect(src(snap(tile=LOWER))).to_be_null()
    is_custom(src(snap(tile=DEEP)), 'ride back')
    is_custom(src(snap(tile=MINE_IN, inv={name: 1 for name in outfit})), 'wear the slave disguise')
    is_custom(src(snap(tile=MINE_IN, worn=outfit)), 'walk through the guarded mine cave')
    is_custom(src(snap(tile=CAMP, worn=outfit + [ITEM.PICKAXE])), 'open the slave-only mine doors')


test('the lower mine is through the guarded cave', mine_lower)


def plans_recovery():
    src = tt.plans_recovery_step
    expect(src(snap(inv={ITEM.PLANS: 1}))).to_be_null()
    is_custom(src(snap(tile=CAMP, free=0)), 'leave the camp')
    is_custom(src(snap(tile=CAMP, known=False)), 'leave the camp')
    is_custom(src(snap(tile=DESERT, bank={ITEM.PLANS: 1})), 'cross the Shantay Pass north')
    expect(src(snap(known=False)).kind).to_be('scan_bank')
    withdraws(src(snap(bank={ITEM.PLANS: 1})), ITEM.PLANS, 1)
    is_custom(src(snap(tile=CAMP, inv={ITEM.BEDABIN_KEY: 1})), 'distract Captain Siad')
    is_custom(src(snap(tile=MINE_IN)), 'leave the mine')
    is_custom(src(snap(tile=TENT)), 'leave the prototype tent')
    is_custom(src(snap(tile=DESERT, bank={ITEM.BEDABIN_KEY: 1})), 'cross the Shantay Pass north')
    withdraws(src(snap(bank={ITEM.BEDABIN_KEY: 1})), ITEM.BEDABIN_KEY, 1)
    is_custom(src(snap(tile=DESERT)), 'ask Al Shabim to replace the plans key')
    is_custom(src(snap(tile=DESERT, stage=STAGE.MADE_DART_TIP)), 'ask Al Shabim to replace the plans key')
    # With the key, out in the desert: the camp comes first.
    is_custom(src(snap(tile=UPPER, inv={ITEM.BEDABIN_KEY: 1})), 'distract Captain Siad')


test('lost plans come from the bank, or from Siad with the right key', plans_recovery)


def prototype_remake():
    src = tt.remake_prototype_step
    expect(src(snap(inv={ITEM.DART: 1}), True)).to_be_null()
    is_custom(src(snap(tile=CAMP, known=False), False), 'leave the camp')
    is_custom(src(snap(tile=DESERT, known=False), False), 'cross the Shantay Pass north')
    expect(src(snap(known=False), False).kind).to_be('scan_bank')
    is_custom(src(snap(tile=CAMP, bank={ITEM.DART_TIP: 1}), False), 'leave the camp')
    is_custom(src(snap(tile=DESERT, bank={ITEM.DART_TIP: 1}), False), 'cross the Shantay Pass north')
    withdraws(src(snap(bank={ITEM.DART: 1}), True), ITEM.DART, 1)
    withdraws(src(snap(bank={ITEM.DART: 1, ITEM.DART_TIP: 1}), False), ITEM.DART_TIP, 1)
    expect(src(snap(bank={ITEM.DART_TIP: 1}, free=0), False).kind).to_be('wait')
    is_custom(src(snap(inv={ITEM.DART_TIP: 1, ITEM.FEATHER: 10}), False), 'attach feathers')
    withdraws(src(snap(inv={ITEM.DART_TIP: 1}, bank={ITEM.FEATHER: 20}), False), ITEM.FEATHER, 10)
    # Plans, then hammer, then bar, then getting there.
    withdraws(src(snap(bank={ITEM.PLANS: 1}), False), ITEM.PLANS, 1)
    has_plans = {ITEM.PLANS: 1}
    withdraws(src(snap(inv=has_plans, bank={ITEM.HAMMER: 1}), False), ITEM.HAMMER, 1)
    has_plans = {ITEM.PLANS: 1, ITEM.HAMMER: 1}
    withdraws(src(snap(inv=has_plans, bank={ITEM.BAR: 1}), False), ITEM.BAR, 1)
    has_kit = {ITEM.PLANS: 1, ITEM.HAMMER: 1, ITEM.BAR: 1}
    is_custom(src(snap(tile=TENT, inv=has_kit), False), 'leave the prototype tent')
    is_custom(src(snap(tile=DESERT, inv=has_kit), False), 'forge the prototype dart tip')


test('the prototype is remade from whatever is missing, nearest first', prototype_remake)


def labels():
    shop = Fake(npc='Shantay')
    expect(tt.step_label(Fake(kind='talk', stop=Fake(npc='Irena')))).to_be('talk Irena')
    expect(tt.step_label(Fake(kind='buy', qty=2, item='Bar', shop=shop))).to_contain('Bar')
    expect(tt.step_label(Fake(kind='withdraw', items=[{'name': 'Bar', 'qty': 2}]))).to_contain('Bar')
    expect(tt.step_label(Fake(kind='deposit', keep=['a', 'b']))).to_be('deposit keep=a|b')
    expect(tt.step_label(Fake(kind='custom', name='thing'))).to_be('thing')
    expect(tt.step_label(Fake(kind='wait', reason='why'))).to_be('wait:why')
    expect(tt.step_label(Fake(kind='equip', item='Bar'))).to_be('equip Bar')
    expect(tt.step_label(Fake(kind='scan_bank'))).to_be('scan_bank')
    expect(tt.step_label(Fake(kind='done'))).to_be('done')
    expect(tt.step_label(Fake(kind='other'))).to_be('other')


test('every step kind has a label for the stuck-run dump', labels)


def decide_branches():
    water = {'Waterskin(4)': 4, ITEM.KEBAB: 16, ITEM.COINS: 1000}

    # Not started: preparation, then dress, then go south, then Irena.
    is_custom(tt.decide(snap(stage=STAGE.NOT_STARTED, inv=FULL_KIT)), 'wear the desert quest loadout')
    expect(tt.decide(snap(stage=STAGE.NOT_STARTED)).name).to_contain('earn')

    # The captain's stages keep the loadout first.
    is_custom(tt.decide(snap(tile=DESERT, stage=STAGE.APPROACHED_CAPTAIN, inv=water)), 'cross the Shantay Pass north')

    is_custom(tt.decide(snap(tile=DESERT, stage=STAGE.KILLED_CAPTAIN, inv=water)), 'cross the Shantay Pass north')

    # A sealed area at the pineapple stage leaves first.
    is_custom(tt.decide(snap(tile=MINE_IN, stage=STAGE.FINDING_PINEAPPLE, inv=water, worn=list(tt.SLAVE_OUTFIT))), 'leave the mine')


    # Plans held, kit complete, in the tent: out first.
    kit = {'Waterskin(4)': 4, ITEM.KEBAB: 16, ITEM.PLANS: 1, ITEM.BAR: 1, ITEM.HAMMER: 1, ITEM.FEATHER: 10}
    is_custom(tt.decide(snap(tile=TENT, stage=STAGE.RETRIEVED_PLANS, inv=kit)), 'leave the prototype tent')

    # The pineapple is gone: south to Al Shabim, with water already in hand.
    south_kit = {'Waterskin(4)': 4, ITEM.KEBAB: 16}
    step = tt.decide(snap(stage=STAGE.LEARNED_DARTS, inv=south_kit))
    expect(step.kind in ['buy', 'custom', 'scan_bank', 'withdraw']).to_be(True)

    # After the cart: back down to the deep mine.
    done = list(tt.SLAVE_OUTFIT) + [ITEM.PICKAXE]
    is_custom(tt.decide(snap(tile=MINE_IN, stage=STAGE.USED_MINE_CART, inv=water, worn=done)), 'walk through the guarded mine cave')

    # The rescue from the desert goes back to the camp.
    is_custom(tt.decide(snap(tile=DESERT, stage=STAGE.RESCUE, inv=water, worn=list(tt.SLAVE_OUTFIT))), 'cross the Shantay Pass north')


test("decide's stage branches route through the helpers", decide_branches)


def skills_are_logged_on_a_ride():
    scene = Scene(LOWER)
    scene.stats['agility'] = 41
    run(tt.ride_mine_cart(tt.LOWER_CART, scene.log))
    expect(scene.logged('Agility=41')).to_be(True)
    expect(skills.level('agility')).to_be(41)


test('each cart attempt logs the Agility it rolls on', skills_are_logged_on_a_ride)

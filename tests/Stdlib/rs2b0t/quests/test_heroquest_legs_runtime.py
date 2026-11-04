"""Heroes' Quest sealed doors, lava eel, feather and both partner roles."""

from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.heroquest import blackarm, doors, eel, feather, phoenix, shops, state
from rs2004.quests.defs.heroquest.areas import HERO_ID, HERO_LOC, HERO_NAMED, HERO_NPC, HERO_TILE
from rs2004.quests.defs.heroquest.journal import HERO_STAGE
from rs2004.quests.engine.types import QuestSnapshot


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, id, name='Quest item'):
    def effect(*args):
        scene.item(id, name)
    return effect


def world():
    scene = Scene(HERO_TILE.CABINET_STAND)
    spy_on(event_signal, 'pending', returns=False)
    return scene


def role_decisions():
    scene = world()
    snap = QuestSnapshot(bank_known=True, inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set())
    spy_on(blackarm, 'talk_and_close', impl=answer(True))
    spy_on(blackarm, 'disguise_step', returns=None)
    spy_on(blackarm, 'should_fetch_key', returns=True)
    for stage, expected in [
        [HERO_STAGE.STARTED, 'ask Katrine'], [HERO_STAGE.BLACKARM_HQ, 'take Hartigen'],
        [HERO_STAGE.BLACKARM_PAPERS, 'spare set'], [HERO_STAGE.BLACKARM_MANSION, 'report to Grip'],
        [HERO_STAGE.BLACKARM_PAPERS_GIVEN, 'ask Grip'], [HERO_STAGE.BLACKARM_LOOTED, None],
    ]:
        step = blackarm.blackarm_armband_step(snap, stage)
        if expected:
            expect(step.name).to_contain(expected)
        else:
            expect(step.kind).to_be('wait')
    snap.inv_ids[HERO_ID.ID_PAPERS] = 1
    expect(blackarm.blackarm_armband_step(snap, HERO_STAGE.BLACKARM_PAPERS).run).to_be(blackarm.enter_mansion)
    snap.inv_ids[HERO_ID.MISC_KEY] = 1
    expect(blackarm.blackarm_armband_step(snap, HERO_STAGE.BLACKARM_PAPERS_GIVEN).run).to_be(blackarm.lure_grip_and_take_keyring)
    expect(blackarm.blackarm_armband_step(snap, -1)).to_be_null()
    expect(blackarm.blackarm_sealed(snap)).to_be(False)
    spy_on(phoenix, 'snipe_kit_owned', returns=True)
    spy_on(phoenix, 'snipe_kit_step', returns=None)
    spy_on(phoenix, 'talk_in_hideout', impl=answer(True))
    spy_on(phoenix, 'talk_and_close', impl=answer(True))
    for stage in [HERO_STAGE.STARTED, HERO_STAGE.PHOENIX_SPOKEN]:
        expect(run_wait(phoenix.phoenix_armband_step(snap, stage).run(scene.log))).to_be(True)
    expect(phoenix.phoenix_armband_step(snap, HERO_STAGE.PHOENIX_ALFONSE).run).to_be(phoenix.talk_to_charlie)
    expect(phoenix.phoenix_armband_step(snap, HERO_STAGE.PHOENIX_KILLED_GRIP).kind).to_be('wait')
    snap.inv_ids[HERO_ID.CANDLESTICK] = 1
    expect(phoenix.phoenix_armband_step(snap, HERO_STAGE.PHOENIX_KILLED_GRIP).run).to_be(phoenix.hand_in_candlestick)
    expect(phoenix.phoenix_armband_step(snap, -1)).to_be_null()
    for id in [HERO_ID.RAW_LAVA_EEL, HERO_ID.OILY_ROD, HERO_ID.BLAMISH_OIL,
               HERO_ID.HARRALANDER_VIAL, HERO_ID.HARRALANDER, HERO_ID.UNID_HARRALANDER]:
        snap.inv_ids = {}
        snap.bank_ids = {id: 1}
        expect(eel.eel_step(snap).items[0]['id']).to_be(id)
    spy_on(eel, 'cross_teleport_door', impl=answer(True))
    expect(run_wait(eel.cross_deep_gate(True, scene.log))).to_be(True)
    expect(state.banked_id(QuestSnapshot(bank_known=False), 1)).to_be(0)
    from rs2004.game import reader
    spy_on(reader, 'main_modal_texts', returns=['A Rival waits'])
    expect(state.modal_said('rival')).to_be(True)


test('both armband roles resume from handed-over papers, keys and rewards and eel materials withdraw by id', role_decisions)


def stockist_failures():
    scene = world()
    from rs2004.catalogs.record import Record
    item = Record({'name': 'Disguise', 'qty': 1, 'sources': [Record({'npc': 'Shopkeeper', 'anchor': scene.at, 'gp': 100})]})
    street = spy_on(shops, 'return_to_street', impl=answer(False))
    expect(run_wait(shops.buy_from_any(item, scene.log))).to_be(False)
    street.mock_implementation(answer(True))
    execute = spy_on(shops, 'execute_step', impl=answer(False))
    expect(run_wait(shops.buy_from_any(item, scene.log))).to_be(False)
    scene.item(HERO_ID.COINS, HERO_NAMED.COINS, count=100)
    expect(run_wait(shops.buy_from_any(item, scene.log))).to_be(False)
    expect(scene.logged('had no')).to_be(True)


test('disguise sourcing stops at failed street exits, coin withdrawals and exhausted stockists', stockist_failures)


DOORS = [
    [doors.enter_brimhaven_hq, 'in_brimhaven_hq', True],
    [doors.leave_brimhaven_hq, 'in_brimhaven_hq', False],
    [doors.enter_mansion, 'in_mansion', True],
    [doors.leave_mansion, 'in_mansion', False],
    [doors.enter_kitchen, 'in_kitchen', True],
    [doors.leave_kitchen, 'in_kitchen', False],
    [doors.push_panel, 'in_garden', True],
    [doors.push_panel_back, 'in_kitchen', True],
    [doors.cross_side_door_out, 'in_side_room', False],
    [doors.cross_treasure_door_out, 'in_treasure_room', False],
]


def region_test(scene, name):
    return lambda tile: scene.region == name


def door(fn, region, entering):
    scene = world()
    scene.region = 'in_garden' if fn == doors.push_panel_back else ('' if entering else region)
    for name in ['in_brimhaven_hq', 'in_mansion', 'in_kitchen', 'in_garden', 'in_yard', 'in_side_room', 'in_treasure_room']:
        patch(doors, name, region_test(scene, name))
    # The fake crossing owns only its boundary; each doorway's own goal still reads the scene.
    spy_on(doors, 'return_to_street', impl=answer(True))
    spy_on(doors, 'enter_kitchen', impl=answer(True)) if fn == doors.push_panel else None
    cross = spy_on(doors, 'cross_teleport_door', impl=answer(False))
    expect(run_wait(fn(scene.log))).to_be(False)

    def crossed(opts):
        scene.region = region if entering else ''
        expect(opts.is_far()).to_be(True)
        return True
        yield

    cross.mock_implementation(crossed)
    expect(run_wait(fn(scene.log))).to_be(True)
    if fn != doors.push_panel_back:
        expect(run_wait(fn(scene.log))).to_be(True)


test_each(DOORS)('Heroes sealed doorway checks its destination: %s', door)


def keyed_doors_and_escape():
    scene = world()
    for fn, region in [[doors.cross_side_door_in, 'in_side_room'], [doors.cross_treasure_door_in, 'in_treasure_room']]:
        inside = spy_on(doors, region, returns=False)
        used = spy_on(doors, 'use_on_loc', impl=answer(False))
        expect(run_wait(fn(scene.log))).to_be(False)
        used.mock_implementation(answer(True))
        expect(run_wait(fn(scene.log))).to_be(True)
        inside.mock_return_value(True)
        expect(run_wait(fn(scene.log))).to_be(True)
        restore_all()
    scene = world()
    regions = ['in_treasure_room', 'in_mansion', 'in_side_room']
    steps = ['cross_treasure_door_out', 'leave_mansion', 'cross_side_door_out', 'push_panel_back', 'leave_kitchen', 'leave_brimhaven_hq']
    for region in regions:
        spy_on(doors, region, returns=True)
    for name in steps:
        step = spy_on(doors, name, impl=answer(False))
        expect(run_wait(doors.return_to_street(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    expect(run_wait(doors.return_to_street(scene.log))).to_be(True)


test('keyed rooms and returning to the street enforce every pocket exit', keyed_doors_and_escape)


def herb_and_eel():
    scene = world()
    expect(run_wait(eel.identify_harralander(scene.log))).to_be(False)
    scene.item(HERO_ID.UNID_HARRALANDER, 'Herb', effect=lambda op: False)
    expect(run_wait(eel.identify_harralander(scene.log))).to_be(False)
    scene.pack = []
    scene.item(HERO_ID.UNID_HARRALANDER, 'Herb', effect=give(scene, HERO_ID.HARRALANDER))
    expect(run_wait(eel.identify_harralander(scene.log))).to_be(True)
    expect(run_wait(eel.identify_harralander(scene.log))).to_be(True)
    expect(run_wait(eel.farm_harralander(scene.log))).to_be(True)
    scene.pack = []
    scene.walk_ok = False
    expect(run_wait(eel.farm_harralander(scene.log))).to_be(False)
    scene.walk_ok = True
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(eel.farm_harralander(scene.log))).to_be(False)
    pending.mock_return_value(False)
    expect(run_wait(eel.farm_harralander(scene.log))).to_be(False)
    scene.npc('Chaos druid', id=HERO_NPC.CHAOS_DRUID)
    expect(run_wait(eel.farm_harralander(scene.log))).to_be(False)
    scene.on_ground(HERO_ID.UNID_HARRALANDER, 'Herb')
    expect(run_wait(eel.farm_harralander(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(eel.cook_lava_eel(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(eel.cook_lava_eel(scene.log))).to_be(False)
    scene.loc('Range')
    scene.item(HERO_ID.RAW_LAVA_EEL, 'Raw eel', on_use=lambda target: False)
    expect(run_wait(eel.cook_lava_eel(scene.log))).to_be(False)
    scene.take(HERO_ID.RAW_LAVA_EEL)
    scene.item(HERO_ID.RAW_LAVA_EEL, 'Raw eel', on_use=give(scene, HERO_ID.LAVA_EEL))
    expect(run_wait(eel.cook_lava_eel(scene.log))).to_be(True)
    expect(run_wait(eel.cook_lava_eel(scene.log))).to_be(True)


test('harralander is farmed and identified and raw eel is cooked on a reachable range', herb_and_eel)


def jailer_and_velrak():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(eel.kill_jailer(scene.log))).to_be(False)
    scene.walk_ok = True
    fight = spy_on(eel, 'fight', impl=answer(False))
    expect(run_wait(eel.kill_jailer(scene.log))).to_be(False)
    fight.mock_implementation(answer(True))
    expect(run_wait(eel.kill_jailer(scene.log))).to_be(False)
    scene.on_ground(HERO_ID.JAIL_KEY, 'Jail key')
    expect(run_wait(eel.kill_jailer(scene.log))).to_be(True)
    expect(run_wait(eel.kill_jailer(scene.log))).to_be(True)
    cross = spy_on(eel, 'cross_jail_door', impl=answer(False))
    expect(run_wait(eel.free_velrak(scene.log))).to_be(False)
    cross.mock_implementation(answer(True))
    talk = spy_on(eel, 'talk_until', impl=answer(False))
    expect(run_wait(eel.free_velrak(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(eel.free_velrak(scene.log))).to_be(True)
    scene.item(HERO_ID.DUSTY_KEY, 'Dusty key')
    expect(run_wait(eel.free_velrak(scene.log))).to_be(True)
    expect(cross.calls[-1][0]).to_be(False)
    expect(run_wait(eel.ask_gerrant_for_slime(scene.log))).to_be(True)


test('Velrak is entered with the jail key and left after receiving the dusty key', jailer_and_velrak)


def fishing():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(eel.fish_inside(scene.log))).to_be(False)
    scene.walk_ok = True
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(eel.fish_inside(scene.log))).to_be(False)
    pending.mock_return_value(False)
    expect(run_wait(eel.fish_inside(scene.log))).to_be(False)
    scene.item(HERO_ID.FISHING_BAIT, 'Bait')
    expect(run_wait(eel.fish_inside(scene.log))).to_be(False)
    scene.npc('Fishing spot', id=HERO_NPC.LAVA_FISH, effect=give(scene, HERO_ID.RAW_LAVA_EEL))
    expect(run_wait(eel.fish_inside(scene.log))).to_be(True)
    cross = spy_on(eel, 'cross_deep_gate', impl=answer(False))
    expect(run_wait(eel.fish_lava_eel(scene.log))).to_be(False)
    scene.take(HERO_ID.RAW_LAVA_EEL)
    expect(run_wait(eel.fish_lava_eel(scene.log))).to_be(False)
    cross.mock_implementation(answer(True))
    expect(run_wait(eel.fish_lava_eel(scene.log))).to_be(True)
    expect(cross.calls[-1][0]).to_be(False)
    teleport = spy_on(eel, 'cross_teleport_door', impl=answer(True))
    expect(run_wait(eel.cross_jail_door(True, scene.log))).to_be(True)
    expect(teleport.calls[-1][0].use_item).to_be(HERO_ID.JAIL_KEY)


test('lava eel fishing requires bait and exits the sealed deep dungeon after catching', fishing)


def queen_and_feather():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(feather.kill_ice_queen(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(feather.kill_ice_queen(scene.log))).to_be(False)
    scene.npc('Ice Queen', id=HERO_NPC.ICE_QUEEN)
    fight = spy_on(feather, 'fight', impl=answer(False))
    expect(run_wait(feather.kill_ice_queen(scene.log))).to_be(False)
    fight.mock_implementation(answer(True))
    expect(run_wait(feather.kill_ice_queen(scene.log))).to_be(False)
    scene.on_ground(HERO_ID.ICE_GLOVES, HERO_NAMED.ICE_GLOVES, effect=lambda op: False)
    expect(run_wait(feather.kill_ice_queen(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(HERO_ID.ICE_GLOVES, HERO_NAMED.ICE_GLOVES)
    expect(run_wait(feather.kill_ice_queen(scene.log))).to_be(True)
    expect(run_wait(feather.kill_ice_queen(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(feather.take_feather(scene.log))).to_be(False)
    scene.walk_ok = True
    scene.pack = []
    expect(run_wait(feather.take_feather(scene.log))).to_be(False)
    scene.wear(HERO_NAMED.ICE_GLOVES)
    expect(run_wait(feather.take_feather(scene.log))).to_be(False)
    scene.npc('Firebird', id=HERO_NPC.FIREBIRD)
    scene.on_ground(HERO_ID.FEATHER, 'Feather', effect=lambda op: False)
    expect(run_wait(feather.take_feather(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(HERO_ID.FEATHER, 'Feather')
    expect(run_wait(feather.take_feather(scene.log))).to_be(True)
    expect(run_wait(feather.take_feather(scene.log))).to_be(True)


test('the Ice Queen drop is confirmed and the feather is taken only with ice gloves worn', queen_and_feather)


def ship_and_equipment():
    scene = world()
    scene.wear(HERO_NAMED.ICE_GLOVES)
    scene.wear('Sword')
    expect(run_wait(feather.unequip_all(scene.log))).to_be(True)
    expect(len(scene.worn)).to_be(1)
    expect(run_wait(feather.step_off_ship(scene.log))).to_be(True)
    scene.at = feather.ENTRANA_LANDING
    expect(run_wait(feather.step_off_ship(scene.log))).to_be(False)
    scene.loc('Gangplank', ['Cross'], effect=lambda op: setattr(scene, 'at', Tile(scene.at.x, scene.at.z, 0)))
    expect(run_wait(feather.step_off_ship(scene.log))).to_be(True)
    expect(run_wait(feather.sail_to_entrana(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(feather.sail_from_entrana(scene.log))).to_be(False)
    scene.walk_ok = True
    talk = spy_on(feather, 'talk_through', impl=answer(False))
    expect(run_wait(feather.sail_from_entrana(scene.log))).to_be(False)

    def sailed(*args):
        scene.at = HERO_TILE.PORT_SARIM_MONK
        return True
        yield

    talk.mock_implementation(sailed)
    expect(run_wait(feather.sail_from_entrana(scene.log))).to_be(True)
    expect(run_wait(feather.sail_from_entrana(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(feather.sail_to_entrana(scene.log))).to_be(False)
    scene.walk_ok = True
    talk.mock_implementation(answer(False))
    expect(run_wait(feather.sail_to_entrana(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(feather.sail_to_entrana(scene.log))).to_be(False)


test('Entrana travel waits for the gangplank and strips everything except allowed gloves', ship_and_equipment)


def partner_dialogues():
    scene = world()
    rows = [
        [blackarm, blackarm.talk_to_trobert, 'enter_brimhaven_hq', 'talk_until'],
        [blackarm, blackarm.ask_grip_for_key, 'enter_mansion', 'talk_until'],
        [blackarm, blackarm.hand_in_candlestick, 'return_to_street', 'talk_until'],
        [phoenix, phoenix.talk_to_charlie, 'enter_kitchen', 'talk_and_close'],
    ]
    for module, fn, entrance, conversation in rows:
        enter = spy_on(module, entrance, impl=answer(False))
        expect(run_wait(fn(scene.log))).to_be(False)
        enter.mock_implementation(answer(True))
        talked = spy_on(module, conversation, impl=answer(True))
        expect(run_wait(fn(scene.log))).to_be(True)
        expect(len(talked.calls)).to_be(1)
    for name in ['return_to_street', 'enter_hideout', 'talk_until']:
        step = spy_on(phoenix, name, impl=answer(False))
        expect(run_wait(phoenix.hand_in_candlestick(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    expect(run_wait(phoenix.hand_in_candlestick(scene.log))).to_be(True)


test('both partner roles leave sealed rooms before handing a candlestick in', partner_dialogues)


def keyring_and_lure():
    scene = world()
    expect(run_wait(blackarm.take_keyring(scene.log))).to_be(False)
    scene.on_ground(HERO_ID.GRIP_KEYS, 'Keyring', effect=lambda op: False)
    expect(run_wait(blackarm.take_keyring(scene.log))).to_be(False)
    scene.ground = []
    enter = spy_on(blackarm, 'enter_mansion', impl=answer(False))
    expect(run_wait(blackarm.lure_grip_and_take_keyring(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(blackarm.lure_grip_and_take_keyring(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(blackarm.lure_grip_and_take_keyring(scene.log))).to_be(False)
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(blackarm.lure_grip_and_take_keyring(scene.log))).to_be(False)
    pending.mock_return_value(False)
    scene.loc('Cabinet', id=HERO_LOC.CABINET_OPEN)
    expect(run_wait(blackarm.lure_grip_and_take_keyring(scene.log))).to_be(False)
    scene.npc('Grip', id=HERO_NPC.GRIP, tile=HERO_TILE.GRIP_LURE)
    scene.later(lambda: scene.on_ground(HERO_ID.GRIP_KEYS, 'Keyring'))
    expect(run_wait(blackarm.lure_grip_and_take_keyring(scene.log))).to_be(True)
    expect(scene.has(HERO_ID.GRIP_KEYS)).to_be(True)
    expect(run_wait(blackarm.lure_grip_and_take_keyring(scene.log))).to_be(True)
    scene.item(HERO_ID.MISC_KEY, 'Spare key')
    expect(run_wait(blackarm.ask_grip_for_key(scene.log))).to_be(True)


test('the Black Arm role lures Grip until the shared keyring drop appears', keyring_and_lure)


def treasure():
    scene = world()
    inside = spy_on(blackarm, 'in_treasure_room', returns=False)
    for name in ['enter_mansion', 'cross_treasure_door_in']:
        step = spy_on(blackarm, name, impl=answer(False))
        expect(run_wait(blackarm.loot_candlesticks(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    opened = spy_on(blackarm, 'open_container', impl=answer(False))
    out = spy_on(blackarm, 'cross_treasure_door_out', impl=answer(True))
    expect(run_wait(blackarm.loot_candlesticks(scene.log))).to_be(False)
    opened.mock_implementation(answer(True))
    prompt = spy_on(blackarm, 'prompt_loc', impl=answer(False))
    expect(run_wait(blackarm.loot_candlesticks(scene.log))).to_be(False)

    def search(opts, log):
        scene.item(HERO_ID.CANDLESTICK, 'Candlestick', count=2)
        return opts.expect()
        yield

    prompt.mock_implementation(search)
    expect(run_wait(blackarm.loot_candlesticks(scene.log))).to_be(True)
    expect(run_wait(blackarm.loot_candlesticks(scene.log))).to_be(True)
    expect(len(out.calls) > 1).to_be(True)


test('treasure looting confirms candlesticks and retries a failed exit separately', treasure)


def arrow_slit():
    scene = world()
    inside = spy_on(phoenix, 'in_side_room', returns=False)
    for name in ['push_panel', 'cross_side_door_in']:
        step = spy_on(phoenix, name, impl=answer(False))
        expect(run_wait(phoenix.reach_arrow_slit(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    expect(run_wait(phoenix.reach_arrow_slit(scene.log))).to_be(True)
    reach = spy_on(phoenix, 'reach_arrow_slit', impl=answer(False))
    expect(run_wait(phoenix.snipe_grip(scene.log))).to_be(False)
    reach.mock_implementation(answer(True))
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(phoenix.snipe_grip(scene.log))).to_be(False)
    pending.mock_return_value(False)
    expect(run_wait(phoenix.snipe_grip(scene.log))).to_be(False)
    scene.at = HERO_TILE.ARROW_SLIT
    scene.npc('Grip', id=HERO_NPC.GRIP, tile=HERO_TILE.GRIP_LURE)
    expect(run_wait(phoenix.snipe_grip(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Grip', id=HERO_NPC.GRIP, tile=HERO_TILE.GRIP_LURE,
              effect=lambda op: scene.on_ground(HERO_ID.GRIP_KEYS, 'Keyring'))
    expect(run_wait(phoenix.snipe_grip(scene.log))).to_be(True)
    expect(scene.logged('Grip is down')).to_be(True)


test('the Phoenix role shoots only on the arrow slit row and confirms the shared keyring drop', arrow_slit)

# Kills chickens and picks up their bones: walking, combat and looting in one small script.
#
# Settings (all optional):
#   npc_ids    NPC types to attack                    default [41], chickens
#   loot_ids   ground items to pick up                 default [526], bones
#   loot_goal  log out once the inventory holds this   default 3
#   area       [x, z, radius] to fight in              default the chicken pen east of Lumbridge
#   teleport   a ::tele argument for staff accounts, used on start when the area is far away,
#              e.g. "0,50,51,30,34" for the Lumbridge pen

NPC_IDS = settings.get('npc_ids', [41])
LOOT_IDS = settings.get('loot_ids', [526])
LOOT_GOAL = settings.get('loot_goal', 3)
AREA = settings.get('area', [3230, 3298, 8])
TELEPORT = settings.get('teleport', None)

# A target that neither side has hit for this many ticks after the attack is given up on.
GIVE_UP_TICKS = 15
# Without collision data an item behind a fence can't be reached, so it's skipped after this many tries.
MAX_PICKUP_TRIES = 3

target = None
attack_tick = 0
kills = 0
pickup_key = None
pickup_tries = 0
unreachable = []


def count_loot():
    return get_inventory_count_by_id(LOOT_IDS)


def on_start():
    log('Starting at', get_x(), get_z())
    if TELEPORT and distance_to(AREA[0], AREA[1]) > 50:
        log('Teleporting to', TELEPORT)
        command('tele ' + TELEPORT)


def on_progress_report():
    return {'Kills': kills, 'Loot held': count_loot(), 'Loot goal': LOOT_GOAL}


def on_npc_despawned(npc):
    global target, kills
    if npc.index == target and npc.hp == 0:
        kills += 1
        log('Killed', npc, '- kills so far:', kills)
        target = None


def on_server_message(msg):
    global target
    if msg.startswith("I can't reach"):
        log('Unreachable; picking another target')
        target = None


def next_loot():
    best = None
    for item in get_ground_items(LOOT_IDS, radius=AREA[2]):
        if (item.id, item.x, item.z) in unreachable:
            continue
        if best is None or distance_to(item.x, item.z) < distance_to(best.x, best.z):
            best = item
    return best


def fighting_target():
    npc = get_npc(target)
    if npc is None:
        return False
    return in_combat() or npc.in_combat() or get_tick() - attack_tick < GIVE_UP_TICKS


def loop():
    global target, attack_tick, pickup_key, pickup_tries

    if target is not None:
        if fighting_target():
            return 600
        target = None

    if count_loot() >= LOOT_GOAL:
        if in_combat():
            return 600
        log('Holding', count_loot(), 'loot after', kills, 'kills; done')
        stop_account()
        return 1000

    if is_inventory_full():
        log('Inventory full; done')
        stop_account()
        return 1000

    loot = next_loot()
    if loot is not None and not in_combat():
        key = (loot.id, loot.x, loot.z)
        pickup_tries = pickup_tries + 1 if key == pickup_key else 1
        pickup_key = key
        if pickup_tries > MAX_PICKUP_TRIES:
            log("Can't reach", loot, '- leaving it')
            unreachable.append(key)
            return 0
        log('Picking up', loot)
        take_ground_item(loot)
        return 1200

    npc = get_nearest_npc_by_id(NPC_IDS, radius=AREA[2], in_combat=False)
    if npc is None:
        if distance_to(AREA[0], AREA[1]) > 2:
            walk_to(AREA[0], AREA[1])
        return 1200

    if attack_npc(npc):
        target = npc.index
        attack_tick = get_tick()
        log('Attacking', npc)

    return 1200

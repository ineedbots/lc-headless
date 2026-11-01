// Exports rs2b0t's walker data (MIT, see thirdparty/rs2b0t) to data/nav as JSON, compiled the way rs2b0t's
// PathFinder.addEdges compiles it, so NavGraph reads one list of edges with their costs and requirements.
// Run once with Bun when rs2b0t's data changes, and commit the output:
//
//     bun tools/nav/export_rs2b0t.ts ../rs2b0t data/nav

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [rs2b0tRoot, outDir] = process.argv.slice(2);
if (!rs2b0tRoot || !outDir) {
    console.error('usage: bun tools/nav/export_rs2b0t.ts <rs2b0t folder> <output folder>');
    process.exit(2);
}

const webwalk = path.resolve(rs2b0tRoot, 'src/bot/event/webwalk');
const load = (file: string) => import(pathToFileURL(path.join(webwalk, file)).href);

const { allDoorRows, allTransportRows } = await load('loadTransportGraph.ts');
const { activateTransportRows } = await load('activateStateAware.ts');
const { specialRequiresAt } = await load('specialRequires.ts');
const { edgeCostForKind, DEFAULT_EDGE_COST } = await load('geometry/edgeCosts.ts');
const { SPELL_TELEPORTS, JEWELLERY_TELEPORTS } = await load('teleportCatalog.ts');
const { SPECIAL_CROSSINGS } = await load('data/specialCrossings.ts');
const { KNOWN_DANGER_ZONES } = await load('data/dangerZones.ts');
const { BANK_LOCATIONS } = await import(pathToFileURL(path.resolve(rs2b0tRoot, 'src/bot/api/bank/BankLocations.ts')).href);
const stairs = JSON.parse(fs.readFileSync(path.join(webwalk, 'data/stairEdges.json'), 'utf8'));

// rs2b0t derives its stair edges from its own engine's content; where the 289 engine's ladder script lands a player on
// another tile, the fix found live replaces the edge's from or to tile. Each fix names the loc and its option.
const STAIR_FIXES = [
    // Black Knights' Fortress: the ladder at (3021,3510) stands at the end of the walled strip that leads to the grill,
    // and is climbed from and lands on (3022,3510); rs2b0t's edges put both outside the strip, at (3021,3512), so the
    // grill had no route (phase 16a's live run).
    { locId: 1747, locX: 3021, locZ: 3510, action: 'Climb-up', from: { x: 3022, z: 3510, level: 0 } },
    { locId: 1746, locX: 3021, locZ: 3510, action: 'Climb-down', to: { x: 3022, z: 3510, level: 0 } },
    // And the ladder at (3022,3518) up to the secret passage that leads to the hole is used from (3022,3517) on both
    // levels; rs2b0t's edges put its ends at (3021,3519) and (3021,3518), where it answers "I can't reach that!".
    { locId: 1750, locX: 3022, locZ: 3518, action: 'Climb-up', from: { x: 3022, z: 3517, level: 0 }, to: { x: 3022, z: 3517, level: 1 } },
    { locId: 1749, locX: 3022, locZ: 3518, action: 'Climb-down', from: { x: 3022, z: 3517, level: 1 }, to: { x: 3022, z: 3517, level: 0 } },
];
for (const fix of STAIR_FIXES) {
    const stair = stairs.find((s: any) => s.locId === fix.locId && s.locX === fix.locX && s.locZ === fix.locZ && s.action === fix.action);
    if (!stair) {
        throw new Error(`stair fix for loc ${fix.locId} at (${fix.locX},${fix.locZ}) '${fix.action}' matches no edge`);
    }
    Object.assign(stair, fix.from ? { from: fix.from } : {}, fix.to ? { to: fix.to } : {});
}

const DOOR_DIR: Record<string, [number, number]> = { N: [0, 1], E: [1, 0], S: [0, -1], W: [-1, 0] };
const LANDING_KINDS = new Set(['dungeon', 'portal', 'ship', 'gangplank', 'teleport', 'shortcut']);

// Leaves out what JSON can't hold (undefined) and turns RegExps into their source and flags.
const plain = (value: unknown): unknown => JSON.parse(JSON.stringify(value, (_key, v) => (v instanceof RegExp ? { pattern: v.source, flags: v.flags } : v)));

const edges: unknown[] = [];
for (const door of allDoorRows()) {
    const [dx, dz] = DOOR_DIR[door.dir];
    const a = { x: door.x, z: door.z, level: door.level };
    const b = { x: door.x + dx, z: door.z + dz, level: door.level };
    const requires = specialRequiresAt(door.x, door.z, door.level);
    for (const [from, to] of [[a, b], [b, a]]) {
        edges.push({ kind: 'door', from, to, cost: DEFAULT_EDGE_COST.door, locName: door.locName, action: 'Open', locX: door.x, locZ: door.z, locId: door.locId, requires });
    }
}

for (const edge of activateTransportRows([...allTransportRows(), ...stairs])) {
    if (edge.disabledReason || edge.blacklist === true) {
        continue;
    }
    const dx = edge.to.x - edge.from.x;
    const dz = edge.to.z - edge.from.z;
    const midpointDoor = edge.kind === 'door' && (Math.abs(dx) === 2 || Math.abs(dz) === 2) && dx % 2 === 0 && dz % 2 === 0;
    const base = edge.requires ?? specialRequiresAt(edge.from.x, edge.from.z, edge.from.level);
    const requires = /^slash$/i.test(edge.action) && /web/i.test(edge.locName) ? { ...(base ?? {}), slashTool: true } : base;
    edges.push({
        kind: edge.kind,
        from: edge.from,
        to: edge.to,
        cost: edgeCostForKind(edge.kind),
        locName: edge.locName,
        action: edge.action,
        locX: edge.locX ?? (midpointDoor ? edge.from.x + dx / 2 : edge.from.x),
        locZ: edge.locZ ?? (midpointDoor ? edge.from.z + dz / 2 : edge.from.z),
        locId: edge.locId,
        openLocId: edge.openLocId,
        toLevel: edge.to.level !== edge.from.level ? edge.to.level : undefined,
        toTile: LANDING_KINDS.has(edge.kind) ? { x: edge.to.x, z: edge.to.z } : undefined,
        acceptAnyLanding: edge.kind === 'portal' || edge.kind === 'teleport' ? true : undefined,
        requires
    });
}

// Edges rs2b0t's data lacks, found live on the 289 engine.
const EDGE_ADDITIONS = [
    // Shilo Village: the quest ends at the dolmen in Bervirius' tomb, whose only way out is the climbing rocks
    // (`oploc1,zqhandholds` teleports a climber to 0_43_46_12_32 and steps them east), so the retreat to a bank and
    // the next quest in the queue had no route out of it (phase 17d's live run).
    { kind: 'dungeon', from: { x: 2764, z: 9376, level: 0 }, to: { x: 2765, z: 2976, level: 0 }, cost: edgeCostForKind('dungeon'), locName: 'Climbing rocks', action: 'Climb', locX: 2765, locZ: 9376, locId: 2236, toTile: { x: 2765, z: 2976 } },
    // Elemental Workshop: the quest ends down the spiral stairs, which `oploc1,elemental_workshop_spiralstairs` climbs
    // to 0_42_54_21_41, so the retreat to a bank and the next quest in the queue had no route out (phase 17f's live run).
    { kind: 'dungeon', from: { x: 2716, z: 9888, level: 0 }, to: { x: 2709, z: 3497, level: 0 }, cost: edgeCostForKind('dungeon'), locName: 'Staircase', action: 'Climb-up', locX: 2714, locZ: 9887, locId: 3416, toTile: { x: 2709, z: 3497 } },
    // The stairs land in the room behind the odd looking wall, which `open_and_close_double_door2` opens from inside
    // with a Push; only the way in needs the key.
    { kind: 'door', from: { x: 2709, z: 3496, level: 0 }, to: { x: 2709, z: 3495, level: 0 }, cost: edgeCostForKind('door'), locName: 'Odd looking wall', action: 'Push', locX: 2709, locZ: 3495, locId: 3391, toTile: { x: 2709, z: 3495 } },
];
edges.push(...EDGE_ADDITIONS);

const write = (name: string, value: unknown) => {
    const text = JSON.stringify(plain(value));
    fs.writeFileSync(path.join(outDir, name), text + '\n');
    console.log(`${name}: ${Array.isArray(value) ? value.length + ' entries, ' : ''}${(text.length / 1024).toFixed(0)} KB`);
};

if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
}
write('edges.json', edges);
write('teleports.json', [...SPELL_TELEPORTS, ...JEWELLERY_TELEPORTS]);
// Crossings rs2b0t's table lacks, found live on the 289 engine.
const CROSSING_ADDITIONS = [
    // Black Knights' Fortress: a fortress guard stops anyone entering the knights' banquet hall from the west, and only
    // lets them through on this answer. The hall is the only way to the ladder up to the hole (phase 16a's live run).
    { x: 3020, z: 3515, level: 0, locName: 'Door', action: 'Open', dialogue: { choose: ["I don't care. I'm going in anyway."] }, label: "Black Knights' Fortress banquet hall" },
    // Shilo Village: the climb out of Bervirius' tomb is an Agility roll, and a fall drops the climber back beside it.
    { x: 2764, z: 9376, level: 0, locName: 'Climbing rocks', action: 'Climb', toTile: { x: 2765, z: 2976, level: 0 }, arrivalRadius: 2, retryOnGameMessage: { message: { pattern: 'you fall!', flags: 'i' }, attempts: 4, reason: 'Agility roll failed' }, label: "Bervirius' tomb climbing rocks (phase 17d)" },
];
write('crossings.json', [...SPECIAL_CROSSINGS, ...CROSSING_ADDITIONS]);
write('danger_zones.json', KNOWN_DANGER_ZONES);
write('banks.json', BANK_LOCATIONS.map((bank: { tile: { x: number; z: number; level: number }; approach?: { x: number; z: number; level: number } }) => ({
    ...bank,
    tile: { x: bank.tile.x, z: bank.tile.z, level: bank.tile.level },
    approach: bank.approach ? { x: bank.approach.x, z: bank.approach.z, level: bank.approach.level } : undefined
})));

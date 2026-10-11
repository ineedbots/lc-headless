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
write('crossings.json', SPECIAL_CROSSINGS);
write('danger_zones.json', KNOWN_DANGER_ZONES);
write('banks.json', BANK_LOCATIONS.map((bank: { tile: { x: number; z: number; level: number }; approach?: { x: number; z: number; level: number } }) => ({
    ...bank,
    tile: { x: bank.tile.x, z: bank.tile.z, level: bank.tile.level },
    approach: bank.approach ? { x: bank.approach.x, z: bank.approach.z, level: bank.approach.level } : undefined
})));

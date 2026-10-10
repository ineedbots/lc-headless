// Exports rs2b0t's world catalogs (MIT, see third_party/rs2b0t) to the stdlib as Python literals, so
// rs2004/catalogs reads the same tables rs2b0t's bots do. Keys become snake_case and tiles become Tile(x, z,
// level). Run once with Bun when rs2b0t's data changes, and commit the output:
//
//     bun tools/catalogs/export_rs2b0t.ts ../rs2b0t src/Script/Stdlib/rs2004/catalogs/_data.py

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [rs2b0tRoot, outFile] = process.argv.slice(2);
if (!rs2b0tRoot || !outFile) {
    console.error('usage: bun tools/catalogs/export_rs2b0t.ts <rs2b0t folder> <output .py>');
    process.exit(2);
}

const bot = path.resolve(rs2b0tRoot, 'src/bot');
const load = (file: string) => import(pathToFileURL(path.join(bot, file)).href);

const fishing = await load('data/fishingLocations.ts');
const woodcutting = await load('data/woodcuttingLocations.ts');
const mining = await load('data/miningLocations.ts');
const cows = await load('data/cowKillerLocations.ts');
const runes = await load('data/runeCraftLocations.ts');
const pickpocket = await load('data/pickpocketTargets.ts');
const herbs = await load('data/herbs.ts');
const shops = await load('data/shopdb.ts');
const ranges = await load('data/cookingRanges.ts');
const surfaces = await load('data/cookSurfaceLocs.ts');
const cooking = await load('api/cooking/CookLocations.ts');
const walk = await load('api/map/WalkDestinations.ts');
const fire = await load('api/firemaking/Firemaking.ts');
const spells = await load('data/spelldb.ts');

const snake = (key: string): string => key.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();

const isTile = (value: any): boolean =>
    value !== null && typeof value === 'object' && !Array.isArray(value)
    && typeof value.x === 'number' && typeof value.z === 'number' && typeof value.level === 'number'
    && Object.keys(value).every(k => ['x', 'z', 'level'].includes(k));

// A Python literal for a value, indented by depth.
const py = (value: any, depth = 0): string => {
    const pad = '    '.repeat(depth + 1);
    const end = '    '.repeat(depth);
    if (value === undefined || value === null) {
        return 'None';
    }
    if (typeof value === 'boolean') {
        return value ? 'True' : 'False';
    }
    if (typeof value === 'number') {
        return Number.isFinite(value) ? String(value) : 'None';
    }
    if (typeof value === 'string') {
        return JSON.stringify(value);
    }
    if (value instanceof RegExp) {
        return JSON.stringify(value.source);
    }
    if (value instanceof Set) {
        return py([...value].sort(), depth);
    }
    if (isTile(value)) {
        return `Tile(${value.x}, ${value.z}, ${value.level})`;
    }
    if (Array.isArray(value)) {
        if (value.length === 0) {
            return '[]';
        }
        if (value.every(v => typeof v !== 'object' || v === null || isTile(v))) {
            return `[${value.map(v => py(v, depth)).join(', ')}]`;
        }
        return `[\n${value.map(v => pad + py(v, depth + 1)).join(',\n')},\n${end}]`;
    }
    const entries = Object.entries(value).filter(([, v]) => v !== undefined && typeof v !== 'function');
    if (entries.length === 0) {
        return '{}';
    }
    // A record of plain values goes on one line.
    const plainValue = (v: any): boolean => typeof v !== 'object' || v === null || isTile(v) || (Array.isArray(v) && v.every(e => typeof e !== 'object' || e === null || isTile(e)));
    if (entries.every(([, v]) => plainValue(v))) {
        return `{${entries.map(([k, v]) => `${JSON.stringify(snake(k))}: ${py(v, depth + 1)}`).join(', ')}}`;
    }
    return `{\n${entries.map(([k, v]) => `${pad}${JSON.stringify(snake(k))}: ${py(v, depth + 1)}`).join(',\n')},\n${end}}`;
};

// Record keys such as item names stay as they are.
const pyRecord = (record: Record<string, any>): string => {
    const entries = Object.entries(record);
    return `{\n${entries.map(([k, v]) => `    ${JSON.stringify(k)}: ${py(v, 1)}`).join(',\n')},\n}`;
};

const tables: [string, string][] = [
    ['FISHING_LOCATIONS', py(fishing.FISHING_LOCATIONS)],
    ['SHILO_WATER_VENDOR', py(fishing.SHILO_WATER_VENDOR)],
    ['WOODCUTTING_LOCATIONS', py(woodcutting.WOODCUTTING_LOCATIONS)],
    ['ENT_NPC_IDS', py(woodcutting.ENT_NPC_IDS)],
    ['ENT_LIFE_TICKS', py(woodcutting.ENT_LIFE_TICKS)],
    ['MINING_LOCATIONS', py(mining.MINING_LOCATIONS)],
    ['COW_LOCATIONS', py(cows.COW_LOCATIONS)],
    ['DRAYNOR_BANK', py(cows.DRAYNOR_BANK)],
    ['FALADOR_EAST_BANK', py(cows.FALADOR_EAST_BANK)],
    ['ARDOUGNE_WEST_BANK', py(cows.ARDOUGNE_WEST_BANK)],
    ['AL_KHARID_BANK', py(cows.AL_KHARID_BANK)],
    ['TOLL_COIN_TARGET', py(cows.TOLL_COIN_TARGET)],
    ['RUNES', pyRecord(runes.RUNES)],
    ['DEFAULT_RUNE', py(runes.DEFAULT_RUNE)],
    ['PICKPOCKET_TARGETS', py(pickpocket.PICKPOCKET_TARGETS)],
    ['ARDOUGNE_PICKPOCKET_TARGETS', py(pickpocket.ARDOUGNE_PICKPOCKET_TARGETS)],
    ['HERBS', py(herbs.HERBS)],
    ['COOKING_SURFACE_LOCS', py(surfaces.COOKING_SURFACE_LOCS)],
    ['COOKING_RANGE_LOCS', py(ranges.COOKING_RANGE_LOCS)],
    ['CATHERBY_RANGE', py(ranges.CATHERBY_RANGE)],
    ['FISH_CAMP_COOK_PLANS', pyRecord(ranges.FISH_CAMP_COOK_PLANS)],
    ['COOK_LOCATIONS', py(cooking.COOK_LOCATIONS)],
    ['WALK_DESTINATIONS', py(walk.WALK_DESTINATIONS)],
    ['FIRE_SPOTS', pyRecord(fire.FIRE_SPOTS)],
    ['LOG_LEVELS', pyRecord(fire.LOG_LEVELS)],
    ['SPELL_DB', pyRecord(spells.SPELL_DB)],
];

const header = `"""rs2b0t's world catalogs as data, generated by tools/catalogs/export_rs2b0t.ts from rs2b0t (MIT, see
third_party/rs2b0t). Don't edit it by hand: change rs2b0t's tables and run the exporter again."""

from rs2004.geometry import Tile
`;

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, header + tables.map(([name, value]) => `\n${name} = ${value}\n`).join(''));
// The shop database is large, so it's a module of its own, read only when a script asks about shops.
const shopsFile = path.join(path.dirname(outFile), '_shops.py');
fs.writeFileSync(shopsFile, header.replace('\nfrom rs2004.geometry import Tile\n', '') + `\nSHOP_DB = ${pyRecord(shops.SHOP_DB)}\n`);
console.log(`wrote ${tables.length} tables to ${outFile}, and the shop database to ${shopsFile}`);

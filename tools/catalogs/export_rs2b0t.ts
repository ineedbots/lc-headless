// Exports rs2b0t's world catalogs (MIT, see thirdparty/rs2b0t) to the stdlib as Python literals, so
// rs2004/catalogs reads the same tables rs2b0t's bots do. Keys become snake_case and tiles become Tile(x, z,
// level). Run once with Bun when rs2b0t's data changes, and commit the output:
//
//     bun tools/catalogs/export_rs2b0t.ts ../rs2b0t src/Script/Stdlib/rs2004/catalogs/_data.py
//
// It writes _shops.py, _items.py, _drops.py and _clues.py beside _data.py too: large tables read on first use. And the
// market's tables, to ../market/_data.py.

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
const items = await load('data/itemdb.ts');
const drops = await load('data/dropdb.ts');
const prices = await load('data/marketprices.ts');
const aliases = await load('data/itemAliases.ts');
const collisions = await load('data/nameCollisions.ts');
const untradeable = await load('data/untradeable.ts');
const clues = await load('api/ai/clues/data/cluedb.ts');

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
    ['STAFF_RUNES', pyRecord(spells.STAFF_RUNES)],
];

const header = `"""rs2b0t's world catalogs as data, generated by tools/catalogs/export_rs2b0t.ts from rs2b0t (MIT, see
thirdparty/rs2b0t). Don't edit it by hand: change rs2b0t's tables and run the exporter again."""

from rs2004.geometry import Tile
`;

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, header + tables.map(([name, value]) => `\n${name} = ${value}\n`).join(''));
// The shop database is large, so it's a module of its own, read only when a script asks about shops.
const shopsFile = path.join(path.dirname(outFile), '_shops.py');
const plainHeader = header.replace('\nfrom rs2004.geometry import Tile\n', '');
fs.writeFileSync(shopsFile, plainHeader + `\nSHOP_DB = ${pyRecord(shops.SHOP_DB)}\n`);
// So are the item and drop databases.
const itemsFile = path.join(path.dirname(outFile), '_items.py');
fs.writeFileSync(itemsFile, plainHeader + `\nITEM_DB = ${py(items.ITEM_DB)}\n`);
const dropsFile = path.join(path.dirname(outFile), '_drops.py');
fs.writeFileSync(dropsFile, plainHeader + `\nDROP_DB = ${pyRecord(drops.DROP_DB)}\n`);
// Keyed by obj id, so the keys are ints.
const pyIdRecord = (record: Record<string, any>): string => {
    const entries = Object.entries(record);
    return `{\n${entries.map(([k, v]) => `    ${Number(k)}: ${py(v, 1)}`).join(',\n')},\n}`;
};

// The clue database too: the hunting framework reads which objs are clues and caskets, and the clue engine the
// rest.
const cluesFile = path.join(path.dirname(outFile), '_clues.py');
fs.writeFileSync(cluesFile, header + `\nCLUE_DB = ${pyIdRecord(clues.CLUE_DB)}\n\nCASKET_IDS = ${pyIdRecord(clues.CASKET_IDS)}\n`);
console.log(`wrote ${tables.length} tables to ${outFile}, and the shop, item, drop and clue databases beside it`);

const marketFile = path.join(path.dirname(outFile), '..', 'market', '_data.py');
fs.mkdirSync(path.dirname(marketFile), { recursive: true });
const marketTables: [string, string][] = [
    ['MARKET_PRICES', py(prices.MARKET_PRICES)],
    ['ITEM_ALIASES', pyIdRecord(aliases.ITEM_ALIASES)],
    ['NAME_SYNONYMS', pyRecord(aliases.NAME_SYNONYMS)],
    ['NAME_COLLISIONS', py(collisions.NAME_COLLISIONS)],
    ['UNTRADEABLE_IDS', py(untradeable.UNTRADEABLE_IDS)],
];
fs.writeFileSync(marketFile, plainHeader.replace('world catalogs', 'market tables') + marketTables.map(([name, value]) => `\n${name} = ${value}\n`).join(''));
console.log(`wrote ${marketTables.length} market tables to ${marketFile}`);

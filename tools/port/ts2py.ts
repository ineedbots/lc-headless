// Translates rs2b0t's TypeScript (MIT, see thirdparty/rs2b0t) into a first draft of the stdlib's Python, for a
// person to finish (docs/design/BotApiParityDesign.md §2). It uses rs2b0t's own TypeScript compiler and type
// checker, so it knows which calls wait: an await becomes yield from where the callee returns a Promise and
// this client's function waits too, which the stubs say (-> Wait[...]). What it can't translate it marks with
// "# ts2py:" for the person to fix. Run with Bun from the repository:
//
//     bun tools/port/ts2py.ts ../rs2b0t src/bot/api/tasks/Anchor.ts [more.ts ...] [--out <file or folder>] [--stdlib]
//
// A bot's draft uses the names every script has as builtins; with --stdlib, for a module of the stdlib, it imports
// each from the stdlib module that exports it. Without --out it prints the draft. The draft is committed after the hand fixes; it isn't regenerated over them.

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const allArgs = process.argv.slice(2);
const stdlibMode = allArgs.includes('--stdlib');
const args = allArgs.filter(a => a !== '--stdlib');
const outIndex = args.indexOf('--out');
const outPath = outIndex >= 0 ? args[outIndex + 1] : null;
const positional = outIndex >= 0 ? args.filter((_, i) => i !== outIndex && i !== outIndex + 1) : args;
const [rs2b0tArg, ...inputs] = positional;
if (!rs2b0tArg || inputs.length === 0) {
    console.error('usage: bun tools/port/ts2py.ts <rs2b0t folder> <file.ts ...> [--out <file or folder>] [--stdlib]');
    process.exit(2);
}

const rs2b0tRoot = path.resolve(rs2b0tArg);
const botRoot = path.join(rs2b0tRoot, 'src/bot');
const repoRoot = path.resolve(import.meta.dir, '../..');
const ts = (await import(pathToFileURL(path.join(rs2b0tRoot, 'node_modules/typescript/lib/typescript.js')).href)).default;
type Node = any;

// ---- Names

const KEYWORDS = new Set([
    'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
    'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while',
    'with', 'yield', 'None', 'True', 'False', 'match',
]);

// A variable may not take the name of a builtin the draft calls.
const SHADOWED = new Set(['set', 'list', 'dict', 'len', 'any', 'all', 'str', 'int', 'float', 'bool', 'max', 'min', 'range', 'sorted', 'enumerate', 'isinstance', 'round', 'abs', 'type', 'next', 'sum', 'callable', 'getattr', 'print', 'iter', 'zip', 'reversed', 'object', 'tuple', 'format', 'hash']);

function snake(name: string): string {
    if (name.startsWith('#')) {
        name = '_' + name.slice(1);
    }
    if (name.toUpperCase() === name || /^[A-Z]/.test(name)) {
        return name;
    }
    const text = name.replace(/([a-z0-9])([A-Z])/g, '$1_$2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2').toLowerCase();
    return KEYWORDS.has(text) ? text + '_' : text;
}

// A CapWords facade object becomes its lower-case instance: ChatDialog is chat_dialog.
function facade(name: string): string {
    return name.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
}

// rs2b0t's event names to this client's.
function eventName(name: string): string {
    return name.replace(/\./g, '_').replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
}

// ---- Where rs2b0t's modules live here, by their path under src/bot without the extension. 'builtins' means
// every script has the names already; a module path means an import.

const MODULES: Record<string, string> = {
    'api/bot/Bot': 'builtins',
    'api/execution/Execution': 'builtins',
    'api/execution/EventSignal': 'builtins',
    'api/events/EventBus': 'builtins',
    'api/inventory/Inventory': 'builtins',
    'api/equipment/Equipment': 'builtins',
    'api/game/Game': 'builtins',
    'api/skills/Skills': 'builtins',
    'api/npcs/Npcs': 'builtins',
    'api/players/Players': 'builtins',
    'api/locs/Locs': 'builtins',
    'api/grounditems/GroundItems': 'builtins',
    'api/model/Npc': 'builtins',
    'api/model/Player': 'builtins',
    'api/model/Loc': 'builtins',
    'api/model/GroundItem': 'builtins',
    'api/model/Interactable': 'builtins',
    'api/bank/Bank': 'builtins',
    'api/bank/Banking': 'builtins',
    'api/bank/bankOps': 'builtins',
    'api/bank/bankRules': 'builtins',
    'api/tasks/PeriodicBank': 'builtins',
    'api/shop/Shop': 'builtins',
    'api/trade/Trade': 'builtins',
    'api/ui/dialogue/ChatDialog': 'builtins',
    'api/ui/widgets/Modals': 'builtins',
    'api/ui/questlog/Quests': 'builtins',
    'api/prayer/Prayer': 'builtins',
    'api/combat/Special': 'builtins',
    'api/combat/CombatStyle': 'builtins',
    'api/magic/Autocast': 'builtins',
    'api/walking/Traversal': 'builtins',
    'api/walking/Reach': 'builtins',
    'api/chatbox/gameMessages': 'builtins',
    'event/webwalk/DirectNavigator': 'builtins',
    'geometry/Tile': 'builtins',
    'geometry/Area': 'builtins',
    'runtime/Settings': 'builtins',
    'runtime/RunManager': 'builtins',
    'runtime/RecoveryHints': 'builtins',
    'runtime/ScriptActivity': 'builtins',
    'runtime/ScriptRunner': 'builtins',
    'api/acquisition/Tools': 'rs2004.catalogs',
    'api/acquisition/ToolAcquire': 'rs2004.catalogs',
    'api/acquisition/ItemAcquisition': 'rs2004.catalogs',
    'api/tasks/Anchor': 'rs2004.catalogs',
    'api/tasks/ContinueDialog': 'rs2004.catalogs',
    'api/tasks/DeathRecovery': 'rs2004.catalogs',
    'api/sustain/Sustain': 'rs2004.catalogs',
    'api/combat/food': 'rs2004.catalogs',
    'api/combat/eatTiming': 'rs2004.catalogs',
    'api/combat/boostPotions': 'rs2004.catalogs',
    'api/combat/keepList': 'rs2004.catalogs',
    'api/combat/fightUpkeep': 'rs2004.catalogs',
    'api/loadout/loadoutPlan': 'rs2004.catalogs',
    'api/loadout/loadouts': 'rs2004.catalogs',
    'api/loadout/loadoutStore': 'rs2004.catalogs',
    'api/loadout/loadoutSetting': 'rs2004.catalogs',
    'api/trade/PartnerTrade': 'rs2004.catalogs',
    'api/cooking/CookLocations': 'rs2004.catalogs',
    'api/map/WalkDestinations': 'rs2004.catalogs',
    'api/firemaking/Firemaking': 'rs2004.catalogs',
    'data/fishingLocations': 'rs2004.catalogs',
    'data/fishingMethods': 'rs2004.catalogs',
    'data/gatheringLocations': 'rs2004.catalogs',
    'data/miningLocations': 'rs2004.catalogs',
    'data/miningRocks': 'rs2004.catalogs',
    'data/woodcuttingLocations': 'rs2004.catalogs',
    'data/cowKillerLocations': 'rs2004.catalogs',
    'data/runeCraftLocations': 'rs2004.catalogs',
    'data/pickpocketTargets': 'rs2004.catalogs',
    'data/herbs': 'rs2004.catalogs',
    'data/shopdb': 'rs2004.catalogs',
    'data/spelldb': 'rs2004.catalogs',
    'data/cookingRanges': 'rs2004.catalogs',
    'event/webwalk/geometry/Reachability': 'builtins',
    'event/webwalk/walkOpening': 'builtins',
    'event/webwalk/Navigator': 'builtins',
    'event/webwalk/wilderness': 'builtins',
    'api/bank/BankLocations': 'builtins',
    'api/query/Query': 'builtins',
    'adapter/ClientAdapter': 'builtins',
    'api/inventory/packRules': 'rs2004.catalogs',
    'api/thieving/CakeStall': 'rs2004.catalogs',
    'api/thieving/cakeStallData': 'rs2004.catalogs',
    'api/thieving/stealRules': 'rs2004.catalogs',
    'api/thieving/targets': 'rs2004.catalogs',
    'api/firemaking/LightFire': 'rs2004.catalogs',
    'api/combat/CombatStyleLogic': 'rs2004.catalogs',
    'api/altar/Altars': 'rs2004.catalogs',
    'api/map/Teleport': 'rs2004.catalogs',
    'api/map/regions': 'rs2004.catalogs',
    'data/cookLocations': 'rs2004.catalogs',
    'data/itemdb': 'rs2004.catalogs',
    'data/dropdb': 'rs2004.catalogs',
    'api/ai/quests/exec/primitives': 'rs2004.quests.exec.primitives',
    'api/ai/quests/exec/prompts': 'rs2004.quests.exec.prompts',
    'api/ai/quests/prayer': 'rs2004.quests.prayer',
};

const QUEST_DEFS_PREFIX = 'api/ai/quests/defs/';

// rs2b0t's defs/<quest>/<file> is rs2004.quests.defs.<quest>.<file>, and a package's index is the package.
function questDefsModule(module: string): string {
    const parts = module.slice(QUEST_DEFS_PREFIX.length).split('/').map(snake);
    if (parts.length > 1 && parts[parts.length - 1] === 'index') {
        parts.pop();
    }
    return ['rs2004.quests.defs', ...parts].join('.');
}

// Modules a headless client leaves out: their imports are dropped, and calls into them marked.
const LEFT_OUT = ['paint/', 'panel/', 'multibox/', 'input/', 'runtime/diag/', 'api/ai/clues/cluePaint'];

// Builtin objects whose rs2b0t name isn't the facade rule's.
const OBJECT_NAMES: Record<string, string> = {
    bus: 'events',
    events: 'events',
    reader: 'reader',
    GameMessages: 'game_messages',
};

// Members renamed here beyond snake_case, by the rs2b0t object or class.
const MEMBER_RENAMES: Record<string, Record<string, string>> = {
    ChatDialog: { continue: 'continue_' },
};

// ---- What the stubs say: which calls wait, and the parameters each takes.

interface Param {
    name: string;
    optional: boolean;
}

interface StubFunction {
    wait: boolean;
    params: Param[];
}

class Stubs {
    classes = new Map<string, Map<string, StubFunction>>();
    instances = new Map<string, string>();
    functions = new Map<string, StubFunction>();

    constructor(folder: string) {
        for (const file of walk(folder).filter(f => f.endsWith('.pyi'))) {
            this.read(fs.readFileSync(file, 'utf8'));
        }
    }

    private read(text: string): void {
        let current: string | null = null;
        for (const line of text.split(/\r?\n/)) {
            const cls = /^class (\w+)/.exec(line);
            if (cls) {
                current = cls[1];
                this.classes.set(current, this.classes.get(current) ?? new Map());
                continue;
            }
            const instance = /^(\w+): (_?\w+)\s*$/.exec(line);
            if (instance) {
                this.instances.set(instance[1], instance[2]);
                current = null;
                continue;
            }
            const def = /^(\s*)def (\w+)\((.*)\)\s*(?:->\s*(.*))?:/.exec(line);
            if (!def) {
                if (line.length > 0 && !/^\s/.test(line)) {
                    current = null;
                }
                continue;
            }
            const params = splitParams(def[3])
                .map(p => ({ name: p.split(/[:=]/)[0].replace(/^\*+/, '').trim(), optional: p.includes('=') }))
                .filter(p => p.name && p.name !== 'self');
            const fn = { wait: /\bWait\[/.test(def[4] ?? ''), params };
            if (def[1].length > 0 && current) {
                this.classes.get(current)!.set(def[2], fn);
            } else if (def[1].length === 0) {
                this.functions.set(def[2], fn);
                current = null;
            }
        }
    }

    method(owner: string, name: string): StubFunction | undefined {
        const cls = this.instances.get(owner) ?? owner;
        return this.classes.get(cls)?.get(name);
    }
}

function splitParams(text: string): string[] {
    const out: string[] = [];
    let depth = 0;
    let current = '';
    for (const c of text) {
        if (c === '[' || c === '(') depth++;
        if (c === ']' || c === ')') depth--;
        if (c === ',' && depth === 0) {
            out.push(current);
            current = '';
        } else {
            current += c;
        }
    }
    if (current.trim()) out.push(current);
    return out;
}

function walk(folder: string): string[] {
    if (!fs.existsSync(folder)) return [];
    return fs.readdirSync(folder, { withFileTypes: true }).flatMap(entry => {
        const full = path.join(folder, entry.name);
        return entry.isDirectory() ? walk(full) : [full];
    });
}

const stubs = new Stubs(path.join(repoRoot, 'scripts/typings'));

// ---- Where each of the stdlib's public names is defined, for --stdlib's imports

const stdlibRoot = path.join(repoRoot, 'src/Script/Stdlib');

function stdlibExports(): Map<string, string> {
    // By name: the module that both lists it in __all__ and defines it, else one that lists it, else one that defines it.
    const ranked = new Map<string, { module: string; rank: number }>();
    for (const file of walk(path.join(stdlibRoot, 'rs2004')).filter(f => f.endsWith('.py'))) {
        const rel = path.relative(stdlibRoot, file).replace(/\\/g, '/').replace(/\.py$/, '').replace(/\/__init__$/, '');
        if (rel.split('/').some(part => part.startsWith('_') && part !== '__init__')) continue;
        const module = rel.replace(/\//g, '.');
        const text = fs.readFileSync(file, 'utf8');
        const listed = new Set<string>();
        for (const all of text.matchAll(/^__all__\s*\+?=\s*\[([\s\S]*?)\]/gm)) {
            for (const name of all[1].matchAll(/'(\w+)'/g)) listed.add(name[1]);
        }
        const defined = new Set<string>();
        for (const def of text.matchAll(/^(?:def|class) (\w+)|^(\w+)\s*=/gm)) defined.add(def[1] ?? def[2]);
        for (const name of new Set([...listed, ...defined])) {
            if (name.startsWith('_')) continue;
            const rank = (listed.has(name) ? 2 : 0) + (defined.has(name) ? 1 : 0);
            const best = ranked.get(name);
            if (!best || rank > best.rank) ranked.set(name, { module, rank });
        }
    }
    const out = new Map<string, string>();
    for (const [name, { module }] of ranked) out.set(name, module);
    return out;
}

const STDLIB_EXPORTS = stdlibMode ? stdlibExports() : new Map<string, string>();

// ---- The program, with rs2b0t's compiler options

const configPath = path.join(rs2b0tRoot, 'tsconfig.json');
const config = ts.readConfigFile(configPath, ts.sys.readFile);
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, rs2b0tRoot);
const files = inputs.map(f => path.resolve(rs2b0tRoot, f));
const program = ts.createProgram(files, parsed.options);
const checker = program.getTypeChecker();

// rs2b0t's calls by the callee's name, read from every file under src/bot on first use. By name, not by symbol,
// so a call of another function with the same name counts too; that only makes the spreading more careful.
let callIndex: Map<string, Node[]> | null = null;

// rs2b0t's scripts/index.ts: each ScriptRegistry.register({...}), and the names it imports, read on first use.
let registry: { entries: Node[]; imports: Map<string, { file: string; name: string }> } | null = null;

function readRegistry(): NonNullable<typeof registry> {
    if (registry) return registry;
    const file = path.join(botRoot, 'scripts/index.ts');
    const sf = ts.createSourceFile(file, fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '', ts.ScriptTarget.Latest, true);
    const entries: Node[] = [];
    const imports = new Map<string, { file: string; name: string }>();
    for (const st of sf.statements) {
        if (ts.isImportDeclaration(st) && st.importClause) {
            const target = path.resolve(path.dirname(file), st.moduleSpecifier.text.replace(/\.js$/, '.ts'));
            if (st.importClause.name) imports.set(st.importClause.name.text, { file: target, name: 'default' });
            for (const el of st.importClause.namedBindings?.elements ?? []) {
                imports.set(el.name.text, { file: target, name: (el.propertyName ?? el.name).text });
            }
        }
        if (ts.isExpressionStatement(st) && ts.isCallExpression(st.expression) && st.expression.expression.getText() === 'ScriptRegistry.register') {
            const arg = st.expression.arguments[0];
            if (arg && ts.isObjectLiteralExpression(arg)) entries.push(arg);
        }
    }
    registry = { entries, imports };
    return registry;
}

function samePath(a: string, b: string): boolean {
    return path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase();
}

// The registry entry whose create() makes this file's default export.
function registryEntry(file: string): Node | null {
    const { entries, imports } = readRegistry();
    for (const entry of entries) {
        const create = entry.properties.find((p: Node) => ts.isPropertyAssignment(p) && p.name.getText() === 'create');
        const body = create && ts.isArrowFunction(create.initializer) ? create.initializer.body : null;
        if (!body || !ts.isNewExpression(body) || !ts.isIdentifier(body.expression)) continue;
        const made = imports.get(body.expression.text);
        if (made && made.name === 'default' && samePath(made.file, file)) return entry;
    }
    return null;
}

// What a name the registry imports is called in file, when it comes from file.
function registryImport(name: string, file: string): string | null {
    const found = readRegistry().imports.get(name);
    return found && found.name !== 'default' && samePath(found.file, file) ? found.name : null;
}

function callsNamed(name: string): Node[] {
    if (!callIndex) {
        const index = new Map<string, Node[]>();
        for (const file of walk(botRoot).filter(f => f.endsWith('.ts') && !f.endsWith('.d.ts'))) {
            const sf = program.getSourceFile(file) ?? ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true);
            const visit = (n: Node): void => {
                if (ts.isCallExpression(n)) {
                    const callee = n.expression;
                    const key = ts.isIdentifier(callee) ? callee.text : ts.isPropertyAccessExpression(callee) ? callee.name.text : null;
                    if (key) {
                        const calls = index.get(key) ?? [];
                        calls.push(n);
                        index.set(key, calls);
                    }
                }
                ts.forEachChild(n, visit);
            };
            visit(sf);
        }
        callIndex = index;
    }
    return callIndex.get(name) ?? [];
}

// ---- The translator

interface Options {
    name: string;
    // Python's parameters in order: the required properties, then the optional ones.
    params: Param[];
}

interface FunctionScope {
    // An object parameter spread into parameters of its own: its name, and theirs.
    options: Options | null;
    generator: boolean;
    inClass: string | null;
}

class Translator {
    private out: string[] = [];
    private depth = 0;
    private prelude: string[][] = [];
    private temp = 0;
    private imports = new Map<string, Set<string>>();
    private needs = new Set<string>();
    private scopes: FunctionScope[] = [];
    // Translated in this file: functions whose object parameter was spread into parameters.
    private expanded = new Map<string, Param[]>();
    private exported: string[] = [];

    constructor(private readonly sf: Node, private readonly rel: string) {}

    run(): string {
        for (const statement of this.sf.statements) {
            this.statement(statement, true);
        }
        this.registration();
        const header: string[] = [];
        header.push(`"""Ported from rs2b0t's src/bot/${this.rel} (MIT, see thirdparty/rs2b0t). A ts2py draft: fix what's`);
        header.push('marked "ts2py:", then this line."""');
        header.push('');
        for (const name of [...this.needs].sort()) {
            header.push(`import ${name}`);
        }
        for (const [module, names] of [...this.imports].sort()) {
            header.push(`from ${module} import ${[...names].sort().join(', ')}`);
        }
        if (this.exported.length > 0) {
            header.push('');
            header.push(`__all__ = [${this.exported.map(n => `'${n}'`).join(', ')}]`);
        }
        header.push('');
        return [...header, ...layout(this.out)].join('\n').trimEnd() + '\n';
    }

    // A bot file's default-exported class, as rs2b0t's scripts/index.ts registers it: BOT = define_bot(...).
    private registration(): void {
        const cls = this.sf.statements.find((st: Node) => ts.isClassDeclaration(st) && (st.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.DefaultKeyword));
        if (!cls || !cls.name) return;
        const entry = registryEntry(this.sf.fileName);
        if (!entry) return;
        const fields: string[] = [];
        for (const prop of entry.properties) {
            if (!ts.isPropertyAssignment(prop)) continue;
            const key = prop.name.getText();
            const value = prop.initializer;
            if (key === 'create') {
                fields.push(`create=${cls.name.text}`);
            } else if (key === 'settingsSchema') {
                const own = ts.isIdentifier(value) ? registryImport(value.text, this.sf.fileName) : null;
                if (own) {
                    fields.push(`settings_schema=${this.valueName(own)}`);
                } else {
                    this.emit(this.todo(`the registry's settingsSchema is ${value.getText().slice(0, 60)}, from outside this file`));
                    fields.push('settings_schema=None');
                }
            } else if (ts.isStringLiteral(value) || ts.isNoSubstitutionTemplateLiteral(value)) {
                fields.push(`${snake(key)}=${pyString(value.text)}`);
            } else if (ts.isArrayLiteralExpression(value) && value.elements.every((el: Node) => ts.isStringLiteral(el))) {
                fields.push(`${snake(key)}=[${value.elements.map((el: Node) => pyString(el.text)).join(', ')}]`);
            } else {
                this.emit(this.todo(`the registry's ${key} is ${value.getText().slice(0, 60)}`));
            }
        }
        this.emit('');
        this.emit('');
        this.emit('BOT = define_bot(');
        for (const field of fields) this.emit(`    ${field},`);
        this.emit(')');
    }

    // -- Output

    private emit(line: string): void {
        this.out.push(line === '' ? '' : '    '.repeat(this.depth) + line);
    }

    private todo(why: string, node?: Node): string {
        const where = node ? ` (line ${this.sf.getLineAndCharacterOfPosition(node.getStart()).line + 1})` : '';
        return `# ts2py: ${why.replace(/\s+/g, ' ')}${where}`;
    }

    private notes: string[][] = [];

    // A note for the statement being translated, emitted above it; used inside expressions.
    private flag(why: string, node?: Node): void {
        const note = this.todo(why, node);
        if (this.notes.length > 0) {
            this.notes[this.notes.length - 1].push(note);
        } else {
            this.emit(note);
        }
    }

    // Runs a translation that may come to nothing, and when it does, takes back what it emitted and hoisted, so
    // what's translated again after it isn't emitted twice.
    private tentative<T>(attempt: () => T | null): T | null {
        const out = this.out.length;
        const preludes = this.prelude.map(p => p.length);
        const notes = this.notes.map(n => n.length);
        const temp = this.temp;
        const result = attempt();
        if (result === null) {
            this.out.length = out;
            this.prelude.forEach((p, i) => (p.length = preludes[i]));
            this.notes.forEach((n, i) => (n.length = notes[i]));
            this.temp = temp;
        }
        return result;
    }

    private fresh(stem: string): string {
        this.temp += 1;
        return `_${stem}${this.temp}`;
    }

    private pre(line: string): void {
        if (this.prelude.length === 0) {
            this.emit(line);
        } else {
            this.prelude[this.prelude.length - 1].push(line);
        }
    }

    // Runs body with a fresh prelude, and emits what expressions hoisted before what body emits.
    private withPrelude(body: () => void): void {
        this.prelude.push([]);
        this.notes.push([]);
        const start = this.out.length;
        body();
        const hoisted = this.prelude.pop()!;
        const notes = this.notes.pop()!;
        const emitted = this.out.splice(start);
        for (const note of notes) {
            this.out.push('    '.repeat(this.depth) + note);
        }
        for (const line of hoisted) {
            this.out.push(line.startsWith('\n') ? line.slice(1) : '    '.repeat(this.depth) + line);
        }
        this.out.push(...emitted);
    }

    private comments(node: Node): void {
        const text = this.sf.getFullText();
        const ranges = ts.getLeadingCommentRanges(text, node.getFullStart()) ?? [];
        for (const range of ranges) {
            const raw = text.slice(range.pos, range.end);
            if (raw.startsWith('/**')) {
                continue;
            }
            for (const line of commentLines(raw)) {
                this.emit(line ? `# ${line}` : '#');
            }
        }
    }

    private docstring(node: Node): void {
        const text = this.sf.getFullText();
        const ranges = ts.getLeadingCommentRanges(text, node.getFullStart()) ?? [];
        const docs = ranges.map((r: any) => text.slice(r.pos, r.end)).filter((r: string) => r.startsWith('/**'));
        if (docs.length === 0) return;
        const lines = commentLines(docs[docs.length - 1]).filter(l => !l.startsWith('@'));
        if (lines.length === 0) return;
        const body = lines.map(l => l.trim()).join(' ').trim().replace(/"""/g, "'''").replace(/\\/g, '\\\\');
        this.emit(`"""${body}"""`);
    }

    // -- Imports

    private moduleOf(specifier: string): string | null {
        let rel: string;
        if (specifier.startsWith('#/bot/')) {
            rel = specifier.slice('#/bot/'.length);
        } else if (specifier.startsWith('.')) {
            const from = path.dirname(this.sf.fileName);
            rel = path.relative(botRoot, path.resolve(from, specifier)).replace(/\\/g, '/');
        } else {
            return null;
        }
        return rel.replace(/\.(js|ts)$/, '');
    }

    private importDeclaration(node: Node): void {
        const specifier = node.moduleSpecifier.text;
        const module = this.moduleOf(specifier);
        const clause = node.importClause;
        if (!clause || clause.isTypeOnly || module === null) {
            return;
        }
        if (LEFT_OUT.some(prefix => module.startsWith(prefix))) {
            this.emit(this.todo(`left out: an import from ${module}, which a headless client doesn't have`));
            return;
        }
        // Each name as the code reads it: a facade by its instance's name.
        const names: string[] = [];
        if (clause.name) {
            names.push(this.identifier(clause.name));
        }
        // A renamed import ({ normalizeJournal as normalize }) is found by the name its module exports.
        const exported = new Map<string, string>();
        for (const element of clause.namedBindings?.elements ?? []) {
            if (!element.isTypeOnly && !this.isTypeOnlySymbol(element.name)) {
                const name = this.identifier(element.name);
                names.push(name);
                if (element.propertyName) {
                    exported.set(name, this.identifier(element.propertyName));
                }
            }
        }
        if (names.length === 0) {
            return;
        }
        const imported = (name: string, as: string = name): string =>
            exported.has(name) && exported.get(name) !== as ? `${exported.get(name)} as ${as}` : as;
        // A quest's own files map by path: several quests export the same names (FALADOR_WEST_BANK, in_cave), so the
        // name index would import another quest's.
        if (stdlibMode && module.startsWith(QUEST_DEFS_PREFIX)) {
            const target = questDefsModule(module);
            for (const name of names) {
                this.addImport(target, imported(name, this.valueName(name)));
            }
            return;
        }
        const target = MODULES[module];
        // In the stdlib nothing is a builtin: each name comes from the module that exports it, and a module that
        // is a facade of its own, execution, is imported whole.
        if (stdlibMode && (target === 'builtins' || target === 'rs2004.catalogs' || target === undefined)) {
            const missing: string[] = [];
            for (const name of names) {
                const home = STDLIB_EXPORTS.get(exported.get(name) ?? name);
                if (home) {
                    this.addImport(home, imported(name));
                } else if (fs.existsSync(path.join(stdlibRoot, 'rs2004', `${name}.py`))) {
                    this.addImport('rs2004', name);
                } else {
                    missing.push(name);
                }
            }
            if (missing.length > 0) {
                this.emit(this.todo(`import ${missing.join(', ')} from ${module}, which isn't ported yet`));
            }
            return;
        }
        if (target === 'builtins') {
            return;
        }
        if (target === undefined) {
            this.emit(this.todo(`import ${names.join(', ')} from ${module}, which isn't ported yet`));
            return;
        }
        for (const name of names) {
            this.addImport(target, imported(name, this.valueName(name)));
        }
    }

    // `export { a, b } from './journal.js'`: a quest's index re-exports its files' names, and its tests import them
    // from the package, so the draft imports them and lists them in __all__.
    private reExport(node: Node): void {
        if (node.isTypeOnly || !node.moduleSpecifier || !node.exportClause || !ts.isNamedExports(node.exportClause)) {
            return;
        }
        const module = this.moduleOf(node.moduleSpecifier.text);
        if (module === null) {
            return;
        }
        const names = node.exportClause.elements
            .filter((element: Node) => !element.isTypeOnly && !this.isTypeOnlySymbol(element.name))
            .map((element: Node) => this.valueName(this.identifier(element.name)));
        if (names.length === 0) {
            return;
        }
        if (!stdlibMode || !module.startsWith(QUEST_DEFS_PREFIX)) {
            this.emit(this.todo(`re-export ${names.join(', ')} from ${module}`));
            return;
        }
        const target = questDefsModule(module);
        for (const name of names) {
            this.addImport(target, name);
            if (!this.exported.includes(name)) {
                this.exported.push(name);
            }
        }
    }

    private addImport(module: string, name: string): void {
        const set = this.imports.get(module) ?? new Set();
        set.add(name);
        this.imports.set(module, set);
    }

    private isTypeOnlySymbol(id: Node): boolean {
        const symbol = this.aliased(checker.getSymbolAtLocation(id));
        if (!symbol) return false;
        const flags = symbol.flags;
        return (flags & (ts.SymbolFlags.Value)) === 0;
    }

    private aliased(symbol: any): any {
        if (symbol && symbol.flags & ts.SymbolFlags.Alias) {
            return checker.getAliasedSymbol(symbol);
        }
        return symbol;
    }

    // -- Statements

    private statement(node: Node, top = false): void {
        if (!top || !ts.isImportDeclaration(node)) {
            this.comments(node);
        }
        this.withPrelude(() => this.statementBody(node, top));
    }

    private statementBody(node: Node, top: boolean): void {
        const k = ts.SyntaxKind;
        switch (node.kind) {
            case k.ImportDeclaration:
                this.importDeclaration(node);
                return;
            case k.InterfaceDeclaration:
            case k.TypeAliasDeclaration:
                return;
            case k.ExportDeclaration:
                this.reExport(node);
                return;
            case k.FunctionDeclaration:
                this.functionDeclaration(node, top);
                return;
            case k.ClassDeclaration:
                this.classDeclaration(node);
                return;
            case k.EnumDeclaration:
                this.enumDeclaration(node);
                return;
            case k.VariableStatement:
                for (const declaration of node.declarationList.declarations) {
                    this.variable(declaration, top && hasExport(node));
                }
                return;
            case k.ExportAssignment:
                this.emit(`${node.isExportEquals ? 'module_exports' : 'BOT'} = ${this.expr(node.expression)}`);
                return;
            case k.ExpressionStatement:
                this.expressionStatement(node.expression);
                return;
            case k.ReturnStatement:
                this.returnStatement(node);
                return;
            case k.IfStatement:
                this.ifStatement(node, false);
                return;
            case k.Block:
                for (const statement of node.statements) this.statement(statement);
                return;
            case k.ForOfStatement:
                this.forOf(node);
                return;
            case k.ForInStatement:
                this.emit(`for ${this.bindingTarget(node.initializer)} in ${this.expr(node.expression)}:`);
                this.block(node.statement);
                return;
            case k.ForStatement:
                this.forStatement(node);
                return;
            case k.WhileStatement:
                this.emit(`while ${this.condition(node.expression)}:`);
                this.block(node.statement);
                return;
            case k.DoStatement:
                this.emit('while True:');
                this.depth++;
                this.blockStatements(node.statement);
                this.emit(`if not (${this.condition(node.expression)}):`);
                this.emit('    break');
                this.depth--;
                return;
            case k.BreakStatement:
                this.emit(node.label ? this.todo('a labelled break') : 'break');
                return;
            case k.ContinueStatement:
                this.emit(node.label ? this.todo('a labelled continue') : 'continue');
                return;
            case k.ThrowStatement:
                this.emit(`raise ${this.errorExpr(node.expression)}`);
                return;
            case k.TryStatement:
                this.tryStatement(node);
                return;
            case k.SwitchStatement:
                this.switchStatement(node);
                return;
            case k.EmptyStatement:
                return;
            case k.LabeledStatement:
                this.emit(this.todo('a labelled statement', node));
                this.statement(node.statement);
                return;
            default:
                this.emit(this.todo(`a ${k[node.kind]} statement`, node));
        }
    }

    private block(node: Node): void {
        this.depth++;
        const before = this.out.length;
        this.blockStatements(node);
        if (this.out.length === before) {
            this.emit('pass');
        }
        this.depth--;
    }

    private blockStatements(node: Node): void {
        if (ts.isBlock(node)) {
            for (const statement of node.statements) this.statement(statement);
        } else {
            this.statement(node);
        }
    }

    private variable(declaration: Node, exported: boolean): void {
        const init = declaration.initializer;
        if (ts.isIdentifier(declaration.name)) {
            // A CapWords const is read as its facade name (identifier()), so it's declared by that name too.
            const text = declaration.name.text;
            const name = /^[A-Z][a-z]/.test(text) && !(init && ts.isClassExpression(init)) ? facade(text) : this.valueName(text);
            if (exported) this.exported.push(name);
            if (!init) {
                this.emit(`${name} = None`);
                return;
            }
            if (ts.isArrowFunction(init) || ts.isFunctionExpression(init)) {
                this.functionLike(name, init, false);
                return;
            }
            this.emit(`${name} = ${this.awaitedOr(init)}`);
            return;
        }
        // Destructuring.
        const source = init ? this.awaitedOr(init) : 'None';
        if (ts.isArrayBindingPattern(declaration.name)) {
            const names = declaration.name.elements.map((e: Node) => (ts.isOmittedExpression(e) ? '_' : this.bindingTarget(e.name)));
            this.emit(`${names.join(', ')} = ${source}`);
            return;
        }
        const holder = /^[\w.]+$/.test(source) ? source : this.fresh('o');
        if (holder !== source) this.emit(`${holder} = ${source}`);
        for (const element of declaration.name.elements) {
            const prop = element.propertyName ? element.propertyName.getText() : element.name.getText();
            const target = this.bindingTarget(element.name);
            const read = `${holder}.${snake(prop)}`;
            this.emit(element.initializer ? `${target} = ${read} if ${read} is not None else ${this.expr(element.initializer)}` : `${target} = ${read}`);
        }
    }

    private bindingTarget(node: Node): string {
        if (ts.isVariableDeclarationList(node)) {
            return this.bindingTarget(node.declarations[0].name);
        }
        if (ts.isIdentifier(node)) return this.valueName(node.text);
        if (ts.isArrayBindingPattern(node)) {
            return node.elements.map((e: Node) => (ts.isOmittedExpression(e) ? '_' : this.bindingTarget(e.name))).join(', ');
        }
        this.flag('an object pattern here');
        return '_o';
    }

    private expressionStatement(e: Node): void {
        const k = ts.SyntaxKind;
        if (ts.isAwaitExpression(e)) {
            const inner = this.awaitTarget(e);
            this.emit(inner.wait ? `yield from ${inner.text}` : inner.text);
            return;
        }
        if (ts.isBinaryExpression(e) && isAssignment(e.operatorToken.kind)) {
            this.assignment(e);
            return;
        }
        if ((ts.isPostfixUnaryExpression(e) || ts.isPrefixUnaryExpression(e)) && (e.operator === k.PlusPlusToken || e.operator === k.MinusMinusToken)) {
            this.emit(`${this.expr(e.operand)} ${e.operator === k.PlusPlusToken ? '+=' : '-='} 1`);
            return;
        }
        if (ts.isCallExpression(e) && e.questionDotToken === undefined && this.optionalChainStatement(e)) {
            return;
        }
        if (ts.isCallExpression(e) && e.questionDotToken) {
            const callee = ts.isPropertyAccessExpression(e.expression) ? this.member(e.expression) : this.expr(e.expression);
            const fn = /^[\w.]+$/.test(callee) ? callee : this.fresh('fn');
            if (fn !== callee) this.emit(`${fn} = ${callee}`);
            this.emit(`if ${fn} is not None:`);
            this.depth++;
            const call = `${fn}(${this.argList(e)})`;
            this.emit(this.returnsPromise(e) && this.waitsHere(e) ? `yield from ${call}` : call);
            this.depth--;
            return;
        }
        if (ts.isCallExpression(e)) {
            const call = this.callStatement(e);
            if (call !== null) {
                this.emit(call);
                return;
            }
        }
        if (ts.isVoidExpression(e)) {
            this.emit(`${this.expr(e.expression)}  ${this.todo('was void: a generator that is not driven does nothing')}`);
            return;
        }
        const text = this.expr(e);
        const unawaited = ts.isCallExpression(e) && this.returnsPromise(e) && this.waitsHere(e);
        this.emit(unawaited ? `${text}  ${this.todo('not awaited in rs2b0t; a generator that is not driven does nothing')}` : text);
    }

    // a?.b() as a statement becomes an if.
    private optionalChainStatement(e: Node): boolean {
        let callee = e.expression;
        if (ts.isPropertyAccessExpression(callee) && callee.questionDotToken) {
            const holder = this.expr(callee.expression);
            if (ts.isIdentifier(callee.expression) && this.optionsNamed(callee.expression.text)) {
                return false;
            }
            this.emit(`if ${holder} is not None:`);
            this.depth++;
            this.emit(`${holder}.${this.memberName(callee)}(${this.argList(e)})`);
            this.depth--;
            return true;
        }
        return false;
    }

    // Statement-only rewrites: forEach, map.set and array.push of several.
    private callStatement(e: Node): string | null {
        const callee = e.expression;
        if (!ts.isPropertyAccessExpression(callee)) return null;
        const method = callee.name.text;
        const kind = this.collectionKind(callee.expression);
        if (method === 'forEach' && e.arguments.length === 1) {
            const fn = e.arguments[0];
            if (ts.isArrowFunction(fn) && fn.parameters.length >= 1) {
                const item = this.bindingTarget(fn.parameters[0].name);
                const index = fn.parameters.length > 1 ? this.bindingTarget(fn.parameters[1].name) : null;
                this.emit(index ? `for ${index}, ${item} in enumerate(${this.expr(callee.expression)}):` : `for ${item} in ${this.expr(callee.expression)}:`);
                if (ts.isBlock(fn.body)) {
                    this.block(fn.body);
                } else {
                    this.depth++;
                    this.expressionStatement(fn.body);
                    this.depth--;
                }
                return '';
            }
        }
        if (kind === 'map' && method === 'set' && e.arguments.length === 2) {
            return `${this.expr(callee.expression)}[${this.expr(e.arguments[0])}] = ${this.expr(e.arguments[1])}`;
        }
        if (kind === 'array' && method === 'push' && e.arguments.length > 1) {
            return `${this.expr(callee.expression)}.extend([${e.arguments.map((a: Node) => this.expr(a)).join(', ')}])`;
        }
        return null;
    }

    private assignment(e: Node): void {
        const op = e.operatorToken.kind;
        const k = ts.SyntaxKind;
        const left = this.expr(e.left);
        const right = this.awaitedOr(e.right);
        const ops: Record<number, string> = {
            [k.EqualsToken]: '=', [k.PlusEqualsToken]: '+=', [k.MinusEqualsToken]: '-=', [k.AsteriskEqualsToken]: '*=',
            [k.SlashEqualsToken]: '/=', [k.PercentEqualsToken]: '%=', [k.BarEqualsToken]: '|=', [k.AmpersandEqualsToken]: '&=',
        };
        if (op === k.QuestionQuestionEqualsToken) {
            this.emit(`if ${left} is None:`);
            this.emit(`    ${left} = ${right}`);
            return;
        }
        if (op === k.BarBarEqualsToken) {
            this.emit(`${left} = ${left} or ${right}`);
            return;
        }
        if (op === k.AmpersandAmpersandEqualsToken) {
            this.emit(`${left} = ${left} and ${right}`);
            return;
        }
        if (ts.isArrayLiteralExpression(e.left)) {
            this.emit(`${e.left.elements.map((x: Node) => this.expr(x)).join(', ')} = ${right}`);
            return;
        }
        this.emit(`${left} ${ops[op] ?? this.todo(k[op])} ${right}`);
    }

    private returnStatement(node: Node): void {
        if (!node.expression) {
            this.emit('return');
            return;
        }
        const e = node.expression;
        if (ts.isAwaitExpression(e)) {
            const inner = this.awaitTarget(e);
            if (inner.wait) {
                const name = this.fresh('result');
                this.emit(`${name} = yield from ${inner.text}`);
                this.emit(`return ${name}`);
                return;
            }
            this.emit(`return ${inner.text}`);
            return;
        }
        // An async function that returns a call's Promise without awaiting it gives its caller what the call
        // resolves to, which a generator gets by yielding from the call.
        if (this.scopes.at(-1)?.generator && ts.isCallExpression(e) && this.waitsHere(e)) {
            const name = this.fresh('result');
            this.emit(`${name} = yield from ${this.expr(e)}`);
            this.emit(`return ${name}`);
            return;
        }
        // `return a && call()` resolves the call's Promise too, so the short circuit becomes a test before the yield.
        if (this.scopes.at(-1)?.generator && ts.isBinaryExpression(e)) {
            const k = ts.SyntaxKind;
            const operator = e.operatorToken.kind;
            let right = e.right;
            while (ts.isParenthesizedExpression(right)) right = right.expression;
            if ((operator === k.AmpersandAmpersandToken || operator === k.BarBarToken) && ts.isCallExpression(right) && this.waitsHere(right)) {
                const left = this.fresh('c');
                this.emit(`${left} = ${this.expr(e.left)}`);
                this.emit(operator === k.AmpersandAmpersandToken ? `if not (${left}):` : `if ${left}:`);
                this.emit(`    return ${left}`);
                const name = this.fresh('result');
                this.emit(`${name} = yield from ${this.expr(right)}`);
                this.emit(`return ${name}`);
                return;
            }
        }
        this.emit(`return ${this.expr(e)}`);
    }

    private ifStatement(node: Node, elif: boolean): void {
        this.emit(`${elif ? 'elif' : 'if'} ${this.condition(node.expression)}:`);
        this.block(node.thenStatement);
        const otherwise = node.elseStatement;
        if (!otherwise) return;
        if (ts.isIfStatement(otherwise)) {
            // An elif's condition can't take a prelude of its own, so one that needs it nests instead.
            const before = this.prelude.length;
            this.prelude.push([]);
            const condition = this.condition(otherwise.expression);
            const hoisted = this.prelude.pop()!;
            void before;
            if (hoisted.length === 0) {
                this.out.push('    '.repeat(this.depth) + `elif ${condition}:`);
                this.block(otherwise.thenStatement);
                if (otherwise.elseStatement) {
                    this.elseOf(otherwise.elseStatement);
                }
                return;
            }
            this.emit('else:');
            this.depth++;
            this.statement(otherwise);
            this.depth--;
            return;
        }
        this.elseOf(otherwise);
    }

    private elseOf(node: Node): void {
        if (ts.isIfStatement(node)) {
            this.emit('else:');
            this.depth++;
            this.statement(node);
            this.depth--;
            return;
        }
        this.emit('else:');
        this.block(node);
    }

    private forOf(node: Node): void {
        const iterable = node.expression;
        if (ts.isCallExpression(iterable) && ts.isPropertyAccessExpression(iterable.expression) && iterable.expression.expression.getText() === 'Object') {
            const method = iterable.expression.name.text;
            const target = this.bindingTarget(node.initializer);
            const of = this.expr(iterable.arguments[0]);
            const py = method === 'entries' ? `${of}.items()` : method === 'keys' ? `${of}.keys()` : `${of}.values()`;
            this.emit(`for ${target} in ${py}:`);
            this.block(node.statement);
            return;
        }
        const pattern = ts.isVariableDeclarationList(node.initializer) ? node.initializer.declarations[0].name : null;
        if (pattern && ts.isObjectBindingPattern(pattern)) {
            const item = this.fresh('item');
            this.emit(`for ${item} in ${this.iterable(iterable)}:`);
            this.depth++;
            for (const element of pattern.elements) {
                const prop = element.propertyName ? element.propertyName.getText() : element.name.getText();
                this.emit(`${this.bindingTarget(element.name)} = ${item}.${snake(prop)}`);
            }
            this.blockStatements(node.statement);
            this.depth--;
            return;
        }
        this.emit(`for ${this.bindingTarget(node.initializer)} in ${this.iterable(iterable)}:`);
        this.block(node.statement);
    }

    private iterable(e: Node): string {
        const kind = this.collectionKind(e);
        if (kind === 'map') return `${this.expr(e)}.items()`;
        return this.expr(e);
    }

    private forStatement(node: Node): void {
        // for (let i = a; i < b; i++) is a range.
        const init = node.initializer;
        const cond = node.condition;
        const inc = node.incrementor;
        if (init && ts.isVariableDeclarationList(init) && init.declarations.length === 1 && cond && ts.isBinaryExpression(cond) && inc
            && (ts.isPostfixUnaryExpression(inc) || ts.isPrefixUnaryExpression(inc))) {
            const decl = init.declarations[0];
            const name = decl.name.getText();
            const start = decl.initializer ? this.expr(decl.initializer) : '0';
            const up = inc.operator === ts.SyntaxKind.PlusPlusToken;
            if (cond.left.getText() === name) {
                const end = this.expr(cond.right);
                const op = cond.operatorToken.kind;
                const k = ts.SyntaxKind;
                if (up && (op === k.LessThanToken || op === k.LessThanEqualsToken)) {
                    const stop = op === k.LessThanToken ? end : `${end} + 1`;
                    this.emit(`for ${snake(name)} in range(${start === '0' ? '' : start + ', '}${stop}):`);
                    this.block(node.statement);
                    return;
                }
                if (!up && (op === k.GreaterThanEqualsToken || op === k.GreaterThanToken)) {
                    const stop = op === k.GreaterThanEqualsToken ? `${end} - 1` : end;
                    this.emit(`for ${snake(name)} in range(${start}, ${stop}, -1):`);
                    this.block(node.statement);
                    return;
                }
            }
        }
        // for (let i = 0; i < n && more; i++) is a range that stops early.
        if (init && ts.isVariableDeclarationList(init) && init.declarations.length === 1 && cond && ts.isBinaryExpression(cond)
            && cond.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken && ts.isBinaryExpression(cond.left)
            && cond.left.operatorToken.kind === ts.SyntaxKind.LessThanToken && inc && ts.isPostfixUnaryExpression(inc)
            && inc.operator === ts.SyntaxKind.PlusPlusToken) {
            const decl = init.declarations[0];
            const name = decl.name.getText();
            if (cond.left.left.getText() === name && inc.operand.getText() === name) {
                const start = decl.initializer ? this.expr(decl.initializer) : '0';
                this.emit(`for ${snake(name)} in range(${start === '0' ? '' : start + ', '}${this.expr(cond.left.right)}):`);
                this.depth++;
                this.emit(`if not (${this.condition(cond.right)}):`);
                this.emit('    break');
                this.blockStatements(node.statement);
                this.depth--;
                return;
            }
        }
        if (init) {
            if (ts.isVariableDeclarationList(init)) {
                for (const d of init.declarations) this.variable(d, false);
            } else {
                this.expressionStatement(init);
            }
        }
        // Why: a continue would skip an increment at the bottom, so with one in the body it runs at the top of
        // every pass after the first.
        if (inc && containsContinue(node.statement)) {
            const first = this.fresh('first');
            this.emit(`${first} = True`);
            this.emit('while True:');
            this.depth++;
            this.emit(`if not ${first}:`);
            this.depth++;
            this.expressionStatement(inc);
            this.depth--;
            this.emit(`${first} = False`);
            if (cond) {
                this.emit(`if not (${this.condition(cond)}):`);
                this.emit('    break');
            }
            this.blockStatements(node.statement);
            this.depth--;
            return;
        }
        this.emit(`while ${cond ? this.condition(cond) : 'True'}:`);
        this.depth++;
        this.blockStatements(node.statement);
        if (inc) this.expressionStatement(inc);
        this.depth--;
    }

    private tryStatement(node: Node): void {
        this.emit('try:');
        this.block(node.tryBlock);
        if (node.catchClause) {
            const variable = node.catchClause.variableDeclaration;
            this.emit(variable ? `except Exception as ${snake(variable.name.getText())}:` : 'except Exception:');
            this.block(node.catchClause.block);
        } else {
            this.emit('except Exception as e:');
            this.depth++;
            if (node.finallyBlock) this.blockStatements(node.finallyBlock);
            this.emit('raise e');
            this.depth--;
        }
        if (node.finallyBlock) {
            this.emit(this.todo('pocketpy has no finally: this ran on every exit, including a raise and a return', node));
            this.blockStatements(node.finallyBlock);
        }
    }

    private switchStatement(node: Node): void {
        const subject = this.expr(node.expression);
        const holder = /^[\w.]+$/.test(subject) ? subject : this.fresh('case');
        if (holder !== subject) this.emit(`${holder} = ${subject}`);
        let first = true;
        let pending: string[] = [];
        for (const clause of node.caseBlock.clauses) {
            const isDefault = ts.isDefaultClause(clause);
            if (!isDefault) pending.push(this.expr(clause.expression));
            if (clause.statements.length === 0 && !isDefault) continue;
            const body = clause.statements.filter((s: Node) => !ts.isBreakStatement(s));
            if (isDefault) {
                this.emit(first ? 'if True:' : 'else:');
            } else {
                const test = pending.length === 1 ? `${holder} == ${pending[0]}` : `${holder} in [${pending.join(', ')}]`;
                this.emit(`${first ? 'if' : 'elif'} ${test}:`);
            }
            this.depth++;
            const before = this.out.length;
            for (const statement of body) {
                if (ts.isBlock(statement)) {
                    for (const s of statement.statements) {
                        if (!ts.isBreakStatement(s)) this.statement(s);
                    }
                } else {
                    this.statement(statement);
                }
            }
            if (this.out.length === before) this.emit('pass');
            this.depth--;
            first = false;
            pending = [];
        }
    }

    // -- Functions and classes

    private functionDeclaration(node: Node, top: boolean): void {
        if (!node.name) return;
        const name = this.valueName(node.name.text);
        if (top && hasExport(node)) this.exported.push(name);
        this.docstringBefore = node;
        this.functionLike(name, node, false);
    }

    private docstringBefore: Node | null = null;

    private functionLike(name: string, node: Node, method: boolean, decorators: string[] = []): void {
        const generator = isAsync(node);
        const options = this.optionsParameter(node);
        if (options) this.expanded.set(name, [...this.leadingParams(node), ...options.params]);
        const params = this.parameters(node, method, options);
        for (const decorator of decorators) this.emit(decorator);
        this.emit(`def ${name}(${params.join(', ')}):`);
        this.depth++;
        const docFrom = this.docstringBefore ?? node;
        this.docstringBefore = null;
        this.docstring(docFrom);
        this.scopes.push({ options, generator, inClass: method ? (this.currentClass ?? null) : (this.scopes.at(-1)?.inClass ?? null) });
        const start = this.out.length;
        this.defaults(node, options);
        if (node.body && ts.isBlock(node.body)) {
            for (const statement of node.body.statements) this.statement(statement);
        } else if (node.body) {
            this.withPrelude(() => this.returnStatement({ expression: node.body }));
        } else {
            this.emit(`raise NotImplementedError('${name}')`);
        }
        const body = this.out.slice(start).join('\n');
        if (generator && !/\byield\b/.test(body)) {
            this.emit('if False:');
            this.emit('    yield');
            this.emit(this.todo('async without an await: a generator for its callers, who yield from it'));
        }
        if (this.out.length === start) this.emit('pass');
        this.scopes.pop();
        this.depth--;
        this.emit('');
    }

    private leadingParams(node: Node): Param[] {
        return node.parameters.slice(0, -1).map((p: Node) => ({ name: ts.isIdentifier(p.name) ? this.valueName(p.name.text) : '_', optional: !!(p.questionToken || p.initializer) }));
    }

    // A last parameter typed as a plain object (an interface or a literal type of data, not a class) becomes a
    // parameter for each property, when the body only reads its properties: the stdlib takes parameters
    // where rs2b0t takes an options object.
    private optionsParameter(node: Node): Options | null {
        const last = node.parameters?.at(-1);
        if (!last || !ts.isIdentifier(last.name) || last.dotDotDotToken) return null;
        const type = checker.getNonNullableType(checker.getTypeAtLocation(last));
        const symbol = type.getSymbol?.() ?? type.symbol;
        if (!symbol || symbol.flags & ts.SymbolFlags.Class || checker.isArrayType?.(type) || type.getCallSignatures?.().length) return null;
        if (!(symbol.flags & (ts.SymbolFlags.Interface | ts.SymbolFlags.TypeLiteral))) return null;
        const props = checker.getPropertiesOfType(type);
        if (props.length === 0 || props.length > 12) return null;
        if (props.some((p: any) => {
            const decl = p.valueDeclaration;
            return !decl || ts.isMethodSignature(decl) || ts.isMethodDeclaration(decl);
        })) return null;
        if (node.parameters.slice(0, -1).some((p: Node) => p.questionToken || p.initializer) && props.some((p: any) => !(p.flags & ts.SymbolFlags.Optional))) return null;
        const name = last.name.text;
        let onlyProps = true;
        const visit = (n: Node): void => {
            if (ts.isIdentifier(n) && n.text === name && n !== last.name) {
                const parent = n.parent;
                if (!(ts.isPropertyAccessExpression(parent) && parent.expression === n)) onlyProps = false;
            }
            ts.forEachChild(n, visit);
        };
        if (node.body) visit(node.body);
        if (!onlyProps) return null;
        // A caller passing an object it already has, a Tile say, would need it taken apart at the call, so only
        // a parameter rs2b0t always passes as a literal is spread.
        const fnName = node.name && ts.isIdentifier(node.name) ? node.name.text : ts.isVariableDeclaration(node.parent) ? node.parent.name.getText() : null;
        const index = node.parameters.length - 1;
        if (fnName && callsNamed(fnName).some((c: Node) => c.arguments.length > index && !ts.isObjectLiteralExpression(c.arguments[index]))) return null;
        const optional = (p: any) => !!(p.flags & ts.SymbolFlags.Optional) || !!last.questionToken || !!last.initializer;
        const required = props.filter((p: any) => !optional(p)).map((p: any) => ({ name: snake(p.name), optional: false }));
        const rest = props.filter(optional).map((p: any) => ({ name: snake(p.name), optional: true }));
        return { name, params: [...required, ...rest] };
    }

    private parameters(node: Node, method: boolean, options: Options | null): string[] {
        const out: string[] = method ? ['self'] : [];
        const list = options ? node.parameters.slice(0, -1) : node.parameters;
        for (const p of list) {
            if (p.name.kind === ts.SyntaxKind.ThisKeyword || p.name.getText() === 'this') continue;
            const name = ts.isIdentifier(p.name) ? this.valueName(p.name.text) : this.fresh('arg');
            if (p.dotDotDotToken) {
                out.push(`*${name}`);
                continue;
            }
            const optional = p.questionToken || p.initializer;
            const literal = p.initializer ? literalDefault(p.initializer) : null;
            out.push(optional ? `${name}=${literal ?? 'None'}` : name);
        }
        if (options) {
            for (const prop of options.params) out.push(prop.optional ? `${prop.name}=None` : prop.name);
        }
        return out;
    }

    // Defaults that aren't literals, and destructured parameters, are set at the top of the body.
    private defaults(node: Node, options: Options | null): void {
        const list = options ? node.parameters.slice(0, -1) : node.parameters;
        for (const p of list) {
            if (ts.isObjectBindingPattern(p.name) || ts.isArrayBindingPattern(p.name)) {
                this.emit(this.todo('a destructured parameter', p));
                continue;
            }
            if (p.initializer && literalDefault(p.initializer) === null) {
                const name = this.valueName(p.name.text);
                this.emit(`if ${name} is None:`);
                this.depth++;
                this.withPrelude(() => this.emit(`${name} = ${this.expr(p.initializer)}`));
                this.depth--;
            }
        }
    }

    private currentClass: string | null = null;

    private classDeclaration(node: Node): void {
        const name = node.name ? node.name.text : this.fresh('Class');
        if (hasExport(node)) this.exported.push(name);
        const heritage = (node.heritageClauses ?? []).find((h: Node) => h.token === ts.SyntaxKind.ExtendsKeyword);
        const base = heritage ? heritage.types[0].expression.getText() : null;
        const previous = this.currentClass;
        this.currentClass = name;
        this.emit(base ? `class ${name}(${this.valueName(base)}):` : `class ${name}:`);
        this.depth++;
        this.docstring(node);
        const start = this.out.length;
        const instanceFields: Node[] = [];
        for (const member of node.members) {
            if (ts.isPropertyDeclaration(member)) {
                const isStatic = (member.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.StaticKeyword);
                const init = member.initializer;
                if (isStatic || !init || literalDefault(init) !== null) {
                    this.comments(member);
                    this.withPrelude(() => this.emit(`${this.memberDeclName(member)} = ${init ? this.expr(init) : 'None'}`));
                } else {
                    instanceFields.push(member);
                }
            }
        }
        const ctor = node.members.find((m: Node) => ts.isConstructorDeclaration(m));
        if (ctor || instanceFields.length > 0 || ctorParameterProperties(ctor).length > 0) {
            this.emit('');
            this.constructorDeclaration(ctor, instanceFields, base);
        }
        for (const member of node.members) {
            if (ts.isMethodDeclaration(member)) {
                this.emit('');
                this.comments(member);
                const method = this.methodName(member.name.getText(), base);
                // A private method is called as memberName() names it, with a leading _.
                const isPrivate = (member.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.PrivateKeyword);
                const methodName = method !== null && isPrivate && !method.startsWith('_') ? `_${method}` : method;
                if (methodName === null) {
                    this.emit(this.todo(`${member.name.getText()} left out: paint and the panel aren't headless`));
                    continue;
                }
                const isStatic = (member.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.StaticKeyword);
                const isAbstract = (member.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.AbstractKeyword);
                if (isAbstract && !member.body) {
                    this.emit(`def ${methodName}(self):`);
                    this.emit(`    raise NotImplementedError(f'{type(self).__name__} must define ${methodName}()')`);
                    continue;
                }
                this.docstringBefore = member;
                this.functionLike(methodName, member, !isStatic, isStatic ? ['@staticmethod'] : []);
                if (methodName === 'on_stop' && member.parameters.length === 0) {
                    this.patchStopReason();
                }
            } else if (ts.isGetAccessorDeclaration(member)) {
                this.emit('');
                this.docstringBefore = member;
                this.functionLike(this.memberDeclName(member), member, true, ['@property']);
            } else if (ts.isSetAccessorDeclaration(member)) {
                this.emit(this.todo(`a setter for ${member.name.getText()}`, member));
            }
        }
        if (this.out.length === start) this.emit('pass');
        this.depth--;
        this.emit('');
        this.emit('');
        this.currentClass = previous;
    }

    // rs2b0t's onStop() takes nothing; this client's on_stop gets the reason.
    private patchStopReason(): void {
        for (let i = this.out.length - 1; i >= 0; i--) {
            if (/def on_stop\(self\):/.test(this.out[i])) {
                this.out[i] = this.out[i].replace('def on_stop(self):', 'def on_stop(self, reason=None):');
                return;
            }
        }
    }

    private methodName(name: string, base: string | null): string | null {
        if (name === 'onPaint' || name === 'paintControls') return null;
        if (name === 'constructor') return '__init__';
        const renamed = MEMBER_RENAMES[this.currentClass ?? '']?.[name];
        return renamed ?? snake(name.replace(/^#/, '_'));
    }

    private memberDeclName(member: Node): string {
        const raw = member.name.getText();
        const isPrivate = raw.startsWith('#') || (member.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.PrivateKeyword);
        const name = snake(raw.replace(/^#/, ''));
        return isPrivate && !name.startsWith('_') ? `_${name}` : name;
    }

    private constructorDeclaration(ctor: Node | undefined, fields: Node[], base: string | null): void {
        const params = ctor ? this.parameters(ctor, true, null) : ['self'];
        this.emit(`def __init__(${params.join(', ')}):`);
        this.depth++;
        this.scopes.push({ options: null, generator: false, inClass: this.currentClass });
        const start = this.out.length;
        if (ctor) this.defaults(ctor, null);
        for (const p of ctorParameterProperties(ctor)) {
            const name = this.valueName(p.name.getText());
            this.emit(`self.${this.memberDeclName(p)} = ${name}`);
        }
        const superCall = ctor?.body?.statements.find((s: Node) => ts.isExpressionStatement(s) && ts.isCallExpression(s.expression) && s.expression.expression.kind === ts.SyntaxKind.SuperKeyword);
        if (superCall && base) {
            this.emit(`${base}.__init__(self${superCall.expression.arguments.length ? ', ' + this.argList(superCall.expression) : ''})`);
        }
        for (const field of fields) {
            this.comments(field);
            this.withPrelude(() => this.emit(`self.${this.memberDeclName(field)} = ${this.expr(field.initializer)}`));
        }
        for (const statement of ctor?.body?.statements ?? []) {
            if (statement === superCall) continue;
            this.statement(statement);
        }
        if (this.out.length === start) this.emit('pass');
        this.scopes.pop();
        this.depth--;
    }

    private enumDeclaration(node: Node): void {
        this.emit(`class ${node.name.text}:`);
        this.depth++;
        let next = 0;
        for (const member of node.members) {
            const value = member.initializer ? this.expr(member.initializer) : String(next);
            if (!member.initializer || ts.isNumericLiteral(member.initializer)) next = Number(value) + 1;
            this.emit(`${member.name.getText()} = ${value}`);
        }
        this.depth--;
        this.emit('');
    }

    // -- Expressions

    private condition(e: Node): string {
        return this.expr(e);
    }

    // An expression whose own await, at the top, becomes a yield from on this line.
    private awaitedOr(e: Node): string {
        if (ts.isAwaitExpression(e)) {
            const inner = this.awaitTarget(e);
            return inner.wait ? `yield from ${inner.text}` : inner.text;
        }
        return this.expr(e);
    }

    private awaitTarget(e: Node): { text: string; wait: boolean } {
        const inner = e.expression;
        if (ts.isCallExpression(inner) && inner.expression.getText() === 'Promise.all' && inner.arguments.length === 1) {
            const all = this.fresh('all');
            this.pre(`${all} = []`);
            this.pre(`for _g in ${this.expr(inner.arguments[0])}:`);
            this.pre('    _r = yield from _g');
            this.pre(`    ${all}.append(_r)`);
            this.flag('Promise.all ran these at once; here they run one after another', e);
            return { text: all, wait: false };
        }
        const text = this.expr(inner);
        return { text, wait: this.waitsHere(inner) };
    }

    // Whether this client's version of what the expression calls waits, so the call must be yielded from.
    private waitsHere(e: Node): boolean {
        let call = e;
        while (ts.isParenthesizedExpression(call)) call = call.expression;
        if (!ts.isCallExpression(call)) {
            return this.isPromise(checker.getTypeAtLocation(e));
        }
        const stub = this.stubFor(call);
        if (stub) return stub.wait;
        return this.isPromise(checker.getTypeAtLocation(call));
    }

    private returnsPromise(call: Node): boolean {
        return this.isPromise(checker.getTypeAtLocation(call));
    }

    private isPromise(type: any): boolean {
        if (!type) return false;
        if (type.isUnion && type.isUnion()) return type.types.some((t: any) => this.isPromise(t));
        const symbol = type.getSymbol?.() ?? type.symbol;
        return symbol?.name === 'Promise';
    }

    private stubFor(call: Node): StubFunction | undefined {
        const callee = call.expression;
        if (ts.isPropertyAccessExpression(callee)) {
            const method = this.memberName(callee);
            const owner = callee.expression;
            if (ts.isIdentifier(owner)) {
                const found = stubs.method(this.identifier(owner), method);
                if (found) return found;
            }
            const typeName = this.typeName(owner);
            if (typeName) {
                return stubs.method(typeName, method) ?? stubs.method(`_${typeName}`, method);
            }
            return undefined;
        }
        if (ts.isIdentifier(callee)) {
            return stubs.functions.get(this.valueName(callee.text));
        }
        return undefined;
    }

    private typeName(e: Node): string | null {
        const type = checker.getNonNullableType(checker.getTypeAtLocation(e));
        const symbol = type?.getSymbol?.() ?? type?.symbol;
        return symbol ? symbol.name : null;
    }

    // What kind of collection a value is, from its type: 'array', 'set', 'map', 'string' or null.
    private collectionKind(e: Node): string | null {
        const type = checker.getNonNullableType(checker.getTypeAtLocation(e));
        if (!type) return null;
        if (type.flags & ts.TypeFlags.StringLike) return 'string';
        if (checker.isArrayType?.(type) || checker.isTupleType?.(type)) return 'array';
        const name = (type.getSymbol?.() ?? type.symbol)?.name;
        if (name === 'Array' || name === 'ReadonlyArray') return 'array';
        if (name === 'Set' || name === 'ReadonlySet') return 'set';
        if (name === 'Map' || name === 'ReadonlyMap') return 'map';
        if (type.isUnion?.()) {
            const kinds = new Set(type.types.map((t: any) => (t.flags & ts.TypeFlags.StringLike ? 'string' : checker.isArrayType?.(t) ? 'array' : null)));
            if (kinds.size === 1) return [...kinds][0] as string | null;
        }
        return null;
    }

    // An object typed by an index signature is a dict; one typed by an interface, a Record.
    private isDictLike(e: Node): boolean {
        const type = checker.getNonNullableType(checker.getTypeAtLocation(e));
        if (!type) return false;
        return !!(checker.getIndexInfoOfType?.(type, ts.IndexKind.String) ?? type.getStringIndexType?.());
    }

    private valueName(name: string, _?: unknown): string {
        if (name === 'undefined') return 'None';
        if (OBJECT_NAMES[name]) return OBJECT_NAMES[name];
        const py = snake(name);
        return SHADOWED.has(py) ? py + '_' : py;
    }

    // A name read in an expression: a facade object is its lower-case instance, a class keeps its name.
    private identifier(node: Node): string {
        const text = node.text;
        if (text === 'undefined') return 'None';
        if (text === 'NaN') return "float('nan')";
        if (text === 'Infinity') return "float('inf')";
        const scope = this.scopes.at(-1);
        if (OBJECT_NAMES[text]) return OBJECT_NAMES[text];
        if (/^[A-Z][a-z]/.test(text)) {
            const symbol = this.aliased(checker.getSymbolAtLocation(node));
            if (symbol && symbol.flags & ts.SymbolFlags.Variable && !(symbol.flags & ts.SymbolFlags.Class)) {
                const decl = symbol.valueDeclaration;
                // A const object with methods is one of rs2b0t's facades.
                if (decl && ts.isVariableDeclaration(decl)) return facade(text);
            }
            return text;
        }
        void scope;
        const py = snake(text);
        return SHADOWED.has(py) && this.isLocal(node) ? py + '_' : py;
    }

    // A variable or parameter of the code being translated, rather than a global such as JavaScript's own.
    private isLocal(node: Node): boolean {
        const symbol = checker.getSymbolAtLocation(node);
        const decl = symbol?.valueDeclaration;
        return !!decl && decl.getSourceFile() === this.sf;
    }

    private memberName(access: Node): string {
        const name = access.name.text ?? access.name.getText();
        const owner = access.expression.getText();
        const renamed = MEMBER_RENAMES[owner]?.[name];
        if (renamed) return renamed;
        if (name.startsWith('#')) return '_' + snake(name.slice(1));
        const symbol = checker.getSymbolAtLocation(access.name);
        const decl = symbol?.valueDeclaration;
        if (decl && (decl.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.PrivateKeyword)) {
            const own = snake(name);
            return own.startsWith('_') ? own : '_' + own;
        }
        if (/^[A-Z]/.test(name) && name.toUpperCase() !== name) return name;
        return snake(name);
    }

    private expr(e: Node): string {
        const k = ts.SyntaxKind;
        switch (e.kind) {
            case k.Identifier:
                return this.identifier(e);
            case k.PrivateIdentifier:
                return '_' + snake(e.text.slice(1));
            case k.ThisKeyword:
                return 'self';
            case k.SuperKeyword:
                return 'super()';
            case k.NullKeyword:
                return 'None';
            case k.TrueKeyword:
                return 'True';
            case k.FalseKeyword:
                return 'False';
            case k.NumericLiteral:
                return e.getText().replace(/_/g, '');
            case k.BigIntLiteral:
                return e.getText().replace(/n$/, '');
            case k.StringLiteral:
            case k.NoSubstitutionTemplateLiteral:
                return pyString(e.text);
            case k.TemplateExpression:
                return this.template(e);
            case k.RegularExpressionLiteral:
                this.flag(`a regular expression, ${e.getText()}; pocketpy has no re`, e);
                return pyString(e.getText());
            case k.ParenthesizedExpression:
                return `(${this.expr(e.expression)})`;
            case k.AsExpression:
            case k.SatisfiesExpression:
            case k.TypeAssertionExpression:
            case k.NonNullExpression:
                return this.expr(e.expression);
            case k.AwaitExpression:
                return this.hoistAwait(e);
            case k.PropertyAccessExpression:
                return this.propertyAccess(e);
            case k.ElementAccessExpression:
                return this.elementAccess(e);
            case k.CallExpression:
                return this.call(e);
            case k.NewExpression:
                return this.newExpression(e);
            case k.BinaryExpression:
                return this.binary(e);
            case k.PrefixUnaryExpression:
                return this.prefix(e);
            case k.PostfixUnaryExpression: {
                // x++ in an expression gives x, then counts: held before the statement, where it runs first.
                const operand = this.expr(e.operand);
                if (hoistable(e) && !hasConditionalAncestor(e)) {
                    const held = this.fresh('v');
                    this.pre(`${held} = ${operand}`);
                    this.pre(`${operand} ${e.operator === k.PlusPlusToken ? '+=' : '-='} 1`);
                    return held;
                }
                this.flag('an increment inside an expression', e);
                return operand;
            }
            case k.ConditionalExpression:
                if (this.awaitsWithin(e.whenTrue) || this.awaitsWithin(e.whenFalse)) {
                    const holder = this.fresh('c');
                    this.pre(`if ${this.expr(e.condition)}:`);
                    const yes = this.nested(() => this.expr(e.whenTrue));
                    for (const line of yes.lines) this.pre(`    ${line}`);
                    this.pre(`    ${holder} = ${yes.value}`);
                    this.pre('else:');
                    const no = this.nested(() => this.expr(e.whenFalse));
                    for (const line of no.lines) this.pre(`    ${line}`);
                    this.pre(`    ${holder} = ${no.value}`);
                    return holder;
                }
                {
                    // Why: a lambda takes everything after its colon, so (lambda: a if c else None) is always a lambda.
                    const branch = (node: Node): string => {
                        const text = this.expr(node);
                        return text.startsWith('lambda') ? `(${text})` : text;
                    };
                    return `(${branch(e.whenTrue)} if ${this.expr(e.condition)} else ${branch(e.whenFalse)})`;
                }
            case k.ArrowFunction:
            case k.FunctionExpression:
                return this.arrow(e);
            case k.ObjectLiteralExpression:
                return this.objectLiteral(e);
            case k.ArrayLiteralExpression:
                return this.arrayLiteral(e);
            case k.TypeOfExpression:
                this.flag('typeof outside a comparison', e);
                return `type(${this.expr(e.expression)}).__name__`;
            case k.VoidExpression:
                return 'None';
            case k.SpreadElement:
                return `*${this.expr(e.expression)}`;
            case k.TaggedTemplateExpression:
                this.flag('a tagged template', e);
                return 'None';
            case k.ClassExpression:
                this.flag('a class expression; classes go at module level in pocketpy', e);
                return 'None';
            default:
                this.flag(`a ${k[e.kind]}`, e);
                return 'None';
        }
    }

    // Whether the expression awaits a call that waits here, outside any function inside it.
    private awaitsWithin(e: Node): boolean {
        let found = false;
        const visit = (n: Node): void => {
            if (found || ts.isFunctionLike(n)) return;
            if (ts.isAwaitExpression(n) && this.waitsHere(n.expression)) {
                found = true;
                return;
            }
            ts.forEachChild(n, visit);
        };
        visit(e);
        return found;
    }

    // Translates an expression with a prelude of its own, given back as lines rather than emitted.
    // The operands being translated under an if of their own, as a short circuit's right side is: a condition
    // above one of them no longer decides whether what's inside runs.
    private guards: Node[] = [];

    private nested(fn: () => string): { lines: string[]; value: string } {
        this.prelude.push([]);
        const value = fn();
        // A lifted def keeps its body's indentation, less the statement's own.
        const indent = '    '.repeat(this.depth);
        const lines = this.prelude.pop()!.map(line => (line.startsWith('\n') ? line.slice(1 + indent.length) : line));
        return { lines, value };
    }

    private hoistAwait(e: Node): string {
        const inner = this.awaitTarget(e);
        if (!inner.wait) return inner.text;
        const name = this.fresh('w');
        if (hasConditionalAncestor(e, this.guards.at(-1))) {
            this.flag('this await was inside a condition, and now always runs first', e);
        }
        this.pre(`${name} = yield from ${inner.text}`);
        return name;
    }

    private template(e: Node): string {
        const parts: string[] = [e.head.text];
        const exprs: string[] = [];
        for (const span of e.templateSpans) {
            exprs.push(this.expr(span.expression));
            parts.push(span.literal.text);
        }
        const literalText = parts.join('');
        const usesBraces = /[{}]/.test(literalText);
        const quote = exprs.some(x => x.includes("'")) ? '"' : "'";
        if (usesBraces || exprs.some(x => x.includes(quote))) {
            const pieces: string[] = [];
            parts.forEach((p, i) => {
                if (p) pieces.push(pyString(p));
                if (i < exprs.length) pieces.push(`str(${exprs[i]})`);
            });
            return pieces.join(' + ') || "''";
        }
        let out = 'f' + quote;
        parts.forEach((p, i) => {
            out += escapeFor(p, quote);
            if (i < exprs.length) out += `{${exprs[i]}}`;
        });
        return out + quote;
    }

    private propertyAccess(e: Node): string {
        const owner = e.expression;
        const name = e.name.text;
        const ownerText = this.expr(owner);
        const optional = !!e.questionDotToken;
        const kind = this.collectionKind(owner);
        let text: string;
        if (name === 'length' && (kind === 'array' || kind === 'string' || kind === null)) {
            text = `len(${ownerText})`;
        } else if (name === 'size' && (kind === 'set' || kind === 'map')) {
            text = `len(${ownerText})`;
        } else if (owner.getText() === 'Number' && name === 'MAX_SAFE_INTEGER') {
            text = '9007199254740991';
        } else if (owner.getText() === 'Number' && name === 'POSITIVE_INFINITY') {
            text = "float('inf')";
        } else if (owner.getText() === 'Math' && name === 'PI') {
            this.needs.add('math');
            text = 'math.pi';
        } else if (this.isDictLike(owner) && !this.declaresProperty(owner, name)) {
            text = `${ownerText}.get(${pyString(name)})`;
        } else {
            if (ts.isIdentifier(owner) && this.optionsNamed(owner.text)) {
                return optional ? `${snake(name)}` : snake(name);
            }
            text = `${ownerText}.${this.memberName(e)}`;
        }
        if (optional) {
            return `(${text} if ${ownerText} is not None else None)`;
        }
        return text;
    }

    private optionsNamed(name: string): boolean {
        for (let i = this.scopes.length - 1; i >= 0; i--) {
            if (this.scopes[i].options?.name === name) return true;
        }
        return false;
    }

    // A member the type marks optional reads with getattr, since a Python object may not have it at all.
    private member(access: Node): string {
        if (ts.isIdentifier(access.expression) && this.optionsNamed(access.expression.text)) {
            return snake(access.name.text);
        }
        const symbol = checker.getSymbolAtLocation(access.name);
        const owner = this.expr(access.expression);
        if (symbol && symbol.flags & ts.SymbolFlags.Optional && !this.isDictLike(access.expression)) {
            return `getattr(${owner}, '${this.memberName(access)}', None)`;
        }
        return `${owner}.${this.memberName(access)}`;
    }

    private declaresProperty(owner: Node, name: string): boolean {
        const type = checker.getNonNullableType(checker.getTypeAtLocation(owner));
        return !!type?.getProperty?.(name);
    }

    private elementAccess(e: Node): string {
        const owner = this.expr(e.expression);
        const index = this.expr(e.argumentExpression);
        const kind = this.collectionKind(e.expression);
        const write = isWriteTarget(e);
        if (!write && kind !== 'array' && kind !== 'string' && this.isDictLike(e.expression)) {
            return `${owner}.get(${index})`;
        }
        // The first of an array made here, sorted or filtered, is undefined in JavaScript when it's empty.
        if (!write && kind === 'array' && ts.isCallExpression(e.expression) && index === '0') {
            return `(${owner} or [None])[0]`;
        }
        return `${owner}[${index}]`;
    }

    private argList(call: Node, target?: Param[]): string {
        const items: string[] = [];
        const args = call.arguments ?? [];
        args.forEach((a: Node, i: number) => {
            if (i === args.length - 1 && ts.isObjectLiteralExpression(a) && target && this.allKeys(a, target.slice(i))) {
                items.push(...this.spreadArgs(a, target.slice(i)));
            } else {
                items.push(this.expr(a));
            }
        });
        return items.join(', ');
    }

    private allKeys(o: Node, params: Param[]): boolean {
        const names = params.map(p => p.name);
        return o.properties.length > 0 && o.properties.every((p: Node) => (ts.isPropertyAssignment(p) || ts.isShorthandPropertyAssignment(p)) && names.includes(snake(p.name.getText())));
    }

    // pocketpy takes a parameter by keyword only when it has a default, so the required ones go by position.
    private spreadArgs(o: Node, params: Param[]): string[] {
        const values = new Map<string, string>();
        for (const p of o.properties) {
            values.set(snake(p.name.getText()), ts.isShorthandPropertyAssignment(p) ? this.identifier(p.name) : this.expr(p.initializer));
        }
        const out: string[] = [];
        for (const param of params.filter(p => !p.optional)) {
            out.push(values.get(param.name) ?? 'None');
            values.delete(param.name);
        }
        for (const [key, value] of values) out.push(`${key}=${value}`);
        return out;
    }

    private call(e: Node): string {
        const callee = e.expression;
        const optionalCall = !!e.questionDotToken;
        const special = this.tentative(() => this.builtinCall(e));
        if (special !== null) {
            // Why: x?.toLowerCase() is a JavaScript method, which builtinCall translates without its ?. guard.
            if (ts.isPropertyAccessExpression(callee) && callee.questionDotToken) {
                return `(${special} if ${this.expr(callee.expression)} is not None else None)`;
            }
            return special;
        }
        const stub = this.stubFor(e);
        let params: Param[] | undefined = stub?.params;
        if (!params && ts.isIdentifier(callee)) {
            params = this.expanded.get(this.valueName(callee.text));
        }
        if (ts.isPropertyAccessExpression(callee) && callee.expression.getText() === 'ScriptRunner') {
            const method = callee.name.text;
            if (method === 'stop') {
                return this.scopes.at(-1)?.inClass ? `self.request_finish(${this.argList(e)})` : 'stop_script()';
            }
            if (method === 'paintControls') return 'None';
            this.flag(`ScriptRunner.${method}`, e);
            return 'None';
        }
        if (ts.isPropertyAccessExpression(callee) && callee.name.text === 'each' && /^(test|it)$/.test(callee.expression.getText())) {
            return `test_each(${this.argList(e)})`;
        }
        if (ts.isPropertyAccessExpression(callee) && callee.name.text === 'on' && e.arguments.length === 2 && ts.isStringLiteral(e.arguments[0])) {
            return `${this.expr(callee.expression)}.on(${pyString(eventName(e.arguments[0].text))}, ${this.expr(e.arguments[1])})`;
        }
        if (ts.isPropertyAccessExpression(callee) && /^(bool|num|str|list|tile|raw)$/.test(callee.name.text) && /settings$/.test(callee.expression.getText()) && e.arguments.length > 0 && ts.isStringLiteral(e.arguments[0])) {
            const rest = e.arguments.slice(1).map((a: Node) => this.expr(a));
            return `${this.expr(callee.expression)}.${callee.name.text}(${[pyString(snake(e.arguments[0].text)), ...rest].join(', ')})`;
        }
        const fn = optionalCall && ts.isPropertyAccessExpression(callee) ? this.member(callee) : this.expr(callee);
        if (optionalCall && !/^[\w.]+$/.test(fn)) {
            const holder = this.fresh('fn');
            this.pre(`${holder} = ${fn}`);
            return `(${holder}(${this.argList(e, params)}) if ${holder} is not None else None)`;
        }
        const text = `${fn}(${this.argList(e, params)})`;
        if (optionalCall) return `(${text} if ${fn} is not None else None)`;
        return text;
    }

    // Calls of JavaScript's own functions and methods, as Python's.
    private builtinCall(e: Node): string | null {
        const callee = e.expression;
        const args = e.arguments.map((a: Node) => this.expr(a));
        if (ts.isIdentifier(callee)) {
            switch (callee.text) {
                case 'String':
                    return `str(${args[0] ?? "''"})`;
                case 'Number':
                    this.flag('Number(): int or float?', e);
                    return `float(${args[0]})`;
                case 'Boolean':
                    return `bool(${args[0]})`;
                case 'parseInt':
                    return `int(${args[0]})`;
                case 'parseFloat':
                    return `float(${args[0]})`;
                case 'isNaN':
                    return `(${args[0]} != ${args[0]})`;
                case 'defineBot':
                    return this.defineBot(e);
            }
            return null;
        }
        if (!ts.isPropertyAccessExpression(callee)) return null;
        const owner = callee.expression;
        const ownerText = owner.getText();
        const method = callee.name.text;
        if (ownerText === 'Math') {
            switch (method) {
                case 'max':
                case 'min':
                    return `${method}(${args.join(', ')})`;
                case 'abs':
                    return `abs(${args[0]})`;
                case 'floor':
                    if (ts.isBinaryExpression(e.arguments[0]) && e.arguments[0].operatorToken.kind === ts.SyntaxKind.SlashToken) {
                        return `(${this.expr(e.arguments[0].left)} // ${this.expr(e.arguments[0].right)})`;
                    }
                    this.needs.add('math');
                    return `math.floor(${args[0]})`;
                case 'ceil':
                case 'sqrt':
                case 'log':
                case 'sin':
                case 'cos':
                case 'atan2':
                case 'exp':
                case 'trunc':
                    this.needs.add('math');
                    return `math.${method}(${args.join(', ')})`;
                case 'round':
                    return `round(${args[0]})`;
                case 'hypot':
                    return `(${args.map(a => `(${a}) ** 2`).join(' + ')}) ** 0.5`;
                case 'pow':
                    return `(${args[0]}) ** (${args[1]})`;
                case 'sign':
                    return `(1 if ${args[0]} > 0 else (-1 if ${args[0]} < 0 else 0))`;
                case 'random':
                    this.needs.add('random');
                    return 'random.random()';
            }
        }
        if (ownerText === 'Number') {
            switch (method) {
                case 'isFinite':
                    return `(isinstance(${args[0]}, int) or isinstance(${args[0]}, float))`;
                case 'isInteger':
                    return `isinstance(${args[0]}, int)`;
                case 'parseInt':
                    return `int(${args[0]})`;
                case 'isNaN':
                    return `(${args[0]} != ${args[0]})`;
            }
        }
        if (ownerText === 'Object') {
            switch (method) {
                case 'keys':
                    return `list(${args[0]}.keys())`;
                case 'values':
                    return `list(${args[0]}.values())`;
                case 'entries':
                    return `list(${args[0]}.items())`;
                case 'fromEntries':
                    return `{_k: _v for _k, _v in ${args[0]}}`;
                case 'freeze':
                    return args[0];
            }
            if (method === 'hasOwn' && args.length === 2) return `(${args[1]} in ${args[0]})`;
            if (method === 'assign' && args.length === 2) {
                this.pre(`for _k, _v in (${args[1]}).items():`);
                this.pre(`    ${args[0]}[_k] = _v`);
                return args[0];
            }
            this.flag(`Object.${method}`, e);
            return 'None';
        }
        if (ownerText === 'JSON') {
            this.needs.add('json');
            return method === 'stringify' ? `json.dumps(${args[0]})` : `json.loads(${args[0]})`;
        }
        if (ownerText === 'Array' && method === 'isArray') return `isinstance(${args[0]}, list)`;
        if (ownerText === 'Array' && method === 'from' && args.length === 1) return `list(${args[0]})`;
        if (ownerText === 'console') return `log(${args.join(', ')})`;
        if ((ownerText === 'Date' || ownerText === 'performance') && method === 'now') {
            this.needs.add('_core');
            return '_core.step_time()';
        }
        if (ownerText === 'Promise') {
            this.flag(`Promise.${method}`, e);
            return 'None';
        }

        const kind = this.collectionKind(owner);
        const of = this.expr(owner);
        const fn = e.arguments[0];
        if (kind === 'string') {
            switch (method) {
                case 'toLowerCase':
                    return `${of}.lower()`;
                case 'toUpperCase':
                    return `${of}.upper()`;
                case 'trim':
                    return `${of}.strip()`;
                case 'trimStart':
                    return `${of}.lstrip()`;
                case 'trimEnd':
                    return `${of}.rstrip()`;
                case 'startsWith':
                    return `${of}.startswith(${args[0]})`;
                case 'endsWith':
                    return `${of}.endswith(${args[0]})`;
                case 'includes':
                    return `(${args[0]} in ${of})`;
                case 'indexOf':
                    return `${of}.find(${args.join(', ')})`;
                case 'split':
                    if (ts.isRegularExpressionLiteral(fn)) {
                        if (/^\/\\s[+*]\/$/.test(fn.getText())) return `${of}.split()`;
                        const plain = regexAsText(fn.getText());
                        if (plain && !plain.anchored) return `${of}.split(${pyString(plain.text)})`;
                        this.flag(`split on a regular expression, ${fn.getText()}`, e);
                        return `${of}.split()`;
                    }
                    return `${of}.split(${args[0]})`;
                case 'replace':
                case 'replaceAll':
                    if (ts.isRegularExpressionLiteral(fn)) return this.regexReplace(of, fn, args[1], e);
                    if (method === 'replace') this.flag('replace: rs2b0t replaced only the first', e);
                    return `${of}.replace(${args[0]}, ${args[1]})`;
                case 'slice':
                case 'substring':
                    return `${of}[${args[0] ?? ''}:${args[1] ?? ''}]`;
                case 'charAt':
                    return `${of}[${args[0]}]`;
                case 'padStart':
                    return `${of}.rjust(${args.join(', ')})`;
                case 'padEnd':
                    return `${of}.ljust(${args.join(', ')})`;
                case 'repeat':
                    return `(${of} * ${args[0]})`;
                case 'localeCompare':
                    return `((${of} > ${args[0]}) - (${of} < ${args[0]}))`;
                case 'match':
                case 'test':
                case 'search':
                    this.flag(`String.${method} needs a regular expression: ${e.getText()}`, e);
                    return 'None';
            }
        }
        if (ts.isRegularExpressionLiteral(owner) && method === 'test') {
            const test = regexTest(owner.getText(), args[0]);
            if (test) return test;
            this.flag(`a regular expression test: ${owner.getText()}`, e);
            return 'False';
        }
        if (kind === 'array' || kind === null) {
            const lambda = fn && (ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) && !ts.isBlock(fn.body) ? fn : null;
            // A destructured parameter, ([name, runes]) =>, is a tuple in the comprehension.
            const first = lambda?.parameters[0]?.name;
            const bound = first ? this.bindingTarget(first) : '_x';
            // pocketpy can't parse a loop target in brackets, so the loop's tuple is bare (for name, runes in ...) and
            // only the value it gives is bracketed.
            const target = bound;
            const item = bound.includes(',') ? `(${bound})` : bound;
            // Why: ([needle]) => binds the element's first entry, which a bare name would read as the whole element.
            if (first && ts.isArrayBindingPattern(first) && !bound.includes(',')) {
                this.flag(`a one-element destructured parameter: ${bound} is the element here, not its first entry`, e);
            }
            const index = lambda?.parameters[1] ? this.bindingTarget(lambda.parameters[1].name) : null;
            const loop = index ? `for ${index}, ${item} in enumerate(${of})` : `for ${target} in ${of}`;
            const body = lambda ? this.expr(lambda.body) : fn ? `${this.expr(fn)}(${item})` : item;
            switch (method) {
                case 'map':
                    if (kind === 'array' || lambda) return `[${body} ${loop}]`;
                    break;
                case 'filter':
                    if (kind === 'array' || lambda) return fn?.getText() === 'Boolean' ? `[${item} for ${target} in ${of} if ${item}]` : `[${item} ${loop} if ${body}]`;
                    break;
                case 'find':
                    if (kind === 'array' || lambda) return `([${item} ${loop} if ${body}] or [None])[0]`;
                    break;
                case 'findIndex':
                    if (kind === 'array' || lambda) return `([${index ?? '_i'} for ${index ?? '_i'}, ${item} in enumerate(${of}) if ${body}] or [-1])[0]`;
                    break;
                case 'some':
                    if (kind === 'array' || lambda) return `any([${body} ${loop}])`;
                    break;
                case 'every':
                    if (kind === 'array' || lambda) return `all([${body} ${loop}])`;
                    break;
                case 'flatMap':
                    if (kind === 'array' || lambda) {
                        const flat = this.fresh('flat');
                        this.pre(`${flat} = []`);
                        this.pre(`${loop}:`);
                        this.pre(`    ${flat}.extend(${body})`);
                        return flat;
                    }
                    break;
                case 'includes':
                    if (kind === 'array') return `(${args[0]} in ${of})`;
                    break;
                case 'indexOf':
                    if (kind === 'array') return `(${of}.index(${args[0]}) if ${args[0]} in ${of} else -1)`;
                    break;
                case 'join':
                    if (kind === 'array') return `${args[0] ?? "','"}.join(${of})`;
                    break;
                case 'slice':
                    if (kind === 'array') return `${of}[${args[0] ?? ''}:${args[1] ?? ''}]`;
                    break;
                case 'concat':
                    if (kind === 'array') return [of, ...args].map(a => `list(${a})`).join(' + ');
                    break;
                case 'fill': {
                    // Array(n).fill(v), rs2b0t's tests' list of n copies.
                    const owner = callee.expression;
                    if ((ts.isCallExpression(owner) || ts.isNewExpression(owner)) && owner.expression.getText() === 'Array' && owner.arguments?.length === 1 && args.length === 1) {
                        const count = this.expr(owner.arguments[0]);
                        return `[${args[0]}] * ${/^[\w.]+$/.test(count) ? count : `(${count})`}`;
                    }
                    break;
                }
                case 'push':
                    if (kind === 'array' && args.length === 1) return `${of}.append(${args[0]})`;
                    break;
                case 'pop':
                    if (kind === 'array') return `${of}.pop()`;
                    break;
                case 'shift':
                    if (kind === 'array') return `${of}.pop(0)`;
                    break;
                case 'unshift':
                    if (kind === 'array') return `${of}.insert(0, ${args[0]})`;
                    break;
                case 'reverse':
                    if (kind === 'array') return `${of}.reverse()`;
                    break;
                case 'at':
                    if (kind === 'array') return `(${of}[${args[0]}] if len(${of}) > 0 else None)`;
                    break;
                case 'sort':
                    if (kind === 'array') return this.sortCall(of, fn, e);
                    break;
                case 'toSorted':
                    if (kind === 'array') return this.sortCall(`list(${of})`, fn, e);
                    break;
                case 'reduce':
                    return this.reduceCall(of, e);
            }
        }
        if (kind === 'set') {
            switch (method) {
                case 'has':
                    return `(${args[0]} in ${of})`;
                case 'add':
                    return `${of}.add(${args[0]})`;
                case 'delete':
                    return `${of}.discard(${args[0]})`;
                case 'clear':
                    return `${of}.clear()`;
            }
        }
        if (kind === 'map') {
            switch (method) {
                case 'has':
                    return `(${args[0]} in ${of})`;
                case 'get':
                    return `${of}.get(${args[0]})`;
                case 'set':
                    this.flag('Map.set inside an expression', e);
                    return `${of}.__setitem__(${args[0]}, ${args[1]})`;
                case 'delete':
                    return `${of}.pop(${args[0]}, None)`;
                case 'keys':
                    return `list(${of}.keys())`;
                case 'values':
                    return `list(${of}.values())`;
                case 'entries':
                    return `list(${of}.items())`;
                case 'clear':
                    return `${of}.clear()`;
            }
        }
        if (method === 'toFixed') return `f'{${of}:.${args[0] ?? 0}f}'`;
        if (method === 'toString' && args.length === 0) return `str(${of})`;
        return null;
    }

    private sortCall(of: string, fn: Node | undefined, e: Node): string {
        const statement = ts.isExpressionStatement(e.parent);
        if (!fn) return statement ? `${of}.sort()` : `sorted(${of})`;
        const key = comparatorKey(fn, (n: Node) => this.expr(n));
        if (!key) {
            this.flag(`sort by ${fn.getText()}: give a key`, e);
            return statement ? `${of}.sort()` : `sorted(${of})`;
        }
        const keyArg = `key=lambda ${key.param}: ${key.body}${key.reverse ? ', reverse=True' : ''}`;
        return statement ? `${of}.sort(${keyArg})` : `sorted(${of}, ${keyArg})`;
    }

    // reduce((total, x) => total + f(x), 0) is a sum; the rest are loops.
    private reduceCall(of: string, e: Node): string {
        const fn = e.arguments[0];
        const init = e.arguments[1];
        if (fn && ts.isArrowFunction(fn) && !ts.isBlock(fn.body) && fn.parameters.length === 2 && init) {
            const acc = fn.parameters[0].name.getText();
            const body = fn.body;
            if (ts.isBinaryExpression(body) && body.operatorToken.kind === ts.SyntaxKind.PlusToken && body.left.getText() === acc) {
                const item = this.bindingTarget(fn.parameters[1].name);
                const total = `sum([${this.expr(body.right)} for ${item} in ${of}])`;
                return this.expr(init) === '0' ? total : `${this.expr(init)} + ${total}`;
            }
        }
        if (fn && (ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) && fn.parameters.length >= 2 && init) {
            const acc = this.fresh('acc');
            const reducer = this.expr(fn);
            this.pre(`${acc} = ${this.expr(init)}`);
            this.pre(`for _x in ${of}:`);
            this.pre(`    ${acc} = ${reducer}(${acc}, _x)`);
            return acc;
        }
        this.flag('reduce: write the loop', e);
        return 'None';
    }

    private regexReplace(of: string, fn: Node, replacement: string, e: Node): string {
        const plain = regexAsText(fn.getText());
        if (plain && !plain.caseless) {
            const lit = pyString(plain.text);
            const n = plain.text.length;
            const front = replacement === "''" ? '' : `${replacement} + `;
            const back = replacement === "''" ? '' : ` + ${replacement}`;
            if (plain.start && !plain.end) return `(${front}${of}[${n}:] if ${of}.startswith(${lit}) else ${of})`;
            if (plain.end && !plain.start) return `(${of}[:-${n}]${back} if ${of}.endswith(${lit}) else ${of})`;
            if (!plain.anchored) {
                if (!plain.global) this.flag('replace: rs2b0t replaced only the first', e);
                return `${of}.replace(${pyString(plain.text)}, ${replacement})`;
            }
        }
        this.flag(`replace with a regular expression: ${fn.getText()}`, e);
        return of;
    }

    private defineBot(e: Node): string {
        const literal = e.arguments[0];
        if (!literal || !ts.isObjectLiteralExpression(literal)) return `define_bot(${e.arguments.map((a: Node) => this.expr(a)).join(', ')})`;
        const items = literal.properties.map((p: Node) => {
            const key = snake(p.name.getText());
            let value: string;
            if (ts.isPropertyAssignment(p) && key === 'create' && ts.isArrowFunction(p.initializer) && ts.isNewExpression(p.initializer.body) && (p.initializer.body.arguments?.length ?? 0) === 0) {
                value = this.expr(p.initializer.body.expression);
            } else if (ts.isMethodDeclaration(p)) {
                this.flag('a method in define_bot', p);
                value = 'None';
            } else {
                value = ts.isShorthandPropertyAssignment(p) ? this.identifier(p.name) : this.expr(p.initializer);
            }
            return `${key}=${value}`;
        });
        return `define_bot(${items.join(', ')})`;
    }

    private newExpression(e: Node): string {
        const ctor = e.expression.getText();
        const args = (e.arguments ?? []).map((a: Node) => this.expr(a));
        switch (ctor) {
            case 'Set':
                return args.length ? `set(${args[0]})` : 'set()';
            case 'Map':
                return args.length ? `{_k: _v for _k, _v in ${args[0]}}` : '{}';
            case 'Array':
                return args.length ? `[None] * ${args[0]}` : '[]';
            case 'Error':
                return `RuntimeError(${args.join(', ')})`;
            case 'TypeError':
            case 'RangeError':
                return `${ctor === 'RangeError' ? 'ValueError' : 'TypeError'}(${args.join(', ')})`;
            case 'Date':
                this.needs.add('_core');
                this.flag('new Date', e);
                return '_core.step_time()';
            case 'Promise':
                this.flag('new Promise', e);
                return 'None';
        }
        return `${this.expr(e.expression)}(${this.argList(e)})`;
    }

    private errorExpr(e: Node): string {
        return ts.isNewExpression(e) ? this.newExpression(e) : this.expr(e);
    }

    private binary(e: Node): string {
        const k = ts.SyntaxKind;
        const op = e.operatorToken.kind;
        if (isAssignment(op)) {
            this.flag('an assignment inside an expression', e);
            return this.expr(e.left);
        }
        // typeof x === 'string'
        if ((op === k.EqualsEqualsEqualsToken || op === k.ExclamationEqualsEqualsToken || op === k.EqualsEqualsToken || op === k.ExclamationEqualsToken) && ts.isTypeOfExpression(e.left) && ts.isStringLiteral(e.right)) {
            const test = typeTest(this.expr(e.left.expression), e.right.text);
            return op === k.EqualsEqualsEqualsToken || op === k.EqualsEqualsToken ? test : `not ${test}`;
        }
        if ((op === k.AmpersandAmpersandToken || op === k.BarBarToken || op === k.QuestionQuestionToken) && this.awaitsWithin(e.right)) {
            const holder = this.fresh('c');
            this.pre(`${holder} = ${this.expr(e.left)}`);
            const test = op === k.AmpersandAmpersandToken ? holder : op === k.BarBarToken ? `not ${holder}` : `${holder} is None`;
            this.pre(`if ${test}:`);
            this.guards.push(e.right);
            const inner = this.nested(() => this.expr(e.right));
            this.guards.pop();
            for (const line of inner.lines) this.pre(`    ${line}`);
            this.pre(`    ${holder} = ${inner.value}`);
            return holder;
        }
        const left = this.expr(e.left);
        const right = this.expr(e.right);
        const nullish = (n: Node) => n.kind === k.NullKeyword || (ts.isIdentifier(n) && n.text === 'undefined');
        switch (op) {
            case k.EqualsEqualsEqualsToken:
            case k.EqualsEqualsToken:
                if (nullish(e.right)) return `${left} is None`;
                if (nullish(e.left)) return `${right} is None`;
                return `${left} == ${right}`;
            case k.ExclamationEqualsEqualsToken:
            case k.ExclamationEqualsToken:
                if (nullish(e.right)) return `${left} is not None`;
                if (nullish(e.left)) return `${right} is not None`;
                return `${left} != ${right}`;
            case k.AmpersandAmpersandToken:
                return `${left} and ${right}`;
            case k.BarBarToken:
                return `${left} or ${right}`;
            case k.QuestionQuestionToken: {
                // A call on the left is made once: held before the statement, where it runs first anyway.
                if (left.includes('(') && !hasConditionalAncestor(e) && hoistable(e)) {
                    const held = this.fresh('v');
                    this.pre(`${held} = ${left}`);
                    return `(${held} if ${held} is not None else ${right})`;
                }
                return `(${left} if ${left} is not None else ${right})`;
            }
            case k.InstanceOfKeyword:
                return `isinstance(${left}, ${right})`;
            case k.InKeyword:
                return `${left} in ${right}`;
            case k.PlusToken: {
                const stringy = (n: Node) => this.collectionKind(n) === 'string';
                if (stringy(e.left) && !stringy(e.right)) return `${left} + str(${right})`;
                if (stringy(e.right) && !stringy(e.left)) return `str(${left}) + ${right}`;
                return `${left} + ${right}`;
            }
            case k.GreaterThanGreaterThanGreaterThanToken:
                this.flag('>>> is unsigned', e);
                return `${left} >> ${right}`;
            case k.CommaToken:
                this.flag('a comma expression', e);
                return right;
        }
        const text = e.operatorToken.getText();
        return `${left} ${text} ${right}`;
    }

    private prefix(e: Node): string {
        const k = ts.SyntaxKind;
        const operand = this.expr(e.operand);
        switch (e.operator) {
            case k.ExclamationToken:
                return `not ${needsParens(e.operand) ? `(${operand})` : operand}`;
            case k.MinusToken:
                return `-${operand}`;
            case k.PlusToken:
                return operand;
            case k.TildeToken:
                return `~${operand}`;
            case k.PlusPlusToken:
            case k.MinusMinusToken:
                // ++x in an expression counts, then gives x.
                if (hoistable(e) && !hasConditionalAncestor(e)) {
                    this.pre(`${operand} ${e.operator === k.PlusPlusToken ? '+=' : '-='} 1`);
                    return operand;
                }
                this.flag('an increment inside an expression', e);
                return operand;
        }
        return operand;
    }

    private arrow(e: Node): string {
        if (ts.isBlock(e.body) && e.body.statements.length === 0) {
            return 'lambda *_args: None';
        }
        const params = this.parameters(e, false, null).join(', ');
        if (!ts.isBlock(e.body) && !isAsync(e) && literalDefaultsOnly(e)) {
            this.scopes.push({ options: null, generator: false, inClass: this.scopes.at(-1)?.inClass ?? null });
            this.prelude.push([]);
            const body = this.expr(e.body);
            const hoisted = this.prelude.pop()!;
            this.scopes.pop();
            if (hoisted.length === 0) {
                return `lambda${params ? ' ' + params : ''}: ${body}`;
            }
        }
        // A block body, or an async one, becomes a def before the statement.
        const name = this.fresh('fn');
        const saved = this.out;
        const savedDepth = this.depth;
        this.out = [];
        this.depth = 0;
        const prelude = this.prelude;
        this.prelude = [];
        this.functionLike(name, e, false);
        const lines = this.out;
        this.out = saved;
        this.depth = savedDepth;
        this.prelude = prelude;
        for (const line of lines) {
            if (line === '') continue;
            this.pre('\n' + '    '.repeat(this.depth) + line);
        }
        return name;
    }

    private objectLiteral(e: Node): string {
        if (e.properties.length === 0) return this.isDictLike(e) ? '{}' : 'Record({})';
        const dict = this.isDictLike(e);
        if (this.isSettingsSchema(e)) return this.settingsSchema(e);
        if (this.isSettingDef(e)) return this.settingDef(e);
        const items: string[] = [];
        const spreads: string[] = [];
        // In source order, a spread or the properties between spreads, since a later one overrides an earlier.
        const segments: { spread?: string; items?: string[] }[] = [];
        let methods = false;
        for (const p of e.properties) {
            if (ts.isSpreadAssignment(p)) {
                const spread = this.expr(p.expression);
                spreads.push(spread);
                segments.push({ spread });
                continue;
            }
            if (segments.length === 0 || segments[segments.length - 1].spread !== undefined) segments.push({ items: [] });
            const run = segments[segments.length - 1].items!;
            if (ts.isMethodDeclaration(p) || ts.isGetAccessorDeclaration(p)) {
                methods = true;
                const name = this.fresh('fn');
                const saved = this.out;
                const savedDepth = this.depth;
                this.out = [];
                this.depth = 0;
                const prelude = this.prelude;
                this.prelude = [];
                this.functionLike(name, p, false);
                const lines = this.out;
                this.out = saved;
                this.depth = savedDepth;
                this.prelude = prelude;
                for (const line of lines) {
                    if (line !== '') this.pre('\n' + '    '.repeat(this.depth) + line);
                }
                items.push(`'${snake(p.name.getText())}': ${name}`);
                run.push(items[items.length - 1]);
                continue;
            }
            const rawKey = p.name.getText();
            const key = ts.isComputedPropertyName(p.name) ? this.expr(p.name.expression) : pyString(dict ? unquote(rawKey) : snake(unquote(rawKey)));
            const value = ts.isShorthandPropertyAssignment(p) ? this.identifier(p.name) : this.expr(p.initializer);
            items.push(`${key}: ${value}`);
            run.push(items[items.length - 1]);
        }
        const body = this.wrap('{', items, '}');
        if (spreads.length > 0) {
            // pocketpy builds {**a} wrong without an error, so the spread is merged in a loop.
            const merged = this.fresh('merged');
            this.pre(`${merged} = {}`);
            for (const segment of segments) {
                const source = segment.spread !== undefined
                    ? `(${segment.spread}._fields if isinstance(${segment.spread}, Record) else ${segment.spread})`
                    : this.wrap('{', segment.items!, '}');
                this.pre(`for _k, _v in ${source}.items():`);
                this.pre(`    ${merged}[_k] = _v`);
            }
            this.imports.set('rs2004.catalogs.record', new Set([...(this.imports.get('rs2004.catalogs.record') ?? []), 'Record']));
            return dict ? merged : `Record(${merged})`;
        }
        if (dict) return body;
        this.imports.set('rs2004.catalogs.record', new Set([...(this.imports.get('rs2004.catalogs.record') ?? []), 'Record']));
        const typed = this.contextualTypeName(e);
        if (methods && typed === 'Task') {
            return `Task(${items.map(i => i.replace(/^'(\w+)': /, '$1=')).join(', ')})`;
        }
        return `Record(${body})`;
    }

    private contextualTypeName(e: Node): string | null {
        const type = checker.getContextualType(e);
        const symbol = type?.getSymbol?.() ?? type?.aliasSymbol;
        return symbol?.name ?? null;
    }

    private isSettingsSchema(e: Node): boolean {
        const type = checker.getContextualType(e);
        return type?.aliasSymbol?.name === 'SettingsSchema';
    }

    private isSettingDef(e: Node): boolean {
        const name = this.contextualTypeName(e);
        if (name === 'SettingDef') return true;
        const keys = e.properties.map((p: Node) => p.name?.getText());
        return keys.includes('type') && keys.includes('default') && keys.every((key: string) => SETTING_DEF_FIELDS.includes(key));
    }

    private settingsSchema(e: Node): string {
        const items = e.properties.map((p: Node) => {
            if (ts.isSpreadAssignment(p)) {
                this.flag('a spread of another schema: add its entries', p);
                return `'_spread': None`;
            }
            const key = pyString(snake(unquote(p.name.getText())));
            const value = ts.isShorthandPropertyAssignment(p) ? this.identifier(p.name) : ts.isObjectLiteralExpression(p.initializer) ? this.settingDef(p.initializer) : this.expr(p.initializer);
            return `${key}: ${value}`;
        });
        return this.wrap('{', items, '}');
    }

    private settingDef(e: Node): string {
        const fields: Record<string, string> = {};
        for (const p of e.properties) {
            if (!ts.isPropertyAssignment(p) && !ts.isShorthandPropertyAssignment(p)) {
                this.flag('a setting field', p);
                continue;
            }
            const key = p.name.getText();
            let value = ts.isShorthandPropertyAssignment(p) ? this.identifier(p.name) : this.expr(p.initializer);
            if (key === 'showIf' && ts.isObjectLiteralExpression(p.initializer)) {
                const show: Record<string, string> = {};
                for (const q of p.initializer.properties) {
                    show[q.name.getText()] = q.name.getText() === 'key' && ts.isStringLiteral(q.initializer) ? pyString(snake(q.initializer.text)) : this.expr(q.initializer);
                }
                value = `{'key': ${show.key}, 'any_of': ${show.anyOf}}`;
            }
            fields[key] = value;
        }
        const head = [fields.type ?? "'string'", fields.default ?? 'None'];
        const rest = Object.entries(fields).filter(([key]) => key !== 'type' && key !== 'default').map(([key, value]) => (key === '_' ? value : `${snake(key)}=${value}`));
        return `SettingDef(${[...head, ...rest].join(', ')})`;
    }

    // Items on one line when they fit, else one a line, indented from the statement.
    private wrap(open: string, items: string[], close: string): string {
        const flat = `${open}${items.join(', ')}${close}`;
        if (flat.length + this.depth * 4 <= 110 || items.length < 2) return flat;
        const pad = '    '.repeat(this.depth + 1 + this.nest);
        const end = '    '.repeat(this.depth + this.nest);
        return `${open}\n${items.map(i => `${pad}${i},`).join('\n')}\n${end}${close}`;
    }

    private nest = 0;

    private arrayLiteral(e: Node): string {
        const spread = e.elements.some((x: Node) => ts.isSpreadElement(x));
        if (!spread) return this.wrap('[', e.elements.map((x: Node) => this.expr(x)), ']');
        const parts: string[] = [];
        let plain: string[] = [];
        for (const x of e.elements) {
            if (ts.isSpreadElement(x)) {
                if (plain.length) parts.push(`[${plain.join(', ')}]`);
                plain = [];
                parts.push(`list(${this.expr(x.expression)})`);
            } else {
                plain.push(this.expr(x));
            }
        }
        if (plain.length) parts.push(`[${plain.join(', ')}]`);
        return parts.join(' + ');
    }
}

const SETTING_DEF_FIELDS = ['type', 'default', 'label', 'min', 'max', 'step', 'help', 'options', 'optionLabels', 'group', 'showIf', 'color', 'optionsFrom', 'csvToggle'];

// ---- Layout: two blank lines around top-level definitions, one before a method, none at the start of a body.

function layout(lines: string[]): string[] {
    const out: string[] = [];
    const indentOf = (line: string) => line.length - line.trimStart().length;
    const dropBlanks = (): number => {
        let n = 0;
        while (out.length > 0 && out[out.length - 1] === '') {
            out.pop();
            n++;
        }
        return n;
    };
    for (const raw of lines) {
        const line = raw.trimEnd();
        if (line === '') {
            out.push('');
            continue;
        }
        const indent = indentOf(line);
        const trimmed = line.trimStart();
        const afterDecorator = out.length > 0 && /^\s*@/.test(out[out.length - 1]);
        if (/^(def |class |@)/.test(trimmed) && !afterDecorator) {
            // Comments right above stay attached.
            let attached = 0;
            while (out.length - 1 - attached >= 0 && /^\s*#/.test(out[out.length - 1 - attached]) && indentOf(out[out.length - 1 - attached]) === indent) attached++;
            const comments = out.splice(out.length - attached, attached);
            dropBlanks();
            const previous = out[out.length - 1];
            const opensBody = previous !== undefined && indentOf(previous) < indent && (/:$/.test(previous) || /"""$/.test(previous));
            const wanted = out.length === 0 || opensBody ? 0 : indent === 0 ? 2 : 1;
            for (let n = 0; n < wanted; n++) out.push('');
            out.push(...comments, line);
            continue;
        }
        const blanks = dropBlanks();
        const previous = out[out.length - 1];
        if (previous !== undefined) {
            // A closing bracket ends the statement above it, rather than starting one.
            if (indent === 0 && indentOf(previous) > 0 && !/^[)\]}]/.test(trimmed)) {
                out.push('', '');
            } else if (!/:$/.test(previous)) {
                for (let n = 0; n < Math.min(blanks, indent === 0 ? 2 : 1); n++) out.push('');
            }
        }
        out.push(line);
    }
    return out;
}

// ---- Helpers on nodes

function hasExport(node: Node): boolean {
    return (node.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.ExportKeyword);
}

function isAsync(node: Node): boolean {
    return (node.modifiers ?? []).some((m: Node) => m.kind === ts.SyntaxKind.AsyncKeyword) || !!node.asteriskToken;
}

function isAssignment(op: number): boolean {
    const k = ts.SyntaxKind;
    return op >= k.FirstAssignment && op <= k.LastAssignment;
}

function isWriteTarget(e: Node): boolean {
    const parent = e.parent;
    return ts.isBinaryExpression(parent) && parent.left === e && isAssignment(parent.operatorToken.kind);
}

function hasConditionalAncestor(e: Node, stop?: Node): boolean {
    let node = e;
    while (node !== stop && node.parent && !ts.isStatement(node.parent)) {
        const parent = node.parent;
        if (ts.isConditionalExpression(parent) && parent.condition !== node) return true;
        if (ts.isBinaryExpression(parent) && parent.right === node) {
            const op = parent.operatorToken.kind;
            if (op === ts.SyntaxKind.AmpersandAmpersandToken || op === ts.SyntaxKind.BarBarToken || op === ts.SyntaxKind.QuestionQuestionToken) return true;
        }
        node = parent;
    }
    return false;
}

// Whether a value in the expression can be held in a variable before its statement: not inside a function the
// statement makes, nor in a loop's test, which run more than once.
function hoistable(e: Node): boolean {
    let node = e;
    while (node.parent && !ts.isStatement(node.parent)) {
        if (ts.isFunctionLike(node.parent)) return false;
        node = node.parent;
    }
    return !(node.parent && ts.isIterationStatement(node.parent, false));
}

function containsContinue(node: Node): boolean {
    let found = false;
    const visit = (n: Node): void => {
        if (found) return;
        if (ts.isContinueStatement(n) && !n.label) found = true;
        if (ts.isIterationStatement(n, false) || ts.isFunctionLike(n)) return;
        ts.forEachChild(n, visit);
    };
    ts.forEachChild(node, visit);
    return found;
}

function ctorParameterProperties(ctor: Node | undefined): Node[] {
    if (!ctor) return [];
    return ctor.parameters.filter((p: Node) => (p.modifiers ?? []).some((m: Node) => [ts.SyntaxKind.PrivateKeyword, ts.SyntaxKind.PublicKeyword, ts.SyntaxKind.ProtectedKeyword, ts.SyntaxKind.ReadonlyKeyword].includes(m.kind)));
}

function literalDefault(e: Node): string | null {
    const k = ts.SyntaxKind;
    switch (e.kind) {
        case k.NumericLiteral:
            return e.getText().replace(/_/g, '');
        case k.StringLiteral:
            return pyString(e.text);
        case k.TrueKeyword:
            return 'True';
        case k.FalseKeyword:
            return 'False';
        case k.NullKeyword:
            return 'None';
        case k.PrefixUnaryExpression:
            if (e.operator === k.MinusToken && ts.isNumericLiteral(e.operand)) return '-' + e.operand.getText().replace(/_/g, '');
            return null;
        case k.Identifier:
            return e.text === 'undefined' ? 'None' : null;
    }
    return null;
}

function literalDefaultsOnly(e: Node): boolean {
    return e.parameters.every((p: Node) => !p.initializer || literalDefault(p.initializer) !== null);
}

function needsParens(e: Node): boolean {
    return ts.isBinaryExpression(e) || ts.isConditionalExpression(e);
}

function typeTest(value: string, kind: string): string {
    switch (kind) {
        case 'string':
            return `isinstance(${value}, str)`;
        case 'number':
            return `((isinstance(${value}, int) or isinstance(${value}, float)) and not isinstance(${value}, bool))`;
        case 'boolean':
            return `isinstance(${value}, bool)`;
        case 'function':
            return `callable(${value})`;
        case 'undefined':
            return `${value} is None`;
        case 'object':
            return `(isinstance(${value}, dict) or isinstance(${value}, list))`;
    }
    return 'False';
}

// A regular expression of plain text, anchored or not, as the text and its flags.
function regexAsText(source: string): { text: string; caseless: boolean; global: boolean; start: boolean; end: boolean; anchored: boolean } | null {
    const m = /^\/(.*)\/([a-z]*)$/.exec(source);
    if (!m) return null;
    let body = m[1];
    const start = body.startsWith('^');
    const end = body.endsWith('$') && !body.endsWith('\\$');
    if (start) body = body.slice(1);
    if (end) body = body.slice(0, -1);
    body = body.replace(/\\([\/.\-'"()[\]{}?*+|^$])/g, '$1').replace(/\\b/g, '');
    if (/[\\.|?*+()[\]{}^$]/.test(body)) return null;
    return { text: body, caseless: m[2].includes('i'), global: m[2].includes('g'), start, end, anchored: start || end };
}

// A test of plain alternatives, /^(a|b)$/i and the like, as Python string tests on value.
function regexTest(source: string, value: string): string | null {
    const m = /^\/(.*)\/([a-z]*)$/.exec(source);
    if (!m) return null;
    let body = m[1];
    const caseless = m[2].includes('i');
    const start = body.startsWith('^');
    const end = body.endsWith('$') && !body.endsWith('\\$');
    if (start) body = body.slice(1);
    if (end) body = body.slice(0, -1);
    if (/^\((?:\?:)?(.*)\)$/.test(body)) body = body.replace(/^\((?:\?:)?(.*)\)$/, '$1');
    // A word boundary is near enough to a plain match for names.
    body = body.replace(/\\b/g, '');
    const alternatives = body.split('|').map(a => a.replace(/\\([\/.\-'"()[\]{}?*+|^$])/g, '$1'));
    if (alternatives.some(a => a.length === 0 || /[\\.?*+()[\]{}^$]/.test(a))) return null;
    const subject = caseless ? `${value}.lower()` : value;
    const tests = alternatives.map(a => {
        const text = pyString(caseless ? a.toLowerCase() : a);
        if (start && end) return `${subject} == ${text}`;
        if (start) return `${subject}.startswith(${text})`;
        if (end) return `${subject}.endswith(${text})`;
        return `${text} in ${subject}`;
    });
    const joined = tests.length === 1 ? tests[0] : tests.join(' or ');
    return `(${joined})`;
}

// (a, b) => f(a) - f(b) sorts by f; with b first, in reverse.
function comparatorKey(fn: Node, expr: (n: Node) => string): { param: string; body: string; reverse: boolean } | null {
    if (!(ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) || fn.parameters.length !== 2) return null;
    let body = fn.body;
    if (ts.isBlock(body)) {
        if (body.statements.length !== 1 || !ts.isReturnStatement(body.statements[0]) || !body.statements[0].expression) return null;
        body = body.statements[0].expression;
    }
    if (!ts.isBinaryExpression(body) || body.operatorToken.kind !== ts.SyntaxKind.MinusToken) return null;
    const a = fn.parameters[0].name.getText();
    const b = fn.parameters[1].name.getText();
    const swap = (text: string, from: string, to: string) => text.replace(new RegExp(`\\b${from}\\b`, 'g'), to);
    const left = body.left.getText();
    const right = body.right.getText();
    if (swap(left, a, b) === right && !new RegExp(`\\b${b}\\b`).test(left)) {
        return { param: snake(a), body: expr(body.left), reverse: false };
    }
    if (swap(left, b, a) === right && !new RegExp(`\\b${a}\\b`).test(left)) {
        return { param: snake(b), body: expr(body.left), reverse: true };
    }
    return null;
}

function unquote(key: string): string {
    return /^['"].*['"]$/.test(key) ? key.slice(1, -1) : key;
}

function pyString(text: string): string {
    const quote = text.includes("'") && !text.includes('"') ? '"' : "'";
    return quote + escapeFor(text, quote) + quote;
}

function escapeFor(text: string, quote: string): string {
    return text.replace(/\\/g, '\\\\').replace(new RegExp(quote, 'g'), '\\' + quote).replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t');
}

function commentLines(raw: string): string[] {
    if (raw.startsWith('//')) return [raw.replace(/^\/\/\s?/, '').trimEnd()];
    return raw
        .replace(/^\/\*\*?/, '')
        .replace(/\*\/$/, '')
        .split(/\r?\n/)
        .map(line => line.replace(/^\s*\*\s?/, '').trimEnd())
        .filter((line, i, all) => line.length > 0 || (i > 0 && i < all.length - 1));
}

// ---- Run

for (const file of files) {
    const sf = program.getSourceFile(file);
    if (!sf) {
        console.error(`${file}: not found`);
        process.exit(1);
    }
    const rel = path.relative(botRoot, file).replace(/\\/g, '/');
    const python = new Translator(sf, rel).run();
    if (!outPath) {
        process.stdout.write(`# ---- ${rel}\n${python}\n`);
        continue;
    }
    // Into the folder by file name, or by rs2b0t's folders too when two inputs share a file name.
    const base = facade(path.basename(file, '.ts')) + '.py';
    const shared = files.filter(f => path.basename(f) === path.basename(file)).length > 1;
    const target = files.length === 1 && outPath.endsWith('.py') ? outPath : path.join(outPath, shared ? path.dirname(rel) : '', base);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, python);
    console.error(`${rel} -> ${target}`);
}

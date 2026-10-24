"""Lists what of rs2b0t (MIT, see thirdparty/rs2b0t) the standard library doesn't have yet, by the snake_case
names of rs2b0t's exports. A name counts as ported when it appears in the stdlib or the stubs; NOT_PORTED
lists what's left out on purpose (docs/BotApiParityDesign.md §1). Run with CPython:

    python -I tools/port/coverage.py ../rs2b0t                  # the public API, index.d.ts
    python -I tools/port/coverage.py ../rs2b0t api/thieving     # each module under src/bot/api/thieving
    python -I tools/port/coverage.py ../rs2b0t --bots           # each bot's imports from outside its folder

It exits with 1 when something is missing, so a phase's "Done when" can run it.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SEARCHED = ['src/Script/Stdlib', 'scripts/typings']

# Left out on purpose: rs2b0t files whose exports a headless client has no use for, by path under src/bot.
NOT_PORTED_FILES = (
    'paint/', 'panel/', 'multibox/', 'input/', 'adapter/', 'runtime/diag/', 'runtime/RenderGate.ts', 'runtime/WorkerClock.ts',
    'runtime/producers.ts', 'runtime/producerDirty.ts', 'runtime/AutoRelogin.ts', 'runtime/LoginBackoff.ts',
    'runtime/LoginCoordination.ts', 'runtime/Credentials.ts', 'runtime/WorldSwitch.ts', 'runtime/WelcomeScreen.ts',
    'runtime/ScriptRegistry.ts', 'runtime/abi.ts', 'runtime/loader.ts', 'runtime/box.ts', 'runtime/buildInfo.ts',
    'runtime/desktopStorage.ts', 'runtime/BotClient.ts', 'event/webwalk/cameraFollow.ts', 'event/webwalk/pathOverlay.ts',
    'event/webwalk/pathPaintTheme.ts', 'event/webwalk/pathScenePaint.ts', 'event/webwalk/pathPublish.ts',
    'event/webwalk/NavWorker.ts', 'api/ai/clues/cluePaint.ts',
)
# Left out on purpose: single names, by the module that exports them.
NOT_PORTED_NAMES = {
    'index.d.ts': {'apiVersion', 'registerScript', 'cameraYaw', 'cameraPitch', 'setCameraYaw', 'onPaint', 'snapshotGeneration',
                   'snapshotReady', 'waitSnapshotAfter', 'toString', 'constructor'},
    'api/bank/Bank.ts': {'BackpackItem'},
    'api/inventory/Inventory.ts': {'backpackSnapshots'},
    'runtime/ScriptRunner.ts': {'ScriptRunner'},
    'runtime/BotHost.ts': {'BotHost'},
    'runtime/Scheduler.ts': {'Scheduler'},
    'runtime/ScriptContext.ts': {'ScriptAborted', 'ScriptContext'},
    # The navigator here plans at once, so nearest_walkable_bank and bank_cost_for_navigator serve both.
    'api/bank/BankLocations.ts': {'nearestWalkableBankAsync', 'bankCostForFinder'},
    # rs2b0t's 289 component ids for the staff spell chooser; spell_button_com finds the buttons by shape.
    'api/combat/CombatStyleLogic.ts': {'AUTO_CHOOSE_COM', 'AUTO_TOGGLE_COM'},
    # rs2b0t's 289 modal ids for the duel screens; rs2004.duel finds each screen by its text.
    'api/duel/Duel.ts': {'DUEL_SELECT_MODAL', 'DUEL_CONFIRM_MODAL', 'DUEL_WIN_MODAL'},
}

EXPORT = re.compile(r'^export\s+(?:declare\s+)?(?:default\s+)?(?:async\s+)?(?:abstract\s+)?(function\*?|const|let|class|type|interface|enum)\s+([A-Za-z_0-9]+)', re.M)
IMPORT = re.compile(r"import\s+(type\s+)?\{([^}]*)\}\s+from\s+'((?:\.\./)+)([^']+)'", re.S)


def snake(name):
    """rs2b0t's name as the stdlib spells it: camelCase becomes snake_case, and CONSTANTS and CapWords classes stay."""
    if name.upper() == name or name[0].isupper():
        return name
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', text)
    return text.lower()


def candidates(name):
    """The spellings a ported name may have: rs2b0t's own, snake_case, with a trailing _ for a Python keyword, and
    a CapWords facade as its lower-case object (ChatDialog is chat_dialog)."""
    lower = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    return {name, snake(name), snake(name) + '_', lower}


def haystack():
    texts = []
    for base in SEARCHED:
        for folder, _, files in os.walk(os.path.join(ROOT, base)):
            for file in files:
                if file.endswith(('.py', '.pyi')):
                    with open(os.path.join(folder, file), encoding='utf-8') as f:
                        texts.append(f.read())
    return '\n'.join(texts)


def present(hay, name):
    return any(re.search(r'\b' + re.escape(c) + r'\b', hay) for c in candidates(name))


def left_out(module, name=None):
    if module.startswith(NOT_PORTED_FILES):
        return True
    return name is not None and name in NOT_PORTED_NAMES.get(module, ())


def check_dts(rs2b0t, hay):
    """The public API: each export of index.d.ts, and each member of its facades and classes."""
    with open(os.path.join(rs2b0t, 'packages/rs2b0t-api/index.d.ts'), encoding='utf-8') as f:
        dts = f.read()
    missing = []
    for kind, name in EXPORT.findall(dts):
        if kind not in ('type', 'interface') and not left_out('index.d.ts', name) and not present(hay, name):
            missing.append(name)
    for block in re.finditer(r'^export (?:const|(?:abstract )?class) ([A-Za-z_0-9]+)[^{\n]*\{\n(.*?)^\};?$', dts, re.M | re.S):
        owner, body = block.group(1), block.group(2)
        for name in sorted(set(re.findall(r'^\s{4}(?:readonly |static |abstract |protected )*([a-zA-Z_][A-Za-z0-9_]*)\??\s*[(:<]', body, re.M))):
            if not left_out('index.d.ts', name) and not present(hay, name):
                missing.append(f'{owner}.{name}')
    for name in missing:
        print(f'index.d.ts: missing {name}')
    return len(missing)


def check_modules(rs2b0t, hay, paths):
    """Each module under the paths, by its exports."""
    bot = os.path.join(rs2b0t, 'src/bot')
    total = 0
    for path in paths:
        start = os.path.join(bot, path)
        files = [start] if os.path.isfile(start) else [os.path.join(d, f) for d, _, fs in os.walk(start) for f in fs]
        for file in sorted(files):
            module = os.path.relpath(file, bot).replace('\\', '/')
            if not module.endswith('.ts') or module.endswith('.test.ts') or left_out(module):
                continue
            with open(file, encoding='utf-8') as f:
                exports = [name for kind, name in EXPORT.findall(f.read()) if kind not in ('type', 'interface')]
            missing = [name for name in exports if not left_out(module, name) and not present(hay, name)]
            if missing:
                print(f'{module}: missing {" ".join(missing)} ({len(exports) - len(missing)} of {len(exports)} here)')
                total += len(missing)
    return total


def check_bots(rs2b0t, hay):
    """Each bundled bot, by the names it imports from outside its own folder."""
    scripts = os.path.join(rs2b0t, 'src/bot/scripts')
    total = 0
    for name in sorted(os.listdir(scripts)):
        folder = os.path.join(scripts, name)
        if not os.path.isdir(folder):
            continue
        missing = set()
        for directory, _, files in os.walk(folder):
            for file in files:
                if not file.endswith('.ts') or file.endswith('.test.ts'):
                    continue
                with open(os.path.join(directory, file), encoding='utf-8') as f:
                    source = f.read()
                for is_type, names, ups, module in IMPORT.findall(source):
                    # Two levels up leaves the bot's folder for src/bot.
                    if is_type or len(ups) < 6:
                        continue
                    module = module.replace('.js', '.ts')
                    for imported in names.split(','):
                        imported = imported.strip().split(' as ')[0].strip()
                        if not imported or imported.startswith('type ') or left_out(module, imported):
                            continue
                        if not present(hay, imported):
                            missing.add(f'{module.replace(".ts", "")}:{imported}')
        if missing:
            print(f'{name}: missing {" ".join(sorted(missing))}')
            total += 1
    return total


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rs2b0t = argv[1]
    hay = haystack()
    rest = argv[2:]
    if rest == ['--bots']:
        missing = check_bots(rs2b0t, hay)
    elif rest:
        missing = check_modules(rs2b0t, hay, rest)
    else:
        missing = check_dts(rs2b0t, hay)
    print('nothing missing' if missing == 0 else f'{missing} missing')
    return 0 if missing == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

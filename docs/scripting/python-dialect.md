# Python, imports, tools and porting

## The Python dialect

Scripts run on pocketpy 2.2, a subset of Python 3. Most everyday Python works; these differences are the ones scripts hit.

### Syntax

- `match` is a keyword, so it can't name a variable or parameter. Where rs2b0t's functions take `match`, these take `text` or `name`.
- `try` has no `finally` and no `else`.
- Generator expressions don't exist: write `any([x for x in xs])`, not `any(x for x in xs)`.
- `yield from` may only be a statement, or the right side of an assignment. Not `if (yield from wait()):`; write `ok = yield from wait()` then `if ok:`.
- In unpacking, a starred name must come last (`first, *rest = items`), and only lists and tuples unpack.
- A parenthesised import can't have a trailing comma.
- Avoid chained comparisons such as `a < b < c`; write `a < b and b < c`.

### Functions and classes

- A parameter can be passed by keyword only when it has a default value, and a default must be a literal: `timeout=6000`, not `timeout=TIMEOUT`.
- A function can read the variables of the function it's defined in, but not of one further out. A lambda inside a nested function that uses the outer function's variable fails, or quietly gets a builtin of the same name, such as `id` or `min`. Copy the value into a local of the nested function first.
- Classes must be defined at module level, not inside a function.
- A class has at most one base class.
- A class that defines `__eq__` must define `__ne__` too.
- An attribute set on an instance doesn't replace a method of its class. Give the instance a differently named attribute and call it from the method (as [`Task`](script-structure.md#taskbot-and-task) does).

### Types and the library

- Ints are 64-bit, and `bool` isn't a kind of `int`.
- Tuples can't be added together.
- `dict(another_dict)` doesn't copy; use `{k: v for k, v in d.items()}`. `dict.setdefault` and `str.isdigit` don't exist.
- `x in range(...)` doesn't work; compare the bounds.
- There's no `re` module.
- `time.sleep()` raises `RuntimeError`. Wait with [`execution`](waiting.md).
- Sets, dict ordering, `**kwargs`, `isinstance(x, (A, B))` and f-strings do work.

## Imports

`import name` looks, in order:

1. The client's standard library, the `rs2004` package. Its public names are already builtins, so scripts don't import it, except for [`rs2004.catalogs`](catalogs.md).
2. `scripts/name.py`, then `scripts/lib/name.py`. Packages (folders with `__init__.py`) work too.
3. pocketpy's own modules: `math`, `random`, `json`, `time`, `collections` and so on.

Nothing else is searched, and pip packages can't be used.

```python
import random
from rs2004.catalogs import FOOD_OPTIONS
import my_helpers           # scripts/my_helpers.py or scripts/lib/my_helpers.py
```

## Working on a script

### Reloading on save

```
rs2004-headless client.jsonc --account accounts/<name>.jsonc --watch
```

`--watch` reloads the script whenever you save it, or a module it imports, without logging out. The new code starts fresh: new globals, `on_start()` again, and events from before the save skipped (queued bot messages are kept). If a save breaks the script, or it fails later, the account stays logged in and idle until the next save. A change to the account file needs a restart.

### Debugging in VS Code

`--debugger` lets VS Code debug one account's script, with breakpoints, stepping, variables and a debug console that can call the API.

1. Install VS Code's pocketpy extension (`pocketpy.pocketpy`).
2. Add to `.vscode/launch.json`:

   ```json
   {
       "type": "pocketpy",
       "request": "attach",
       "name": "Attach to rs2004-headless",
       "host": "127.0.0.1",
       "port": 6110,
       "sourceFolder": "${workspaceFolder}/scripts"
   }
   ```

3. Run `rs2004-headless client.jsonc --account accounts/<name>.jsonc --debugger`, then start the configuration. The account logs in once the debugger attaches.

While paused, the whole process is paused and the server hears nothing, so a long pause may end in a reconnect. `scripting.callTimeoutMs` doesn't apply under the debugger. Breakpoints work in `scripts/` but not `scripts/lib/`. `--debugger` needs `--account` and can't be combined with `--watch`.

### Editor support

`scripts/typings/__builtins__.pyi` and `scripts/typings/rs2004/catalogs/__init__.pyi` declare the API for Pylance and Pyright, and the repository's `pyrightconfig.json` points them there. Opening the repository or the `scripts` folder gives completion and type checks.

## Revisions

`game.revision()` gives the server's revision. Branch on it where content differs.

- **289** is what the catalogs and walker data were built from.
- **274** plays as 289, but anything added after 274 doesn't exist, and some map squares differ, so a few walker routes cross scenery 274 doesn't have.
- **225** doesn't say whether the world is members, so `traversal` plans as on a free world. Its player menu is fixed (`Duel-with`, `Attack`, `Follow`, `Trade with`). Ids added after 225 don't exist.

## Porting from rs2b0t

The API is rs2b0t's, in Python's style, so a bot translates mostly line by line.

| TypeScript | Python |
|---|---|
| `class Miner extends LoopingBot { loop() {...} }` | `class Miner(LoopingBot): def loop(self): ...` |
| `export default defineBot({ name: 'Miner', create: () => new Miner() })` | `BOT = define_bot(name='Miner', create=Miner)` |
| `await Execution.delayUntil(() => Inventory.isFull(), 3000)` | `yield from execution.delay_until(lambda: inventory.is_full(), 3000)` |
| `Npcs.query().name('Guard').within(3).nearest()` | `npcs.query().name('Guard').within(3).nearest()` |
| `npc.inCombat`, `item.useOn(range)` | `npc.in_combat`, `item.use_on(range)` |
| `this.settings.str('rock', 'Copper rocks')` | `self.settings.str('rock', 'Copper rocks')` |
| `this.on('skill.xp', e => ...)` | `self.on('skill_xp', lambda e: ...)` |
| `Game.tile()?.x` | `game.tile().x if game.tile() else None` |

- Facades are lower case (`Npcs` is `npcs`, `GroundItems` is `ground_items`) and camelCase becomes snake_case. A name that's a Python keyword gains a trailing underscore: `ChatDialog.continue()` is `chat_dialog.continue_()`.
- A thing's `interact` walks to it first, as the game's client does.
- `npc.level` is its combat level; a thing's floor is `thing.tile().level`.
- `chat_message`'s `type` is a name (`'game'`, `'public'` and so on), not the webclient's number.
- A setting that doesn't fit its schema is an error before login rather than quietly the default.
- `chooseOption(match)` is `choose_option(text)`, and `make(match)` is `make(name)`.

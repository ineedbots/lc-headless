"""rs2b0t's describe, test and expect, for its tests as ts2py drafts them. StdlibTests.cpp runs this before each
test_*.py here, then run_specs(), which runs every test and raises with each failure. A spec starting with
`# fixture: name` also loads fixtures/name.py into the same isolated VM before the test source."""

_SPECS = []
_PREFIX = []
_BEFORE = []
_AFTER = []


def describe(name, body):
    _PREFIX.append(name)
    body()
    _PREFIX.pop()


def test(name, body):
    _SPECS.append((' > '.join(_PREFIX + [name]), body))


it = test


class _RowCase:
    """One row's test: the body called with the row's entries, or the row itself when it isn't a list."""

    def __init__(self, body, row):
        self.body = body
        self.row = row

    def __call__(self):
        if isinstance(self.row, (list, tuple)):
            return self.body(*self.row)
        return self.body(self.row)


def _row_name(name, row):
    """Bun's test.each name: %s, %i, %d and %p take the row's entries in turn, and $field reads a field."""
    entries = list(row) if isinstance(row, (list, tuple)) else [row]
    out = ''
    i = 0
    used = 0
    while i < len(name):
        if name[i] == '%' and i + 1 < len(name) and name[i + 1] in 'sidp':
            out += str(entries[used]) if used < len(entries) else ''
            used += 1
            i += 2
            continue
        if name[i] == '$':
            j = i + 1
            while j < len(name) and (name[j].lower() != name[j].upper() or name[j] == '_'):
                j += 1
            field = name[i + 1:j]
            value = getattr(row, field, None) if not isinstance(row, dict) else row.get(field)
            out += str(value)
            i = j
            continue
        out += name[i]
        i += 1
    return out


def test_each(rows):
    """rs2b0t's test.each(rows)(name, body): a test per row."""
    def register(name, body):
        for row in rows:
            test(_row_name(name, row), _RowCase(body, row))
    return register


def before_each(body):
    _BEFORE.append(body)


def after_each(body):
    _AFTER.append(body)


def _drain(result):
    # A body drafted as a generator, from rs2b0t's async ones, is run to its end.
    if result is not None and hasattr(result, '__next__'):
        for _ in result:
            pass


def run_specs(selected_name=None):
    failures = []
    selected = 0
    for name, body in _SPECS:
        if selected_name is not None and name != selected_name:
            continue
        selected += 1
        try:
            for hook in _BEFORE:
                _drain(hook())
            _drain(body())
        except Exception as e:
            failures.append(f'{name}: {type(e).__name__}: {e}')
        for hook in _AFTER:
            _drain(hook())
        restore_all()
    if len(failures) > 0:
        raise AssertionError(f'{len(failures)} of {selected} failed:\n' + '\n'.join(failures))
    if len(_SPECS) == 0:
        raise AssertionError('no tests')
    if selected_name is not None and selected == 0:
        raise AssertionError('no test named ' + selected_name)


# rs2b0t's spyOn and stubs. pocketpy ignores a method set on an instance, but takes one set on its class, so a spy on
# an object patches the object's class; on a module or a class, the thing itself. Every patch is put back after each
# test.
_PATCHES = []


class Spy:
    """A stand-in that records each call's arguments in calls and gives impl(*args), or returns. A callable object,
    not a function, so the class it sits on doesn't bind it to self."""

    def __init__(self, impl=None, returns=None):
        self.impl = impl
        self.returns = returns
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        if self.impl is not None:
            return self.impl(*args, **kwargs)
        return self.returns

    def mock_return_value(self, value):
        self.impl = None
        self.returns = value
        return self

    def mock_implementation(self, impl):
        self.impl = impl
        return self

    def called(self):
        return len(self.calls) > 0


def _owner(target):
    if isinstance(target, type) or type(target).__name__ == 'module':
        return target
    return type(target)


def patch(target, name, value):
    """Sets name on target's class (or on target, for a module or class) until the test ends."""
    owner = _owner(target)
    _PATCHES.append((owner, name, getattr(owner, name, None)))
    setattr(owner, name, value)
    return value


def spy_on(target, name, impl=None, returns=None):
    """rs2b0t's spyOn(target, name), with mockImplementation as impl and mockReturnValue as returns."""
    return patch(target, name, Spy(impl, returns))


def stub(obj, **fields):
    """Sets plain attributes on an object until the test ends, as rs2b0t's stubProps."""
    for name, value in fields.items():
        _PATCHES.append((obj, name, getattr(obj, name, None)))
        setattr(obj, name, value)


def restore_all():
    while len(_PATCHES) > 0:
        owner, name, original = _PATCHES.pop()
        setattr(owner, name, original)


# Fakes for a test's world, standing in where rs2b0t's tests build object literals.

class Fake:
    """An object of the given fields; a field that's a function is called as a method, without self."""

    def __init__(self, **fields):
        self._fields = fields

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return self._fields.get(name)

    def __repr__(self):
        return f'Fake({self._fields})'


class FakeQuery:
    """An entity query over a list of fakes: name, action, where, within, nearest, first, count, exists and results. A
    fake is named by its name field and offers its actions()."""

    def __init__(self, rows):
        self.rows = rows

    def name(self, *names):
        flat = []
        for n in names:
            flat.extend(n if isinstance(n, list) else [n])
        wanted = [n.lower() for n in flat]
        return FakeQuery([r for r in self.rows if (r.name or '').lower() in wanted])

    def action(self, op):
        return FakeQuery([r for r in self.rows if op.lower() in [a.lower() for a in r.actions()]])

    def where(self, fn):
        return FakeQuery([r for r in self.rows if fn(r)])

    def within(self, radius):
        return FakeQuery([r for r in self.rows if r.distance() <= radius])

    def within_of(self, origin, radius):
        return FakeQuery([r for r in self.rows if r.tile().distance_to(origin) <= radius])

    def id(self, *ids):
        return FakeQuery([r for r in self.rows if r.id in ids])

    def inside(self, area):
        from rs2004.entities import _area_test
        test = _area_test(area)
        return FakeQuery([r for r in self.rows if test(r.tile())])

    def nearest(self):
        """The row of least distance(), or the first when the rows have no distance."""
        if not self.rows:
            return None
        if all([callable(getattr(r, 'distance', None)) for r in self.rows]):
            return sorted(self.rows, key=lambda r: r.distance())[0]
        return self.rows[0]

    def first(self):
        return self.nearest()

    def count(self):
        return len(self.rows)

    def exists(self):
        return len(self.rows) > 0

    def results(self):
        return list(self.rows)


def querying(supply):
    """A query() that reads supply() afresh each time."""
    return lambda: FakeQuery(supply())


class FakeChat:
    """A chat dialog that plays pages in order: 'continue', or a list of options. chosen records each option picked
    and on_choose(text) runs after it; install(chat_dialog) puts it over the dialog's calls until the test ends."""

    def __init__(self, pages=None):
        self.pages = list(pages) if pages is not None else []
        self.chosen = []
        self.on_choose = None
        self.shown = []

    def texts(self):
        return list(self.shown)

    def is_open(self):
        return len(self.pages) > 0

    def can_continue(self):
        return len(self.pages) > 0 and self.pages[0] == 'continue'

    def options(self):
        if len(self.pages) == 0 or self.pages[0] == 'continue':
            return []
        return list(self.pages[0])

    def continue_(self):
        if len(self.pages) > 0:
            self.pages.pop(0)
        return True
        yield

    def choose_option(self, text):
        self.chosen.append(text)
        if len(self.pages) > 0:
            self.pages.pop(0)
        if self.on_choose is not None:
            self.on_choose(text)
        return True
        yield

    def install(self, chat_dialog):
        for name in ['is_open', 'can_continue', 'options', 'continue_', 'choose_option', 'texts']:
            spy_on(chat_dialog, name, impl=getattr(self, name))
        return self


class Scene:
    """A quest leg's whole world over the facades: where the player stands, the pack and what's worn, the locs, NPCs
    and ground items about, the game messages said, the chat, and a clock. Everything is put back when the test ends.

    A wait answers at once and costs game time: a tick is 600 ms, and a delay_until whose condition never comes costs
    its whole timeout, so a leg's own deadline runs out as it would live. after_wait holds what happens once the
    player next waits, one entry per wait. A thing's effect(op), or use_on's effect(target), says what its click does,
    and returning False from it refuses the click. A thing stands dist tiles off, or with dist=None as far as its tile
    is from the player. Walking arrives unless walk_ok is False or the tile is in no_walk; talk_status and
    loc_op_status are what reach answers, and loc_op_effect(name, op) what its loc_op does."""

    def __init__(self, at=None):
        import _core
        from rs2004 import execution
        from rs2004.catalogs.tasks import sustain
        from rs2004.dialogue import chat_dialog, modals
        from rs2004.entities import ground_items, locs, npcs
        from rs2004.game import game, reader, skills
        from rs2004.items import equipment, inventory
        from rs2004.reach import reach
        from rs2004.tabs import quests
        from rs2004.traversal import traversal
        self.at = at
        self.pack = []
        self.worn = []
        self.locs = []
        self.npcs = []
        self.ground = []
        self.said = []
        self.lines = []
        self.walks = []
        self.ticks = 0
        self.clock = 0
        self.fighting = False
        self.walk_ok = True
        self.no_walk = []
        self.stats = {}
        self.status = 'in_progress'
        self.main_modal = -1
        self.after_wait = []
        self.talk_status = 'done'
        self.talks = []
        self.loc_op_status = 'done'
        self.loc_ops = []
        self.loc_op_effect = None
        self.main_texts = []
        self._next_index = 1
        self.chat = FakeChat([]).install(chat_dialog)
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(game, 'in_combat', impl=lambda: self.fighting)
        spy_on(game, 'tick', impl=lambda: self.ticks)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(inventory, 'items', impl=lambda: list(self.pack))
        spy_on(inventory, 'count', impl=lambda name: sum([i.count for i in self.pack if (i.name or '').lower() == name.lower()]))
        spy_on(inventory, 'count_by_id', impl=lambda id: sum([i.count for i in self.pack if i.id == id]))
        spy_on(inventory, 'contains', impl=self._pack_holds)
        spy_on(inventory, 'first', impl=self._pack_first)
        spy_on(inventory, 'free', impl=lambda: 28 - len(self.pack))
        spy_on(inventory, 'used', impl=lambda: len(self.pack))
        spy_on(inventory, 'is_full', impl=lambda: len(self.pack) >= 28)
        spy_on(equipment, 'items', impl=lambda: list(self.worn))
        spy_on(equipment, 'contains', impl=self._wearing)
        spy_on(equipment, 'equip', impl=self._equip)
        spy_on(equipment, 'unequip', impl=self._unequip)
        spy_on(skills, 'level', impl=lambda name: self.stats.get(name, 99))
        spy_on(skills, 'effective', impl=lambda name: self.stats.get(name, 99))
        spy_on(skills, 'xp', impl=lambda name: self.stats.get(name, 99))
        spy_on(skills, 'hp_fraction', impl=lambda: self.stats.get('hp_fraction', 1))
        spy_on(traversal, 'walk_resilient', impl=self._walk)
        spy_on(traversal, 'walk_to', impl=self._walk)
        spy_on(execution, 'delay_ticks', impl=self._delay_ticks)
        spy_on(execution, 'delay_until', impl=self._delay_until)
        spy_on(execution, 'delay_until_ticks', impl=self._delay_until_ticks)
        spy_on(sustain, 'run', impl=self._idle)
        spy_on(modals, 'is_open', impl=lambda: self.main_modal != -1)
        spy_on(modals, 'close', impl=self._close_modal)
        spy_on(modals, 'close_if_open', impl=self._close_modal)
        spy_on(reader, 'modals', impl=lambda: Fake(main=self.main_modal, side=-1, chat=-1))
        spy_on(reader, 'main_modal_texts', impl=lambda: list(self.main_texts))
        spy_on(reach, 'npc_dialog', impl=self._talk)
        spy_on(reach, 'loc_op', impl=self._loc_op)
        spy_on(quests, 'status', impl=lambda name: self.status)
        spy_on(_core, 'step_time', impl=lambda: self.clock)
        spy_on(_core, 'close_interfaces', impl=self._close_interfaces)
        spy_on(_core, 'message_mark', impl=lambda: len(self.said))
        spy_on(_core, 'game_messages_since', impl=lambda mark: [(n, self.said[n]) for n in range(mark, len(self.said))])

    def log(self, line):
        self.lines.append(line)

    def logged(self, text):
        return len([line for line in self.lines if text in line]) > 0

    def say(self, text):
        self.said.append(text)

    def later(self, effect):
        """Runs effect at the player's next wait, after any already queued."""
        self.after_wait.append(effect)

    def item(self, id, name, count=1, actions=None, effect=None, on_use=None):
        """Puts an item in the pack."""
        thing = self._item(id, name, count, actions, effect, on_use, self.pack)
        self.pack.append(thing)
        return thing

    def wear(self, name, id=0, actions=None):
        thing = self._item(id, name, 1, actions, None, None, self.worn)
        self.worn.append(thing)
        return thing

    def drop_item(self, thing):
        if thing in self.pack:
            self.pack.remove(thing)

    def has(self, id):
        return len([i for i in self.pack if i.id == id]) > 0

    def take(self, id):
        """Removes every item of that id from the pack."""
        self.pack = [i for i in self.pack if i.id != id]

    def loc(self, name, actions=None, tile=None, effect=None, id=0, dist=2, on_use=None):
        thing = self._placed(self.locs, id, name, actions, tile, effect, dist, on_use)
        self.locs.append(thing)
        return thing

    def npc(self, name, actions=None, tile=None, effect=None, id=0, dist=2, targets_me=False, others=False):
        thing = self._placed(self.npcs, id, name, actions, tile, effect, dist, None, targets_me, others)
        thing._fields['network_tile'] = thing.tile
        self.npcs.append(thing)
        return thing

    def on_ground(self, id, name, tile=None, effect=None, dist=2):
        """A ground item whose Take moves it to the pack, unless its effect says otherwise."""
        def taken(op):
            if effect is not None:
                return effect(op)
            self.item(id, name)
            self.ground = [g for g in self.ground if g.id != id]
            return True

        thing = self._placed(self.ground, id, name, ['Take'], tile, taken, dist, None)
        self.ground.append(thing)
        return thing

    def _item(self, id, name, count, actions, effect, on_use, owner):
        def interact(op):
            return effect is None or effect(op) is not False

        def use_on(target):
            return on_use is None or on_use(target) is not False

        return Fake(id=id, name=name, count=count, actions=lambda: actions if actions is not None else ['Use', 'Drop'], interact=interact, use_on=use_on)

    def _placed(self, rows, id, name, actions, tile, effect, dist, on_use, targets_me=False, others=False):
        index = self._next_index
        self._next_index += 1
        where = tile if tile is not None else self.at

        def interact(op):
            return effect is None or effect(op) is not False

        def is_valid():
            return index in [r.index for r in self.locs + self.npcs + self.ground]

        def distance():
            return dist if dist is not None else where.distance_to(self.at)

        return Fake(id=id, index=index, name=name, on_use=on_use, tile=lambda: where, distance=distance, actions=lambda: actions if actions is not None else [], interact=interact, valid=is_valid, in_combat=False, targets_me=lambda: targets_me, targets_another_player=lambda: others)

    def _pack_holds(self, name):
        return len([i for i in self.pack if (i.name or '').lower() == name.lower()]) > 0

    def _pack_first(self, name):
        rows = [i for i in self.pack if (i.name or '').lower() == name.lower()]
        return rows[0] if len(rows) > 0 else None

    def _wearing(self, name):
        return len([i for i in self.worn if (i.name or '').lower() == name.lower()]) > 0

    def _equip(self, name):
        rows = [i for i in self.pack if (i.name or '').lower() == name.lower()]
        if len(rows) == 0:
            return False
        self.pack.remove(rows[0])
        self.worn.append(rows[0])
        return True
        yield

    def _unequip(self, name):
        rows = [i for i in self.worn if (i.name or '').lower() == name.lower()]
        if len(rows) == 0:
            return False
        self.worn.remove(rows[0])
        self.pack.append(rows[0])
        return True
        yield

    def _walk(self, dest, radius=0, attempts=0, timeout_ms=0, log=None, avoid_zones=None):
        self.walks.append(dest)
        if not self.walk_ok or dest in self.no_walk:
            return False
        self.at = dest
        return True
        yield

    def _pump(self):
        if len(self.after_wait) > 0:
            self.after_wait.pop(0)()

    def _delay_ticks(self, n=1):
        self.ticks += n
        self.clock += 600 * n
        self._pump()
        return None
        yield

    def _delay_until(self, cond, timeout_ms=6000):
        self._pump()
        ok = cond()
        self.clock += 600 if ok else timeout_ms
        return ok
        yield

    def _delay_until_ticks(self, cond, ticks=1):
        self._pump()
        ok = cond()
        self.ticks += 1 if ok else ticks
        self.clock += 600 if ok else 600 * ticks
        return ok
        yield

    def _idle(self, *args):
        return None
        yield

    def _close_modal(self):
        self.main_modal = -1
        return True
        yield

    def _close_interfaces(self):
        self.main_modal = -1

    def _talk(self, name, near, open_ms=15000, log=None):
        self.talks.append(name)
        return self.talk_status
        yield

    def _loc_op(self, name, op, near, expect, within=10, id=None, expect_ms=12000, refused=None, log=None):
        self.loc_ops.append((name, op))
        if self.loc_op_effect is not None:
            self.loc_op_effect(name, op)
        return self.loc_op_status
        yield


def instant_until(cond, timeout_ms=6000):
    """execution.delay_until that answers at once."""
    return cond()
    yield


def instant_until_ticks(cond, ticks=1):
    return cond()
    yield


def instant_ticks(n=1):
    return None
    yield


def run_wait(gen):
    """Runs a Wait to its end, as run_specs does a test body, and gives its result."""
    if gen is None or not hasattr(gen, '__next__'):
        return gen
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        return stop.value


def _fields(value):
    if hasattr(value, '_fields') and isinstance(value._fields, dict):
        return value._fields
    if isinstance(value, dict):
        return value
    return None


def _is_sequence(value):
    return isinstance(value, list) or isinstance(value, tuple)


def deep_equal(a, b):
    if _is_sequence(a) and _is_sequence(b):
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if not deep_equal(a[i], b[i]):
                return False
        return True
    fa = _fields(a)
    fb = _fields(b)
    if fa is not None and fb is not None:
        keys = [k for k in fa if fa[k] is not None]
        other = [k for k in fb if fb[k] is not None]
        if len(keys) != len(other):
            return False
        for k in keys:
            if not deep_equal(fa[k], fb.get(k)):
                return False
        return True
    if fb is not None and fa is None and a is not None and not _is_sequence(a):
        # A class instance against a plain object of its fields.
        return matches_object(a, b)
    return a == b


def _read(value, key):
    fields = _fields(value)
    if fields is not None and key in fields:
        return fields[key]
    return getattr(value, key, None)


def matches_object(actual, expected):
    fields = _fields(expected)
    if fields is None:
        if _is_sequence(expected) and _is_sequence(actual):
            if len(expected) != len(actual):
                return False
            for i in range(len(expected)):
                if not matches_object(actual[i], expected[i]):
                    return False
            return True
        return deep_equal(actual, expected)
    for key in fields:
        if not matches_object(_read(actual, key), fields[key]):
            return False
    return True


class Expect:
    def __init__(self, actual, negate=False):
        self.actual = actual
        self.negate = negate

    @property
    def not_(self):
        return Expect(self.actual, not self.negate)

    @property
    def resolves(self):
        """A drafted async call is a generator; this runs it and expects its result."""
        out = []

        def run():
            result = yield from self.actual
            out.append(result)

        _drain(run())
        return Expect(out[0], self.negate)

    def check(self, ok, what):
        if ok == self.negate:
            raise AssertionError(f"expected {repr(self.actual)} {'not ' if self.negate else ''}{what}")

    def to_be(self, expected):
        self.check(self.actual is expected or deep_equal(self.actual, expected) and not _is_sequence(expected), f'to be {repr(expected)}')

    def to_equal(self, expected):
        self.check(deep_equal(self.actual, expected), f'to equal {repr(expected)}')

    def to_strict_equal(self, expected):
        self.to_equal(expected)

    def to_match_object(self, expected):
        self.check(matches_object(self.actual, expected), f'to match {repr(expected)}')

    def to_be_greater_than(self, n):
        self.check(self.actual > n, f'to be > {n}')

    def to_be_greater_than_or_equal(self, n):
        self.check(self.actual >= n, f'to be >= {n}')

    def to_be_less_than(self, n):
        self.check(self.actual < n, f'to be < {n}')

    def to_be_less_than_or_equal(self, n):
        self.check(self.actual <= n, f'to be <= {n}')

    def to_be_close_to(self, n, digits=2):
        self.check(abs(self.actual - n) < 10 ** -digits / 2, f'to be close to {n}')

    def to_be_undefined(self):
        self.check(self.actual is None, 'to be undefined')

    def to_be_null(self):
        self.check(self.actual is None, 'to be null')

    def to_be_defined(self):
        self.check(self.actual is not None, 'to be defined')

    def to_be_truthy(self):
        self.check(bool(self.actual), 'to be truthy')

    def to_be_falsy(self):
        self.check(not self.actual, 'to be falsy')

    def to_contain(self, item):
        self.check(item in self.actual, f'to contain {repr(item)}')

    def to_contain_equal(self, item):
        self.check(len([a for a in self.actual if deep_equal(a, item)]) > 0, f'to contain {repr(item)}')

    def to_have_length(self, n):
        self.check(len(self.actual) == n, f'to have length {n}')

    def to_start_with(self, prefix):
        self.check(self.actual.startswith(prefix), f'to start with {repr(prefix)}')

    def to_end_with(self, suffix):
        self.check(self.actual.endswith(suffix), f'to end with {repr(suffix)}')

    def to_throw(self, text=None):
        try:
            self.actual()
        except Exception as e:
            self.check(text is None or text in str(e), f"to throw {repr(text)}")
            return
        self.check(False, 'to throw')


def expect(actual, _message=None):
    return Expect(actual)


# rs2b0t's tests read its objects' fields as attributes, where this client gives some, such as a bank, as dicts.
# record_view adapts a function at the boundary: dicts coming out are Records, Records going in are their dicts, and
# a callback is handed Records.
def _snake(key):
    out = ''
    for c in key:
        out += ('_' + c.lower()) if c.upper() == c and c.lower() != c else c
    return out


def _snaked(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out[_snake(k)] = _snaked(v)
        return out
    if isinstance(value, list):
        return [_snaked(v) for v in value]
    return value


# A dict comes out as a Record of its fields in snake_case, as rs2b0t's tests name them, keeping the dict to hand back.
def as_records(value):
    from rs2004.catalogs import Record
    if isinstance(value, dict):
        record = Record(_snaked(value))
        record._plain = value
        return record
    if isinstance(value, list):
        return [as_records(v) for v in value]
    if isinstance(value, tuple):
        return tuple([as_records(v) for v in value])
    return value


def plain(value):
    """Records as dicts all the way down, for json.dumps."""
    fields = _fields(value)
    if fields is not None:
        out = {}
        for k in fields:
            out[k] = plain(fields[k])
        return out
    if _is_sequence(value):
        return [plain(v) for v in value]
    return value


def _as_plain(value):
    if hasattr(value, '_plain') and value._plain is not None:
        return value._plain
    if hasattr(value, '_fields') and isinstance(value._fields, dict):
        fields = value._fields
        # A fake with methods, such as a navigator, goes in as it is.
        if len([v for v in fields.values() if callable(v)]) > 0:
            return value
        # rs2b0t's tests give a tile as {x, z, level}; here a tile is a Tile.
        if 'x' in fields and 'z' in fields and len([k for k in fields if k not in ('x', 'z', 'level')]) == 0:
            return Tile(fields['x'], fields['z'], fields.get('level', 0))
        return fields
    if callable(value) and not isinstance(value, type):
        return lambda *args: value(*[as_records(a) for a in args])
    return value


def record_view(fn):
    def call(*args):
        out = fn(*[_as_plain(a) for a in args])
        if out is not None and hasattr(out, '__next__'):
            return _records_after(out)
        return as_records(out)
    return call


def _records_after(gen):
    result = yield from gen
    return as_records(result)


class Obj:
    """rs2b0t's plain objects, for code that reads them both as attributes and as a dict: a transport is
    transport['loc_x'] here and transport.locX there. A field not given reads as None."""

    def __init__(self, fields):
        self._fields = fields

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return self._fields.get(name)

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._fields[key] = value

    def __contains__(self, key):
        return key in self._fields

    def get(self, key, default=None):
        return self._fields.get(key, default)

    def items(self):
        return self._fields.items()

    def keys(self):
        return self._fields.keys()

    def __repr__(self):
        return f'Obj({self._fields})'

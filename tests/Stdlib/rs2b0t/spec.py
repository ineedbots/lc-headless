"""rs2b0t's describe, test and expect, for its tests as ts2py drafts them. StdlibTests.cpp runs this before each
test_*.py here, then run_specs(), which runs every test and raises with each failure."""

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


def before_each(body):
    _BEFORE.append(body)


def after_each(body):
    _AFTER.append(body)


def _drain(result):
    # A body drafted as a generator, from rs2b0t's async ones, is run to its end.
    if result is not None and hasattr(result, '__next__'):
        for _ in result:
            pass


def run_specs():
    failures = []
    for name, body in _SPECS:
        try:
            for hook in _BEFORE:
                _drain(hook())
            _drain(body())
        except Exception as e:
            failures.append(f'{name}: {type(e).__name__}: {e}')
        for hook in _AFTER:
            _drain(hook())
    if len(failures) > 0:
        raise AssertionError(f'{len(failures)} of {len(_SPECS)} failed:\n' + '\n'.join(failures))
    if len(_SPECS) == 0:
        raise AssertionError('no tests')


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

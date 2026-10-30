"""Checks Python for what pocketpy, the scripts' VM, does differently from CPython, and silently gets wrong or
refuses to load. Run with CPython over files or folders:

    python -I tools/port/lint.py src/Script/Stdlib scripts

It exits with 1 when it finds something. Each rule comes from a probe of pocketpy 2.2 (see
docs/design/BotApiParityDesign.md §4, "As built").
"""

import ast
import os
import symtable
import sys
import tokenize

# Methods pocketpy's builtin types don't have.
MISSING_METHODS = {
    'isdigit': 'str has no isdigit()',
    'isupper': 'str has no isupper()',
    'islower': 'str has no islower()',
    'isalpha': 'str has no isalpha()',
    'isalnum': 'str has no isalnum()',
    'isspace': 'str has no isspace()',
    'capitalize': 'str has no capitalize()',
    'setdefault': 'dict has no setdefault()',
}
LITERALS = (ast.Constant,)


class Finder(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path
        self.found = []
        self.functions = 0

    def report(self, node, message):
        self.found.append((node.lineno, message))

    def visit_FunctionDef(self, node):
        self.check_defaults(node)
        self.functions += 1
        self.generic_visit(node)
        self.functions -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self.check_defaults(node)
        self.generic_visit(node)

    def check_defaults(self, node):
        defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
        for default in defaults:
            if not is_literal(default):
                self.report(default, 'a default must be a literal')
        if node.args.vararg is not None and node.args.defaults:
            self.report(node, '*args after a parameter with a default')

    def visit_ClassDef(self, node):
        if self.functions > 0:
            self.report(node, 'a class inside a function; pocketpy has classes at module level only')
        names = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
        if '__eq__' in names and '__ne__' not in names:
            self.report(node, 'a class with __eq__ needs __ne__ too')
        self.generic_visit(node)

    def visit_GeneratorExp(self, node):
        self.report(node, "a generator expression doesn't parse; use a list comprehension")
        self.generic_visit(node)

    def check_comprehension(self, node):
        if len(node.generators) > 1:
            self.report(node, "a nested comprehension doesn't parse; use a loop")
        self.generic_visit(node)

    visit_ListComp = check_comprehension
    visit_SetComp = check_comprehension
    visit_DictComp = check_comprehension

    def visit_List(self, node):
        if any(isinstance(e, ast.Starred) for e in node.elts):
            self.report(node, '[*a, b] builds a wrong list without an error; use list(a) + [b]')
        self.generic_visit(node)

    visit_Tuple = visit_List
    visit_Set = visit_List

    def visit_Dict(self, node):
        if any(key is None for key in node.keys):
            self.report(node, '{**a} builds a wrong dict without an error; merge in a loop')
        self.generic_visit(node)

    def visit_Try(self, node):
        if node.finalbody:
            self.report(node, 'pocketpy has no finally')
        self.generic_visit(node)

    def visit_Compare(self, node):
        self.generic_visit(node)

    def visit_FormattedValue(self, node):
        # pocketpy ends an f-string's expression at the first colon, so what follows is read as a format spec.
        for inner in ast.walk(node.value):
            if isinstance(inner, (ast.Slice, ast.Dict, ast.Lambda)):
                self.report(node, "a colon inside an f-string's braces is read as a format spec; compute it first")
                break
        self.generic_visit(node)

    def visit_comprehension(self, node):
        # pocketpy's comprehensions unpack one level: `for i, (a, b) in ...` is a syntax error.
        if isinstance(node.target, ast.Tuple) and any(isinstance(e, ast.Tuple) for e in node.target.elts):
            self.report(node.target, 'a nested tuple target in a comprehension')
        self.generic_visit(node)

    def visit_NamedExpr(self, node):
        self.report(node, 'the walrus operator')
        self.generic_visit(node)

    def visit_Match(self, node):
        self.report(node, 'a match statement')
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id == 'match':
            self.report(node, 'match is a keyword in pocketpy')
        self.generic_visit(node)

    def visit_arg(self, node):
        if node.arg == 'match':
            self.report(node, 'match is a keyword in pocketpy')
        self.generic_visit(node)

    def visit_keyword(self, node):
        if node.arg == 'match':
            self.report(node, 'match is a keyword in pocketpy')
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr == 'match':
            self.report(node, 'match is a keyword in pocketpy')
        self.generic_visit(node)

    def visit_YieldFrom(self, node):
        parent = getattr(node, 'parent', None)
        if not isinstance(parent, (ast.Expr, ast.Assign, ast.AnnAssign)):
            self.report(node, 'yield from only as a statement or the right side of an assignment')
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr in MISSING_METHODS:
                self.report(node, MISSING_METHODS[func.attr])
            if func.attr == 'replace' and len(node.args) == 3:
                self.report(node, 'str.replace takes no count')
        if isinstance(func, ast.Name):
            if func.id in ('min', 'max') and any(k.arg == 'default' for k in node.keywords):
                self.report(node, f'{func.id}() takes no default=')
            # Why: anything but a list or generator of pairs is most often a dict being copied, as dict(x or {}) is.
            if func.id == 'dict' and len(node.args) == 1 and not isinstance(node.args[0], (ast.List, ast.ListComp, ast.GeneratorExp, ast.Tuple, ast.Call)):
                self.report(node, "dict(a_dict) raises; copy with a comprehension")
        self.generic_visit(node)


def is_literal(node):
    if isinstance(node, LITERALS):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        return True
    # A tuple of literals is one too, as tests/Stdlib/test_upkeep.py's ticking() shows.
    return isinstance(node, ast.Tuple) and all(is_literal(e) for e in node.elts)


def link_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def implicit_concatenation(path):
    """Two string literals side by side, which pocketpy doesn't join."""
    found = []
    with open(path, 'rb') as f:
        previous = None
        for token in tokenize.tokenize(f.readline):
            if token.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING):
                if token.type == tokenize.NEWLINE:
                    previous = None
                continue
            # Why: from 3.12 an f-string is FSTRING_START ... FSTRING_END, not one STRING.
            if token.type in (tokenize.STRING, tokenize.FSTRING_START) and previous is not None and previous.type in (tokenize.STRING, tokenize.FSTRING_END):
                found.append((token.start[0], "strings side by side aren't joined; use +"))
            previous = token
    return found


def parenthesised_targets(path):
    """for (a, b) in ...: pocketpy doesn't parse a loop target in brackets, in a comprehension at least."""
    found = []
    with open(path, 'rb') as f:
        previous = None
        for token in tokenize.tokenize(f.readline):
            if token.type == tokenize.OP and token.string in ('(', '[') and previous is not None and previous.type == tokenize.NAME and previous.string == 'for':
                found.append((token.start[0], "a loop target in brackets doesn't parse; write for a, b in ..."))
            if token.type not in (tokenize.NL, tokenize.COMMENT):
                previous = token
    return found


def unicode_escapes(path):
    """\\u, \\U and \\N{...} in a string, which pocketpy rejects as an invalid escape: use chr()."""
    found = []
    with open(path, 'rb') as f:
        for token in tokenize.tokenize(f.readline):
            if token.type not in (tokenize.STRING, tokenize.FSTRING_MIDDLE):
                continue
            text = token.string
            if token.type == tokenize.STRING and text.lstrip('bBfFuU')[:1] in ('r', 'R'):
                continue
            at = 0
            while True:
                at = text.find('\\', at)
                if at < 0 or at + 1 >= len(text):
                    break
                if text[at + 1] in 'uUN':
                    found.append((token.start[0], "pocketpy has no \\u, \\U or \\N escapes; use chr()"))
                    break
                at += 2
    return found


def two_level_closures(source, path):
    """A function nested two deep reading a local of the outermost function: pocketpy gives it a builtin or
    None instead."""
    found = []
    try:
        table = symtable.symtable(source, path, 'exec')
    except SyntaxError:
        return found

    def walk(scope, outers):
        for child in scope.get_children():
            if child.get_type() == 'function':
                if len(outers) >= 2:
                    grand = outers[-2]
                    locals_of_grand = {s.get_name() for s in grand.get_symbols() if s.is_local() or s.is_parameter()}
                    parent_locals = {s.get_name() for s in outers[-1].get_symbols() if s.is_local() or s.is_parameter()}
                    for symbol in child.get_symbols():
                        name = symbol.get_name()
                        if symbol.is_free() and name in locals_of_grand and name not in parent_locals:
                            found.append((child.get_lineno(), f"{child.get_name()} reads {name} from two functions out, which pocketpy can't"))
                walk(child, outers + [child])
            else:
                walk(child, outers)

    walk(table, [])
    return found


# Why: JavaScript assigns an outer let from inside a function, where Python binds a new local and leaves the outer
# one alone, so ts2py's drafts lose the write silently: Fight Arena's stage cache never held a stage, and Troll
# Stronghold's walk guard forgot that its prayer was up.
def rebound_outer_names(tree):
    """A function assigning a module variable without global, or its enclosing function's variable without
    nonlocal. Only plain assignments count: a loop or comprehension variable reusing a name is the usual Python."""
    def bound(target):
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.Tuple, ast.List)):
            return set().union(*[bound(e) for e in target.elts]) if target.elts else set()
        if isinstance(target, ast.Starred):
            return bound(target.value)
        return set()

    module_vars = set()
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        for t in targets:
            module_vars.update(bound(t))

    def own_nodes(fn):
        stack = list(fn.body)
        while stack:
            node = stack.pop()
            yield node
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                stack.extend(ast.iter_child_nodes(node))

    def assigned(fn):
        names = set()
        declared = set()
        for node in own_nodes(fn):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                declared.update(node.names)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
            for t in targets:
                names.update(bound(t))
        return names - declared

    def params(fn):
        a = fn.args
        return {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | {x.arg for x in [a.vararg, a.kwarg] if x}

    def meant_outer(fn, name):
        """Whether the function reads the name before it writes it, or only writes it: either way it meant the
        outer one. A local that's written and then read is an ordinary shadow."""
        reads = []
        writes = []
        for node in own_nodes(fn):
            if isinstance(node, ast.AugAssign) and name in bound(node.target):
                reads.append((node.lineno, node.col_offset))
            if isinstance(node, ast.Name) and node.id == name:
                (reads if isinstance(node.ctx, ast.Load) else writes).append((node.lineno, node.col_offset))
            if isinstance(node, ast.Assign) and any(name in bound(t) for t in node.targets):
                if any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node.value)):
                    reads.append((node.lineno, -1))
        if not reads:
            return True
        return min(reads) < min(writes)

    found = []

    def walk(node, enclosing):
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, enclosing)
                continue
            mine = {name for name in assigned(child) - params(child) if meant_outer(child, name)}
            for name in sorted(mine & module_vars):
                found.append((child.lineno, f'{child.name} assigns {name} as a new local; the module variable needs global'))
            if enclosing is not None:
                outer = assigned(enclosing) | params(enclosing)
                for name in sorted((mine & outer) - module_vars):
                    found.append((child.lineno, f"{child.name} assigns {name} as a new local; {enclosing.name}'s needs nonlocal or a holder"))
            walk(child, child)

    walk(tree, None)
    return found


# Why: a closure reads its loop's variable when it runs, not when it's made, and a spec's test() runs its body after
# the loop has ended, so every test of a for-loop of cases checked the last case: Fight Arena's journal stages did.
def loop_closures(tree):
    """A def made in a for loop's body and handed to test() there, reading the loop's variable."""
    found = []
    for loop in ast.walk(tree):
        if not isinstance(loop, ast.For):
            continue
        names = {n.id for n in ast.walk(loop.target) if isinstance(n, ast.Name)}
        deferred = set()
        for statement in loop.body:
            for call in ast.walk(statement):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'test':
                    deferred.update(a.id for a in call.args if isinstance(a, ast.Name))
        for statement in loop.body:
            for fn in ast.walk(statement):
                if not isinstance(fn, ast.FunctionDef) or fn.name not in deferred:
                    continue
                own = {a.arg for a in fn.args.args}
                inner = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - own
                for name in sorted(names & inner):
                    found.append((fn.lineno, f'{fn.name} reads the loop variable {name} when test() runs it, after the loop has moved on; pass it to a function that returns the closure'))
    return found


# Why: ts2py flattens rs2b0t's options objects into parameters, and an option can share a module function's name:
# Observatory Quest's supply(snap, planks, ...) then called its own boolean planks(snap).
def shadowed_callees(tree):
    """A parameter named like a module-level function or import that the function's body both reads and calls."""
    module_callables = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            module_callables.add(node.name)
        elif isinstance(node, ast.ImportFrom):
            module_callables.update(a.asname or a.name for a in node.names)
    found = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        names = {a.arg for a in fn.args.args + fn.args.kwonlyargs} & module_callables
        callees = {id(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        # A callback parameter is only ever called; one also read as a value is the option that hid the function.
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and id(n) not in callees} & names
        for call in ast.walk(fn):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in names:
                found.append((call.lineno, f'{fn.name} calls {call.func.id}, which its parameter of that name hides'))
    return sorted(set(found))


def nested_ternaries(tree, source):
    """A conditional expression holding another without brackets, which pocketpy won't parse."""
    found = []
    lines = source.split('\n')
    for node in ast.walk(tree):
        if not isinstance(node, ast.IfExp):
            continue
        for part in (node.body, node.orelse, node.test):
            if isinstance(part, ast.IfExp):
                before = lines[part.lineno - 1][:part.col_offset].rstrip()
                if not before.endswith('('):
                    found.append((part.lineno, 'a conditional expression inside another needs brackets'))
    return found


# Why: pocketpy calls a class's method before a function set on the instance under the same name (a plain value set
# there does win), so obj.opened = fn under a method named opened is silently ignored; the clue executor's test world
# lost its casket hook that way.
def shadowed_methods(tree):
    """A function (a lambda, or a def local to the same function) set as an attribute named like a method of a class
    in this file."""
    methods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods.update(n.name for n in node.body if isinstance(n, ast.FunctionDef))
    found = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        local_defs = set(n.name for n in fn.body if isinstance(n, ast.FunctionDef))
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            if not (isinstance(value, ast.Lambda) or (isinstance(value, ast.Name) and value.id in local_defs)):
                continue
            for t in node.targets:
                if isinstance(t, ast.Attribute) and t.attr in methods:
                    found.append((t.lineno, f'.{t.attr} = a function is ignored where {t.attr} is also a method: pocketpy calls the method'))
    return sorted(set(found))


_SCRIPT_BUILTINS = None
PYTHON_BUILTINS = set(dir(__builtins__) if isinstance(__builtins__, type(os)) else __builtins__.keys())


def script_builtins():
    """Every name a script gets without an import: CPython's builtins and the scripts' builtins stub."""
    global _SCRIPT_BUILTINS
    if _SCRIPT_BUILTINS is None:
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(repo, 'scripts', 'typings', '__builtins__.pyi'), encoding='utf-8') as f:
            stub = ast.parse(f.read())
        names = set(dir(__builtins__) if isinstance(__builtins__, type(os)) else __builtins__.keys())
        for node in stub.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, ast.Assign):
                names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        _SCRIPT_BUILTINS = names
    return _SCRIPT_BUILTINS


_CORE_BUILTINS = None


def core_builtins():
    """What a stdlib module gets without an import: CPython's builtins and the names the C++ binds, which are the
    stub's names that no stdlib module defines."""
    global _CORE_BUILTINS
    if _CORE_BUILTINS is None:
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        python_layer = set()
        # Why: a quest's module is imported by its full name, never a builtin, so its own BANK doesn't hide the binding.
        quest_defs = os.path.join('rs2004', 'quests', 'defs') + os.sep
        for path in files([os.path.join(repo, 'src', 'Script', 'Stdlib')]):
            if quest_defs in os.path.normpath(path):
                continue
            with open(path, encoding='utf-8') as f:
                tree = ast.parse(f.read(), path)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    python_layer.add(node.name)
                elif isinstance(node, ast.Assign):
                    python_layer.update(t.id for t in node.targets if isinstance(t, ast.Name))
        _CORE_BUILTINS = PYTHON_BUILTINS | (script_builtins() - python_layer)
    return _CORE_BUILTINS


# Why: a name a bot forgot to import loads fine and raises only when the line runs, which a live run found after
# 30 minutes of other bots passing: JiveKQ's on_start used sustain without importing it.
def undefined_names(tree, path):
    """Names a script under scripts/ reads that nothing defines, imports or makes a builtin. Scoping is file-wide:
    a name defined anywhere counts, so this finds the forgotten import, not every scoping slip. A stdlib module
    is held to CPython's builtins alone."""
    parts = os.path.abspath(path).replace('\\', '/').split('/')
    in_stdlib = 'Stdlib' in parts and 'tests' not in parts
    if ('scripts' not in parts and not in_stdlib) or 'typings' in parts \
            or any(isinstance(n, ast.ImportFrom) and any(a.name == '*' for a in n.names) for n in ast.walk(tree)):
        return []
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
        elif isinstance(node, ast.arg):
            defined.add(node.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            defined.update((a.asname or a.name).split('.')[0] for a in node.names)
        elif isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            defined.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)
    # Why: a stdlib module gets the C++ bindings but not the Python layer, which it must import.
    known = core_builtins() if in_stdlib else script_builtins()
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in defined and node.id not in known:
            found.setdefault(node.id, node.lineno)
    return [(line, f'{name} is never defined or imported') for name, line in found.items()]


def lint(path):
    with open(path, encoding='utf-8') as f:
        source = f.read()
    try:
        tree = ast.parse(source, path)
    except SyntaxError as e:
        return [(e.lineno or 0, f'a syntax error: {e.msg}')]
    link_parents(tree)
    finder = Finder(path)
    finder.visit(tree)
    found = finder.found + nested_ternaries(tree, source) + implicit_concatenation(path) + parenthesised_targets(path) + unicode_escapes(path) + two_level_closures(source, path) + rebound_outer_names(tree) + loop_closures(tree) + shadowed_callees(tree)
    return sorted(set(found + undefined_names(tree, path) + shadowed_methods(tree)))


def files(paths):
    for path in paths:
        if os.path.isdir(path):
            for folder, _, names in os.walk(path):
                for name in sorted(names):
                    if name.endswith('.py'):
                        yield os.path.join(folder, name)
        else:
            yield path


def required_params(trees):
    """Each function name's parameters without a default, in every def of that name across the files."""
    found = {}
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                found.setdefault(node.name, []).append(_required(node))
            elif isinstance(node, ast.ClassDef):
                # A class is called by its name, so its __init__'s parameters, less self, count under that name.
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        found.setdefault(node.name, []).append(_required(item) - {'self'})
    return found


def _required(node):
    args = node.args
    positional = args.posonlyargs + args.args
    return {a.arg for a in positional[:len(positional) - len(args.defaults)]}


def keywords_to_required(trees):
    """A keyword naming a parameter without a default, which pocketpy binds only by position."""
    required = required_params(trees)
    found = {}
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.keywords:
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
            defs = required.get(name)
            if not defs:
                continue
            for keyword in node.keywords:
                if keyword.arg is not None and all(keyword.arg in r for r in defs):
                    found.setdefault(path, []).append((node.lineno, f"{name}'s {keyword.arg} has no default, so pocketpy takes it by position only"))
    return found


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    total = 0
    paths = list(files(argv[1:]))
    # Why: a call's definitions are looked up in the stdlib and scripts too, whichever files are linted.
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    known = [os.path.join(repo, 'src', 'Script', 'Stdlib'), os.path.join(repo, 'scripts')]
    trees = {}
    for path in paths + list(files(known)):
        key = os.path.abspath(path)
        if key in trees:
            continue
        try:
            with open(path, encoding='utf-8') as f:
                trees[key] = ast.parse(f.read(), path)
        except SyntaxError:
            pass
    cross = keywords_to_required(trees)
    for path in paths:
        for line, message in sorted(set(lint(path) + cross.get(os.path.abspath(path), []))):
            print(f'{path}:{line}: {message}')
            total += 1
    print('nothing found' if total == 0 else f'{total} found')
    return 0 if total == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

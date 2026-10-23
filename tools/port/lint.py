"""Checks Python for what pocketpy, the scripts' VM, does differently from CPython, and silently gets wrong or
refuses to load. Run with CPython over files or folders:

    python -I tools/port/lint.py src/Script/Stdlib scripts

It exits with 1 when it finds something. Each rule comes from a probe of pocketpy 2.2 (see
docs/BotApiParityDesign.md §4, "As built").
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
            # Why: a name or attribute is most often a dict being copied; a list of pairs is built in place.
            if func.id == 'dict' and len(node.args) == 1 and isinstance(node.args[0], (ast.Dict, ast.DictComp, ast.Name, ast.Attribute)):
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
    found = finder.found + implicit_concatenation(path) + two_level_closures(source, path)
    return sorted(set(found))


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
                args = node.args
                positional = args.posonlyargs + args.args
                required = {a.arg for a in positional[:len(positional) - len(args.defaults)]}
                found.setdefault(node.name, []).append(required)
    return found


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

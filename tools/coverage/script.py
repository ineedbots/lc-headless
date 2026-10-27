"""Collect embedded stdlib line coverage: python3 tools/coverage/script.py.

Uses pocketpy in the application tests, not CPython tracing. Supports Linux Clang and Windows MSVC.
"""

import argparse
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
STDLIB = ROOT / "src" / "Script" / "Stdlib"
STYLE = """body{font:15px system-ui;margin:2rem;color:#202124}a{color:#1558a6}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:.25rem .6rem;border-bottom:1px solid #ddd}
pre{margin:0;white-space:pre-wrap}tr.hit{background:#e6f4ea}tr.miss{background:#fce8e6}
.number{width:4rem;color:#555}.count{width:5rem}.partial{color:#a21b14;font-weight:bold}"""


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def executable_lines(manifest_path):
    manifest = load(manifest_path)
    if manifest.get("version") != 1 or not manifest.get("files"):
        raise RuntimeError("Missing or unsupported script coverage manifest")
    sources = {path.relative_to(STDLIB).as_posix(): path for path in STDLIB.rglob("*.py")}
    if set(sources) != set(manifest["files"]):
        raise RuntimeError("Embedded stdlib files differ from this checkout; rebuild before collecting coverage")
    counts = {}
    for name, source in sources.items():
        entry = manifest["files"][name]
        text = source.read_bytes().decode("utf-8")
        if entry["source"] != text:
            raise RuntimeError(f"Embedded source differs from {source}; rebuild before collecting coverage")
        lines = entry["lines"]
        if any(type(line) is not int or line < 1 or line > len(text.splitlines()) for line in lines):
            raise RuntimeError(f"Invalid executable-line map: {name}")
        counts[name] = dict.fromkeys(lines, 0)
    return counts


def merge(manifest_path, raw):
    counts = executable_lines(manifest_path)
    profiles = sorted(raw.glob("*.json"))
    if not profiles:
        raise RuntimeError("Tests produced no script coverage profiles")
    for path in profiles:
        profile = load(path)
        if profile.get("version") != 1 or profile.get("failed") is not False:
            raise RuntimeError(f"Invalid or failed script coverage profile: {path}")
        for name, hits in profile["files"].items():
            if name not in counts:
                raise RuntimeError(f"Profile contains a non-stdlib file: {name}")
            for line, count in hits.items():
                number = int(line)
                if number not in counts[name] or type(count) is not int or count < 0:
                    raise RuntimeError(f"Trace does not match executable-line map: {name}:{line}")
                counts[name][number] += count
    if not any(count > 0 for lines in counts.values() for count in lines.values()):
        raise RuntimeError("Script coverage contains no executed stdlib lines")
    return counts


def percent(covered, total):
    return 100 * covered / total if total else 100.0


def page(title, body, stylesheet="style.css"):
    return (f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f'<link rel="stylesheet" href="{stylesheet}"><body>{body}</body></html>')


def report(counts, output, partial=False):
    files = {}
    lcov = []
    rows = []
    summary = ["Stdlib line coverage (pocketpy)", "File  Covered / Executable  Percent"]
    html_dir = output / "html"
    html_dir.mkdir()
    (html_dir / "style.css").write_text(STYLE, encoding="utf-8")
    for name, lines in sorted(counts.items()):
        covered = sum(value > 0 for value in lines.values())
        total = len(lines)
        value = percent(covered, total)
        files[name] = {"covered": covered, "executable": total, "percent": value}
        summary.append(f"{name}  {covered} / {total}  {value:.2f}%")
        repo_path = "src/Script/Stdlib/" + name
        lcov.extend(["TN:", f"SF:{repo_path}"])
        lcov.extend(f"DA:{line},{count}" for line, count in sorted(lines.items()))
        lcov.extend([f"LF:{total}", f"LH:{covered}", "end_of_record"])
        rows.append(f'<tr><td><a href="files/{html.escape(name)}.html">{html.escape(name)}</a></td>'
                    f'<td>{covered} / {total}</td><td>{value:.2f}%</td></tr>')
        source_rows = []
        text = (STDLIB / name).read_bytes().decode("utf-8")
        for line, source in enumerate(text.splitlines(), 1):
            count = lines.get(line)
            status = "" if count is None else ("hit" if count else "miss")
            display = "" if count is None else str(count)
            source_rows.append(f'<tr class="{status}" id="L{line}"><td class="number">'
                               f'<a href="#L{line}">{line}</a></td><td class="count">{display}</td>'
                               f'<td><pre>{html.escape(source)}</pre></td></tr>')
        destination = html_dir / "files" / (name + ".html")
        destination.parent.mkdir(parents=True, exist_ok=True)
        stylesheet = os.path.relpath(html_dir / "style.css", destination.parent).replace("\\", "/")
        index = os.path.relpath(html_dir / "index.html", destination.parent).replace("\\", "/")
        destination.write_text(page(name, f'<a href="{index}">All files</a><h1>{html.escape(name)}</h1>'
                                    f'<p>{covered} / {total} executable lines ({value:.2f}%). '
                                    'Counts are pocketpy line trace events.</p><table>'
                                    + "".join(source_rows) + "</table>", stylesheet), encoding="utf-8")

    covered = sum(item["covered"] for item in files.values())
    total = sum(item["executable"] for item in files.values())
    totals = {"covered": covered, "executable": total, "percent": percent(covered, total)}
    summary.append(f"TOTAL  {covered} / {total}  {totals['percent']:.2f}%")
    if partial:
        summary.insert(1, "PARTIAL: tests failed; these results are incomplete.")
    result = "\n".join(summary) + "\n"
    (output / "summary.txt").write_text(result, encoding="utf-8")
    (output / "summary.json").write_text(json.dumps({"version": 1, "partial": partial,
                                                   "totals": totals, "files": files}, indent=2) + "\n",
                                         encoding="utf-8")
    (output / "coverage.lcov").write_text("\n".join(lcov) + "\n", encoding="utf-8")
    warning = '<p class="partial">PARTIAL: tests failed; these results are incomplete.</p>' if partial else ""
    (html_dir / "index.html").write_text(page("Stdlib line coverage",
        f'<h1>Stdlib line coverage</h1>{warning}<p>{covered} / {total} executable lines '
        f'({totals["percent"]:.2f}%). All embedded stdlib modules are included.</p>'
        '<p>Real-cache tests skip without cache data; hidden Slow tests are excluded.</p>'
        '<table><tr><th>File</th><th>Covered / executable</th><th>Coverage</th></tr>'
        + "".join(rows) + "</table>"), encoding="utf-8")
    print(result, flush=True)


def collect(binary, output, parallel, preset):
    if output.exists():
        shutil.rmtree(output)
    raw = output / "raw"
    raw.mkdir(parents=True)
    env = os.environ.copy()
    env.pop("RS2004_SCRIPT_COVERAGE_DIR", None)
    env["RS2004_SCRIPT_COVERAGE_MANIFEST"] = str(output / "manifest.json")
    # Also permits reusing the native coverage build without racing on default.profraw.
    env["LLVM_PROFILE_FILE"] = str(output / f"native-%{parallel}m.profraw")
    subprocess.run([binary, "[ScriptCoverageManifest]"], cwd=ROOT, env=env, check=True)
    executable_lines(output / "manifest.json")
    env.pop("RS2004_SCRIPT_COVERAGE_MANIFEST")
    env["RS2004_SCRIPT_COVERAGE_DIR"] = str(raw)
    result = subprocess.run(["ctest", "--preset", preset, "--parallel", str(parallel), "--no-tests=error"],
                            cwd=ROOT, env=env, check=False)
    counts = merge(output / "manifest.json", raw)
    report(counts, output, partial=result.returncode != 0)
    print(f"HTML report: {output / 'html' / 'index.html'}", flush=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = "windows-script-coverage" if sys.platform == "win32" else "linux-script-coverage"
    parser.add_argument("--preset", default=default, help="matching configure/build/test preset (Debug)")
    parser.add_argument("--no-build", action="store_true", help="use an existing build")
    parser.add_argument("--parallel", type=int, default=4)
    args = parser.parse_args()
    if args.parallel < 1:
        parser.error("--parallel must be positive")
    # Preset names also select the output directory under build/.
    if not args.preset or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in args.preset):
        parser.error("--preset must be a simple preset name")
    if not args.no_build:
        subprocess.run(["cmake", "--preset", args.preset], cwd=ROOT, check=True)
        subprocess.run(["cmake", "--build", "--preset", args.preset, "--parallel", str(args.parallel)],
                       cwd=ROOT, check=True)
    build = ROOT / "build" / args.preset
    binary = load(build / "test-runtime-Debug.json")["tests"]
    return collect(binary, build / "script-coverage", args.parallel, args.preset)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Script coverage failed: {error}", file=sys.stderr)
        sys.exit(1)

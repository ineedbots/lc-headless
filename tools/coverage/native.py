"""Build and run the native coverage suite: python3 tools/coverage/native.py.

Requires Linux, vcpkg, and matching Clang/llvm-cov/llvm-profdata installations.
Reports stay under build/linux-coverage/coverage; normal builds are unaffected.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build" / "linux-coverage"


def run(command, **kwargs):
    display = command
    coverage_command = "-sources" in command
    if coverage_command:
        display = command[:command.index("-sources")] + ["-sources", "<project sources>"]
        kwargs.update(stderr=subprocess.PIPE, text=True)
    print("+ " + " ".join(map(str, display)), flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False, **kwargs)
    if coverage_command and result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    result.check_returncode()
    # LLVM can report mapping mismatches but still return success. Check stderr directly
    # because --fatal-warnings is not supported by every llvm-cov version.
    if coverage_command and "warning:" in result.stderr:
        raise RuntimeError("LLVM coverage emitted warnings; the report cannot be trusted")
    return result


def major_version(tool):
    result = subprocess.run([tool, "--version"], check=True, capture_output=True, text=True)
    match = re.search(r"version\s+(\d+)", result.stdout + result.stderr, re.IGNORECASE)
    if not match:
        raise RuntimeError(f"Cannot determine LLVM version: {tool}")
    return int(match[1])


def llvm_tool(name, compiler, major):
    # Prefer the compiler's siblings, then versioned and unversioned PATH tools.
    candidates = [Path(compiler).parent / name, f"{name}-{major}", name]
    for candidate in candidates:
        found = shutil.which(str(candidate))
        if found and major_version(found) == major:
            return found
    raise RuntimeError(f"Install {name} matching Clang {major} (including its major version)")


def collect(manifest, output, parallel):
    compiler = manifest["compiler"]
    major = major_version(compiler)
    profdata = llvm_tool("llvm-profdata", compiler, major)
    cov = llvm_tool("llvm-cov", compiler, major)
    for key in ("application", "tests", "entrypoint"):
        path = manifest.get(key)
        if not path or not Path(path).is_file():
            raise RuntimeError(f"Missing {key}: {path or 'not in coverage manifest'}; rebuild linux-coverage first")

    # Only clear this runner's fixed output directory, never a caller-supplied path.
    if output.exists():
        shutil.rmtree(output)
    raw = output / "raw"
    raw.mkdir(parents=True)
    env = os.environ.copy()
    # LLVM locks and merges a bounded pool of profiles as processes exit. One file per test
    # would write several gigabytes for this suite; the pool still supports parallel CTest runs.
    env["LLVM_PROFILE_FILE"] = str(raw / f"%{parallel}m.profraw")
    test_result = subprocess.run(
        ["ctest", "--preset", "linux-coverage", "--parallel", str(parallel), "--no-tests=error"],
        cwd=ROOT, env=env, check=False,
    )

    profiles = sorted(raw.glob("*.profraw"))
    if not profiles:
        raise RuntimeError(f"CTest exited {test_result.returncode} and produced no coverage profiles")
    # Use a response file so profile paths remain quoted, including checkout paths with spaces.
    inputs = output / "profiles.rsp"
    inputs.write_text("".join(json.dumps(str(path)) + "\n" for path in profiles), encoding="utf-8")
    merged = output / "coverage.profdata"
    run([profdata, "merge", "-sparse", "@" + str(inputs), "-o", str(merged)])

    # Explicit source selection excludes tests, dependencies and generated embedded Python.
    sources = sorted(str(path) for path in (ROOT / "src").rglob("*")
                     if path.suffix in (".cpp", ".hpp"))
    common = [manifest["tests"], "-object", manifest["entrypoint"], "-instr-profile", str(merged)]
    selection = ["-sources", *sources]
    summary = run([cov, "report", *common, *selection], stdout=subprocess.PIPE, text=True).stdout
    (output / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary, flush=True)
    with (output / "summary.json").open("w", encoding="utf-8") as report:
        run([cov, "export", "-summary-only", *common, *selection], stdout=report)
    data = json.loads((output / "summary.json").read_text(encoding="utf-8"))["data"]
    if not data or sum(item["totals"]["lines"]["covered"] for item in data) == 0:
        raise RuntimeError("Coverage report contains no executed project lines")
    with (output / "coverage.lcov").open("w", encoding="utf-8") as report:
        run([cov, "export", "-format=lcov", *common, *selection], stdout=report)
    run([cov, "show", "-format=html", "-show-line-counts-or-regions", "-show-branches=count",
         "-output-dir", str(output / "html"), *common, *selection], stdout=subprocess.DEVNULL)

    print(f"HTML report: {output / 'html' / 'index.html'}", flush=True)
    print("Real-cache tests skip without cache data; hidden [Slow] tests are not part of this baseline.")
    if test_result.returncode:
        print("Tests failed; the generated coverage report is partial.", file=sys.stderr)
    return test_result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-build", action="store_true", help="collect from an existing coverage build")
    parser.add_argument("--parallel", type=int, default=4, help="build and test parallelism (default: 4)")
    args = parser.parse_args()
    if args.parallel < 1:
        parser.error("--parallel must be positive")
    if sys.platform != "linux":
        parser.error("Native coverage currently requires Linux Clang")
    if not args.no_build:
        run(["cmake", "--preset", "linux-coverage"])
        run(["cmake", "--build", "--preset", "linux-coverage", "--parallel", str(args.parallel)])
    manifest = json.loads((BUILD / "coverage-Debug.json").read_text(encoding="utf-8"))
    return collect(manifest, BUILD / "coverage", args.parallel)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Native coverage failed: {error}", file=sys.stderr)
        sys.exit(1)

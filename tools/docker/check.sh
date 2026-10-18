#!/usr/bin/env bash
# Builds and tests the linux-clang preset in Docker, on Ubuntu 24.04 and Arch, in Debug and Release:
#
#     tools/docker/check.sh              # both
#     tools/docker/check.sh ubuntu       # one
#
# The source is mounted read-only, so the checkout is never touched. Logs go to build/docker/<distro>/. Each distro
# keeps vcpkg's binary cache in the volume rs2004-vcpkg-<distro>, so only the first run builds Boost and OpenSSL.
# Works from Linux and from Git Bash on Windows.
set -euo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
here="$root/tools/docker"
distros=("$@")
if [ ${#distros[@]} -eq 0 ]; then
    distros=(ubuntu arch)
fi

# Docker Desktop on Windows takes Windows paths, and Git Bash would rewrite /src and /out without this.
export MSYS_NO_PATHCONV=1
hostPath() {
    if command -v cygpath > /dev/null; then
        cygpath -w "$1"
    else
        echo "$1"
    fi
}

for distro in "${distros[@]}"; do
    if [ ! -f "$here/Dockerfile.$distro" ]; then
        echo "No Dockerfile.$distro in tools/docker" >&2
        exit 2
    fi

    echo "Building the $distro image"
    docker build -q -t "rs2004-linux:$distro" -f "$(hostPath "$here/Dockerfile.$distro")" "$(hostPath "$here")" > /dev/null
done

pids=()
for distro in "${distros[@]}"; do
    out="$root/build/docker/$distro"
    mkdir -p "$out"
    docker run --rm \
        -v "$(hostPath "$root"):/src:ro" \
        -v "$(hostPath "$out"):/out" \
        -v "rs2004-vcpkg-$distro:/root/.cache/vcpkg" \
        "rs2004-linux:$distro" bash /src/tools/docker/run-tests.sh > "$out/summary.log" 2>&1 &
    pids+=($!)
done

failed=0
for i in "${!distros[@]}"; do
    status=0
    wait "${pids[$i]}" || status=$?
    echo "== ${distros[$i]} (exit $status)"
    cat "$root/build/docker/${distros[$i]}/summary.log"
    if [ "$status" -ne 0 ]; then
        failed=1
    fi
done

exit "$failed"

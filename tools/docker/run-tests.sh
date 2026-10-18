#!/usr/bin/env bash
# Runs inside a container made by check.sh: copies the read-only source at /src, then configures with the linux-clang
# preset, and builds and tests linux-debug and linux-release. Full logs go to /out.
set -uo pipefail

rsync -a --delete --exclude build/ --exclude data/cache/ --exclude '*.log' --exclude progress/ /src/ /work/
cd /work

clang++ --version | head -n 1
cmake --version | head -n 1

if ! cmake --preset linux-clang > /out/configure.log 2>&1; then
    echo "configure failed:"
    tail -n 40 /out/configure.log
    exit 1
fi

failed=0
for config in debug release; do
    if ! cmake --build --preset "linux-$config" -j"$(nproc)" > "/out/build-$config.log" 2>&1; then
        echo "$config: build failed:"
        grep -E "error|warning:" "/out/build-$config.log" | head -n 60
        failed=1
        continue
    fi

    echo "$config: built, $(grep -c 'warning:' "/out/build-$config.log") warnings"
    if ! ctest --preset "linux-$config" -j"$(nproc)" > "/out/test-$config.log" 2>&1; then
        failed=1
    fi

    grep -E "tests passed|\((Failed|Timeout|Subprocess aborted|Exception)\)" "/out/test-$config.log"
done

exit "$failed"

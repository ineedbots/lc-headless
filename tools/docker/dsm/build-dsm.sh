#!/bin/bash
set -euo pipefail

mkdir -p /work/vcpkg-cache
export VCPKG_DEFAULT_BINARY_CACHE=/work/vcpkg-cache
export VCPKG_MAX_CONCURRENCY="$DSM_BUILD_JOBS"

cmake --preset linux-clang -B /work/build \
    -DCMAKE_C_COMPILER=/usr/bin/clang-19 \
    -DCMAKE_CXX_COMPILER=/usr/bin/clang++-19 \
    -DCMAKE_CXX_FLAGS=-stdlib=libc++ \
    -DVCPKG_OVERLAY_TRIPLETS=/opt/dsm-triplets \
    -DVCPKG_TARGET_TRIPLET=x64-linux-dsm

cmake --build /work/build --config Release \
    --target Rs2004Headless --parallel "$DSM_BUILD_JOBS"

install -d /out/dsm-runtime
install -m 644 /usr/lib/x86_64-linux-gnu/{libc++.so.1,libc++abi.so.1,libunwind.so.1} /out/dsm-runtime/
install -m 755 /work/build/Release/Rs2004Headless /out/Rs2004Headless-dsm

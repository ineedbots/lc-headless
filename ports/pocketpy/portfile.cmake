vcpkg_check_linkage(ONLY_STATIC_LIBRARY)

vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO pocketpy/pocketpy
    REF "v${VERSION}"
    SHA512 ef7c5b9e8c3f2fc1f2ac8637adb3b3055e6372ad7bb40063c8c6a858be9aa4b4125b5ddee76a32649265f3f8b6e21cf891203457412f3b391ef0ed24af7cd673
    HEAD_REF main
)

# Upstream marks the API dllexport on Windows even in a static build, which would export every
# pocketpy function from the executable that links it.
vcpkg_replace_string("${SOURCE_PATH}/include/pocketpy/export.h"
    "#define PK_API __declspec(dllexport)"
    "#define PK_API")

# Release builds __forceinline public functions such as py_retval. Without dllexport, MSVC's C compiler
# then emits no callable copy of them, so they're made plain functions; the unity build in
# CMakeLists.txt still lets the compiler inline them inside the library.
vcpkg_replace_string("${SOURCE_PATH}/include/pocketpy/export.h"
    "#define PK_INLINE __forceinline"
    "#define PK_INLINE")

# Upstream's fix after 2.2.0: a traceback frame's locals and globals are only filled in while the debugger
# is attached, but the GC marks them on every exception, so otherwise it follows uninitialized memory.
# upstream commit: de8351ed0f5646cf3117bc4009afce14bfbfaa47
vcpkg_replace_string("${SOURCE_PATH}/src/public/PyException.c"
    "    BaseExceptionFrame* frame_dump = c11_vector__emplace(&ud->stacktrace);"
    "    BaseExceptionFrame* frame_dump = c11_vector__emplace(&ud->stacktrace);
    py_newnil(&frame_dump->locals);
    py_newnil(&frame_dump->globals);")

# A yielded generator detaches its frame without VM__pop_frame (which would destroy it). It must still
# send the matching trace event: resuming sends PUSH again. Otherwise the profiler retains suspended
# frames, eventually dereferencing a cleared prev_line when a later, empty hook ends profiling.
vcpkg_replace_string("${SOURCE_PATH}/src/interpreter/generator.c"
    "    if(res == RES_YIELD) {"
    "    if(res == RES_YIELD) {
        if(vm->trace_info.func) vm->trace_info.func(vm->top_frame, TRACE_EVENT_POP);")

# The watchdog's deadline uses clock(), which is wall time on Windows but CPU time on Linux, so on Linux
# a call blocked in a binding never times out. It's moved to the monotonic clock, in 64-bit nanoseconds
# because clock_t is a 32-bit long on Windows.
vcpkg_replace_string("${SOURCE_PATH}/include/pocketpy/pocketpy.h"
    "int64_t time_ns();"
    "int64_t time_ns();
int64_t time_monotonic_ns();")
vcpkg_replace_string("${SOURCE_PATH}/include/pocketpy/interpreter/vm.h"
    "clock_t max_reset_time;"
    "int64_t max_reset_time;")
vcpkg_replace_string("${SOURCE_PATH}/src/modules/pkpy.c"
    "info->max_reset_time = clock() + (timeout * (CLOCKS_PER_SEC / 1000));"
    "info->max_reset_time = time_monotonic_ns() + timeout * 1000000;")
vcpkg_replace_string("${SOURCE_PATH}/src/interpreter/ceval.c"
    "clock() > self->watchdog_info.max_reset_time"
    "time_monotonic_ns() > self->watchdog_info.max_reset_time")

# On Windows the monotonic clock multiplies the performance counter's ticks by a billion before dividing,
# which overflows once the machine has been up for about 15 minutes at the usual 10 MHz counter.
vcpkg_replace_string("${SOURCE_PATH}/src/modules/time.c"
    "return (ticksll * NANOS_PER_SEC) / freq.QuadPart;"
    "return (ticksll / freq.QuadPart) * NANOS_PER_SEC + (ticksll % freq.QuadPart) * NANOS_PER_SEC / freq.QuadPart;")

# Upstream's CMakeLists has no install rules, so the port builds the sources with its own.
file(COPY "${CMAKE_CURRENT_LIST_DIR}/CMakeLists.txt" DESTINATION "${SOURCE_PATH}")

vcpkg_cmake_configure(SOURCE_PATH "${SOURCE_PATH}")
vcpkg_cmake_install()
vcpkg_cmake_config_fixup()

file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")

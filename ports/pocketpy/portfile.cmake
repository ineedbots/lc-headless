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

# Upstream's CMakeLists has no install rules, so the port builds the sources with its own.
file(COPY "${CMAKE_CURRENT_LIST_DIR}/CMakeLists.txt" DESTINATION "${SOURCE_PATH}")

vcpkg_cmake_configure(SOURCE_PATH "${SOURCE_PATH}")
vcpkg_cmake_install()
vcpkg_cmake_config_fixup()

file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")

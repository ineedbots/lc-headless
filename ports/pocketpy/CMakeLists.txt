cmake_minimum_required(VERSION 3.25)
project(pocketpy VERSION 2.2.0 LANGUAGES C)

include(GNUInstallDirs)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

file(GLOB_RECURSE POCKETPY_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/*.c)

add_library(pocketpy STATIC ${POCKETPY_SOURCES})

# One translation unit, as upstream builds it, so internal calls inline across source files.
set_target_properties(pocketpy PROPERTIES UNITY_BUILD ON UNITY_BUILD_MODE GROUP)
set_source_files_properties(${POCKETPY_SOURCES} PROPERTIES UNITY_GROUP pocketpy)

target_include_directories(pocketpy PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

# The feature switches change declarations in the public headers, so consumers see the same values
# the library was built with.
target_compile_definitions(pocketpy
    PUBLIC
        PK_ENABLE_OS=1
        PK_ENABLE_THREADS=0
        PK_ENABLE_DLL=0
        PK_ENABLE_DETERMINISM=0
        PK_ENABLE_WATCHDOG=1
        PK_ENABLE_CUSTOM_SNAME=0
        PK_ENABLE_MIMALLOC=0
    PRIVATE
        $<$<BOOL:${WIN32}>:_CRT_SECURE_NO_WARNINGS>)

if(MSVC)
    target_compile_options(pocketpy PRIVATE /utf-8 /wd4267 /wd4244 /wd4146 /wd4819)
elseif(NOT APPLE)
    target_compile_options(pocketpy PRIVATE -Wno-pointer-to-int-cast -Wno-int-to-pointer-cast)
endif()

if(WIN32)
    target_link_libraries(pocketpy PUBLIC ws2_32)
endif()

install(TARGETS pocketpy EXPORT pocketpy-targets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES include/pocketpy.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(DIRECTORY include/pocketpy DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT pocketpy-targets
    NAMESPACE pocketpy::
    FILE pocketpy-config.cmake
    DESTINATION share/pocketpy)

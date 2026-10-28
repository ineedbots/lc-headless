cmake_minimum_required(VERSION 3.25)
project(Rs2004Headless VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)    # for clangd / tooling
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)

include(cmake/Coverage.cmake)

find_package(boost_asio CONFIG REQUIRED)
find_package(boost_beast CONFIG REQUIRED)
find_package(BZip2 REQUIRED)
find_package(Catch2 3 CONFIG REQUIRED)
find_package(Threads REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(pocketpy CONFIG REQUIRED)
find_package(ZLIB REQUIRED)

file(GLOB_RECURSE LIBRARY_SOURCES CONFIGURE_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/*.hpp
)
list(REMOVE_ITEM LIBRARY_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp)

file(GLOB_RECURSE TEST_SOURCES CONFIGURE_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.hpp
)

function(configure_project_target target)
    target_include_directories(${target} PRIVATE src)
    target_precompile_headers(${target} PRIVATE src/pch.hpp)

    target_compile_definitions(${target} PRIVATE BOOST_ASIO_NO_DEPRECATED)
    if(WIN32)
        # Windows 10; Asio warns when it isn't set.
        target_compile_definitions(${target} PRIVATE _WIN32_WINNT=0x0A00)
    endif()

    if(MSVC)
        # /bigobj: Beast's templates and coroutines exceed the default section count in Debug.
        # /MP: the Visual Studio generator compiles a project's sources serially without it.
        target_compile_options(${target} PRIVATE
            /W4 /permissive- /utf-8 /EHsc /Zc:__cplusplus /Zc:preprocessor /bigobj /MP
            "$<$<NOT:$<CONFIG:Debug>>:/WX>")
    else()
        target_compile_options(${target} PRIVATE
            -Wall -Wextra -Wpedantic -Wshadow
            -Wno-missing-field-initializers
            "$<$<NOT:$<CONFIG:Debug>>:-Werror>")
    endif()
endfunction()

# Everything in src/ except main.cpp builds into a static library that the app and the
# tests both link, so the tests exercise exactly the shipped code.
add_library(${PROJECT_NAME}Lib STATIC)
target_sources(${PROJECT_NAME}Lib PRIVATE ${LIBRARY_SOURCES})
configure_project_target(${PROJECT_NAME}Lib)
target_compile_definitions(${PROJECT_NAME}Lib PRIVATE JSON_DIAGNOSTICS=1)
target_link_libraries(${PROJECT_NAME}Lib
    PUBLIC pocketpy::pocketpy
    PRIVATE Boost::asio Boost::beast OpenSSL::SSL OpenSSL::Crypto nlohmann_json::nlohmann_json BZip2::BZip2 ZLIB::ZLIB
            $<$<PLATFORM_ID:Windows>:crypt32>)

# The Python standard library is embedded in the library, regenerated whenever a .py file changes.
file(GLOB_RECURSE STDLIB_FILES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/Script/Stdlib/*.py)
set(STDLIB_SOURCE ${CMAKE_CURRENT_BINARY_DIR}/generated/StdlibFiles.cpp)
add_custom_command(
    OUTPUT ${STDLIB_SOURCE}
    COMMAND ${CMAKE_COMMAND}
        -DSTDLIB_DIR=${CMAKE_CURRENT_SOURCE_DIR}/src/Script/Stdlib
        -DOUTPUT=${STDLIB_SOURCE}
        -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/EmbedStdlib.cmake
    DEPENDS ${STDLIB_FILES} ${CMAKE_CURRENT_SOURCE_DIR}/cmake/EmbedStdlib.cmake
    COMMENT "Embedding the Python standard library"
    VERBATIM)
target_sources(${PROJECT_NAME}Lib PRIVATE ${STDLIB_SOURCE})

add_executable(${PROJECT_NAME})
target_sources(${PROJECT_NAME} PRIVATE src/main.cpp)
if(WIN32)
    target_sources(${PROJECT_NAME} PRIVATE src/main.rc)
endif()
configure_project_target(${PROJECT_NAME})
target_link_libraries(${PROJECT_NAME} PRIVATE ${PROJECT_NAME}Lib)

enable_testing()

add_executable(${PROJECT_NAME}Tests)
target_sources(${PROJECT_NAME}Tests PRIVATE ${TEST_SOURCES})
configure_project_target(${PROJECT_NAME}Tests)
# The example script tests load the repository's scripts folder.
target_compile_definitions(${PROJECT_NAME}Tests PRIVATE RS2004_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_definitions(${PROJECT_NAME}Tests PRIVATE RS2004_APPLICATION_PATH="$<TARGET_FILE:${PROJECT_NAME}>")
add_dependencies(${PROJECT_NAME}Tests ${PROJECT_NAME})
# CacheWriter compresses its fixtures with the libraries the cache reader uses.
target_link_libraries(${PROJECT_NAME}Tests PRIVATE
    ${PROJECT_NAME}Lib
    Boost::asio
    Boost::beast
    OpenSSL::SSL
    OpenSSL::Crypto
    nlohmann_json::nlohmann_json
    BZip2::BZip2
    ZLIB::ZLIB
    Catch2::Catch2WithMain)

include(Catch)
set(TEST_TIMEOUT 60)
if(RS2004_ENABLE_SCRIPT_COVERAGE)
    set(TEST_TIMEOUT 300)
endif()
catch_discover_tests(${PROJECT_NAME}Tests
    DISCOVERY_MODE PRE_TEST
    PROPERTIES TIMEOUT ${TEST_TIMEOUT})

file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/test-runtime-$<CONFIG>.json" CONTENT
    "{\"tests\":\"$<TARGET_FILE:${PROJECT_NAME}Tests>\"}\n")

configure_native_coverage(${PROJECT_NAME}Lib ${PROJECT_NAME} ${PROJECT_NAME}Tests)

# The release archive is one folder laid out like the repository, with the files the client loads from its working
# directory, so it runs from inside the folder with the default paths in client.jsonc.sample. The tests aren't installed.
install(TARGETS ${PROJECT_NAME} RUNTIME DESTINATION .)
install(FILES README.md client.jsonc.sample DESTINATION .)
install(FILES accounts/example.jsonc.sample DESTINATION accounts)
install(FILES data/cache/.gitkeep DESTINATION data/cache)
install(DIRECTORY data/nav DESTINATION data)
install(DIRECTORY scripts/examples scripts/typings DESTINATION scripts)
file(GLOB THIRDPARTY_LICENSES RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} CONFIGURE_DEPENDS thirdparty/*/LICENSE)
foreach(license IN LISTS THIRDPARTY_LICENSES)
    cmake_path(GET license PARENT_PATH folder)
    install(FILES ${license} DESTINATION ${folder})
endforeach()

if(WIN32)
    set(PACKAGE_PLATFORM windows)
    set(CPACK_GENERATOR ZIP)
else()
    set(PACKAGE_PLATFORM linux)
    set(CPACK_GENERATOR TGZ)
endif()
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64|ARM64)$")
    set(PACKAGE_ARCH arm64)
elseif(CMAKE_SIZEOF_VOID_P EQUAL 4)
    set(PACKAGE_ARCH x86)
else()
    set(PACKAGE_ARCH x64)
endif()
set(CPACK_PACKAGE_NAME rs2004-headless)
# The release workflow overrides this with the tag, which can carry a pre-release suffix.
set(CPACK_PACKAGE_FILE_NAME ${CPACK_PACKAGE_NAME}-v${PROJECT_VERSION}-${PACKAGE_PLATFORM}-${PACKAGE_ARCH})
include(CPack)

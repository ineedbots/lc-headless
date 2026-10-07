cmake_minimum_required(VERSION 3.25)
project(Rs2004Headless VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)    # for clangd / tooling

find_package(Catch2 3 CONFIG REQUIRED)
find_package(ixwebsocket CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(pocketpy CONFIG REQUIRED)

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

    if(MSVC)
        target_compile_options(${target} PRIVATE
            /W4 /permissive- /utf-8 /EHsc /Zc:__cplusplus /Zc:preprocessor
            "$<$<NOT:$<CONFIG:Debug>>:/WX>")
    else()
        target_compile_options(${target} PRIVATE
            -Wall -Wextra -Wpedantic -Wshadow
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
    PUBLIC ixwebsocket::ixwebsocket pocketpy::pocketpy
    PRIVATE nlohmann_json::nlohmann_json)

add_executable(${PROJECT_NAME})
target_sources(${PROJECT_NAME} PRIVATE src/main.cpp)
configure_project_target(${PROJECT_NAME})
target_link_libraries(${PROJECT_NAME} PRIVATE ${PROJECT_NAME}Lib)

enable_testing()

add_executable(${PROJECT_NAME}Tests)
target_sources(${PROJECT_NAME}Tests PRIVATE ${TEST_SOURCES})
configure_project_target(${PROJECT_NAME}Tests)
target_link_libraries(${PROJECT_NAME}Tests PRIVATE
    ${PROJECT_NAME}Lib
    nlohmann_json::nlohmann_json
    Catch2::Catch2WithMain)

include(Catch)
catch_discover_tests(${PROJECT_NAME}Tests
    DISCOVERY_MODE PRE_TEST
    PROPERTIES TIMEOUT 60)

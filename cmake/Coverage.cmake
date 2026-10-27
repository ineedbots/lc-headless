option(RS2004_ENABLE_COVERAGE "Instrument native code for LLVM coverage" OFF)
option(RS2004_ENABLE_SCRIPT_COVERAGE "Allow longer test runs with script tracing" OFF)

if(RS2004_ENABLE_COVERAGE)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux" OR NOT CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        message(FATAL_ERROR "Native coverage requires Linux Clang; use the linux-coverage preset")
    endif()
endif()

function(configure_native_coverage library application tests)
    if(NOT RS2004_ENABLE_COVERAGE)
        return()
    endif()

    foreach(target IN ITEMS ${library} ${application} ${tests})
        target_compile_options(${target} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
    endforeach()
    foreach(target IN ITEMS ${application} ${tests})
        target_link_options(${target} PRIVATE -fprofile-instr-generate)
    endforeach()

    # Retain translation units never referenced by the tests, so they appear at zero coverage.
    # CMake applies this feature to the existing library link without linking it a second time.
    set_property(TARGET ${tests} PROPERTY LINK_LIBRARY_OVERRIDE_${library} WHOLE_ARCHIVE)

    # The application contributes main.cpp; only the test executable is run by the collector.
    file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/coverage-$<CONFIG>.json" CONTENT
"{
  \"compiler\": \"${CMAKE_CXX_COMPILER}\",
  \"application\": \"$<TARGET_FILE:${application}>\",
  \"tests\": \"$<TARGET_FILE:${tests}>\"
}
")
endfunction()

option(RS2004_ENABLE_SANITIZERS "Instrument project code with ASan and UBSan" OFF)

if(RS2004_ENABLE_SANITIZERS)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux" OR NOT CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        message(FATAL_ERROR "Sanitizers require Linux Clang; use the linux-sanitizers preset")
    endif()
    if(RS2004_ENABLE_COVERAGE OR RS2004_ENABLE_SCRIPT_COVERAGE)
        message(FATAL_ERROR "Use separate build directories for sanitizers and coverage")
    endif()
endif()

function(configure_project_sanitizers library application tests entrypoint)
    if(NOT RS2004_ENABLE_SANITIZERS)
        return()
    endif()

    foreach(target IN ITEMS ${library} ${entrypoint} ${tests})
        target_compile_options(${target} PRIVATE
            -fsanitize=address,undefined -fno-sanitize-recover=all
            -g -fno-omit-frame-pointer -fno-optimize-sibling-calls)
    endforeach()
    foreach(target IN ITEMS ${application} ${tests})
        target_link_options(${target} PRIVATE -fsanitize=address,undefined)
    endforeach()
endfunction()

#pragma once

#include <filesystem>
#include <vector>

class ScriptVm;

// rs2b0t's own tests, kept in its describe/test/expect form on tests/Stdlib/rs2b0t/spec.py.
class Rs2b0tSpecs
{
public:
    Rs2b0tSpecs() = delete;

    [[nodiscard]] static const std::filesystem::path& GetFolder();
    // The test_*.py files directly in folder, sorted.
    [[nodiscard]] static std::vector<std::filesystem::path> GetFiles(const std::filesystem::path& folder);
    // Loads spec.py and the file into vm, then runs every test, as Catch checks.
    static void Run(ScriptVm& vm, const std::filesystem::path& file);
};

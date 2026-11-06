#include "pch.hpp"
#include "Rs2b0tSpecs.hpp"

#include "Script/ScriptVm.hpp"
#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>

const std::filesystem::path& Rs2b0tSpecs::GetFolder()
{
    static const auto folder = std::filesystem::path{RS2004_SOURCE_DIR} / "tests" / "Stdlib" / "rs2b0t";
    return folder;
}

std::vector<std::filesystem::path> Rs2b0tSpecs::GetFiles(const std::filesystem::path& folder)
{
    auto files = std::vector<std::filesystem::path>{};
    for (const auto& entry : std::filesystem::directory_iterator{folder})
    {
        const auto name = entry.path().filename().string();
        if (name.starts_with("test_") && entry.path().extension() == ".py")
        {
            files.push_back(entry.path());
        }
    }

    std::ranges::sort(files);
    return files;
}

void Rs2b0tSpecs::Run(ScriptVm& vm, const std::filesystem::path& file)
{
    const auto spec = FileUtils::ReadText(GetFolder() / "spec.py");
    REQUIRE(spec.has_value());
    const auto source = FileUtils::ReadText(file);
    REQUIRE(source.has_value());

    REQUIRE_NOTHROW(vm.RunSource(*spec, "spec.py"));
    constexpr auto FIXTURE_PREFIX = "# fixture: "sv;
    if (source->starts_with(FIXTURE_PREFIX))
    {
        const auto end = source->find('\n');
        const auto name = source->substr(FIXTURE_PREFIX.size(), end - FIXTURE_PREFIX.size());
        REQUIRE_FALSE(name.empty());
        REQUIRE(name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_") == std::string::npos);
        const auto fixturePath = GetFolder() / "fixtures" / (name + ".py");
        const auto fixture = FileUtils::ReadText(fixturePath);
        REQUIRE(fixture.has_value());
        REQUIRE_NOTHROW(vm.RunSource(*fixture, fixturePath.filename().string()));
    }
    auto loaded = false;
    CHECK_NOTHROW((vm.RunSource(*source, file.filename().string()), loaded = true));
    if (loaded)
    {
        CHECK_NOTHROW(vm.Call("run_specs"));
    }
}

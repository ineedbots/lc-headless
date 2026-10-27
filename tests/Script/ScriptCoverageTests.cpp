#include "pch.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/ScriptCoverage.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"

#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    constexpr auto SOURCE =
        "# ignored comment\n"                          // 1
        "\n"                                           // 2
        "value = 0\n"                                  // 3
        "def used(flag):\n"                            // 4
        "    if flag:\n"                               // 5
        "        return 7\n"                           // 6
        "    raise ValueError('fixture')\n"            // 7
        "def outer():\n"                               // 8
        "    def never():\n"                           // 9
        "        return 123\n"                         // 10
        "    return never\n"                           // 11
        "class Example:\n"                             // 12
        "    def method(self):\n"                      // 13
        "        return 456\n"sv;                      // 14
    constexpr auto FIXTURE_FILE = "rs2004/__coverage_fixture__.py"sv;
}

TEST_CASE("Script coverage maps uncalled nested functions and methods without executing them", "[ScriptCoverage]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
    const auto lines = ScriptCoverage::ExecutableLines(SOURCE, FIXTURE_FILE);
    CHECK(std::ranges::find(lines, 1) == lines.end());
    CHECK(std::ranges::find(lines, 2) == lines.end());
    CHECK(std::ranges::find(lines, 3) != lines.end());
    CHECK(std::ranges::find(lines, 10) != lines.end());
    CHECK(std::ranges::find(lines, 14) != lines.end());
    CHECK_FALSE(vm.HasFunction("used"));
    CHECK(ScriptCoverage::ExecutableLines("", "empty.py").empty());
    CHECK(ScriptCoverage::ExecutableLines("# comment only\n\n", "comments.py").empty());
    CHECK_THROWS(ScriptCoverage::ExecutableLines("def invalid(:\n", "invalid.py"));
    CHECK(ScriptCoverage::ExecutableLines(SOURCE, FIXTURE_FILE) == lines);
}

TEST_CASE("Script coverage survives exceptions, VM switching and slot reuse", "[ScriptCoverage]")
{
    const auto files = std::array{StdlibFile_s{FIXTURE_FILE, SOURCE}};
    auto coverage = ScriptCoverage{files};
    auto capture = LogCapture{};
    {
        auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
        coverage.AttachToCurrentVm();
        vm.RunSource(SOURCE, "rs2004\\__coverage_fixture__.py");
        py_newbool(py_r0(), true);
        const auto args = std::array{py_r0()};
        vm.Call("used", args);
        CHECK(coverage.GetHits().at(std::string{FIXTURE_FILE})[6] > 0);
        CHECK(coverage.GetHits().at(std::string{FIXTURE_FILE})[7] == 0);
        CHECK(coverage.GetHits().at(std::string{FIXTURE_FILE})[10] == 0);
        CHECK(coverage.GetHits().at(std::string{FIXTURE_FILE})[14] == 0);
        py_newbool(py_r0(), false);
        CHECK_THROWS(vm.Call("used", args));
        CHECK(coverage.GetHits().at(std::string{FIXTURE_FILE})[7] > 0);

        auto other = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
        other.RunSource(SOURCE, FIXTURE_FILE);
        vm.RunSource("unrelated = 1\n", "test_only.py");
    }
    const auto before = coverage.GetHits().at(std::string{FIXTURE_FILE})[3];
    {
        auto reused = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
        reused.RunSource(SOURCE, FIXTURE_FILE);
    }
    CHECK(coverage.GetHits().at(std::string{FIXTURE_FILE})[3] > before);
    CHECK_FALSE(coverage.Failed());
}

// Compiles every embedded source without importing it. The runner invokes this hidden case once
// before CTest, so modules that no test imports still contribute executable lines to the denominator.
TEST_CASE("Write the stdlib coverage manifest", "[.][ScriptCoverageManifest]")
{
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
    const auto* path = std::getenv("RS2004_SCRIPT_COVERAGE_MANIFEST");
#ifdef _MSC_VER
#pragma warning(pop)
#endif
    REQUIRE(path != nullptr);
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
    auto files = nlohmann::json::object();
    for (const auto& file : Stdlib::GetFiles())
    {
        CAPTURE(file.path);
        files[std::string{file.path}] = {{"source", file.source},
                                      {"lines", ScriptCoverage::ExecutableLines(file.source, file.path)}};
    }
    auto output = std::ofstream{};
    output.exceptions(std::ios::failbit | std::ios::badbit);
    output.open(path, std::ios::binary);
    output << nlohmann::json{{"version", 1}, {"files", std::move(files)}}.dump() << '\n';
}

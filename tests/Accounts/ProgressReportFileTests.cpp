#include "pch.hpp"
#include "../TempFolder.hpp"

#include "Accounts/ProgressReportFile.hpp"
#include "Script/ProgressReport_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    // 2026-10-08T14:20:00Z
    const auto REPORT_TIME = std::chrono::sys_days{std::chrono::year{2026} / 10 / 8} + 14h + 20min;

    const auto REPORT = ProgressReport_s{
        .runTime = 1h + 20min + 5s,
        .rows = {{"Kills", "10"}, {"Bones collected", "42"}},
    };

    constexpr auto REPORT_TEXT =
        "Progress at 2026-10-08T14:20:00Z, 1h 20m after the script started\n"
        "+-----------------+-------+\n"
        "| Name            | Value |\n"
        "+-----------------+-------+\n"
        "| Kills           | 10    |\n"
        "| Bones collected | 42    |\n"
        "+-----------------+-------+\n"sv;

    std::string ReadFile(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path, std::ios::binary};
        return std::string{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
    }
}

TEST_CASE("ProgressReportFile formats a report as a table", "[ProgressReportFile]")
{
    CHECK(ProgressReportFile::Format(REPORT, REPORT_TIME) == REPORT_TEXT);

    SECTION("in the script's order, with each cell on one line")
    {
        const auto report = ProgressReport_s{.runTime = 45s, .rows = {{"z", "first"}, {"a", "two\nlines"}}};
        CHECK(ProgressReportFile::Format(report, REPORT_TIME) ==
              "Progress at 2026-10-08T14:20:00Z, 45s after the script started\n"
              "+------+-----------+\n"
              "| Name | Value     |\n"
              "+------+-----------+\n"
              "| z    | first     |\n"
              "| a    | two lines |\n"
              "+------+-----------+\n");
    }

    SECTION("an empty report is an empty table")
    {
        CHECK(ProgressReportFile::Format(ProgressReport_s{.runTime = 5min}, REPORT_TIME) ==
              "Progress at 2026-10-08T14:20:00Z, 5m after the script started\n"
              "+------+-------+\n"
              "| Name | Value |\n"
              "+------+-------+\n"
              "+------+-------+\n");
    }
}

TEST_CASE("ProgressReportFile summarizes a report on one line", "[ProgressReportFile]")
{
    CHECK(ProgressReportFile::Summarize(REPORT) == "Kills: 10, Bones collected: 42");
    CHECK(ProgressReportFile::Summarize(ProgressReport_s{}) == "nothing to report");
}

TEST_CASE("ProgressReportFile starts the file afresh, then appends", "[ProgressReportFile]")
{
    const auto folder = TempFolder{"rs2004-progress-tests"};
    const auto path = folder.GetPath() / "progress" / "bot1.txt";
    std::filesystem::create_directories(path.parent_path());
    folder.WriteFile("progress/bot1.txt", "from the last run\n");

    auto file = ProgressReportFile{path};
    CHECK(file.GetPath() == path);
    file.Write(REPORT, REPORT_TIME);
    CHECK(ReadFile(path) == REPORT_TEXT);

    file.Write(REPORT, REPORT_TIME);
    CHECK(ReadFile(path) == std::format("{}\n{}", REPORT_TEXT, REPORT_TEXT));
}

TEST_CASE("ProgressReportFile creates its folder", "[ProgressReportFile]")
{
    const auto folder = TempFolder{"rs2004-progress-tests"};
    const auto path = folder.GetPath() / "reports" / "nested" / "bot1.txt";
    auto file = ProgressReportFile{path};
    file.Write(REPORT, REPORT_TIME);
    CHECK(ReadFile(path) == REPORT_TEXT);
}

TEST_CASE("ProgressReportFile throws when it can't write", "[ProgressReportFile]")
{
    const auto folder = TempFolder{"rs2004-progress-tests"};
    auto file = ProgressReportFile{folder.GetPath()};
    CHECK_THROWS_AS(file.Write(REPORT, REPORT_TIME), std::runtime_error);
}

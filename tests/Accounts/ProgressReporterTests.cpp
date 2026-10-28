#include "pch.hpp"
#include "../Support/Script/HostFixture.hpp"

#include "Accounts/ProgressReporter.hpp"
#include "Console/LogLevel_e.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = ProgressReporter::Clock;

    constexpr auto COUNTER = R"python(
reports = 0

def on_progress_report():
    global reports
    reports += 1
    return {'Reports': reports}

def loop():
    return 600
)python";

    [[nodiscard]] std::size_t CountReports(const HostFixture& fixture)
    {
        return static_cast<std::size_t>(std::ranges::count_if(fixture.capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.message.starts_with("Progress: ");
        }));
    }
}

TEST_CASE("ProgressReporter survives a write failure and retries at the next interval", "[ProgressReporter][CompletionCoverage]")
{
    auto fixture = HostFixture{COUNTER};
    const auto blocked = fixture.folder.GetPath() / "blocked";
    fixture.folder.WriteFile("blocked", "keep this file");
    const auto path = blocked / "report.txt";
    auto reporter = ProgressReporter{1min, path, fixture.capture.GetLogger()};
    const auto start = Clock::now();
    fixture.host->Step(start);
    reporter.Step(start, *fixture.host);
    CHECK_NOTHROW(reporter.Step(start + 1min, *fixture.host));
    CHECK(fixture.HasLog(LogLevel_e::Warning, "The progress report wasn't saved:"));
    CHECK(fixture.HasLog(LogLevel_e::Info, "Progress: Reports: 1"));
    CHECK(fixture.host->IsActive());
    std::filesystem::remove(blocked);
    reporter.Step(start + 119s, *fixture.host);
    CHECK_FALSE(std::filesystem::exists(path));
    reporter.Step(start + 2min, *fixture.host);
    CHECK(std::filesystem::is_regular_file(path));
    CHECK(fixture.HasLog(LogLevel_e::Info, "Progress: Reports: 2"));
}

TEST_CASE("ProgressReporter reports an interval after the script started, then an interval after each report", "[ProgressReporter]")
{
    auto fixture = HostFixture{COUNTER};
    auto reporter = ProgressReporter{1min, fixture.folder.GetPath() / "progress" / "bot1.txt", fixture.capture.GetLogger()};
    auto& host = *fixture.host;

    const auto start = Clock::now();
    host.Step(start);
    reporter.Step(start, host);
    reporter.Step(start + 59s, host);
    CHECK(CountReports(fixture) == 0);

    reporter.Step(start + 61s, host);
    CHECK(CountReports(fixture) == 1);
    CHECK(fixture.HasLog(LogLevel_e::Info, "Progress: Reports: 1"));
    CHECK(std::filesystem::exists(fixture.folder.GetPath() / "progress" / "bot1.txt"));

    reporter.Step(start + 120s, host);
    CHECK(CountReports(fixture) == 1);
    reporter.Step(start + 121s, host);
    CHECK(CountReports(fixture) == 2);
    CHECK(fixture.HasLog(LogLevel_e::Info, "Progress: Reports: 2"));
}

TEST_CASE("ProgressReporter makes no reports at a zero interval", "[ProgressReporter]")
{
    auto fixture = HostFixture{COUNTER};
    auto reporter = ProgressReporter{0min, fixture.folder.GetPath() / "bot1.txt", fixture.capture.GetLogger()};

    const auto start = Clock::now();
    fixture.host->Step(start);
    reporter.Step(start + 1h, *fixture.host);
    CHECK(CountReports(fixture) == 0);
}

TEST_CASE("ProgressReporter waits while the account is out of game", "[ProgressReporter]")
{
    auto fixture = HostFixture{COUNTER};
    auto reporter = ProgressReporter{1min, fixture.folder.GetPath() / "bot1.txt", fixture.capture.GetLogger()};

    const auto start = Clock::now();
    fixture.host->Step(start);
    fixture.client.Disconnect();
    REQUIRE_FALSE(fixture.host->IsActive());

    reporter.Step(start + 2min, *fixture.host);
    CHECK(CountReports(fixture) == 0);
}

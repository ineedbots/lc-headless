#include "pch.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"
#include "../Support/FleetDatabaseReader.hpp"

#include "Accounts/ExperienceLog.hpp"
#include "Console/Type/LogLevel_e.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    using Clock = ExperienceLog::Clock;

    // The skills the state holds start at 0, so a test sets only the ones it checks.
    void SetXp(GameState_s& state, std::string_view skill, s32 xp, u8 level = 1)
    {
        const auto found = std::ranges::find(ExperienceLog::SKILL_NAMES, skill);
        REQUIRE(found != ExperienceLog::SKILL_NAMES.end());
        const auto index = static_cast<std::size_t>(std::distance(ExperienceLog::SKILL_NAMES.begin(), found));
        state.stats[index].xp = xp;
        state.stats[index].level = level;
        state.stats[index].baseLevel = level;
    }

    std::vector<std::string> ReadLines(const std::filesystem::path& path, std::string_view account = "s18")
    {
        return ReadFleetPayloads(path, "experience", account);
    }

    struct ExperienceFixture
    {
        explicit ExperienceFixture(std::chrono::minutes interval = 5min)
            : folder{"rs2004-experience-tests"}
            , database{std::make_shared<FleetDatabase>(folder.GetPath() / "fleet.sqlite")}
            , log{"s18", interval, capture.GetLogger(), database}
        {
        }

        [[nodiscard]] std::vector<std::string> Lines() const
        {
            return ReadLines(log.GetDatabasePath());
        }

        TempFolder folder;
        LogCapture capture{LogLevel_e::Verbose};
        std::shared_ptr<FleetDatabase> database;
        ExperienceLog log;
    };

    bool HasExperienceLog(const LogCapture& capture, std::string_view text = "experience: ")
    {
        return std::ranges::any_of(capture.GetEntries(), [&](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Info && entry.message.starts_with(text);
        });
    }
}

TEST_CASE("ExperienceLog writes a baseline, then a sample each interval", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    SetXp(state, "attack", 1154);
    SetXp(state, "thieving", 496);

    const auto start = Clock::now();
    fixture.log.Step(start, state, ClientStatus_e::InGame, true);

    const auto path = fixture.log.GetDatabasePath();
    REQUIRE(std::filesystem::exists(path));
    REQUIRE(ReadLines(path).size() == 1);

    const auto baseline = ReadLines(path).front();
    CHECK(baseline.starts_with("{\"time\":\""));
    CHECK(baseline.find("\"account\":\"s18\"") != std::string::npos);
    CHECK(baseline.find("\"state\":\"ingame\",\"settled\":true") != std::string::npos);
    CHECK(baseline.find("\"attack\":{\"level\":1,\"base\":1,\"xp\":1154}") != std::string::npos);
    CHECK(baseline.find("\"thieving\":{\"level\":1,\"base\":1,\"xp\":496}") != std::string::npos);
    CHECK(baseline.ends_with("}}"));

    // Not yet due.
    fixture.log.Step(start + 4min, state, ClientStatus_e::InGame, true);
    CHECK(ReadLines(path).size() == 1);

    SetXp(state, "thieving", 496 + 600);
    fixture.log.Step(start + 5min, state, ClientStatus_e::InGame, true);
    CHECK(ReadLines(path).size() == 2);
}

TEST_CASE("ExperienceLog logs the skills that gained experience, and their rate", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    SetXp(state, "attack", 100);
    SetXp(state, "thieving", 1000);
    SetXp(state, "hitpoints", 500);

    const auto start = Clock::now();
    fixture.log.Step(start, state, ClientStatus_e::InGame, true);
    CHECK_FALSE(HasExperienceLog(fixture.capture));

    SetXp(state, "attack", 150);
    SetXp(state, "thieving", 1000 + 1200);
    fixture.log.Step(start + 5min, state, ClientStatus_e::InGame, true);

    // 5 minutes is 1/12 of an hour, so 50 xp is 600 an hour and 1200 is 14400.
    CHECK(HasExperienceLog(fixture.capture, "experience: Attack +50 xp (600 an hour), Thieving +1200 xp (14400 an hour)"));
}

TEST_CASE("ExperienceLog says nothing for a sample with no gain", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    SetXp(state, "thieving", 1000);

    const auto start = Clock::now();
    fixture.log.Step(start, state, ClientStatus_e::InGame, true);
    fixture.log.Step(start + 5min, state, ClientStatus_e::InGame, true);

    CHECK_FALSE(HasExperienceLog(fixture.capture));
    CHECK(ReadLines(fixture.log.GetDatabasePath()).size() == 2);
}

TEST_CASE("ExperienceLog records the status while out of game, and samples once settled", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    SetXp(state, "thieving", 1000);

    const auto start = Clock::now();
    fixture.log.Step(start, state, ClientStatus_e::Connecting, false);
    fixture.log.Step(start + 5min, state, ClientStatus_e::Connecting, false);

    // A status change is written once; repeating it is not.
    const auto path = fixture.log.GetDatabasePath();
    REQUIRE(ReadLines(path).size() == 1);
    CHECK(ReadLines(path).front().find("\"state\":\"connecting\",\"settled\":false") != std::string::npos);

    // The first settled sample is the baseline, whenever it comes.
    fixture.log.Step(start + 6min, state, ClientStatus_e::InGame, true);
    CHECK(ReadLines(path).size() == 2);
    CHECK(ReadLines(path).back().find("\"state\":\"ingame\",\"settled\":true") != std::string::npos);
}

TEST_CASE("ExperienceLog writes a line when the account logs out", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    SetXp(state, "thieving", 1000);

    const auto start = Clock::now();
    fixture.log.Step(start, state, ClientStatus_e::InGame, true);
    fixture.log.Step(start + 1min, state, ClientStatus_e::LoggingOut, false);
    fixture.log.Step(start + 2min, state, ClientStatus_e::LoggedOut, false);

    const auto lines = fixture.Lines();
    REQUIRE(lines.size() == 3);
    CHECK(lines[1].find("\"state\":\"logging out\"") != std::string::npos);
    CHECK(lines[2].find("\"state\":\"logged out\"") != std::string::npos);
}

TEST_CASE("ExperienceLog starts a new baseline after a logout", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    SetXp(state, "thieving", 1000);

    const auto start = Clock::now();
    fixture.log.Step(start, state, ClientStatus_e::InGame, true);
    fixture.log.Step(start + 1min, state, ClientStatus_e::LoggedOut, false);

    // Back in game at a lower XP, as a relogin can be: no rate is computed across the logout.
    SetXp(state, "thieving", 100);
    fixture.log.Step(start + 2min, state, ClientStatus_e::InGame, true);
    CHECK_FALSE(HasExperienceLog(fixture.capture));
}

TEST_CASE("ExperienceLog waits for the player's stats before taking its baseline", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};

    // In game, but the stats packet hasn't arrived, so the account is not settled yet.
    const auto start = Clock::now();
    CHECK_FALSE(state.IsSettled());
    // In game, but not settled: only the status is recorded, with no XP baseline yet.
    fixture.log.Step(start, state, ClientStatus_e::InGame, false);
    const auto status = ReadLines(fixture.log.GetDatabasePath());
    REQUIRE(status.size() == 1);
    CHECK(status.front().find("\"state\":\"ingame\",\"settled\":false") != std::string::npos);

    // Placed and settled: now the baseline is worth recording.
    state.placed = true;
    state.placedTick = 100;
    state.tick = 101;
    REQUIRE(state.IsSettled());
    SetXp(state, "thieving", 496);
    fixture.log.Step(start + 1min, state, ClientStatus_e::InGame, true);

    const auto line = ReadLines(fixture.log.GetDatabasePath()).back();
    CHECK(line.find("\"thieving\":{\"level\":1,\"base\":1,\"xp\":496}") != std::string::npos);
    CHECK(line.find("\"state\":\"ingame\",\"settled\":true") != std::string::npos);
}

TEST_CASE("ExperienceLog writes every skill, in the game's order", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    for (std::size_t i = 0; i < ExperienceLog::SKILL_NAMES.size(); ++i)
    {
        state.stats[i].xp = static_cast<s32>(i) * 100;
        state.stats[i].level = 10;
        state.stats[i].baseLevel = 10;
    }

    fixture.log.Step(Clock::now(), state, ClientStatus_e::InGame, true);

    const auto line = ReadLines(fixture.log.GetDatabasePath()).front();
    auto previous = std::size_t{0};
    for (const auto& skill : ExperienceLog::SKILL_NAMES)
    {
        const auto found = line.find(std::format("\"{}\":", skill));
        REQUIRE(found != std::string::npos);
        CHECK(found > previous);
        previous = found;
    }
}

TEST_CASE("ExperienceLog names the file after the account", "[ExperienceLog]")
{
    auto folder = TempFolder{"rs2004-experience-tests"};
    auto capture = LogCapture{};
    const auto databasePath = folder.GetPath() / "fleet.sqlite";
    auto database = std::make_shared<FleetDatabase>(databasePath);

    for (const auto& name : {"s18", "s40", "s60"})
    {
        auto log = ExperienceLog{name, 5min, capture.GetLogger(), database};
        log.Step(Clock::now(), GameState_s{}, ClientStatus_e::InGame, true);
        CHECK(ReadLines(databasePath, name).size() == 1);
    }
}

TEST_CASE("ExperienceLog appends across runs rather than truncating", "[ExperienceLog]")
{
    auto fixture = ExperienceFixture{};
    auto state = GameState_s{};
    SetXp(state, "thieving", 1000);

    const auto start = Clock::now();
    fixture.log.Step(start, state, ClientStatus_e::InGame, true);
    fixture.log.Step(start + 5min, state, ClientStatus_e::InGame, true);

    // A fresh log, as a restarted client makes: the earlier samples are kept.
    auto restarted = ExperienceLog{"s18", 5min, fixture.capture.GetLogger(), std::make_shared<FleetDatabase>(fixture.log.GetDatabasePath())};
    restarted.Step(start + 10min, state, ClientStatus_e::InGame, true);

    CHECK(ReadLines(fixture.log.GetDatabasePath()).size() == 3);
}

TEST_CASE("ExperienceLog warns once when it can't write, and never throws", "[ExperienceLog]")
{
    auto folder = TempFolder{"rs2004-experience-tests"};
    auto capture = LogCapture{};
    // A file where the folder should be, so creating the folder fails.
    const auto blocked = folder.GetPath() / "fleet.sqlite";
    std::ofstream{blocked} << "not a database";

    auto log = ExperienceLog{"s18", 1min, capture.GetLogger(), std::make_shared<FleetDatabase>(blocked)};
    auto state = GameState_s{};
    const auto start = Clock::now();

    CHECK_NOTHROW(log.Step(start, state, ClientStatus_e::InGame, true));
    CHECK_NOTHROW(log.Step(start + 1min, state, ClientStatus_e::InGame, true));
    CHECK_NOTHROW(log.Step(start + 2min, state, ClientStatus_e::InGame, true));

    const auto warnings = std::ranges::count_if(capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level == LogLevel_e::Warning && entry.message.find("experience log wasn't saved") != std::string::npos;
    });
    CHECK(warnings == 1);
}

TEST_CASE("ExperienceLog escapes the account name in JSON records", "[ExperienceLog]")
{
    const auto folder = TempFolder{"rs2004-experience-escape-tests"};
    auto capture = LogCapture{};
    const auto name = "fleet\\worker"s;
    const auto databasePath = folder.GetPath() / "fleet.sqlite";
    auto log = ExperienceLog{name, 1min, capture.GetLogger(), std::make_shared<FleetDatabase>(databasePath)};
    log.Step(Clock::now(), GameState_s{}, ClientStatus_e::InGame, true);
    const auto lines = ReadLines(databasePath, name);
    REQUIRE(lines.size() == 1);
    CHECK(nlohmann::json::parse(lines.front()).at("account").get<std::string>() == name);
}

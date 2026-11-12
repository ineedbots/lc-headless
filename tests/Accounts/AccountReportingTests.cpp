#include "pch.hpp"
#include "../Support/Script/HostFixture.hpp"

#include "Accounts/AccountReporting.hpp"
#include "Accounts/Type/ProgressReport_s.hpp"
#include "Config/Type/AccountConfig_s.hpp"
#include "Config/Type/Config_s.hpp"
#include "Console/Type/LogLevel_e.hpp"
#include "Game/GameClient.hpp"
#include "Script/Host/ScriptHost.hpp"
#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("Account reporting preserves progress callbacks despite file failures and defers while disconnected", "[AccountReporting]")
{
    auto fixture = HostFixture{"def on_progress_report():\n    return {'Trips': 7}\n\ndef loop():\n    return 600\n"};
    fixture.folder.WriteFile("blocked", "keep this file");
    auto config = Config_s{};
    config.scripting.progressDirectory = (fixture.folder.GetPath() / "blocked").string();
    config.scripting.experienceDirectory.clear();
    config.scripting.bankLogDirectory.clear();
    config.scripting.inventoryDirectory.clear();
    config.scripting.equipmentDirectory.clear();
    auto settings = AccountConfig_s{.name = "bot1", .script = ScriptConfig_s{.file = "main.py", .progressReportMinutes = 1min}};
    auto reports = std::vector<ProgressReport_s>{};
    auto reporting = AccountReporting{config, settings, fixture.client.GetCache(), fixture.capture.GetLogger(), [&](const ProgressReport_s& report)
    {
        reports.push_back(report);
    }};
    const auto start = ScriptHost::Clock::now();
    fixture.host->Step(start);
    reporting.AfterScript(start, *fixture.host);
    reporting.AfterScript(start + 59s, *fixture.host);
    CHECK(reports.empty());
    reporting.AfterScript(start + 1min, *fixture.host);
    REQUIRE(reports.size() == 1);
    CHECK(reports[0].rows == std::vector<std::pair<std::string, std::string>>{{"Trips", "7"}});
    CHECK(fixture.HasLog(LogLevel_e::Warning, "The progress report wasn't saved:"));
    CHECK(fixture.host->IsActive());
    fixture.client.Disconnect();
    reporting.ObserveSession(start + 2min, fixture.client.GetState(), fixture.client.GetStatus());
    reporting.AfterScript(start + 2min, *fixture.host);
    CHECK(reports.size() == 1);
    CHECK(FileUtils::ReadText(fixture.folder.GetPath() / "blocked") == "keep this file");
}

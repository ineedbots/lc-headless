#include "pch.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"
#include "../Support/TempFolder.hpp"

#include "Accounts/Account.hpp"
#include "Config/AccountFile.hpp"
#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <nlohmann/json.hpp>

namespace
{
    constexpr auto SAVE_SCRIPT = R"python(
def on_start():
    settings_store.save('Miner', 'rock', 'Iron rocks')
    settings_store.save('Miner', 'trips', 7)
    log('saved in memory', settings_store.saved('Miner', 'rock'), settings_store.saved('Miner', 'trips'))
    stop_script()

def loop():
    return 100
)python";

    class LifecycleFixture
    {
    public:
        LifecycleFixture()
        {
            config = server.MakeConfig();
            config.scripting.scriptsDirectory = folder.GetPath().string();
        }

        void Make(std::optional<std::string_view> script = std::nullopt, bool withFile = false, AccountOptions_s options = {})
        {
            auto settings = AccountConfig_s{.name = "bot1", .credentials = FakeGameServer::MakeAccount()};
            if (script)
            {
                folder.WriteFile("main.py", *script);
                settings.script = ScriptConfig_s{.file = "main.py"};
            }
            if (withFile)
            {
                settings.file = folder.GetPath() / "bot1.jsonc";
            }
            account = std::make_unique<Account>(std::make_shared<const Config_s>(config), FakeGameServer::MakeCache(), std::move(settings), ScriptTestRuntime::Get(), capture.GetLogger(), options);
        }

        template <typename TCondition>
        bool Until(TCondition condition)
        {
            const auto deadline = Account::Clock::now() + 5s;
            while (!condition() && !account->IsFinished() && Account::Clock::now() < deadline)
            {
                account->Step(20ms);
            }
            return condition();
        }

        bool HasMessage(std::string_view message) const
        {
            return std::ranges::any_of(capture.GetEntries(), [message](const CapturedLog_s& entry)
            {
                return entry.message == message;
            });
        }

        void RunSavingScript(bool withFile)
        {
            Make(SAVE_SCRIPT, withFile);
            account->Start();
            REQUIRE(Until([this] { return account->DescribeStatus().ends_with(", script stopped"); }));
            CHECK(HasMessage("saved in memory Iron rocks 7"));
            CHECK(account->GetClient().IsInGame());
            CHECK_FALSE(account->IsFinished());
        }

        LogCapture capture;
        FakeGameServer server{TestWorld::Send};
        TempFolder folder{"rs2004-account-lifecycle-tests"};
        Config_s config;
        std::unique_ptr<Account> account;
    };
}

TEST_CASE("An unstarted account ignores steps and interrupts and reports its pending state", "[AccountLifecycleCoverage]")
{
    auto fixture = LifecycleFixture{};
    fixture.Make();
    CHECK(fixture.account->DescribeOutcome() == "never started");
    CHECK(fixture.account->DescribeStatus() == "waiting to log in");
    CHECK_FALSE(fixture.account->Succeeded());
    fixture.account->Step(0ms);
    fixture.account->Interrupt();
    CHECK_FALSE(fixture.account->IsStarted());
    CHECK_FALSE(fixture.account->IsFinished());
    CHECK_FALSE(fixture.account->GetNextLoop());
    CHECK(fixture.server.GetLoginOpcodes().empty());
}

TEST_CASE("An idle account reports login game and confirmed logout states", "[AccountLifecycleCoverage]")
{
    auto fixture = LifecycleFixture{};
    fixture.Make();
    fixture.account->Start();
    CHECK(fixture.account->DescribeStatus() == "logging in, no script");
    CHECK(fixture.account->DescribeOutcome() == "still running");
    REQUIRE(fixture.Until([&] { return !fixture.account->GetClient().GetState().messages.empty(); }));
    CHECK_THAT(fixture.account->DescribeStatus(), Catch::Matchers::StartsWith("in game at (") && Catch::Matchers::EndsWith(", no script"));
    fixture.account->Interrupt();
    CHECK(fixture.account->DescribeStatus() == "logging out, no script");
    REQUIRE(fixture.Until([&] { return fixture.account->IsFinished(); }));
    CHECK(fixture.account->Succeeded());
    CHECK(fixture.account->DescribeStatus() == "logged out");
    fixture.account->Interrupt();
    fixture.account->Step(0ms);
    CHECK(fixture.account->Succeeded());
    CHECK(fixture.server.GetPackets(ClientProt_e::IfButton).size() == 1);
}

TEST_CASE("Stopping a script keeps its account online without commands or loop deadlines", "[AccountLifecycleCoverage]")
{
    auto fixture = LifecycleFixture{};
    fixture.Make("console.command('echo', lambda command: None)\n\ndef on_start():\n    stop_script()\n\ndef loop():\n    raise ValueError('must not run')\n");
    fixture.account->Start();
    REQUIRE(fixture.Until([&] { return fixture.account->DescribeStatus().ends_with(", script stopped"); }));
    CHECK(fixture.account->GetClient().IsInGame());
    CHECK_FALSE(fixture.account->IsFinished());
    CHECK_FALSE(fixture.account->GetNextLoop());
    CHECK(fixture.account->GetCommands().empty());
    CHECK_FALSE(fixture.account->SendCommand({.name = "echo"}));
    fixture.account->Step(0ms);
    CHECK(fixture.server.GetPackets(ClientProt_e::IfButton).empty());
    fixture.account->Interrupt();
    REQUIRE(fixture.Until([&] { return fixture.account->IsFinished(); }));
    CHECK(fixture.account->Succeeded());
}

TEST_CASE("A watched failed script reports its failure while its account remains online", "[AccountLifecycleCoverage]")
{
    auto fixture = LifecycleFixture{};
    fixture.Make("def loop():\n    raise ValueError('broken script')\n", false, {.watchScripts = true});
    fixture.account->Start();
    REQUIRE(fixture.Until([&] { return fixture.account->DescribeStatus().ends_with(", script failed"); }));
    CHECK(fixture.account->GetClient().IsInGame());
    CHECK_FALSE(fixture.account->IsFinished());
    CHECK_FALSE(fixture.account->GetNextLoop());
    CHECK(fixture.account->GetCommands().empty());
    CHECK(fixture.server.GetPackets(ClientProt_e::IfButton).empty());
    fixture.account->Interrupt();
    REQUIRE(fixture.Until([&] { return fixture.account->IsFinished(); }));
}

TEST_CASE("An account stopped by its script reports an unconfirmed logout when interrupted", "[AccountLifecycleCoverage]")
{
    auto fixture = LifecycleFixture{};
    fixture.server.SetIgnoreLogout(true);
    fixture.Make("def on_start():\n    stop_account()\n\ndef loop():\n    return 100\n");
    fixture.account->Start();
    REQUIRE(fixture.Until([&] { return fixture.account->GetClient().GetStatus() == ClientStatus_e::LoggingOut; }));
    CHECK(fixture.account->DescribeStatus() == "logging out, script stopped the account");
    fixture.account->Interrupt();
    CHECK(fixture.account->IsFinished());
    CHECK_FALSE(fixture.account->Succeeded());
    CHECK(fixture.account->DescribeStatus() == "disconnected without a confirmed logout");
    CHECK(fixture.account->GetCommands().empty());
    CHECK_FALSE(fixture.account->SendCommand({.name = "pause"}));
    CHECK_FALSE(fixture.account->Say("too late"));
}

TEST_CASE("An account persists script setting saves while preserving comments and other namespaces", "[AccountLifecycleCoverage]")
{
    auto fixture = LifecycleFixture{};
    fixture.folder.WriteFile("bot1.jsonc", "{\n  // Keep this account comment.\n  \"username\": \"bot\", \"password\": \"secret\",\n  \"script\": {\"file\": \"main.py\", \"settings\": {\"Other\": {\"enabled\": true}}}\n}\n");
    fixture.RunSavingScript(true);
    const auto path = fixture.folder.GetPath() / "bot1.jsonc";
    const auto text = FileUtils::ReadText(path);
    REQUIRE(text);
    CHECK_THAT(*text, Catch::Matchers::ContainsSubstring("// Keep this account comment."));
    const auto parsed = AccountFile::Parse(*text, "bot1");
    REQUIRE(parsed.script);
    const auto settings = nlohmann::json::parse(parsed.script->settings);
    CHECK(settings["Miner"] == nlohmann::json({{"rock", "Iron rocks"}, {"trips", 7}}));
    CHECK(settings["Other"]["enabled"] == true);
    CHECK(fixture.HasMessage(std::format("Saved settings[\"Miner\"].rock to {}", path.string())));
    CHECK_FALSE(std::filesystem::exists(path.string() + ".tmp"));
}

TEST_CASE("An account warns about failed setting saves and keeps the script's in-memory values", "[AccountLifecycleCoverage]")
{
    const auto invalidFile = GENERATE(false, true);
    auto fixture = LifecycleFixture{};
    if (invalidFile)
    {
        fixture.folder.WriteFile("bot1.jsonc", "{ invalid json }");
    }
    fixture.RunSavingScript(true);
    const auto entries = fixture.capture.GetEntries();
    CHECK(std::ranges::count_if(entries, [](const CapturedLog_s& entry)
    {
        return entry.level == LogLevel_e::Warning && entry.message.starts_with("settings[\"Miner\"].") && entry.message.find("wasn't saved to the account file") != std::string::npos;
    }) == 2);
    const auto path = fixture.folder.GetPath() / "bot1.jsonc";
    if (invalidFile)
    {
        CHECK(FileUtils::ReadText(path) == "{ invalid json }");
    }
    else
    {
        CHECK_FALSE(std::filesystem::exists(path));
    }
    CHECK_FALSE(std::filesystem::exists(path.string() + ".tmp"));
}

TEST_CASE("An account without a configuration file accepts setting saves in memory", "[AccountLifecycleCoverage]")
{
    auto fixture = LifecycleFixture{};
    fixture.RunSavingScript(false);
    CHECK_FALSE(std::filesystem::exists(fixture.folder.GetPath() / "bot1.jsonc"));
    CHECK(std::ranges::none_of(fixture.capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level >= LogLevel_e::Warning;
    }));
}

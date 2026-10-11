#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/TestWorld.hpp"
#include "../LogCapture.hpp"
#include "../Script/ScriptTestRuntime.hpp"
#include "../TempFolder.hpp"

#include "Accounts/Account.hpp"
#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Script/BotMessenger.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = Account::Clock;

    constexpr auto WAIT = 10s;
    constexpr auto STEP = 20ms;

    class AccountFixture
    {
    public:
        explicit AccountFixture(std::optional<std::string_view> script, std::chrono::seconds killGrace = 30s, AccountOptions_s options = {}, BotMessenger* messenger = nullptr)
            : server{TestWorld::Send}
            , folder{"rs2004-account-tests"}
        {
            auto config = server.MakeConfig();
            config.scripting.scriptsDirectory = folder.GetPath().string();
            config.scripting.killGraceSeconds = killGrace;

            auto settings = AccountConfig_s{.name = "bot1", .credentials = FakeGameServer::MakeAccount()};
            if (script)
            {
                folder.WriteFile("main.py", *script);
                settings.script = ScriptConfig_s{.file = "main.py"};
            }

            account.emplace(std::make_shared<const Config_s>(config), FakeGameServer::MakeCache(), std::move(settings), ScriptTestRuntime::Get(), capture.GetLogger(), options, messenger);
            account->Login();
        }

        bool StepUntilFinished()
        {
            const auto deadline = Clock::now() + WAIT;
            while (Clock::now() < deadline && !account->IsFinished())
            {
                account->Step(STEP);
            }

            return account->IsFinished();
        }

        void StepFor(std::chrono::milliseconds duration)
        {
            const auto end = Clock::now() + duration;
            while (Clock::now() < end && !account->IsFinished())
            {
                account->Step(STEP);
            }
        }

        [[nodiscard]] bool LoggedOutByButton() const
        {
            return server.GetPackets(ClientProt_e::IfButton).size() == 1;
        }

        [[nodiscard]] bool HasLine(std::string_view message) const
        {
            return std::ranges::any_of(capture.GetEntries(), [message](const CapturedLog_s& entry)
            {
                return entry.message == message;
            });
        }

        LogCapture capture{LogLevel_e::Info};
        FakeGameServer server;
        TempFolder folder;
        std::optional<Account> account;
    };
}

TEST_CASE("An account without a script idles until interrupted", "[Account]")
{
    auto fixture = AccountFixture{std::nullopt};
    fixture.StepFor(200ms);
    CHECK_FALSE(fixture.account->IsFinished());

    fixture.account->Interrupt();
    REQUIRE(fixture.StepUntilFinished());
    CHECK(fixture.account->Succeeded());
    CHECK(fixture.LoggedOutByButton());
    CHECK(fixture.account->DescribeOutcome() == "logged out");

    const auto entries = fixture.capture.GetEntries();
    REQUIRE_FALSE(entries.empty());
    CHECK(entries.front().source == "bot1");
}

TEST_CASE("An account without a script logs out once its idleSeconds are up", "[Account]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send};
    const auto config = std::make_shared<const Config_s>(server.MakeConfig());
    auto account = Account{config, FakeGameServer::MakeCache(), AccountConfig_s{.name = "bot1", .credentials = FakeGameServer::MakeAccount(), .idleSeconds = 1s}, ScriptTestRuntime::Get(), capture.GetLogger()};

    const auto started = Clock::now();
    account.Login();
    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && !account.IsFinished())
    {
        account.Step(STEP);
    }

    REQUIRE(account.IsFinished());
    CHECK(Clock::now() - started >= 1s);
    CHECK(account.Succeeded());
    CHECK(server.GetPackets(ClientProt_e::IfButton).size() == 1);
    CHECK(std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.message == "Logging out: the account has idled for its idleSeconds (1 s)";
    }));
}

TEST_CASE("An account adds its define_bot script's default settings to its file", "[Account]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{};
    const auto folder = TempFolder{"rs2004-account-tests"};
    folder.WriteFile("main.py", "class Miner(LoopingBot):\n    def loop(self):\n        pass\n\n"
                                "BOT = define_bot(name='Miner', create=Miner, settings_schema={'trips': SettingDef('number', 5), 'rock': SettingDef('string', 'Copper rocks')})\n");
    folder.WriteFile("bot1.jsonc", "{\n    \"script\": {\n        \"file\": \"main.py\",\n        \"settings\": {\"Miner\": {\"trips\": 3}}\n    }\n}\n");

    auto config = server.MakeConfig();
    config.scripting.scriptsDirectory = folder.GetPath().string();
    const auto makeAccount = [&](std::filesystem::path file)
    {
        auto settings = AccountConfig_s{
            .name = "bot1",
            .file = std::move(file),
            .credentials = FakeGameServer::MakeAccount(),
            .script = ScriptConfig_s{.file = "main.py", .settings = R"json({"Miner": {"trips": 3}})json"},
        };
        return std::make_unique<Account>(std::make_shared<const Config_s>(config), FakeGameServer::MakeCache(), std::move(settings), ScriptTestRuntime::Get(), capture.GetLogger());
    };

    const auto hasLine = [&capture](LogLevel_e level, std::string_view start)
    {
        return std::ranges::any_of(capture.GetEntries(), [level, start](const CapturedLog_s& entry)
        {
            return entry.level == level && entry.message.starts_with(start);
        });
    };

    SECTION("the ones it lacks, as the script loads")
    {
        const auto file = folder.GetPath() / "bot1.jsonc";
        static_cast<void>(makeAccount(file));

        auto stream = std::ifstream{file, std::ios::binary};
        const auto text = std::string{std::istreambuf_iterator<char>{stream}, std::istreambuf_iterator<char>{}};
        CHECK(text == "{\n    \"script\": {\n        \"file\": \"main.py\",\n        \"settings\": {\"Miner\": {\"trips\": 3, \"rock\": \"Copper rocks\"}}\n    }\n}\n");
        CHECK(hasLine(LogLevel_e::Info, std::format("Added Miner's default settings to {}: rock", file.string())));
    }

    SECTION("and runs on with a warning when it can't")
    {
        static_cast<void>(makeAccount(folder.GetPath() / "missing.jsonc"));
        CHECK(hasLine(LogLevel_e::Warning, "Miner's default settings weren't added to the account file: "));
    }
}

TEST_CASE("An account logs out when its script stops it", "[Account]")
{
    auto fixture = AccountFixture{"def loop():\n    if npcs.query().id(50).exists():\n        stop_account()\n    return 100\n"};
    REQUIRE(fixture.StepUntilFinished());
    CHECK(fixture.account->Succeeded());
    CHECK(fixture.LoggedOutByButton());
}

TEST_CASE("An account logs out when its script fails, and reports the failure", "[Account]")
{
    auto fixture = AccountFixture{"def loop():\n    return 1 // 0\n"};
    REQUIRE(fixture.StepUntilFinished());
    CHECK_FALSE(fixture.account->Succeeded());
    CHECK(fixture.LoggedOutByButton());
}

TEST_CASE("An interrupted account lets its script finish first", "[Account]")
{
    SECTION("a script that handles the signal stops the account itself")
    {
        auto fixture = AccountFixture{"stopping = False\n\ndef on_kill_signal():\n    global stopping\n    stopping = True\n\ndef loop():\n    if stopping:\n        stop_account()\n    return 50\n"};
        fixture.StepFor(200ms);
        fixture.account->Interrupt();
        CHECK_FALSE(fixture.account->IsFinished());

        REQUIRE(fixture.StepUntilFinished());
        CHECK(fixture.account->Succeeded());
    }

    SECTION("a second interrupt logs out at once")
    {
        auto fixture = AccountFixture{"def on_kill_signal():\n    pass\n\ndef loop():\n    return 50\n"};
        fixture.StepFor(200ms);
        fixture.account->Interrupt();
        CHECK_FALSE(fixture.account->IsFinished());
        fixture.account->Interrupt();
        CHECK(fixture.account->GetClient().GetStatus() == ClientStatus_e::LoggingOut);
        REQUIRE(fixture.StepUntilFinished());
        CHECK(fixture.account->Succeeded());
    }

    SECTION("a script that ignores the signal is logged out when the grace runs out")
    {
        auto fixture = AccountFixture{"def on_kill_signal():\n    pass\n\ndef loop():\n    return 50\n", 0s};
        fixture.StepFor(200ms);
        fixture.account->Interrupt();
        REQUIRE(fixture.StepUntilFinished());
        CHECK(fixture.account->Succeeded());
    }
}

TEST_CASE("An interrupt during a logout the server ignores closes the connection at once", "[Account]")
{
    auto fixture = AccountFixture{std::nullopt};
    fixture.server.SetIgnoreLogout(true);
    fixture.account->Interrupt();
    fixture.StepFor(200ms);
    REQUIRE_FALSE(fixture.account->IsFinished());
    CHECK(fixture.account->GetClient().GetStatus() == ClientStatus_e::LoggingOut);

    fixture.account->Interrupt();
    CHECK(fixture.account->IsFinished());
    CHECK_FALSE(fixture.account->Succeeded());
    CHECK(fixture.account->DescribeOutcome() == "disconnected without a confirmed logout");
}

TEST_CASE("An account whose login is refused fails without throwing", "[Account]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{};
    server.SetLoginStatus(3);
    const auto config = std::make_shared<const Config_s>(server.MakeConfig());
    auto account = Account{config, FakeGameServer::MakeCache(), AccountConfig_s{.name = "bot1", .credentials = FakeGameServer::MakeAccount()}, ScriptTestRuntime::Get(), capture.GetLogger()};

    account.Start();
    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && !account.IsFinished())
    {
        account.Step(STEP);
    }

    REQUIRE(account.IsFinished());
    CHECK_FALSE(account.Succeeded());
    CHECK(account.DescribeOutcome() == "failed");
    CHECK(std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level == LogLevel_e::Error && entry.message.find("The account has stopped") != std::string::npos;
    }));
}

TEST_CASE("A watched account stays logged in while its script is broken", "[Account]")
{
    auto fixture = AccountFixture{"def loop():\n    raise ValueError('typo')\n", 30s, AccountOptions_s{.watchScripts = true}};
    fixture.StepFor(300ms);
    CHECK_FALSE(fixture.account->IsFinished());
    CHECK(fixture.server.GetPackets(ClientProt_e::IfButton).empty());

    fixture.folder.RewriteFile("main.py", "def loop():\n    log('fixed')\n    return 100\n");
    fixture.StepFor(1500ms);
    CHECK(fixture.HasLine("fixed"));

    fixture.account->Interrupt();
    REQUIRE(fixture.StepUntilFinished());
    CHECK(fixture.account->Succeeded());
}

TEST_CASE("An account takes bot messages for its script under its username", "[Account]")
{
    auto messenger = BotMessenger{};

    SECTION("a script that handles them gets them")
    {
        auto fixture = AccountFixture{"def on_bot_message(sender, message):\n    log('got', sender, message)\n\ndef loop():\n    return 100\n", 30s, {}, &messenger};
        CHECK(messenger.Send(FakeGameServer::USERNAME, BotMessage_s{.sender = "mule", .json = "[1]"}) == std::optional{true});
        fixture.StepFor(300ms);
        CHECK(fixture.HasLine("got mule [1]"));
    }

    SECTION("an account without a script turns them down")
    {
        auto fixture = AccountFixture{std::nullopt, 30s, {}, &messenger};
        CHECK(messenger.Send(FakeGameServer::USERNAME, BotMessage_s{.sender = "mule", .json = "[1]"}) == std::optional{false});
    }

    CHECK_FALSE(messenger.Send(FakeGameServer::USERNAME, BotMessage_s{.sender = "mule", .json = "[1]"}).has_value());
}

TEST_CASE("A script's relog logs out, waits, and logs back in with the script still loaded", "[Account]")
{
    constexpr auto SCRIPT = R"python(
relogs = 0

def on_reconnect():
    log('back after', relogs, 'relog')

def loop():
    global relogs
    if relogs == 0:
        relogs = 1
        relog(settings.get('delay', 0))
    return 100
)python";

    SECTION("back in after the delay")
    {
        auto fixture = AccountFixture{SCRIPT};
        const auto deadline = Clock::now() + WAIT;
        while (Clock::now() < deadline && !fixture.HasLine("back after 1 relog"))
        {
            fixture.account->Step(STEP);
        }

        CHECK(fixture.HasLine("back after 1 relog"));
        CHECK(fixture.LoggedOutByButton());
        CHECK(fixture.server.GetLoginOpcodes().size() == 2);
        CHECK_FALSE(fixture.account->IsFinished());

        fixture.account->Interrupt();
        REQUIRE(fixture.StepUntilFinished());
        CHECK(fixture.account->Succeeded());
    }
}

TEST_CASE("An interrupt during a relog's wait ends the account logged out", "[Account]")
{
    auto fixture = AccountFixture{"def on_stop(reason):\n    log('stopped:', reason)\n\ndef loop():\n    relog(60)\n    return 100\n"};
    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && fixture.account->GetClient().GetStatus() != ClientStatus_e::LoggedOut)
    {
        fixture.account->Step(STEP);
    }

    REQUIRE(fixture.account->GetClient().GetStatus() == ClientStatus_e::LoggedOut);
    fixture.StepFor(100ms);
    CHECK_FALSE(fixture.account->IsFinished());

    fixture.account->Interrupt();
    CHECK(fixture.account->IsFinished());
    CHECK(fixture.account->Succeeded());
    CHECK(fixture.HasLine("stopped: interrupted"));
    CHECK(fixture.server.GetLoginOpcodes().size() == 1);
}

#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/TestWorld.hpp"
#include "../LogCapture.hpp"
#include "../Script/ScriptTestRuntime.hpp"
#include "../TempFolder.hpp"

#include "Accounts/Account.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientProt.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = Account::Clock;

    constexpr auto WAIT = 10s;
    constexpr auto STEP = 20ms;

    class AccountFixture
    {
    public:
        explicit AccountFixture(std::optional<std::string_view> script, std::chrono::seconds killGrace = 30s)
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

            account.emplace(std::make_shared<const Config_s>(config), std::move(settings), ScriptTestRuntime::Get(), capture.GetLogger());
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

TEST_CASE("An account logs out when its script stops it", "[Account]")
{
    auto fixture = AccountFixture{"def loop():\n    if get_nearest_npc_by_id(50) is not None:\n        stop_account()\n    return 100\n"};
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
    auto account = Account{config, AccountConfig_s{.name = "bot1", .credentials = FakeGameServer::MakeAccount()}, ScriptTestRuntime::Get(), capture.GetLogger()};

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

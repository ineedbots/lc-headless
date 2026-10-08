#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/TestWorld.hpp"
#include "../LogCapture.hpp"
#include "../Script/ScriptTestRuntime.hpp"
#include "../TempFolder.hpp"

#include "Accounts/AccountRunner.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Script/ScriptError.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = AccountRunner::Clock;

    constexpr auto WAIT = 10s;
    constexpr auto LOOPER = "def loop():\n    log('loop')\n    return 100\n";

    AccountOptions_s FastOptions()
    {
        return {.client = {.retryDelay = 100ms, .loginTimeout = 5s, .keepaliveInterval = 50ms}};
    }

    AccountConfig_s MakeAccount(std::string name, const FakeGameServer* ownServer, std::optional<std::string> script)
    {
        auto account = AccountConfig_s{.name = name, .credentials = {.username = name, .password = "secret"}};
        if (ownServer != nullptr)
        {
            account.server = ServerSettings_s{.url = ownServer->Url()};
        }

        if (script)
        {
            account.script = ScriptConfig_s{.file = *script};
        }

        return account;
    }

    std::size_t CountLines(const LogCapture& capture, std::string_view source, std::string_view message)
    {
        const auto entries = capture.GetEntries();
        return static_cast<std::size_t>(std::ranges::count_if(entries, [source, message](const CapturedLog_s& entry)
        {
            return entry.source == source && entry.message == message;
        }));
    }

    // Two fake servers and a scripts folder holding the looper. Accounts log in to the first server
    // unless they name their own, and logins aren't staggered unless a test asks.
    class RunnerFixture
    {
    public:
        RunnerFixture()
            : first{TestWorld::Send}
            , second{TestWorld::Send}
            , folder{"rs2004-runner-tests"}
        {
            folder.WriteFile("looper.py", LOOPER);
            config = first.MakeConfig();
            config.scripting.scriptsDirectory = folder.GetPath().string();
            config.scripting.loginIntervalSeconds = 0s;
        }

        [[nodiscard]] std::unique_ptr<AccountRunner> MakeRunner(std::vector<AccountConfig_s> accounts)
        {
            return std::make_unique<AccountRunner>(std::make_shared<const Config_s>(config), std::move(accounts), ScriptTestRuntime::Get(), capture.GetLogger(), FastOptions());
        }

        [[nodiscard]] bool TimedOut() const
        {
            return Clock::now() - start > WAIT;
        }

        // Warnings and errors from the accounts appear with the next failed check, to explain it.
        void ReportProblems() const
        {
            for (const auto& entry : capture.GetEntries())
            {
                if (entry.level >= LogLevel_e::Warning)
                {
                    UNSCOPED_INFO(std::format("[{}] {}", entry.source, entry.message));
                }
            }
        }

        LogCapture capture{LogLevel_e::Info};
        FakeGameServer first;
        FakeGameServer second;
        TempFolder folder;
        Config_s config;
        Clock::time_point start = Clock::now();
    };
}

TEST_CASE("AccountRunner runs accounts side by side and logs them all out on an interrupt", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    auto runner = fixture.MakeRunner({MakeAccount("bot1", nullptr, "looper.py"), MakeAccount("bot2", &fixture.second, "looper.py")});

    const auto succeeded = runner->Run([&fixture]
    {
        const auto bothLooping = CountLines(fixture.capture, "bot1", "loop") >= 3 && CountLines(fixture.capture, "bot2", "loop") >= 3;
        return bothLooping || fixture.TimedOut() ? 1u : 0u;
    });
    fixture.ReportProblems();

    CHECK(succeeded);
    CHECK(CountLines(fixture.capture, "bot1", "loop") >= 3);
    CHECK(CountLines(fixture.capture, "bot2", "loop") >= 3);
    CHECK(runner->GetAccount(0).DescribeOutcome() == "logged out");
    CHECK(runner->GetAccount(1).DescribeOutcome() == "logged out");
    CHECK(fixture.first.GetPackets(ClientProt_e::IfButton).size() == 1);
    CHECK(fixture.second.GetPackets(ClientProt_e::IfButton).size() == 1);
}

TEST_CASE("AccountRunner keeps scripts running while another account's login stalls", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    fixture.second.SetStalled(true);
    auto runner = fixture.MakeRunner({MakeAccount("bot1", nullptr, "looper.py"), MakeAccount("bot2", &fixture.second, "looper.py")});

    auto loopsDone = std::optional<Clock::time_point>{};
    const auto succeeded = runner->Run([&fixture, &loopsDone]
    {
        if (!loopsDone && CountLines(fixture.capture, "bot1", "loop") >= 5)
        {
            loopsDone = Clock::now();
        }

        return loopsDone || fixture.TimedOut() ? 1u : 0u;
    });
    fixture.ReportProblems();

    REQUIRE(loopsDone.has_value());
    CHECK(*loopsDone - fixture.start < 3s);
    CHECK_FALSE(succeeded);
    CHECK(runner->GetAccount(0).Succeeded());
    CHECK_FALSE(runner->GetAccount(1).Succeeded());
    CHECK(fixture.second.GetLoginOpcodes().empty());
}

TEST_CASE("AccountRunner keeps scripts running while another account reconnects", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    auto runner = fixture.MakeRunner({MakeAccount("bot1", nullptr, "looper.py"), MakeAccount("bot2", &fixture.second, "looper.py")});

    auto phase = 0;
    auto droppedAt = Clock::time_point{};
    auto bot2LoopsAtDrop = std::size_t{0};
    auto bot2LoopsWhileDown = std::size_t{0};
    auto bot1LoopsAtReconnect = std::size_t{0};
    const auto succeeded = runner->Run([&]
    {
        auto& first = fixture.first;
        const auto bot1Loops = CountLines(fixture.capture, "bot1", "loop");
        const auto bot2Loops = CountLines(fixture.capture, "bot2", "loop");
        if (fixture.TimedOut())
        {
            return 1u;
        }

        if (phase == 0 && bot1Loops >= 3 && bot2Loops >= 3)
        {
            first.SetLoginStatus(15);
            first.SetStalled(true);
            first.Close();
            droppedAt = Clock::now();
            bot2LoopsAtDrop = bot2Loops;
            phase = 1;
        }
        else if (phase == 1 && Clock::now() - droppedAt > 1s)
        {
            bot2LoopsWhileDown = bot2Loops - bot2LoopsAtDrop;
            first.SetStalled(false);
            phase = 2;
        }
        else if (phase == 2 && first.GetLoginOpcodes().size() == 2 && runner->GetAccount(0).GetClient().IsInGame())
        {
            bot1LoopsAtReconnect = bot1Loops;
            phase = 3;
        }
        else if (phase == 3 && bot1Loops > bot1LoopsAtReconnect)
        {
            return 1u;
        }

        return 0u;
    });
    fixture.ReportProblems();

    CHECK(phase == 3);
    CHECK(bot2LoopsWhileDown >= 5);
    CHECK(fixture.first.GetLoginOpcodes() == std::vector<u8>{16, 18});
    CHECK(succeeded);
}

TEST_CASE("AccountRunner carries on when one account's login is refused", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    fixture.second.SetLoginStatus(3);
    auto runner = fixture.MakeRunner({MakeAccount("bot1", nullptr, "looper.py"), MakeAccount("bot2", &fixture.second, "looper.py")});

    const auto succeeded = runner->Run([&fixture]
    {
        return CountLines(fixture.capture, "bot1", "loop") >= 3 || fixture.TimedOut() ? 1u : 0u;
    });
    fixture.ReportProblems();

    CHECK_FALSE(succeeded);
    CHECK(runner->GetAccount(0).Succeeded());
    CHECK(runner->GetAccount(1).DescribeOutcome() == "failed");
}

TEST_CASE("AccountRunner logs everyone out on a second interrupt, without waiting for the scripts", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    fixture.folder.WriteFile("stubborn.py", "def on_kill_signal():\n    log('kill')\n\ndef loop():\n    log('loop')\n    return 100\n");
    auto runner = fixture.MakeRunner({MakeAccount("bot1", nullptr, "stubborn.py"), MakeAccount("bot2", &fixture.second, "stubborn.py")});

    const auto succeeded = runner->Run([&fixture]
    {
        if (fixture.TimedOut() || (CountLines(fixture.capture, "bot1", "kill") == 1 && CountLines(fixture.capture, "bot2", "kill") == 1))
        {
            return 2u;
        }

        return CountLines(fixture.capture, "bot1", "loop") >= 2 && CountLines(fixture.capture, "bot2", "loop") >= 2 ? 1u : 0u;
    });
    fixture.ReportProblems();

    CHECK(succeeded);
    CHECK(Clock::now() - fixture.start < 5s);
    CHECK(CountLines(fixture.capture, "bot1", "kill") == 1);
}

TEST_CASE("AccountRunner loads every script before the first login", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    fixture.folder.WriteFile("broken.py", "def on_start():\n    pass\n");
    const auto makeRunner = [&fixture]
    {
        static_cast<void>(fixture.MakeRunner({MakeAccount("bot1", nullptr, "looper.py"), MakeAccount("bot2", &fixture.second, "broken.py")}));
    };

    CHECK_THROWS_AS(makeRunner(), ScriptError);
    CHECK(fixture.first.GetLoginOpcodes().empty());
    CHECK(fixture.second.GetLoginOpcodes().empty());
}

TEST_CASE("AccountRunner spaces the logins out", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    fixture.config.scripting.loginIntervalSeconds = 1s;
    auto runner = fixture.MakeRunner({MakeAccount("bot1", nullptr, std::nullopt), MakeAccount("bot2", &fixture.second, std::nullopt)});

    auto firstLogin = std::optional<Clock::time_point>{};
    auto secondLogin = std::optional<Clock::time_point>{};
    static_cast<void>(runner->Run([&]
    {
        if (!firstLogin && !fixture.first.GetLoginOpcodes().empty())
        {
            firstLogin = Clock::now();
        }

        if (!secondLogin && !fixture.second.GetLoginOpcodes().empty())
        {
            secondLogin = Clock::now();
        }

        return (firstLogin && secondLogin) || fixture.TimedOut() ? 1u : 0u;
    }));
    fixture.ReportProblems();

    REQUIRE(firstLogin.has_value());
    REQUIRE(secondLogin.has_value());
    CHECK(*secondLogin - *firstLogin >= 900ms);
}

TEST_CASE("AccountRunner passes bot messages between its accounts", "[AccountRunner]")
{
    auto fixture = RunnerFixture{};
    auto third = FakeGameServer{TestWorld::Send};
    fixture.folder.WriteFile("ping.py", R"python(
def on_start():
    log('sent', send_bot_message('BOT2', {'ping': 1}), send_bot_message('idler', 1))

def on_bot_message(sender, message):
    log('reply', sender, message['pong'])

def loop():
    return 100
)python");
    fixture.folder.WriteFile("pong.py", R"python(
def on_bot_message(sender, message):
    send_bot_message(sender, {'pong': message['ping'] + 1})

def loop():
    return 100
)python");

    auto runner = fixture.MakeRunner({MakeAccount("bot1", nullptr, "ping.py"), MakeAccount("bot2", &fixture.second, "pong.py"), MakeAccount("idler", &third, std::nullopt)});
    const auto succeeded = runner->Run([&fixture]
    {
        return CountLines(fixture.capture, "bot1", "reply bot2 2") >= 1 || fixture.TimedOut() ? 1u : 0u;
    });
    fixture.ReportProblems();

    CHECK(succeeded);
    CHECK(CountLines(fixture.capture, "bot1", "sent True False") == 1);
    CHECK(CountLines(fixture.capture, "bot1", "reply bot2 2") == 1);
}

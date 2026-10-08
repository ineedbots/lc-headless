#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../Game/TestWorld.hpp"
#include "../LogCapture.hpp"
#include "../TempFolder.hpp"
#include "ScriptTestRuntime.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Script/ScriptError.hpp"
#include "Script/ScriptHost.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    using Clock = ScriptHost::Clock;

    constexpr auto WAIT = 5s;
    constexpr auto PUMP_STEP = 20ms;

    GameClientOptions_s FastOptions()
    {
        return {.retryDelay = 50ms, .loginTimeout = 5s, .keepaliveInterval = 50ms};
    }

    // A logged-in client with a script loaded from a temporary scripts folder. Steps take explicit
    // times, so the tests control when loop() is due.
    class HostFixture
    {
    public:
        explicit HostFixture(std::string_view script, std::string settings = "{}")
            : server{TestWorld::Send}
            , folder{"rs2004-script-host-tests"}
            , client{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()}
        {
            folder.WriteFile("main.py", script);
            host.emplace(ScriptTestRuntime::Get(), client, ScriptHostOptions_s{.scriptsDirectory = folder.GetPath(), .file = "main.py", .settings = std::move(settings)}, capture.GetLogger());
            client.Login();
            const auto deadline = Clock::now() + WAIT;
            while (Clock::now() < deadline && client.GetState().messages.empty())
            {
                client.Pump(PUMP_STEP);
            }

            REQUIRE_FALSE(client.GetState().messages.empty());
        }

        [[nodiscard]] std::vector<std::string> GetScriptLines() const
        {
            auto lines = std::vector<std::string>{};
            for (const auto& entry : capture.GetEntries())
            {
                if (entry.message.starts_with("> "))
                {
                    lines.push_back(entry.message.substr(2));
                }
            }

            return lines;
        }

        [[nodiscard]] bool HasLog(LogLevel_e level, std::string_view text) const
        {
            return std::ranges::any_of(capture.GetEntries(), [level, text](const CapturedLog_s& entry)
            {
                return entry.level == level && entry.message.find(text) != std::string::npos;
            });
        }

        LogCapture capture{LogLevel_e::Info};
        FakeGameServer server;
        TempFolder folder;
        GameClient client;
        std::optional<ScriptHost> host;
    };

    constexpr auto RECORDER = R"python(
def on_start():
    log('>', 'start', get_x() - get_local_player().x)

def on_npc_spawned(npc):
    log('>', 'npc', npc.id)

def on_ground_item_spawned(item):
    log('>', 'item', item.id, item.count)

def on_inventory_changed(com):
    log('>', 'inventory', com)

def on_server_message(msg):
    log('>', 'message', msg)

def on_server_tick(tick):
    log('>', 'tick', tick)

def loop():
    log('>', 'loop')
    return 600
)python";
}

TEST_CASE("ScriptHost starts the script, then passes it what arrived, then calls loop", "[ScriptHost]")
{
    auto fixture = HostFixture{RECORDER};
    const auto start = Clock::now();
    fixture.host->Step(start);

    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "start 0",
        "npc 50",
        "item 995 10",
        "inventory 3214",
        "message Welcome to RuneScape.",
        "tick 1",
        "loop",
    });

    SECTION("loop runs again only once the delay it returned has passed")
    {
        fixture.host->Step(start + 599ms);
        CHECK(fixture.GetScriptLines().size() == 7);
        REQUIRE(fixture.host->GetNextLoop().has_value());
        CHECK(*fixture.host->GetNextLoop() == start + 600ms);

        fixture.host->Step(start + 600ms);
        CHECK(fixture.GetScriptLines().back() == "loop");
        CHECK(fixture.GetScriptLines().size() == 8);
    }

    SECTION("each event and message is passed once")
    {
        fixture.server.Send(ServerProt_e::MessageGame, Fixtures::MessageGame("You catch a shrimp."));
        const auto deadline = Clock::now() + WAIT;
        while (Clock::now() < deadline && fixture.client.GetState().messages.size() < 2)
        {
            fixture.client.Pump(PUMP_STEP);
        }

        fixture.host->Step(start + 1ms);
        CHECK(fixture.GetScriptLines().back() == "message You catch a shrimp.");
        CHECK(fixture.GetScriptLines().size() == 8);
    }

    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
}

TEST_CASE("ScriptHost sends what the script does", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def loop():
    attack_npc(get_nearest_npc_by_id(50))
    return 10000
)python"};

    fixture.host->Step(Clock::now());
    fixture.client.Flush();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::OpNpc2));
    CHECK(fixture.server.GetPackets(ClientProt_e::OpNpc2)[0].payload == std::vector<u8>{0, 100});
    CHECK(fixture.server.GetPackets(ClientProt_e::MoveOpClick).size() == 1);
}

TEST_CASE("ScriptHost stops a script that fails", "[ScriptHost]")
{
    SECTION("an exception in a hook")
    {
        auto fixture = HostFixture{"def on_start():\n    raise ValueError('no chickens')\n\ndef loop():\n    return 600\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "ValueError: no chickens"));
        CHECK(fixture.HasLog(LogLevel_e::Error, "on_start()"));
    }

    SECTION("loop returning something other than an int")
    {
        auto fixture = HostFixture{"def loop():\n    pass\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "loop() must return how many milliseconds to wait, as an int, not NoneType"));
    }

    SECTION("loop returning a negative delay")
    {
        auto fixture = HostFixture{"def loop():\n    return -1\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
    }
}

TEST_CASE("ScriptHost stops when the script asks", "[ScriptHost]")
{
    SECTION("stop_script leaves the account to idle")
    {
        auto fixture = HostFixture{"def on_start():\n    stop_script()\n\ndef loop():\n    log('>', 'loop')\n    return 600\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Stopped);
        CHECK(fixture.GetScriptLines().empty());
        CHECK_FALSE(fixture.host->GetNextLoop().has_value());
    }

    SECTION("stop_account asks for a logout")
    {
        auto fixture = HostFixture{"def loop():\n    stop_account()\n    return 600\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::AccountStopped);
    }
}

TEST_CASE("ScriptHost passes the kill signal to a script that handles it", "[ScriptHost]")
{
    auto fixture = HostFixture{"def on_kill_signal():\n    log('>', 'kill')\n    stop_account()\n\ndef loop():\n    return 600\n"};
    fixture.host->Step(Clock::now());
    REQUIRE(fixture.host->HandlesKillSignal());

    fixture.host->SignalKill();
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"kill"});
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::AccountStopped);
    CHECK_FALSE(fixture.host->HandlesKillSignal());
}

TEST_CASE("ScriptHost gives scripts their settings", "[ScriptHost]")
{
    auto fixture = HostFixture{"def on_start():\n    log('>', settings.npc_id, settings.get('food', 'none'))\n\ndef loop():\n    return 600\n", R"json({"npc_id": 50})json"};
    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"50 none"});
}

TEST_CASE("ScriptHost calls on_reconnect after a dropped connection", "[ScriptHost]")
{
    auto fixture = HostFixture{"def on_reconnect():\n    log('>', 'reconnect')\n\ndef on_npc_spawned(npc):\n    log('>', 'npc', npc.id)\n\ndef loop():\n    return 600\n"};
    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"npc 50"});

    fixture.server.SetLoginStatus(15);
    fixture.server.Close();
    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && fixture.client.GetLoginCount() < 2)
    {
        fixture.client.Pump(PUMP_STEP);
    }

    REQUIRE(fixture.client.GetLoginCount() == 2);
    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"npc 50", "reconnect"});
}

TEST_CASE("ScriptHost calls on_reconnect once a fresh session has placed the player", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def on_reconnect():
    log('>', 'reconnect', get_x() - get_local_player().x, get_x() > 0)

def loop():
    return 600
)python"};
    fixture.host->Step(Clock::now());

    // The server lost the old session, as after a restart, so the reconnect becomes a fresh login.
    fixture.server.SetLoginStatus(2);
    fixture.server.Close();
    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && fixture.client.GetLoginCount() < 2)
    {
        fixture.client.Pump(PUMP_STEP);
        fixture.host->Step(Clock::now());
    }

    REQUIRE(fixture.client.GetLoginCount() == 2);
    while (Clock::now() < deadline && !fixture.client.GetState().placed)
    {
        fixture.client.Pump(PUMP_STEP);
        fixture.host->Step(Clock::now());
    }

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"reconnect 0 True"});
}

TEST_CASE("ScriptHost rejects a script it can't run before login", "[ScriptHost]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{};
    const auto folder = TempFolder{"rs2004-script-host-tests"};
    auto client = GameClient{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeAccount(), capture.GetLogger()};
    const auto load = [&](std::string_view source)
    {
        folder.WriteFile("main.py", source);
        auto host = ScriptHost{ScriptTestRuntime::Get(), client, {.scriptsDirectory = folder.GetPath(), .file = "main.py"}, capture.GetLogger()};
    };

    CHECK_THROWS_WITH(load("def on_start():\n    pass\n"), ContainsSubstring("main.py has no loop() function"));
    CHECK_THROWS_WITH(load("def loop(:\n    return 1\n"), ContainsSubstring("SyntaxError"));
    CHECK_THROWS_WITH(load("walk_to(1, 2)\ndef loop():\n    return 1\n"), ContainsSubstring("not in game"));

    SECTION("a misspelled hook is loaded, with a warning")
    {
        load("def on_npc_spawn(npc):\n    pass\n\ndef loop():\n    return 600\n");
        CHECK(std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning && entry.message.find("on_npc_spawn()") != std::string::npos;
        }));
    }
}

TEST_CASE("The example scripts load without warnings", "[ScriptHost]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{};
    auto client = GameClient{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeAccount(), capture.GetLogger()};
    const auto scripts = std::filesystem::path{RS2004_SOURCE_DIR} / "scripts";
    auto loaded = 0;
    for (const auto& entry : std::filesystem::directory_iterator{scripts / "examples"})
    {
        CAPTURE(entry.path().string());
        const auto file = std::filesystem::relative(entry.path(), scripts);
        CHECK_NOTHROW(ScriptHost{ScriptTestRuntime::Get(), client, {.scriptsDirectory = scripts, .file = file}, capture.GetLogger()});
        ++loaded;
    }

    CHECK(loaded >= 2);
    CHECK(std::ranges::none_of(capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level >= LogLevel_e::Warning;
    }));
}

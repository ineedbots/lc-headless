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
#include "Script/BotMessenger.hpp"
#include "Script/ProgressReport_s.hpp"
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

    using Files = std::vector<std::pair<std::string, std::string>>;

    // A logged-in client with a script loaded from a temporary scripts folder, as main.py beside any other
    // files given. Steps take explicit times, so the tests control when loop() is due.
    class HostFixture
    {
    public:
        explicit HostFixture(std::string_view script, std::string settings = "{}")
            : HostFixture{script, ScriptHostOptions_s{.settings = std::move(settings)}}
        {
        }

        HostFixture(std::string_view script, ScriptHostOptions_s options, const Files& otherFiles = {})
            : server{TestWorld::Send}
            , folder{"rs2004-script-host-tests"}
            , client{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()}
        {
            folder.WriteFile("main.py", script);
            for (const auto& [name, text] : otherFiles)
            {
                folder.WriteFile(name, text);
            }

            options.scriptsDirectory = folder.GetPath();
            options.file = "main.py";
            host.emplace(ScriptTestRuntime::Get(), client, std::move(options), capture.GetLogger());
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

TEST_CASE("ScriptHost asks for progress reports", "[ScriptHost]")
{
    auto reports = std::vector<ProgressReport_s>{};
    auto fixture = HostFixture{R"python(
kills = 0

def on_progress_report():
    global kills
    kills += 1
    return {'Kills': kills, 'Area': 'chickens', 'Rate': 1.5}

def loop():
    return 600
)python", ScriptHostOptions_s{.progressInterval = 1min, .onProgressReport = [&reports](const ProgressReport_s& report)
    {
        reports.push_back(report);
    }}};

    const auto start = Clock::now();
    fixture.host->Step(start);
    fixture.host->Step(start + 59s);
    CHECK(reports.empty());

    fixture.host->Step(start + 60s);
    REQUIRE(reports.size() == 1);
    CHECK(reports[0].runTime == 60s);
    CHECK(reports[0].rows == std::vector<std::pair<std::string, std::string>>{{"Kills", "1"}, {"Area", "chickens"}, {"Rate", "1.5"}});

    fixture.host->Step(start + 119s);
    CHECK(reports.size() == 1);
    fixture.host->Step(start + 120s);
    REQUIRE(reports.size() == 2);
    CHECK(reports[1].runTime == 120s);
    CHECK(reports[1].rows.front() == std::pair<std::string, std::string>{"Kills", "2"});
}

TEST_CASE("ScriptHost stops a script whose progress report isn't a dict", "[ScriptHost]")
{
    auto fixture = HostFixture{"def on_progress_report():\n    return [1]\n\ndef loop():\n    return 600\n", ScriptHostOptions_s{.progressInterval = 1min}};
    const auto start = Clock::now();
    fixture.host->Step(start);
    fixture.host->Step(start + 1min);
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
    CHECK(fixture.HasLog(LogLevel_e::Error, "on_progress_report() must return a dict, not list"));
}

TEST_CASE("ScriptHost warns when reports are asked for but the script makes none", "[ScriptHost]")
{
    auto fixture = HostFixture{"def loop():\n    return 600\n", ScriptHostOptions_s{.progressInterval = 1min}};
    CHECK(fixture.HasLog(LogLevel_e::Warning, "main.py has no on_progress_report()"));
}

TEST_CASE("ScriptHost sends and receives bot messages", "[ScriptHost]")
{
    auto messenger = BotMessenger{};
    auto sent = std::vector<BotMessage_s>{};
    messenger.Register("mule", [&sent](BotMessage_s message)
    {
        sent.push_back(std::move(message));
        return true;
    });
    messenger.Register("busy", [](BotMessage_s)
    {
        return false;
    });

    auto fixture = HostFixture{R"python(
def on_start():
    log('>', 'sent', send_bot_message('Mule', {'want': [995, 10], 'pair': (1, 2), 'note': 'say "hi"', 'none': None}))
    log('>', 'busy', send_bot_message('busy', 1))
    log('>', 'self', send_bot_message('BOT1', {'items': [1, 2], 'none': None}))
    try:
        send_bot_message('nobody', 1)
    except ValueError as e:
        log('>', 'unknown', str(e))
    try:
        send_bot_message('mule', get_local_player())
    except TypeError:
        log('>', 'not json')

def on_bot_message(sender, message):
    log('>', 'got', sender, message)
    if message != 'again':
        send_bot_message('bot1', 'again')

def loop():
    return 600
)python", ScriptHostOptions_s{.messenger = &messenger, .username = "bot1"}};
    messenger.Register("bot1", [&fixture](BotMessage_s message)
    {
        return fixture.host->ReceiveBotMessage(std::move(message));
    });

    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "sent True",
        "busy False",
        "self True",
        "unknown No account in this process has the username nobody",
        "not json",
        "got bot1 {'items': [1, 2], 'none': None}",
    });

    REQUIRE(sent.size() == 1);
    CHECK(sent[0].sender == "bot1");
    CHECK(sent[0].json == R"json({"want": [995, 10], "pair": [1, 2], "note": "say \"hi\"", "none": null})json");

    SECTION("a message sent while handling one waits for the next step")
    {
        fixture.host->Step(start + 1ms);
        CHECK(fixture.GetScriptLines().back() == "got bot1 again");
        CHECK(fixture.GetScriptLines().size() == 7);
    }
}

TEST_CASE("ScriptHost refuses a bot message over the size limit", "[ScriptHost]")
{
    auto messenger = BotMessenger{};
    messenger.Register("mule", [](BotMessage_s)
    {
        return true;
    });

    auto fixture = HostFixture{R"python(
def on_start():
    try:
        send_bot_message('mule', 'x' * 65536)
    except ValueError as e:
        log('>', str(e))
    log('>', send_bot_message('mule', 'x' * 65534))

def loop():
    return 600
)python", ScriptHostOptions_s{.messenger = &messenger, .username = "bot1"}};

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"The message is 65538 bytes as JSON, over the limit of 65536", "True"});
}

TEST_CASE("ScriptHost holds bot messages until the script can handle them", "[ScriptHost]")
{
    auto fixture = HostFixture{"def on_bot_message(sender, message):\n    log('>', sender, message)\n\ndef loop():\n    return 600\n"};
    for (auto i = std::size_t{0}; i < ScriptHost::MAX_BOT_MESSAGES; ++i)
    {
        CHECK(fixture.host->ReceiveBotMessage(BotMessage_s{.sender = "mule", .json = std::to_string(i)}));
    }

    CHECK_FALSE(fixture.host->ReceiveBotMessage(BotMessage_s{.sender = "mule", .json = "100"}));

    fixture.host->Step(Clock::now());
    const auto lines = fixture.GetScriptLines();
    REQUIRE(lines.size() == ScriptHost::MAX_BOT_MESSAGES);
    CHECK(lines.front() == "mule 0");
    CHECK(lines.back() == "mule 99");
    CHECK(fixture.host->ReceiveBotMessage(BotMessage_s{.sender = "mule", .json = "100"}));
}

TEST_CASE("ScriptHost turns bot messages down when the script can't take them", "[ScriptHost]")
{
    SECTION("the script has no on_bot_message")
    {
        auto fixture = HostFixture{"def loop():\n    return 600\n"};
        CHECK_FALSE(fixture.host->ReceiveBotMessage(BotMessage_s{.sender = "mule", .json = "1"}));
    }

    SECTION("the script has stopped")
    {
        auto fixture = HostFixture{"def on_start():\n    stop_script()\n\ndef on_bot_message(sender, message):\n    pass\n\ndef loop():\n    return 600\n"};
        CHECK(fixture.host->ReceiveBotMessage(BotMessage_s{.sender = "mule", .json = "1"}));
        fixture.host->Step(Clock::now());
        CHECK_FALSE(fixture.host->ReceiveBotMessage(BotMessage_s{.sender = "mule", .json = "1"}));
    }
}

TEST_CASE("ScriptHost reloads a watched script when its files change", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
import helper

def on_start():
    log('>', 'start', 'v1', helper.NAME)

def on_npc_spawned(npc):
    log('>', 'npc', npc.id)

def loop():
    return 600
)python", ScriptHostOptions_s{.watchFiles = true}, Files{{"helper.py", "NAME = 'one'\n"}}};

    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start v1 one", "npc 50"});

    SECTION("a changed script starts again from now, once the change has settled")
    {
        fixture.folder.RewriteFile("main.py", "def on_start():\n    log('>', 'start', 'v2')\n\ndef on_npc_spawned(npc):\n    log('>', 'npc', npc.id)\n\ndef loop():\n    return 600\n");
        fixture.host->Step(start + ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.GetScriptLines().size() == 2);

        fixture.host->Step(start + 2 * ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start v1 one", "npc 50", "start v2"});
        CHECK(fixture.HasLog(LogLevel_e::Info, "reloading main.py"));
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
        CHECK(fixture.host->GetNextLoop() == start + 2 * ScriptHost::WATCH_INTERVAL + 600ms);
    }

    SECTION("a change to a module it imports reloads it too")
    {
        fixture.folder.RewriteFile("helper.py", "NAME = 'two'\n");
        fixture.host->Step(start + ScriptHost::WATCH_INTERVAL);
        fixture.host->Step(start + 2 * ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.GetScriptLines().back() == "start v1 two");
    }

    SECTION("a change that can't load waits for the next one")
    {
        fixture.folder.RewriteFile("main.py", "def loop(:\n    return 600\n");
        fixture.host->Step(start + ScriptHost::WATCH_INTERVAL);
        fixture.host->Step(start + 2 * ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "waits for its files to change again"));

        fixture.folder.RewriteFile("main.py", "def on_start():\n    log('>', 'start', 'fixed')\n\ndef loop():\n    return 600\n");
        fixture.host->Step(start + 3 * ScriptHost::WATCH_INTERVAL);
        fixture.host->Step(start + 4 * ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
        CHECK(fixture.GetScriptLines().back() == "start fixed");
    }
}

TEST_CASE("ScriptHost keeps a watched script that fails waiting for a change", "[ScriptHost]")
{
    auto fixture = HostFixture{"def loop():\n    raise ValueError('typo')\n", ScriptHostOptions_s{.watchFiles = true}};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
    CHECK(fixture.HasLog(LogLevel_e::Error, "stopped until its files change"));

    fixture.folder.RewriteFile("main.py", "def on_start():\n    log('>', 'start', 'fixed')\n\ndef loop():\n    return 600\n");
    fixture.host->Step(start + ScriptHost::WATCH_INTERVAL);
    fixture.host->Step(start + 2 * ScriptHost::WATCH_INTERVAL);
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start fixed"});
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

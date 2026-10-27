#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/BitWriter.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/HostFixture.hpp"
#include "../Support/Script/ScriptCoverage.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"
#include "../Support/TempFolder.hpp"

#include "Accounts/ProgressReport_s.hpp"
#include "Cache/GameCache_s.hpp"
#include "Config/Config_s.hpp"
#include "Console/ConsoleCommand_s.hpp"
#include "Console/LogLevel_e.hpp"
#include "Console/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientPackets.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Packet.hpp"
#include "Script/BotMessenger.hpp"
#include "Script/Error/ScriptError.hpp"
#include "Script/Host/ScriptHost.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <nlohmann/json.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    using Clock = ScriptHost::Clock;

    // A component id as a packet carries it.
    std::vector<u8> ComBytes(u16 com)
    {
        return {static_cast<u8>(com >> 8), static_cast<u8>(com & 0xFF)};
    }

    constexpr auto RECORDER = R"python(
def on_start():
    log('>', 'start', game.tile().x - players.local().tile().x)

def on_npc_spawned(npc):
    log('>', 'npc', npc.id)

def on_ground_item_spawned(item):
    log('>', 'item', item.id, item.count)

def on_inventory_changed(e):
    log('>', 'inventory', e.slot, e.id, e.count, e.previous_id)

def on_server_message(msg):
    log('>', 'message', msg)

def on_tick(e):
    log('>', 'tick', e.tick)

def loop():
    log('>', 'loop')
    return 1000
)python";
}

TEST_CASE("ScriptHost starts the script, then passes it what arrived, then calls loop", "[ScriptHost]")
{
    auto fixture = HostFixture{RECORDER};
    const auto start = Clock::now();
    fixture.host->Step(start);

    // clang-format off
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "start 0",
        "npc 50",
        "item 995 10",
        "inventory 0 1511 3 -1",
        "message Welcome to RuneScape.",
        "tick 2",
        "loop",
    });
    // clang-format on

    SECTION("loop runs again only once the delay it returned has passed")
    {
        fixture.host->Step(start + 999ms);
        CHECK(fixture.GetScriptLines().size() == 7);
        REQUIRE(fixture.host->GetNextLoop().has_value());
        CHECK(*fixture.host->GetNextLoop() == start + 1000ms);

        fixture.host->Step(start + 1000ms);
        CHECK(fixture.GetScriptLines().back() == "loop");
        CHECK(fixture.GetScriptLines().size() == 8);
    }

    SECTION("each event and message is passed once")
    {
        fixture.server.Send(ServerProt_e::MessageGame, Fixtures::MessageGame("You catch a shrimp."));

        const auto deadline = Clock::now() + HostFixture::WAIT;
        while (Clock::now() < deadline && fixture.client.GetState().messages.size() < 2)
        {
            fixture.client.Pump(HostFixture::PUMP_STEP);
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
    npcs.query().name('goblin').nearest().interact('Attack')
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

    SECTION("loop returning something other than an int or None")
    {
        auto fixture = HostFixture{"def loop():\n    return 'soon'\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "loop() must return how many milliseconds to wait, as an int, or None, not str"));
    }

    SECTION("loop returning a negative delay")
    {
        auto fixture = HostFixture{"def loop():\n    return -1\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
    }

    SECTION("a generator loop yielding something other than an int")
    {
        auto fixture = HostFixture{"def loop():\n    yield 'soon'\n"};
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "loop() must yield milliseconds as an int, or a wait from execution, not str"));
    }

    SECTION("a generator loop returning a negative delay")
    {
        auto fixture = HostFixture{"def loop():\n    yield 0\n    return -1\n"};
        const auto start = Clock::now();
        fixture.host->Step(start);
        fixture.host->Step(start + 10ms);
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "loop() returned -1"));
    }

    SECTION("an exception in a generator loop after it yielded")
    {
        auto fixture = HostFixture{"def loop():\n    yield 600\n    raise ValueError('no chickens')\n"};
        const auto start = Clock::now();
        fixture.host->Step(start);
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);

        fixture.host->Step(start + 600ms);
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "ValueError: no chickens"));
    }
}

TEST_CASE("ScriptHost resumes a generator loop after each delay it yields", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def loop():
    log('>', 'walk')
    yield 600
    log('>', 'bank')
    yield 1200
    log('>', 'done')
    return 0
)python"};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"walk"});
    REQUIRE(fixture.host->GetNextLoop().has_value());
    CHECK(*fixture.host->GetNextLoop() == start + 600ms);

    fixture.host->Step(start + 599ms);
    CHECK(fixture.GetScriptLines().size() == 1);

    fixture.host->Step(start + 600ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"walk", "bank"});
    CHECK(*fixture.host->GetNextLoop() == start + 1800ms);

    // Finishing runs the rest of the generator, and loop() starts over after what it returned: 0, the next frame.
    fixture.host->Step(start + 1800ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"walk", "bank", "done"});
    CHECK(*fixture.host->GetNextLoop() == start + 1820ms);

    fixture.host->Step(start + 1820ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"walk", "bank", "done", "walk"});
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
}

TEST_CASE("ScriptHost hides loop deadlines while the client cannot run the script", "[ScriptHost]")
{
    auto fixture = HostFixture{"def loop():\n    log('>', 'loop')\n    return 100\n"};
    const auto start = Clock::now();
    fixture.host->Step(start);
    REQUIRE(fixture.host->GetNextLoop().has_value());

    SECTION("disconnected")
    {
        fixture.client.Disconnect();
    }

    SECTION("logging out")
    {
        fixture.client.RequestLogout(5s);
    }

    SECTION("waiting for placement to settle")
    {
        auto& state = const_cast<GameState_s&>(fixture.client.GetState());
        state.placedTick = state.tick;
    }

    // An overdue deadline must not make the runner spin while Step cannot consume it.
    CHECK_FALSE(fixture.host->GetNextLoop().has_value());
    fixture.host->Step(start + 1s);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"loop"});
    CHECK_FALSE(fixture.host->GetNextLoop().has_value());
}

TEST_CASE("ScriptHost waits for the delay a generator loop returns", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
fighting = True

def loop():
    global fighting
    if fighting:
        fighting = False
        log('>', 'fighting')
        return 700
    log('>', 'walk')
    yield 600
    log('>', 'bank')
    return 1200
)python"};
    const auto start = Clock::now();

    // A return before any yield is still a delay, not a call on the next pass.
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"fighting"});
    REQUIRE(fixture.host->GetNextLoop().has_value());
    CHECK(*fixture.host->GetNextLoop() == start + 700ms);

    // A yielded 600 is wall-clock time; only a returned 600 means a server tick.
    fixture.host->Step(start + 700ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"fighting", "walk"});
    CHECK(*fixture.host->GetNextLoop() == start + 1300ms);

    fixture.host->Step(start + 1300ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"fighting", "walk", "bank"});
    CHECK(*fixture.host->GetNextLoop() == start + 2500ms);

    fixture.host->Step(start + 2499ms);
    CHECK(fixture.GetScriptLines().size() == 3);

    fixture.host->Step(start + 2500ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"fighting", "walk", "bank", "walk"});
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

    const auto deadline = Clock::now() + HostFixture::WAIT;
    while (Clock::now() < deadline && fixture.client.GetLoginCount() < 2)
    {
        fixture.client.Pump(HostFixture::PUMP_STEP);
    }

    REQUIRE(fixture.client.GetLoginCount() == 2);
    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"npc 50", "reconnect"});
}

TEST_CASE("ScriptHost calls on_reconnect once a fresh session has placed the player", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def on_reconnect():
    log('>', 'reconnect', game.tile().x - players.local().tile().x, game.tile().x > 0)

def loop():
    return 600
)python"};
    fixture.host->Step(Clock::now());

    // The server lost the old session, as after a restart, so the reconnect becomes a fresh login.
    fixture.server.SetLoginStatus(2);
    fixture.server.Close();

    const auto deadline = Clock::now() + HostFixture::WAIT;
    while (Clock::now() < deadline && fixture.client.GetLoginCount() < 2)
    {
        fixture.client.Pump(HostFixture::PUMP_STEP);
        fixture.host->Step(Clock::now());
    }

    REQUIRE(fixture.client.GetLoginCount() == 2);

    while (Clock::now() < deadline && !fixture.client.GetState().IsSettled())
    {
        fixture.client.Pump(HostFixture::PUMP_STEP);
        fixture.host->Step(Clock::now());
    }

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"reconnect 0 True"});
}

TEST_CASE("ScriptHost's ticks and message marks carry on across a fresh session", "[ScriptHost]")
{
    // A bot that keeps "stunned until tick n" would otherwise wait until the new session's count caught up.
    auto fixture = HostFixture{R"python(
saved = {}

def on_reconnect():
    log('>', 'reconnect', game.tick() > saved['tick'], game_messages.mark() >= saved['mark'])

def loop():
    if 'tick' not in saved:
        saved['tick'] = game.tick()
        saved['mark'] = game_messages.mark()
    return 600
)python"};
    fixture.host->Step(Clock::now());

    fixture.server.SetLoginStatus(2);
    fixture.server.Close();

    const auto deadline = Clock::now() + HostFixture::WAIT;
    while (Clock::now() < deadline && fixture.client.GetLoginCount() < 2)
    {
        fixture.client.Pump(HostFixture::PUMP_STEP);
        fixture.host->Step(Clock::now());
    }

    REQUIRE(fixture.client.GetLoginCount() == 2);

    while (Clock::now() < deadline && !fixture.client.GetState().IsSettled())
    {
        fixture.client.Pump(HostFixture::PUMP_STEP);
        fixture.host->Step(Clock::now());
    }

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"reconnect True True"});
}

TEST_CASE("ScriptHost rejects a script it can't run before login", "[ScriptHost]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{};
    const auto folder = TempFolder{"rs2004-script-host-tests"};
    auto client = GameClient{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger()};
    const auto load = [&](std::string_view source)
    {
        folder.WriteFile("main.py", source);

        auto host = ScriptHost{ScriptTestRuntime::Get(), client, {.scriptsDirectory = folder.GetPath(), .file = "main.py"}, capture.GetLogger()};
    };

    CHECK_THROWS_WITH(load("def on_start():\n    pass\n"), ContainsSubstring("main.py has neither BOT = define_bot(...) nor a loop() function"));
    CHECK_THROWS_WITH(load("def loop(:\n    return 1\n"), ContainsSubstring("SyntaxError"));
    CHECK_THROWS_WITH(load("direct_navigator.walk((1, 2))\ndef loop():\n    return 1\n"), ContainsSubstring("not in game"));

    SECTION("a misspelled hook is loaded, with a warning")
    {
        load("def on_npc_spawn(npc):\n    pass\n\ndef loop():\n    return 600\n");
        CHECK(std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning && entry.message.find("on_npc_spawn()") != std::string::npos;
        }));
    }
}

TEST_CASE("ScriptHost runs on_progress_report and reads its rows as text", "[ScriptHost]")
{
    // clang-format off
    auto fixture = HostFixture{R"python(
kills = 0

def on_progress_report():
    global kills
    kills += 1
    return {'Kills': kills, 'Area': 'chickens', 'Rate': 1.5}

def loop():
    return 600
)python"};
    // clang-format on

    const auto start = Clock::now();
    CHECK_FALSE(fixture.host->IsActive());
    fixture.host->Step(start);
    REQUIRE(fixture.host->IsActive());
    CHECK(fixture.host->GetStartTime() == start);
    CHECK(fixture.host->HasProgressReport());

    const auto report = fixture.host->RunProgressReport(start + 60s);
    REQUIRE(report.has_value());
    CHECK(report->runTime == 60s);
    CHECK(report->rows == std::vector<std::pair<std::string, std::string>>{{"Kills", "1"}, {"Area", "chickens"}, {"Rate", "1.5"}});
    CHECK(fixture.host->RunProgressReport(start + 61s)->rows.front() == std::pair<std::string, std::string>{"Kills", "2"});
}

TEST_CASE("ScriptHost stops a script whose progress report isn't a dict", "[ScriptHost]")
{
    auto fixture = HostFixture{"def on_progress_report():\n    return [1]\n\ndef loop():\n    return 600\n"};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK_FALSE(fixture.host->RunProgressReport(start + 1min).has_value());
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
    CHECK(fixture.HasLog(LogLevel_e::Error, "on_progress_report() must return a dict, not list"));
}

TEST_CASE("ScriptHost has no progress report without on_progress_report", "[ScriptHost]")
{
    auto fixture = HostFixture{"def loop():\n    return 600\n"};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK_FALSE(fixture.host->HasProgressReport());
    CHECK_FALSE(fixture.host->RunProgressReport(start + 1min).has_value());
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
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

    // clang-format off
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
        send_bot_message('mule', players.local())
    except TypeError:
        log('>', 'not json')

def on_bot_message(sender, message):
    log('>', 'got', sender, message)
    if message != 'again':
        send_bot_message('bot1', 'again')

def loop():
    return 600
)python", ScriptHostOptions_s{.messenger = &messenger, .username = "bot1"}};
    // clang-format on
    messenger.Register("bot1", [&fixture](BotMessage_s message)
    {
        return fixture.host->ReceiveBotMessage(std::move(message));
    });

    const auto start = Clock::now();
    fixture.host->Step(start);
    // clang-format off
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "sent True",
        "busy False",
        "self True",
        "unknown No account in this process has the username nobody",
        "not json",
        "got bot1 {'items': [1, 2], 'none': None}",
    });
    // clang-format on

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

    // clang-format off
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
    // clang-format on

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
    // clang-format off
    auto fixture = HostFixture{R"python(
import helper

def on_start():
    log('>', 'start', 'v1', helper.NAME)

def on_npc_spawned(npc):
    log('>', 'npc', npc.id)

def loop():
    return 1000
)python", ScriptHostOptions_s{.watchFiles = true}, HostFixture::Files{{"helper.py", "NAME = 'one'\n"}}};
    // clang-format on

    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start v1 one", "npc 50"});

    SECTION("a changed script starts again from now, once the change has settled")
    {
        fixture.folder.RewriteFile("main.py", "def on_start():\n    log('>', 'start', 'v2')\n\ndef on_npc_spawned(npc):\n    log('>', 'npc', npc.id)\n\ndef loop():\n    return 1000\n");
        fixture.host->Step(start + ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.GetScriptLines().size() == 2);

        fixture.host->Step(start + 2 * ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start v1 one", "npc 50", "start v2"});
        CHECK(fixture.HasLog(LogLevel_e::Info, "reloading main.py"));
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
        CHECK(fixture.host->GetNextLoop() == start + 2 * ScriptHost::WATCH_INTERVAL + 1000ms);
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
        fixture.folder.RewriteFile("main.py", "def loop(:\n    return 1000\n");
        fixture.host->Step(start + ScriptHost::WATCH_INTERVAL);
        fixture.host->Step(start + 2 * ScriptHost::WATCH_INTERVAL);
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
        CHECK(fixture.HasLog(LogLevel_e::Error, "waits for its files to change again"));

        fixture.folder.RewriteFile("main.py", "def on_start():\n    log('>', 'start', 'fixed')\n\ndef loop():\n    return 1000\n");
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

TEST_CASE("ScriptHost resumes a wait for an update on the pump after the state changes", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def loop():
    log('>', 'waiting')
    found = yield from execution.delay_until(lambda: game.tick() > 2, 60000)
    log('>', 'found', found, game.tick())
    return 100000
)python"};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"waiting"});
    REQUIRE(fixture.host->GetNextLoop().has_value());
    CHECK(*fixture.host->GetNextLoop() == start + 60000ms);

    SECTION("a packet resumes it, without waiting for the timeout")
    {
        fixture.host->Step(start + 1ms);
        CHECK(fixture.GetScriptLines().size() == 1);

        fixture.SendTick();
        fixture.host->Step(start + 2ms);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"waiting", "found True 3"});
    }

    SECTION("the timeout resumes it without a packet")
    {
        fixture.host->Step(start + 60000ms);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"waiting", "found False 2"});
    }
}

TEST_CASE("ScriptHost waits a server tick when loop returns 600 or None", "[ScriptHost]")
{
    auto fixture = HostFixture{GENERATE(as<std::string>{}, "def loop():\n    log('>', 'loop', game.tick())\n", "def loop():\n    log('>', 'loop', game.tick())\n    return 600\n")};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"loop 2"});
    CHECK_FALSE(fixture.host->GetNextLoop().has_value());

    fixture.host->Step(start + 5000ms);
    CHECK(fixture.GetScriptLines().size() == 1);

    fixture.SendTick();
    fixture.host->Step(start + 5001ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"loop 2", "loop 3"});
}

TEST_CASE("ScriptHost runs the bot that BOT defines", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
class Fighter(TaskBot):
    loop_delay = 0

    def on_start(self):
        self.count = 0
        self.add(
            Task(lambda: self.count >= 2, self.rest, label='rest'),
            Task(lambda: True, self.fight, label='fight'),
        )

    def fight(self):
        self.count += 1
        log('>', 'fight', self.count, self.active_task_name)
        yield from execution.delay(100)
        log('>', 'fought', self.count)

    def rest(self):
        log('>', 'rest', self.settings.food, self.settings.str('food'))
        self.request_finish('rested')

    def on_stop(self, reason):
        log('>', 'stop', reason)

BOT = define_bot(name='Fighter', create=Fighter, settings_schema={'food': SettingDef('string', 'Shrimps')})
)python"};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"fight 1 fight"});

    // A loop_delay of 0 runs the next task a frame, 20ms, after the last.
    fixture.host->Step(start + 100ms);
    fixture.host->Step(start + 120ms);
    fixture.host->Step(start + 220ms);
    fixture.host->Step(start + 240ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"fight 1 fight", "fought 1", "fight 2 fight", "fought 2", "rest Shrimps Shrimps", "stop rested"});
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Stopped);
}

TEST_CASE("ScriptHost passes events to subscribers, and ends the bot once", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def on_start():
    events.on('tick', lambda e: log('>', 'tick', e.tick))
    events.on('chat_message', lambda e: log('>', 'chat', e.type, e.username, e.text))
    events.on('script_finish', lambda e: log('>', 'finish', e.reason))

def on_stop(reason):
    log('>', 'stop', reason)

def loop():
    raise ValueError('no chickens')
)python"};
    fixture.host->Step(Clock::now());
    // clang-format off
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "chat game None Welcome to RuneScape.",
        "tick 2",
        "stop the script failed",
        "finish the script failed",
    });
    // clang-format on
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);

    fixture.host->Finish("interrupted");
    CHECK(fixture.GetScriptLines().size() == 4);
}

TEST_CASE("ScriptHost checks a script's settings against its schema before login", "[ScriptHost]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{};
    const auto folder = TempFolder{"rs2004-script-host-tests"};
    auto client = GameClient{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger()};
    auto defaultsGiven = 0;
    const auto loadFile = [&](std::string file, std::string settings)
    {
        // clang-format off
        auto host = ScriptHost{ScriptTestRuntime::Get(), client,
            {
                .scriptsDirectory = folder.GetPath(),
                .file = std::move(file),
                .settings = std::move(settings),
                .onSettingDefaults = [&defaultsGiven](std::string_view, std::string_view)
                {
                    ++defaultsGiven;
                },
            },
            capture.GetLogger()};
        // clang-format on
    };

    folder.WriteFile("main.py", "SETTINGS_SCHEMA = {'count': SettingDef('number', 5, min=1), 'home': SettingDef('tile', [3222, 3218])}\n"
                                "def on_start():\n    log(settings.count, settings.home)\n"
                                "def loop():\n    return 1\n");

    const auto load = [&](std::string settings)
    {
        loadFile("main.py", std::move(settings));
    };

    CHECK_THROWS_WITH(load(R"({"count": 0})"), ContainsSubstring("settings.count must be at least 1"));
    CHECK_THROWS_WITH(load(R"({"count": "five"})"), ContainsSubstring("settings.count must be a number"));
    CHECK_THROWS_WITH(load(R"({"home": "east"})"), ContainsSubstring("settings.home must be a tile"));
    CHECK_NOTHROW(load(R"({"count": 2, "colour": "red"})"));
    CHECK(std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level == LogLevel_e::Warning && entry.message.find("settings.colour, which its settings schema doesn't declare") != std::string::npos;
    }));
    // Only a define_bot script has a place of its own in the account file to give defaults for.
    CHECK(defaultsGiven == 0);

    // A define_bot script's are the object under its name.
    folder.WriteFile("bot.py", "class Miner(LoopingBot):\n    def loop(self):\n        pass\n\n"
                               "BOT = define_bot(name='Miner', create=Miner, settings_schema={'count': SettingDef('number', 5, min=1)})\n");

    const auto loadBot = [&](std::string settings)
    {
        loadFile("bot.py", std::move(settings));
    };

    CHECK_THROWS_WITH(loadBot(R"({"Miner": {"count": 0}})"), ContainsSubstring(R"(settings["Miner"].count must be at least 1)"));
    CHECK_THROWS_WITH(loadBot(R"({"Miner": 5})"), ContainsSubstring(R"(settings["Miner"] must be an object)"));
    CHECK_NOTHROW(loadBot(R"({"count": 0, "Fighter": {"count": 0}})"));
    CHECK(defaultsGiven == 1);
}

TEST_CASE("ScriptHost gives a define_bot script the settings under its name, and passes on its defaults", "[ScriptHost]")
{
    auto defaults = std::vector<std::pair<std::string, std::string>>{};
    // clang-format off
    auto fixture = HostFixture{R"python(
class Miner(LoopingBot):
    def on_start(self):
        log('>', self.settings.rock, self.settings.trips, settings.rock, self.settings.home)

    def loop(self):
        pass

SCHEMA = {
    'rock': SettingDef('string', 'Copper rocks'),
    'trips': SettingDef('number', 5, min=1),
    'home': SettingDef('tile', [3222, 3218]),
    'partner': SettingDef('string', None),
}
BOT = define_bot(name='Miner', create=Miner, settings_schema=SCHEMA)
)python",
        ScriptHostOptions_s{
            .settings = R"json({"rock": "Iron rocks", "Miner": {"rock": "Tin rocks"}, "Fighter": {"food": "Trout"}})json",
            .onSettingDefaults = [&defaults](std::string_view botName, std::string_view settingsJson)
            {
                defaults.emplace_back(botName, settingsJson);
            },
        }};
    // clang-format on

    REQUIRE(defaults.size() == 1);
    CHECK(defaults[0].first == "Miner");
    CHECK(nlohmann::json::parse(defaults[0].second) == nlohmann::json::parse(R"json({"rock": "Copper rocks", "trips": 5, "home": [3222, 3218]})json"));

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"Tin rocks 5 Tin rocks Tile(3222, 3218, 0)"});
    CHECK(std::ranges::any_of(fixture.capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level == LogLevel_e::Warning && entry.message == R"(main.py ignores settings.rock: a define_bot script reads only settings["Miner"])";
    }));
}

TEST_CASE("ScriptHost passes on what settings_store saves, once the step is over", "[ScriptHost]")
{
    auto saves = std::vector<SettingSave_s>{};
    // clang-format off
    auto fixture = HostFixture{R"python(
class Miner(LoopingBot):
    def on_start(self):
        log('>', settings_store.saved('Miner', 'rock'))
        settings_store.save('Miner', 'rock', 'Iron rocks')
        settings_store.save('Loadouts', 'sets', [{'name': 'Melee', 'home': Tile(1, 2)}])

    def loop(self):
        log('>', settings_store.saved('Miner', 'rock'), settings_store.saved('Loadouts', 'sets'))
        stop_script()

BOT = define_bot(name='Miner', create=Miner)
)python",
        ScriptHostOptions_s{
            .settings = R"json({"Miner": {"rock": "Tin rocks"}})json",
            .onSettingSave = [&saves](const SettingSave_s& save)
            {
                saves.push_back(save);
            },
        }};
    // clang-format on

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"Tin rocks", "Iron rocks [{'name': 'Melee', 'home': [1, 2, 0]}]"});
    REQUIRE(saves.size() == 2);
    CHECK(saves[0].name == "Miner");
    CHECK(saves[0].key == "rock");
    CHECK(nlohmann::json::parse(saves[0].valueJson) == "Iron rocks");
    CHECK(saves[1].name == "Loadouts");
    CHECK(nlohmann::json::parse(saves[1].valueJson) == nlohmann::json::parse(R"json([{"name": "Melee", "home": [1, 2, 0]}])json"));
}

TEST_CASE("ScriptHost clicks the button under an interface's text", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def loop():
    log('>', 'clicked', interfaces.click_text('accept'), interfaces.click_text('Nothing here'))
    stop_script()
)python"};
    auto openMain = Packet{};
    openMain.P2(TestCache::TRADE_SCREEN);
    fixture.server.Send(ServerProt_e::IfOpenMain, Fixtures::ToBytes(openMain));

    const auto deadline = Clock::now() + HostFixture::WAIT;
    while (Clock::now() < deadline && fixture.client.GetState().interfaces.mainModal != TestCache::TRADE_SCREEN)
    {
        fixture.client.Pump(HostFixture::PUMP_STEP);
    }

    fixture.host->Step(Clock::now());
    fixture.client.Flush();
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"clicked True False"});
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(fixture.server.GetPackets(ClientProt_e::IfButton)[0].payload == std::vector<u8>{TestCache::TRADE_ACCEPT >> 8, TestCache::TRADE_ACCEPT & 0xFF});
}

TEST_CASE("ScriptHost drives a dialogue, an option and Make X to the end", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def loop():
    log('>', 'page', chat_dialog.can_continue(), chat_dialog.texts())
    ok = yield from chat_dialog.continue_()
    log('>', 'continued', ok, chat_dialog.can_continue(), chat_dialog.options())
    ok = yield from chat_dialog.choose_option('NO')
    log('>', 'chose', ok, chat_dialog.make_products(), chat_dialog.options())
    ok = yield from chat_dialog.make_x('long bow', 27)
    log('>', 'made', ok, reader.count_dialog_open())
    stop_script()
)python"};

    auto& client = fixture.client;
    const auto send = [&fixture](ServerProt_e prot, const Packet& packet)
    {
        fixture.server.Send(prot, Fixtures::ToBytes(packet));
    };
    const auto openChat = [&send](u16 id)
    {
        auto packet = Packet{};
        packet.P2(id);
        send(ServerProt_e::IfOpenChat, packet);
    };
    const auto setText = [&send](u16 com, std::string_view text)
    {
        auto packet = Packet{};
        packet.P2(com);
        packet.PJStr(text);
        send(ServerProt_e::IfSetText, packet);
    };
    const auto pumpUntil = [&client](auto condition)
    {
        const auto deadline = Clock::now() + HostFixture::WAIT;
        while (Clock::now() < deadline && !condition())
        {
            client.Pump(HostFixture::PUMP_STEP);
        }

        REQUIRE(condition());
    };
    const auto step = [&fixture]
    {
        fixture.host->Step(Clock::now());
        fixture.client.Flush();
    };
    const auto lastPayload = [&fixture](ClientProt_e prot)
    {
        return fixture.server.GetPackets(prot).back().payload;
    };

    setText(TestCache::DIALOGUE_TEXT, "Hello there.");
    openChat(TestCache::DIALOGUE);
    pumpUntil([&client]
    {
        return client.GetState().interfaces.chatModal == TestCache::DIALOGUE;
    });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePauseButton));
    CHECK(lastPayload(ClientProt_e::ResumePauseButton) == ComBytes(TestCache::DIALOGUE_CONTINUE));

    // The script waits for the server's answer; nothing more is sent meanwhile.
    step();
    CHECK(fixture.server.GetPackets(ClientProt_e::ResumePauseButton).size() == 1);

    setText(TestCache::OPTION_ONE, "Yes please.");
    setText(TestCache::OPTION_TWO, "No thanks.");
    openChat(TestCache::OPTIONS);
    pumpUntil([&client]
    {
        return client.GetState().interfaces.chatModal == TestCache::OPTIONS;
    });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(lastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::OPTION_TWO));

    openChat(TestCache::MAKE_MENU);
    pumpUntil([&client]
    {
        return client.GetState().interfaces.chatModal == TestCache::MAKE_MENU;
    });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton, 2));
    CHECK(lastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::MAKE_X));

    send(ServerProt_e::PCountDialog, Packet{});
    pumpUntil([&client]
    {
        return client.GetState().interfaces.countDialogOpen;
    });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePCountDialog));
    CHECK(lastPayload(ClientProt_e::ResumePCountDialog) == std::vector<u8>{0, 0, 0, 27});
    // clang-format off
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "page True ['Hello there.', 'Click here to continue']",
        "continued True False ['Yes please.', 'No thanks.']",
        "chose True ['Oak Long Bow'] []",
        "made True False",
    });
    // clang-format on
}

TEST_CASE("ScriptHost withdraws with X and deposits by the bank's options", "[ScriptHost]")
{
    constexpr auto BONES = u16{526};
    constexpr auto COINS = u16{995};
    constexpr auto LOGS = u16{1511};

    auto fixture = HostFixture{R"python(
def loop():
    ok = yield from bank.wait_ready()
    log('>', 'ready', ok, bank.count('Bones'), bank.items()[0].actions())
    ok = yield from bank.withdraw_x('bones', 27)
    log('>', 'withdrew', ok, inventory.count('Bones'))
    ok = yield from bank.set_note_mode(True)
    log('>', 'noted', ok)
    yield from bank.deposit_all_matching(deposit_all_except(['Coins']))
    log('>', 'deposited', bank.side_items())
    stop_script()
)python"};

    auto& client = fixture.client;
    const auto send = [&fixture](ServerProt_e prot, const Packet& packet)
    {
        fixture.server.Send(prot, Fixtures::ToBytes(packet));
    };
    const auto sendInventory = [&send](u16 com, const std::vector<std::pair<u16, u8>>& items)
    {
        auto packet = Packet{};
        packet.P2(com);
        packet.P2(static_cast<s32>(items.size()));
        for (const auto& [id, count] : items)
        {
            packet.P2(id + 1);
            packet.P1(count);
        }

        send(ServerProt_e::UpdateInvFull, packet);
    };
    const auto pumpUntil = [&client](auto condition)
    {
        const auto deadline = Clock::now() + HostFixture::WAIT;
        while (Clock::now() < deadline && !condition())
        {
            client.Pump(HostFixture::PUMP_STEP);
        }

        REQUIRE(condition());
    };
    const auto step = [&fixture]
    {
        fixture.host->Step(Clock::now());
        fixture.client.Flush();
    };
    const auto lastPayload = [&fixture](ClientProt_e prot)
    {
        return fixture.server.GetPackets(prot).back().payload;
    };
    const auto itemBytes = [](u16 obj, u16 slot, u16 com)
    {
        auto bytes = ComBytes(obj);
        for (const auto value : {slot, com})
        {
            const auto more = ComBytes(value);
            bytes.insert(bytes.end(), more.begin(), more.end());
        }

        return bytes;
    };

    sendInventory(TestCache::BANK, {{BONES, 30}, {COINS, 100}});
    sendInventory(TestCache::BANK_INVENTORY, {{LOGS, 3}});

    auto open = Packet{};
    open.P2(TestCache::BANK_SCREEN);
    open.P2(TestCache::BANK_SIDE);
    send(ServerProt_e::IfOpenMainSide, open);
    pumpUntil([&client]
    {
        return client.GetState().interfaces.mainModal == TestCache::BANK_SCREEN;
    });

    // 27 isn't 1, 5 or 10, so it's Withdraw X and the count dialog.
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::InvButton5));
    CHECK(lastPayload(ClientProt_e::InvButton5) == itemBytes(BONES, 0, TestCache::BANK));
    send(ServerProt_e::PCountDialog, Packet{});
    pumpUntil([&client]
    {
        return client.GetState().interfaces.countDialogOpen;
    });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePCountDialog));
    CHECK(lastPayload(ClientProt_e::ResumePCountDialog) == std::vector<u8>{0, 0, 0, 27});

    sendInventory(TestCache::INVENTORY, {{LOGS, 3}, {BONES, 27}});
    pumpUntil([&client]
    {
        return client.GetState().inventories.at(TestCache::INVENTORY).slots.size() == 2;
    });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(lastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::BANK_NOTE));

    fixture.SendTick();
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::InvButton4));
    CHECK(lastPayload(ClientProt_e::InvButton4) == itemBytes(LOGS, 0, TestCache::BANK_INVENTORY));
    sendInventory(TestCache::BANK_INVENTORY, {{0xFFFF, 0}});
    pumpUntil([&client]
    {
        return client.GetState().inventories.at(TestCache::BANK_INVENTORY).slots[0].id == -1;
    });
    step();

    // clang-format off
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "ready True 30 ['Withdraw 1', 'Withdraw 5', 'Withdraw 10', 'Withdraw All', 'Withdraw X']",
        "withdrew True 27",
        "noted True",
        "deposited []",
    });
    // clang-format on
}

// rs2b0t's bankSort.test.ts stubs the client; here the fake server plays the engine: the Swap and Insert buttons
// set %bankinsert, and a drag swaps or inserts by it, not by the packet's mode byte.
TEST_CASE("ScriptHost sorts the bank, setting insert mode and putting it back", "[ScriptHost]")
{
    constexpr auto COINS = u16{995};
    constexpr auto LAW_RUNE = u16{563};
    constexpr auto SHARK = u16{385};
    constexpr auto LOGS = u16{1511};
    constexpr auto BONES = u16{526};

    auto fixture = HostFixture{R"python(
def loop():
    result = yield from sort_bank()
    log('>', result.sorted, result.reason, result.mode, result.moves, [item.id for item in bank.items()])
    stop_script()
)python"};

    // Sorted, then topped up with a law rune, which belongs second: one insert, where swaps would take three.
    auto order = std::vector<u16>{COINS, SHARK, LOGS, BONES, LAW_RUNE};
    const auto sendBank = [&fixture, &order]
    {
        auto items = std::vector<std::pair<u16, u8>>{};
        for (const auto id : order)
        {
            items.emplace_back(id, 1);
        }

        fixture.SendInventory(TestCache::BANK, items);
    };
    const auto read2 = [](const std::vector<u8>& bytes, size_t at)
    {
        return static_cast<u16>((bytes[at] << 8) | bytes[at + 1]);
    };
    const auto answerButton = [&fixture, &read2](size_t count, u16 expected)
    {
        REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton, count));
        CHECK(read2(fixture.LastPayload(ClientProt_e::IfButton), 0) == expected);
        const auto value = expected == TestCache::BANK_INSERT ? 1 : 0;
        auto packet = Packet{};
        packet.P2(TestCache::BANK_INSERT_VARP);
        packet.P1(value);
        fixture.Send(ServerProt_e::VarpSmall, packet);
        fixture.PumpUntil([&fixture, value]
        {
            const auto& varps = fixture.client.GetState().varps;
            const auto found = varps.find(TestCache::BANK_INSERT_VARP);
            return found != varps.end() && found->second == value;
        });
    };

    sendBank();
    fixture.SendInventory(TestCache::BANK_INVENTORY, {});
    fixture.OpenMainSide(TestCache::BANK_SCREEN, TestCache::BANK_SIDE);

    // The plan is an insert, so the Insert button first, and the drag once the varp shows it.
    fixture.Step();
    answerButton(1, TestCache::BANK_INSERT);
    fixture.Step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::InvButtonD));
    const auto drag = fixture.LastPayload(ClientProt_e::InvButtonD);
    CHECK(read2(drag, 0) == TestCache::BANK);
    const auto from = read2(drag, 2);
    const auto to = read2(drag, 4);
    CHECK(from == 4);
    CHECK(to == 1);
    CHECK(drag[6] == static_cast<u8>(DragMode_e::Insert));
    const auto item = order[from];
    order.erase(order.begin() + from);
    order.insert(order.begin() + to, item);

    // The engine answers the drag on a later tick, and the next round waits for that answer before it plans.
    fixture.SendTick();
    sendBank();
    fixture.PumpUntil([&fixture]
    {
        return fixture.client.GetState().inventories.at(TestCache::BANK).slots[1].id == LAW_RUNE;
    });
    fixture.Step();

    // Sorted at the next round, so Swap again, as the bank was.
    fixture.SendTick();
    fixture.Step();
    answerButton(2, TestCache::BANK_SWAP);
    fixture.Step();

    CHECK(fixture.server.GetPackets(ClientProt_e::InvButtonD).size() == 1);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"True sorted insert 1 [995, 563, 385, 1511, 526]"});
}

TEST_CASE("ScriptHost buys from a shop in batches the engine runs in a tick", "[ScriptHost]")
{
    constexpr auto BONES = u16{526};
    constexpr auto LOGS = u16{1511};

    auto fixture = HostFixture{R"python(
def loop():
    log('>', 'shop', shop.is_open(), [item.name for item in shop.stock()], trade.active())
    bought = yield from shop.buy('Bones', 16)
    log('>', 'bought', bought)
    stop_script()
)python"};

    fixture.SendInventory(TestCache::SHOP_STOCK, {{BONES, 50}});
    fixture.SendInventory(TestCache::SHOP_SIDE_INV, {{LOGS, 3}});
    fixture.OpenMainSide(TestCache::SHOP_SCREEN, TestCache::SHOP_SIDE);
    fixture.Step();

    const auto bones = std::vector<u8>{BONES >> 8, BONES & 0xFF, 0, 0, TestCache::SHOP_STOCK >> 8, TestCache::SHOP_STOCK & 0xFF};
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::InvButton2));

    for (const auto prot : {ClientProt_e::InvButton4, ClientProt_e::InvButton3, ClientProt_e::InvButton2})
    {
        CHECK(fixture.server.GetPackets(prot).size() == 1);
        CHECK(fixture.LastPayload(prot) == bones);
    }

    fixture.SendInventory(TestCache::INVENTORY, {{LOGS, 3}, {BONES, 16}});
    fixture.PumpUntil([&fixture]
    {
        return fixture.client.GetState().inventories.at(TestCache::INVENTORY).slots.size() == 2;
    });
    fixture.Step();
    fixture.SendTick();
    fixture.Step();
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"shop True ['Bones'] False", "bought 16"});
}

TEST_CASE("ScriptHost offers, accepts and declines a trade by the screen's own options and labels", "[ScriptHost]")
{
    constexpr auto LOGS = u16{1511};

    auto fixture = HostFixture{R"python(
def loop():
    log('>', 'trade', trade.on_offer_screen(), trade.on_confirm_screen(), trade.partner(), shop.is_open())
    ok = yield from trade.offer('Logs', 2)
    log('>', 'offered', ok, [(item.name, item.count) for item in trade.my_offer()], trade.their_offer())
    log('>', 'accepted', trade.accept())
    ok = yield from trade.decline()
    log('>', 'declined', ok, trade.active())
    stop_script()
)python"};

    auto partner = Packet{};
    partner.P2(TestCache::TRADE_PARTNER);
    partner.PJStr("Trading With: Zezima");
    fixture.Send(ServerProt_e::IfSetText, partner);
    fixture.SendInventory(TestCache::TRADE_SIDE_INV, {{LOGS, 3}});
    fixture.OpenMainSide(TestCache::TRADE_SCREEN, TestCache::TRADE_SIDE);

    // 2 isn't 1, 5 or 10, so it's Offer X and the count dialog.
    fixture.Step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::InvButton5));
    CHECK(fixture.LastPayload(ClientProt_e::InvButton5) == std::vector<u8>{LOGS >> 8, LOGS & 0xFF, 0, 0, TestCache::TRADE_SIDE_INV >> 8, TestCache::TRADE_SIDE_INV & 0xFF});
    fixture.Send(ServerProt_e::PCountDialog, Packet{});
    fixture.PumpUntil([&fixture]
    {
        return fixture.client.GetState().interfaces.countDialogOpen;
    });
    fixture.Step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePCountDialog));

    fixture.SendInventory(TestCache::TRADE_MY_OFFER, {{LOGS, 1}, {LOGS, 1}});
    fixture.PumpUntil([&fixture]
    {
        return fixture.client.GetState().inventories.contains(TestCache::TRADE_MY_OFFER);
    });
    fixture.Step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(fixture.LastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::TRADE_ACCEPT));
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::CloseModal));

    fixture.Send(ServerProt_e::IfClose, Packet{});
    fixture.PumpUntil([&fixture]
    {
        return fixture.client.GetState().interfaces.mainModal == -1;
    });
    fixture.Step();
    // clang-format off
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "trade True False Zezima False",
        "offered True [('Logs', 1), ('Logs', 1)] []",
        "accepted True",
        "declined True False",
    });
    // clang-format on
}

TEST_CASE("The example scripts and the ported bots load without warnings", "[ScriptHost]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{};
    auto client = GameClient{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger()};
    const auto scripts = std::filesystem::path{RS2004_SOURCE_DIR} / "scripts";
    auto loaded = 0;
    for (const auto* const folder : {"examples", "bots"})
    {
        for (const auto& entry : std::filesystem::directory_iterator{scripts / folder})
        {
            // A package's own file isn't a script.
            if (entry.path().extension() != ".py" || entry.path().filename() == "__init__.py")
            {
                continue;
            }

            CAPTURE(entry.path().string());

            const auto file = std::filesystem::relative(entry.path(), scripts);
            CHECK_NOTHROW(ScriptHost{ScriptTestRuntime::Get(), client,
                                   {.scriptsDirectory = scripts, .file = file, .callTimeout = ScriptCoverage::AdjustTimeout(1s)},
                                   capture.GetLogger()});
            ++loaded;
        }
    }

    CHECK(loaded >= 5);
    for (const auto& entry : capture.GetEntries())
    {
        INFO(entry.message);
        CHECK(entry.level < LogLevel_e::Warning);
    }
}

TEST_CASE("ScriptHost calls on_death, on_npc_say and on_projectile", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def on_death():
    log('>', 'death')

def on_npc_say(npc, text):
    log('>', 'say', npc.id, text)

def on_projectile(p):
    log('>', 'projectile', p.spotanim, p.destination().x - p.source().x, p.targets_me())

def loop():
    return 600
)python"};
    fixture.host->Step(Clock::now());

    const auto sendHitpoints = [&fixture](u8 level)
    {
        auto stat = Packet{};
        stat.P1(3);
        stat.P4(1154);
        stat.P1(level);
        fixture.Send(ServerProt_e::UpdateStat, stat);
    };

    // Hitpoints arriving at login aren't a death; falling to 0 is.
    sendHitpoints(10);
    sendHitpoints(0);

    auto bits = BitWriter{};
    bits.Put(8, 1);
    bits.Put(1, 1).Put(2, 0);
    bits.Put(14, 16383);

    auto said = Packet{};
    said.P1(0x08);
    said.PJStr("Hello there");
    fixture.server.Send(ServerProt_e::NpcInfo, Fixtures::Concat(bits.GetBytes(), Fixtures::ToBytes(said)));

    fixture.server.Send(ServerProt_e::UpdateZonePartialFollows, Fixtures::Zone(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL));

    auto projectile = Packet{};
    projectile.P1((2 << 4) | 2);
    projectile.P1(3);
    projectile.P1(0);
    projectile.P2(-(Fixtures::PID + 1));
    projectile.P2(91);
    projectile.P1(43);
    projectile.P1(31);
    projectile.P2(51);
    projectile.P2(70);
    projectile.P1(16);
    projectile.P1(64);
    fixture.Send(ServerProt_e::MapProjAnim, projectile);
    fixture.PumpUntil([&fixture]
    {
        return !fixture.client.GetState().projectiles.empty();
    });

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"death", "say 50 Hello there", "projectile 91 3 True"});
}

TEST_CASE("ScriptHost's stall guard restarts a bot that makes no progress", "[ScriptHost]")
{
    constexpr auto SCRIPT = R"python(
def on_start():
    log('>', 'start')

def on_stop(reason):
    log('>', 'stop', reason)

def loop():
    if settings.get('busy', False):
        execution.note_progress()
    return 600
)python";

    const auto run = [](HostFixture& fixture)
    {
        // Ticks 4 s apart, so the guard doesn't take the time between them for a logout.
        const auto start = Clock::now();
        for (auto i = 0; i <= 17; ++i)
        {
            fixture.SendTick();
            fixture.host->Step(start + std::chrono::seconds{i * 4});
        }
    };

    SECTION("a minute without moving, experience or noted progress")
    {
        auto fixture = HostFixture{SCRIPT, ScriptHostOptions_s{.stallMinutes = std::chrono::minutes{1}}};
        run(fixture);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start", "stop the stall guard restarted the bot", "start"});
        CHECK(fixture.HasLog(LogLevel_e::Info, "stall guard: no progress for 1 min"));
        CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
    }

    SECTION("note_progress() keeps it waiting")
    {
        auto fixture = HostFixture{SCRIPT, ScriptHostOptions_s{.settings = R"({"busy": true})", .stallMinutes = std::chrono::minutes{1}}};
        run(fixture);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start"});
    }

    SECTION("off at zero")
    {
        auto fixture = HostFixture{SCRIPT};
        run(fixture);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"start"});
    }
}

TEST_CASE("ScriptHost runs the console commands its script added", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
def echo(command):
    log('>', command.name, command.text, command.args)

console.command('Echo', echo, 'Logs the text')

class Digger(LoopingBot):
    def on_start(self):
        self.command('dig', self.dig)

    def dig(self, command):
        log('>', 'digging')
        stop_account()

    def loop(self):
        return 600

BOT = define_bot(name='Digger', create=Digger)
)python"};

    const auto names = [&fixture]
    {
        auto found = std::vector<std::string>{};
        for (const auto& command : fixture.host->GetCommands())
        {
            found.push_back(command.name + ":" + command.help);
        }

        return found;
    };

    // Every script has the standard library's pause and resume.
    const auto pause = std::string{"pause:Stops stepping the bot until resume; random events are still answered"};
    const auto resume = std::string{"resume:Starts the bot again after pause"};
    CHECK(names() == std::vector<std::string>{"echo:Logs the text", pause, resume});
    CHECK_FALSE(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));

    fixture.host->Step(Clock::now());
    CHECK(names() == std::vector<std::string>{"dig:", "echo:Logs the text", pause, resume});
    CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "echo", .text = "hello  world", .args = {"hello", "world"}}));
    CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));

    fixture.host->Step(Clock::now());
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"echo hello  world ['hello', 'world']", "digging"});
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::AccountStopped);
    CHECK(fixture.host->GetCommands().empty());
}

TEST_CASE("ScriptHost pauses the bot on the console's pause, and carries on at resume", "[ScriptHost]")
{
    auto fixture = HostFixture{R"python(
class Walker(LoopingBot):
    loop_delay = 0

    def loop(self):
        log('>', 'loop')

    def on_pause(self):
        log('>', 'paused')

    def on_resume(self):
        log('>', 'resumed')

BOT = define_bot(name='Walker', create=Walker)
)python"};

    fixture.host->Step(Clock::now());
    CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "pause"}));
    fixture.host->Step(Clock::now());
    fixture.host->Step(Clock::now() + 1s);
    CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "resume"}));
    fixture.host->Step(Clock::now() + 2s);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"loop", "paused", "resumed", "loop"});
}

TEST_CASE("ScriptHost turns console commands down when the script can't take them", "[ScriptHost]")
{
    SECTION("the script hasn't added it")
    {
        auto fixture = HostFixture{"def loop():\n    return 600\n"};
        CHECK_FALSE(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));
    }

    SECTION("too many are waiting")
    {
        auto fixture = HostFixture{"console.command('dig', lambda command: log('>', command.text))\n\ndef loop():\n    return 600\n"};
        for (auto i = std::size_t{0}; i < ScriptHost::MAX_COMMANDS; ++i)
        {
            CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig", .text = std::to_string(i)}));
        }

        CHECK_FALSE(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));
        fixture.host->Step(Clock::now());
        CHECK(fixture.GetScriptLines().size() == ScriptHost::MAX_COMMANDS);
        CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));
    }

    SECTION("the script has stopped")
    {
        auto fixture = HostFixture{"console.command('dig', lambda command: None)\n\ndef on_start():\n    stop_script()\n\ndef loop():\n    return 600\n"};
        CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));
        fixture.host->Step(Clock::now());
        CHECK(fixture.host->GetCommands().empty());
        CHECK_FALSE(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));
    }
}

TEST_CASE("ScriptHost stops a script whose console command fails", "[ScriptHost]")
{
    auto fixture = HostFixture{"def dig(command):\n    raise ValueError('no spade')\n\nconsole.command('dig', dig)\n\ndef loop():\n    return 600\n"};
    CHECK(fixture.host->ReceiveCommand(ConsoleCommand_s{.name = "dig"}));
    fixture.host->Step(Clock::now());
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Failed);
    CHECK(fixture.HasLog(LogLevel_e::Error, "Script error in the dig command, so the script has stopped"));
    CHECK(fixture.HasLog(LogLevel_e::Error, "ValueError: no spade"));
}

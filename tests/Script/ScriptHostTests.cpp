#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../Cache/TestCache.hpp"
#include "../Game/TestWorld.hpp"
#include "../LogCapture.hpp"
#include "../TempFolder.hpp"
#include "ScriptTestRuntime.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Packet.hpp"
#include "Script/BotMessenger.hpp"
#include "Script/ProgressReport_s.hpp"
#include "Script/ScriptError.hpp"
#include "Script/ScriptHost.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    using Clock = ScriptHost::Clock;

    constexpr auto WAIT = 5s;
    constexpr auto PUMP_STEP = 20ms;

    // A component id as a packet carries it.
    std::vector<u8> ComBytes(u16 com)
    {
        return {static_cast<u8>(com >> 8), static_cast<u8>(com & 0xFF)};
    }

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
            , client{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()}
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

        // Sends a PLAYER_INFO, which is a server tick, and pumps until the client has it.
        void SendTick()
        {
            const auto tick = client.GetState().tick;
            server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer());
            const auto deadline = Clock::now() + WAIT;
            while (Clock::now() < deadline && client.GetState().tick == tick)
            {
                client.Pump(PUMP_STEP);
            }

            REQUIRE(client.GetState().tick == tick + 1);
        }

        void Send(ServerProt_e prot, const Packet& packet)
        {
            server.Send(prot, Fixtures::ToBytes(packet));
        }

        void SendInventory(u16 com, const std::vector<std::pair<u16, u8>>& items)
        {
            auto packet = Packet{};
            packet.P2(com);
            packet.P2(static_cast<s32>(items.size()));
            for (const auto& [id, count] : items)
            {
                packet.P2(id + 1);
                packet.P1(count);
            }

            Send(ServerProt_e::UpdateInvFull, packet);
        }

        void OpenMainSide(u16 main, u16 side)
        {
            auto packet = Packet{};
            packet.P2(main);
            packet.P2(side);
            Send(ServerProt_e::IfOpenMainSide, packet);
            PumpUntil([this, main] { return client.GetState().interfaces.mainModal == main; });
        }

        template <typename TCondition>
        void PumpUntil(TCondition condition)
        {
            const auto deadline = Clock::now() + WAIT;
            while (Clock::now() < deadline && !condition())
            {
                client.Pump(PUMP_STEP);
            }

            REQUIRE(condition());
        }

        // Runs the script's step now and sends what it queued.
        void Step()
        {
            host->Step(Clock::now());
            client.Flush();
        }

        [[nodiscard]] std::vector<u8> LastPayload(ClientProt_e prot) const
        {
            return server.GetPackets(prot).back().payload;
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

    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "start 0",
        "npc 50",
        "item 995 10",
        "inventory 0 1511 3 -1",
        "message Welcome to RuneScape.",
        "tick 1",
        "loop",
    });

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

    // Finishing runs the rest of the generator, and loop() starts over after what it returned.
    fixture.host->Step(start + 1800ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"walk", "bank", "done"});
    CHECK(*fixture.host->GetNextLoop() == start + 1800ms);

    fixture.host->Step(start + 1810ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"walk", "bank", "done", "walk"});
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
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
    log('>', 'reconnect', game.tile().x - players.local().tile().x, game.tile().x > 0)

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
    return 1000
)python", ScriptHostOptions_s{.watchFiles = true}, Files{{"helper.py", "NAME = 'one'\n"}}};

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
    found = yield from execution.delay_until(lambda: game.tick() > 1, 60000)
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
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"waiting", "found True 2"});
    }

    SECTION("the timeout resumes it without a packet")
    {
        fixture.host->Step(start + 60000ms);
        CHECK(fixture.GetScriptLines() == std::vector<std::string>{"waiting", "found False 1"});
    }
}

TEST_CASE("ScriptHost waits a server tick when loop returns 600 or None", "[ScriptHost]")
{
    auto fixture = HostFixture{GENERATE(as<std::string>{}, "def loop():\n    log('>', 'loop', game.tick())\n", "def loop():\n    log('>', 'loop', game.tick())\n    return 600\n")};
    const auto start = Clock::now();
    fixture.host->Step(start);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"loop 1"});
    CHECK_FALSE(fixture.host->GetNextLoop().has_value());

    fixture.host->Step(start + 5000ms);
    CHECK(fixture.GetScriptLines().size() == 1);

    fixture.SendTick();
    fixture.host->Step(start + 5001ms);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"loop 1", "loop 2"});
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

    fixture.host->Step(start + 100ms);
    fixture.host->Step(start + 101ms);
    fixture.host->Step(start + 201ms);
    fixture.host->Step(start + 202ms);
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
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "chat game None Welcome to RuneScape.",
        "tick 1",
        "stop the script failed",
        "finish the script failed",
    });
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
    const auto load = [&](std::string settings)
    {
        folder.WriteFile("main.py", "SETTINGS_SCHEMA = {'count': SettingDef('number', 5, min=1), 'home': SettingDef('tile', [3222, 3218])}\n"
                                    "def on_start():\n    log(settings.count, settings.home)\n"
                                    "def loop():\n    return 1\n");
        auto host = ScriptHost{ScriptTestRuntime::Get(), client, {.scriptsDirectory = folder.GetPath(), .file = "main.py", .settings = std::move(settings)}, capture.GetLogger()};
    };

    CHECK_THROWS_WITH(load(R"({"count": 0})"), ContainsSubstring("settings.count must be at least 1"));
    CHECK_THROWS_WITH(load(R"({"count": "five"})"), ContainsSubstring("settings.count must be a number"));
    CHECK_THROWS_WITH(load(R"({"home": "east"})"), ContainsSubstring("settings.home must be a tile"));
    CHECK_NOTHROW(load(R"({"count": 2, "colour": "red"})"));
    CHECK(std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level == LogLevel_e::Warning && entry.message.find("settings.colour, which its settings schema doesn't declare") != std::string::npos;
    }));
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
    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && fixture.client.GetState().interfaces.mainModal != TestCache::TRADE_SCREEN)
    {
        fixture.client.Pump(PUMP_STEP);
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
        const auto deadline = Clock::now() + WAIT;
        while (Clock::now() < deadline && !condition())
        {
            client.Pump(PUMP_STEP);
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
    pumpUntil([&client] { return client.GetState().interfaces.chatModal == TestCache::DIALOGUE; });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePauseButton));
    CHECK(lastPayload(ClientProt_e::ResumePauseButton) == ComBytes(TestCache::DIALOGUE_CONTINUE));

    // The script waits for the server's answer; nothing more is sent meanwhile.
    step();
    CHECK(fixture.server.GetPackets(ClientProt_e::ResumePauseButton).size() == 1);

    setText(TestCache::OPTION_ONE, "Yes please.");
    setText(TestCache::OPTION_TWO, "No thanks.");
    openChat(TestCache::OPTIONS);
    pumpUntil([&client] { return client.GetState().interfaces.chatModal == TestCache::OPTIONS; });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(lastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::OPTION_TWO));

    openChat(TestCache::MAKE_MENU);
    pumpUntil([&client] { return client.GetState().interfaces.chatModal == TestCache::MAKE_MENU; });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton, 2));
    CHECK(lastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::MAKE_X));

    send(ServerProt_e::PCountDialog, Packet{});
    pumpUntil([&client] { return client.GetState().interfaces.countDialogOpen; });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePCountDialog));
    CHECK(lastPayload(ClientProt_e::ResumePCountDialog) == std::vector<u8>{0, 0, 0, 27});
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "page True ['Hello there.', 'Click here to continue']",
        "continued True False ['Yes please.', 'No thanks.']",
        "chose True ['Oak Long Bow'] []",
        "made True False",
    });
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
        const auto deadline = Clock::now() + WAIT;
        while (Clock::now() < deadline && !condition())
        {
            client.Pump(PUMP_STEP);
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
    pumpUntil([&client] { return client.GetState().interfaces.mainModal == TestCache::BANK_SCREEN; });

    // 27 isn't 1, 5 or 10, so it's Withdraw X and the count dialog.
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::InvButton5));
    CHECK(lastPayload(ClientProt_e::InvButton5) == itemBytes(BONES, 0, TestCache::BANK));
    send(ServerProt_e::PCountDialog, Packet{});
    pumpUntil([&client] { return client.GetState().interfaces.countDialogOpen; });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePCountDialog));
    CHECK(lastPayload(ClientProt_e::ResumePCountDialog) == std::vector<u8>{0, 0, 0, 27});

    sendInventory(TestCache::INVENTORY, {{LOGS, 3}, {BONES, 27}});
    pumpUntil([&client] { return client.GetState().inventories.at(TestCache::INVENTORY).slots.size() == 2; });
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(lastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::BANK_NOTE));

    fixture.SendTick();
    step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::InvButton4));
    CHECK(lastPayload(ClientProt_e::InvButton4) == itemBytes(LOGS, 0, TestCache::BANK_INVENTORY));
    sendInventory(TestCache::BANK_INVENTORY, {{0xFFFF, 0}});
    pumpUntil([&client] { return client.GetState().inventories.at(TestCache::BANK_INVENTORY).slots[0].id == -1; });
    step();

    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "ready True 30 ['Withdraw 1', 'Withdraw 5', 'Withdraw 10', 'Withdraw All', 'Withdraw X']",
        "withdrew True 27",
        "noted True",
        "deposited []",
    });
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
    fixture.PumpUntil([&fixture] { return fixture.client.GetState().inventories.at(TestCache::INVENTORY).slots.size() == 2; });
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
    fixture.PumpUntil([&fixture] { return fixture.client.GetState().interfaces.countDialogOpen; });
    fixture.Step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::ResumePCountDialog));

    fixture.SendInventory(TestCache::TRADE_MY_OFFER, {{LOGS, 1}, {LOGS, 1}});
    fixture.PumpUntil([&fixture] { return fixture.client.GetState().inventories.contains(TestCache::TRADE_MY_OFFER); });
    fixture.Step();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(fixture.LastPayload(ClientProt_e::IfButton) == ComBytes(TestCache::TRADE_ACCEPT));
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::CloseModal));

    fixture.Send(ServerProt_e::IfClose, Packet{});
    fixture.PumpUntil([&fixture] { return fixture.client.GetState().interfaces.mainModal == -1; });
    fixture.Step();
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{
        "trade True False Zezima False",
        "offered True [('Logs', 1), ('Logs', 1)] []",
        "accepted True",
        "declined True False",
    });
}

TEST_CASE("The example scripts load without warnings", "[ScriptHost]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{};
    auto client = GameClient{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger()};
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

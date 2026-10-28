#include "pch.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"
#include "../Support/TempFolder.hpp"

#include "Accounts/AccountCommands.hpp"
#include "Game/Protocol/WordPack.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    class CommandsFixture
    {
    public:
        CommandsFixture()
            : commands{accounts, *capture.GetLogger()}
        {
            auto config = server.MakeConfig();
            config.scripting.scriptsDirectory = folder.GetPath().string();
            configuration = std::make_shared<const Config_s>(std::move(config));
            folder.WriteFile("commands.py", R"python(
def echo(command):
    log('echo', command.text)

console.command('echo', echo, 'Logs the text')
console.command('quiet', echo)

def loop():
    return 100
)python");
        }

        Account& Add(std::string name, bool scripted = false)
        {
            auto settings = AccountConfig_s{.name = name, .credentials = FakeGameServer::MakeAccount()};
            if (scripted)
            {
                settings.script = ScriptConfig_s{.file = "commands.py"};
            }
            accounts.push_back(std::make_unique<Account>(configuration, FakeGameServer::MakeCache(), std::move(settings), ScriptTestRuntime::Get(), capture.GetLogger()));
            return *accounts.back();
        }

        std::vector<std::string> Messages() const
        {
            auto messages = std::vector<std::string>{};
            for (const auto& entry : capture.GetEntries())
            {
                if (entry.source.empty())
                {
                    messages.push_back(entry.message);
                }
            }
            return messages;
        }

        void FillQueue(Account& account)
        {
            for (auto i = std::size_t{0}; i < ScriptHost::MAX_COMMANDS; ++i)
            {
                REQUIRE(account.SendCommand({.name = "echo", .text = "waiting"}));
            }
        }

        LogCapture capture{LogLevel_e::Info};
        FakeGameServer server{TestWorld::Send};
        TempFolder folder{"rs2004-command-tests"};
        std::shared_ptr<const Config_s> configuration;
        std::vector<std::unique_ptr<Account>> accounts;
        AccountCommands commands;
    };
}

TEST_CASE("AccountCommands finds file names and usernames without case sensitivity", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    auto& account = fixture.Add("Woodcutter");
    CHECK(fixture.commands.FindAccount("WOODCUTTER") == &account);
    CHECK(fixture.commands.FindAccount("BOT") == &account);
    CHECK(fixture.commands.FindAccount("missing") == nullptr);
    CHECK(fixture.commands.FindAccount("") == nullptr);
}

TEST_CASE("AccountCommands targeted help lists only the target's custom commands", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    fixture.Add("other", true);
    auto& target = fixture.Add("target", true);
    fixture.commands.ShowHelp(&target);
    CHECK(fixture.Messages() == std::vector<std::string>{"target: echo - Logs the text", "target: quiet"});
}

TEST_CASE("AccountCommands reports when help has no custom commands", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    auto& target = fixture.Add("idler");
    fixture.commands.ShowHelp(nullptr);
    auto messages = fixture.Messages();
    REQUIRE(messages.size() == 2);
    CHECK(messages.front().starts_with("Console commands:"));
    CHECK(messages.back() == "No script has added a console command");
    fixture.commands.ShowHelp(&target);
    CHECK(fixture.Messages().back() == "idler: no console commands");
}

TEST_CASE("AccountCommands status respects its account target", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    fixture.Add("other");
    auto& target = fixture.Add("target", true);
    fixture.commands.ShowStatus(&target);
    CHECK(fixture.Messages() == std::vector<std::string>{"target: " + target.DescribeStatus()});
}

TEST_CASE("AccountCommands accepts log levels in any case", "[AccountCommandCoverage]")
{
    const auto [name, level] = GENERATE(
        std::pair{"VERBOSE", LogLevel_e::Verbose}, std::pair{"Info", LogLevel_e::Info},
        std::pair{"WARNING", LogLevel_e::Warning}, std::pair{"Error", LogLevel_e::Error});
    auto fixture = CommandsFixture{};
    const auto args = std::vector<std::string>{name};
    fixture.commands.SetLogLevel(nullptr, args);
    CHECK(fixture.capture.GetLogger()->GetLevel() == level);
    if (level == LogLevel_e::Error)
    {
        CHECK(fixture.Messages().empty());
    }
    else
    {
        REQUIRE(fixture.Messages().size() == 1);
        CHECK(fixture.Messages().front().starts_with("The log level is now "));
    }
}

TEST_CASE("AccountCommands rejects targeted and extra log level arguments", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    auto& target = fixture.Add("target");
    const auto args = std::vector<std::string>{"verbose"};
    fixture.commands.SetLogLevel(&target, args);
    CHECK(fixture.Messages() == std::vector<std::string>{"loglevel applies to every account; leave out the @"});
    const auto extra = std::vector<std::string>{"verbose", "info"};
    fixture.commands.SetLogLevel(nullptr, extra);
    CHECK(fixture.Messages().back() == "loglevel takes one of verbose, info, warning or error");
    CHECK(fixture.capture.GetLogger()->GetLevel() == LogLevel_e::Info);
}

TEST_CASE("AccountCommands refuses public chat for an offline target", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    auto& target = fixture.Add("target");
    fixture.commands.Say(&target, "hello");
    CHECK(fixture.Messages() == std::vector<std::string>{"target isn't in game to say it"});
    CHECK(fixture.server.GetPackets(ClientProt_e::MessagePublic).empty());
    CHECK_FALSE(target.IsStarted());
}

TEST_CASE("AccountCommands truncates public chat before sending it", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    auto& target = fixture.Add("target");
    target.Login();
    REQUIRE(target.GetClient().IsInGame());
    const auto text = std::string(WordPack::MAX_PACK_LENGTH, 'a');
    fixture.commands.Say(&target, text + "discarded");
    target.Step(20ms);
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::MessagePublic));
    const auto packets = fixture.server.GetPackets(ClientProt_e::MessagePublic);
    REQUIRE(packets.size() == 1);
    CHECK(WordPack::Unpack(std::span{packets.front().payload}.subspan(2)) == "A" + text.substr(1));
    CHECK(fixture.Messages() == std::vector<std::string>{
        std::format("Public chat holds {} characters; the rest is cut off", WordPack::MAX_PACK_LENGTH),
        "target says: " + text});
}

TEST_CASE("AccountCommands warns when a targeted script command queue is full", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    auto& target = fixture.Add("target", true);
    fixture.FillQueue(target);
    fixture.commands.SendToScripts(&target, {.name = "echo", .text = "overflow"});
    CHECK(fixture.Messages() == std::vector<std::string>{"target can't take more console commands until it has run the ones waiting"});
}

TEST_CASE("AccountCommands broadcasts past a full queue to other matching scripts", "[AccountCommandCoverage]")
{
    auto fixture = CommandsFixture{};
    auto& full = fixture.Add("full", true);
    fixture.Add("idler");
    auto& available = fixture.Add("available", true);
    fixture.FillQueue(full);
    fixture.commands.SendToScripts(nullptr, {.name = "echo", .text = "broadcast"});
    CHECK(fixture.Messages() == std::vector<std::string>{"full can't take more console commands until it has run the ones waiting"});
    // One slot was consumed by the broadcast; the remaining slots still accept commands.
    for (auto i = std::size_t{1}; i < ScriptHost::MAX_COMMANDS; ++i)
    {
        REQUIRE(available.SendCommand({.name = "echo"}));
    }
    CHECK_FALSE(available.SendCommand({.name = "echo"}));
}

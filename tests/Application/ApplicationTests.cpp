#include "pch.hpp"
#include "../Support/ApplicationProcess.hpp"
#include "../Support/Cache/CacheWriter.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/TempFolder.hpp"

#include "Config/ConfigFile.hpp"
#include "Game/Nav/Navigation.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Utils/FileUtils.hpp"
#include "Script/ScriptVm.hpp"

#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/write.hpp>

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <nlohmann/json.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    void PlacePlayer(FakeGameServer& server, bool)
    {
        server.Send(ServerProt_e::RebuildNormal, Fixtures::Rebuild());
        server.Send(ServerProt_e::UpdatePid, Fixtures::UpdatePid());
        server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer());
        server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer());
    }

    class ApplicationFixture
    {
    public:
        ApplicationFixture() : server{PlacePlayer}, config{server.MakeConfig()}
        {
            auto contents = StoreContents_s{};
            contents.varps = {CacheWriter::MakeDefinition("", {}, std::vector<u8>{5, 0, 7})};
            contents.interfaces = {
                {.id = FakeGameServer::LOGOUT_COMPONENT, .layer = FakeGameServer::LOGOUT_COMPONENT, .type = 4, .buttonType = 1, .clientCode = 205},
                {.id = 2000, .layer = 2000, .type = 2, .clientCode = 206, .width = 8, .height = 36},
                {.id = 2001, .layer = 2001, .type = 2, .width = 4, .height = 7, .objUse = true},
                {.id = 2002, .layer = 2002, .type = 2, .width = 3, .height = 5, .slotBackground = true},
                {.id = 2003, .layer = 2003, .type = 2, .options = {"Deposit 1"}},
                {.id = 2004, .type = 5, .buttonType = 5, .conditions = {{1, 0}}, .scripts = {{5, 0, 0}}},
                {.id = 2005, .type = 5, .buttonType = 5, .conditions = {{1, 1}}, .scripts = {{5, 0, 0}}},
            };
            CacheWriter::MakeStore(contents).Write(folder.GetPath() / "cache");
            folder.WriteFile("nav/edges.json", "[]");
            for (const auto name : Navigation::DATA_FILES)
            {
                folder.WriteFile(std::format("nav/{}.json", name), "[]");
            }
            config.client.cacheDirectory = "cache";
            config.client.navDirectory = "nav";
            config.scripting.scriptsDirectory = "scripts";
            config.scripting.accountsDirectory = "accounts";
            config.scripting.connectAttempts = 0;
            config.scripting.loginIntervalSeconds = 0s;
            folder.WriteFile("scripts/main.py", "def loop():\n    log('application loop')\n    stop_account()\n");
            WriteAccount();
        }

        void WriteAccount(bool script = true)
        {
            auto account = nlohmann::json{{"username", "bot"}, {"password", "secret"}, {"randomEvents", false}, {"runAuto", false}, {"stallMinutes", 0}};
            if (script) account["script"] = {{"file", "main.py"}};
            folder.WriteFile("accounts/bot.jsonc", account.dump());
        }

        ApplicationResult_s Run(std::vector<std::string> arguments = {"--raw-console"}, std::string_view input = "")
        {
            folder.WriteFile("client.jsonc", ConfigFile::Serialize(config));
            return RunApplication(folder.GetPath(), arguments, input);
        }

        TempFolder folder{"rs2004 application tests"};
        FakeGameServer server;
        Config_s config;
    };
}

TEST_CASE("Application entry point reports invalid arguments and missing configuration", "[Application][ApplicationCoverage]")
{
    const auto folder = TempFolder{"rs2004 application arguments"};
    const auto invalid = RunApplication(folder.GetPath(), {"--unknown"});
    CHECK(invalid.exitCode == EXIT_FAILURE);
    CHECK_THAT(invalid.output, ContainsSubstring("Fatal error:"));
    CHECK_THAT(invalid.output, ContainsSubstring("usage:"));
    const auto missing = RunApplication(folder.GetPath(), {"--raw-console"});
    CHECK(missing.exitCode == EXIT_FAILURE);
    CHECK_THAT(missing.output, ContainsSubstring("copy client.jsonc.sample"));
}

TEST_CASE("Application loads accounts and exits successfully after a script requests logout", "[Application][ApplicationCoverage]")
{
    const auto explicitAccount = GENERATE(false, true);
    auto fixture = ApplicationFixture{};
    auto args = std::vector<std::string>{"--raw-console"};
    if (explicitAccount) args.insert(args.end(), {"--account", "accounts/bot.jsonc"});
    const auto result = fixture.Run(args);
    INFO(result.output);
    CHECK(result.exitCode == EXIT_SUCCESS);
    CHECK_THAT(result.output, ContainsSubstring("Running 1 account"));
    CHECK_THAT(result.output, ContainsSubstring("application loop"));
    CHECK_THAT(result.output, ContainsSubstring("Logging out: the script stopped the account"));
    CHECK(result.output.find('\x1b') == std::string::npos);
    CHECK(fixture.server.GetErrors().empty());
    REQUIRE(fixture.server.GetPackets(ClientProt_e::IfButton).size() == 1);
}

TEST_CASE("Application supplies a piped console and writes a log file", "[Application][ApplicationCoverage]")
{
    auto fixture = ApplicationFixture{};
    fixture.config.client.logFile = "logs/application.log";
    const auto result = fixture.Run({}, "help\n");
    INFO(result.output);
    CHECK(result.exitCode == EXIT_SUCCESS);
    CHECK_THAT(result.output, ContainsSubstring("for the console commands"));
    CHECK_THAT(result.output, ContainsSubstring("application loop"));
    const auto log = FileUtils::ReadText(fixture.folder.GetPath() / "logs/application.log");
    REQUIRE(log.has_value());
    CHECK_THAT(*log, ContainsSubstring("Config loaded from"));
    CHECK_THAT(*log, ContainsSubstring("application loop"));
}

TEST_CASE("Application accepts a UTF-8 BOM and CRLF commands from piped input", "[Application][FramingCoverage]")
{
    auto fixture = ApplicationFixture{};
    const auto result = fixture.Run({}, "\xEF\xBB\xBFhelp\r\nhelp\r\n");
    INFO(result.output);
    CHECK(result.exitCode == EXIT_SUCCESS);
    CHECK_THAT(result.output, ContainsSubstring("for the console commands"));
    CHECK_THAT(result.output, ContainsSubstring("application loop"));
    CHECK(result.output.find("Unknown command") == std::string::npos);
    const auto first = result.output.find("Console commands:");
    REQUIRE(first != std::string::npos);
    const auto second = result.output.find("Console commands:", first + 1);
    REQUIRE(second != std::string::npos);
    CHECK(result.output.find("Console commands:", second + 1) == std::string::npos);
    CHECK(fixture.server.GetErrors().empty());
}

TEST_CASE("Application returns failure for a script error", "[Application][ApplicationCoverage]")
{
    auto fixture = ApplicationFixture{};
    fixture.folder.WriteFile("scripts/main.py", "def loop():\n    raise ValueError('application failure')\n");
    const auto result = fixture.Run();
    INFO(result.output);
    CHECK(result.exitCode == EXIT_FAILURE);
    CHECK_THAT(result.output, ContainsSubstring("ValueError: application failure"));
    CHECK_THAT(result.output, ContainsSubstring("Logging out: the script failed"));
}

TEST_CASE("Application explains missing and empty account directories", "[Application][ApplicationCoverage]")
{
    const auto missing = GENERATE(false, true);
    auto fixture = ApplicationFixture{};
    fixture.config.scripting.accountsDirectory = missing ? "absent" : "empty";
    if (!missing) std::filesystem::create_directory(fixture.folder.GetPath() / "empty");
    const auto result = fixture.Run();
    INFO(result.output);
    CHECK(result.exitCode == EXIT_FAILURE);
    CHECK_THAT(result.output, ContainsSubstring(missing ? "no accounts folder" : "no enabled account files"));
}

TEST_CASE("Application resumes a scripted account after debugger configuration", "[Application][CompletionCoverage]")
{
    using Tcp = boost::asio::ip::tcp;
    auto fixture = ApplicationFixture{};
    auto io = boost::asio::io_context{};
    const auto endpoint = Tcp::endpoint{boost::asio::ip::make_address(ScriptVm::DEBUGGER_HOST), ScriptVm::DEBUGGER_PORT};
    auto probe = Tcp::acceptor{io};
    probe.open(Tcp::v4());
    auto error = boost::system::error_code{};
    probe.bind(endpoint, error);
    if (error) SKIP("The debugger's fixed port is already in use");
    probe.close();
    auto configured = false;
    auto response = std::string{};
    auto debugger = std::jthread{[&](std::stop_token stop)
    {
        auto socket = Tcp::socket{io};
        auto ec = boost::system::error_code{};
        const auto deadline = std::chrono::steady_clock::now() + 10s;
        while (!stop.stop_requested() && std::chrono::steady_clock::now() < deadline)
        {
            socket.connect(endpoint, ec);
            if (!ec) break;
            socket.close(ec);
            std::this_thread::sleep_for(10ms);
        }
        if (!socket.is_open()) return;
        const auto message = std::string{R"({"seq":1,"type":"request","command":"configurationDone","arguments":{}})"};
        const auto frame = std::format("Content-Length: {}\r\n\r\n{}", message.size(), message);
        boost::asio::write(socket, boost::asio::buffer(frame), ec);
        if (ec) return;
        configured = true;
        socket.non_blocking(true, ec);
        auto bytes = std::array<char, 4096>{};
        while (!ec && !stop.stop_requested())
        {
            const auto count = socket.read_some(boost::asio::buffer(bytes), ec);
            if (!ec) response.append(bytes.data(), count);
            else if (ec == boost::asio::error::would_block || ec == boost::asio::error::try_again) ec.clear();
            std::this_thread::sleep_for(1ms);
        }
    }};
    const auto result = fixture.Run({"--raw-console", "--debugger", "--account", "accounts/bot.jsonc"});
    debugger.request_stop();
    debugger.join();
    INFO(result.output);
    INFO(response);
    REQUIRE(configured);
    CHECK_THAT(response, ContainsSubstring("configurationDone"));
    CHECK(result.exitCode == EXIT_SUCCESS);
    CHECK_THAT(result.output, ContainsSubstring("Debugger attached"));
    CHECK_THAT(result.output, ContainsSubstring("application loop"));
    CHECK_THAT(result.output, ContainsSubstring("Logging out: the script stopped the account"));
}

TEST_CASE("Application requires a scripted account for the debugger", "[Application][ApplicationCoverage]")
{
    auto fixture = ApplicationFixture{};
    fixture.WriteAccount(false);
    const auto result = fixture.Run({"--raw-console", "--debugger", "--account", "accounts/bot.jsonc"});
    INFO(result.output);
    CHECK(result.exitCode == EXIT_FAILURE);
    CHECK_THAT(result.output, ContainsSubstring("--debugger needs an account with a script"));
}

TEST_CASE("Application creates profiles and enables script watching", "[Application][ApplicationCoverage]")
{
    auto fixture = ApplicationFixture{};
    const auto result = fixture.Run({"--raw-console", "--watch", "--profile"});
    INFO(result.output);
    CHECK(result.exitCode == EXIT_SUCCESS);
    CHECK_THAT(result.output, ContainsSubstring("Watching the scripts"));
    CHECK_THAT(result.output, ContainsSubstring("Script profiling enabled"));
    auto reports = std::vector<std::filesystem::path>{};
    for (const auto& entry : std::filesystem::recursive_directory_iterator{fixture.folder.GetPath() / "profiles"})
    {
        if (entry.path().filename() == "profiler_report.json") reports.push_back(entry.path());
    }
    REQUIRE(reports.size() == 1);
    const auto report = FileUtils::ReadText(reports.front());
    REQUIRE(report.has_value());
    CHECK(nlohmann::json::parse(*report).at("records").contains("main.py"));
}

TEST_CASE("Application continues when its profile directory cannot be created", "[Application][ApplicationCoverage]")
{
    auto fixture = ApplicationFixture{};
    fixture.folder.WriteFile("profiles", "blocked");
    const auto result = fixture.Run({"--raw-console", "--profile"});
    INFO(result.output);
    CHECK(result.exitCode == EXIT_SUCCESS);
    CHECK_THAT(result.output, ContainsSubstring("Couldn't create profile directory"));
    CHECK_THAT(result.output, ContainsSubstring("application loop"));
    CHECK(FileUtils::ReadText(fixture.folder.GetPath() / "profiles") == "blocked");
}

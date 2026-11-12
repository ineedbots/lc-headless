#include "pch.hpp"
#include "Application/ApplicationRequestProcessor.hpp"
#include "Config/ConfigJson.hpp"
#include "Config/ConfigValidator.hpp"
#include "Config/Error/ConfigError.hpp"
#include "Console/LogSinks.hpp"
#include "Io/AsioNetLoop.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"
#include "../Support/Script/HostFixture.hpp"
#include <boost/asio/post.hpp>
#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

TEST_CASE("HTTP settings trim hosts and round trip with strict numeric bounds", "[Http][Config]")
{
    using Json = nlohmann::json;
    auto game = FakeGameServer{};
    CHECK(ConfigJson::ParseConfig("{}").http.host.empty());
    CHECK(ConfigJson::ParseConfig(R"({"http":{"host":" \t "}})").http.host.empty());

    const auto config = ConfigJson::ParseConfig(R"({"http":{"host":" ::1 ","port":12345,"requestTimeoutMs":100,"maxPendingRequests":1,"maxRequestBodyBytes":1,"maxOutputBytes":1}})");
    const auto copy = ConfigJson::ParseConfig(ConfigJson::SerializeConfig(config));
    CHECK(copy.http.host == "::1");
    CHECK(copy.http.port == 12345);
    CHECK(copy.http.requestTimeoutMs == 100ms);

    for (const auto key : {"port", "requestTimeoutMs", "maxPendingRequests", "maxRequestBodyBytes", "maxOutputBytes"})
    {
        for (const auto& value : std::vector<Json>{-1, 0, 18446744073709551615ull, 1.5, "42", true, nullptr})
        {
            INFO(key << " = " << value.dump());
            CHECK_THROWS_AS(ConfigJson::ParseConfig(Json{{"http", {{key, value}}}}.dump()), ConfigError);
        }
    }

    for (const auto host : {"127.0.0.1", "::1", "localhost", ""})
    {
        auto valid = game.MakeConfig();
        valid.http.host = host;
        CHECK_NOTHROW(ConfigValidator::Validate(valid));
    }

    for (const auto host : {"http://localhost", "127.0.0.1:8080", "example.com", "localhost/path", "*", "[::1]:8080", "[::1]"})
    {
        INFO(host);

        auto invalid = game.MakeConfig();
        invalid.http.host = host;
        CHECK_THROWS_AS(ConfigValidator::Validate(invalid), ConfigError);
    }
}

TEST_CASE("Request capacity spans engine and HTTP retirement and completions occur once", "[Http][RequestBridge]")
{
    auto settings = HttpSettings_s{};
    settings.maxPendingRequests = 1;

    auto bridge = ApplicationRequestBridge{settings};
    const auto first = bridge.Reserve();
    REQUIRE(first);
    CHECK_FALSE(bridge.Reserve());
    bridge.Commit({first, ExecuteConsoleCommand_s{"status"}});
    REQUIRE(bridge.Take());
    bridge.Abandon(first->id);
    bridge.RetireHttp(first->id);
    CHECK_FALSE(bridge.Reserve());
    bridge.Complete({.id = first->id});
    bridge.Complete({.id = first->id});
    CHECK(bridge.TakeCompleted().empty());
    CHECK(bridge.Outstanding() == 0);

    const auto second = bridge.Reserve();
    REQUIRE(second);
    CHECK(second->id > first->id);
    bridge.Complete({.id = second->id});
    bridge.Complete({.id = second->id});
    CHECK(bridge.TakeCompleted().size() == 1);
    CHECK_FALSE(bridge.Reserve());
    bridge.RetireHttp(second->id);
    CHECK(bridge.Outstanding() == 0);
    bridge.Close();
    CHECK_FALSE(bridge.Reserve());
}

TEST_CASE("Processor dispatches builtins and snapshots only at safe points and rejects expired work", "[Http][RequestProcessor]")
{
    auto config = std::make_shared<const Config_s>();
    auto logger = std::make_shared<Logger>();
    logger->SetSink(LogSinks::Make({}, {}, true));

    auto runner = AccountRunner{config, FakeGameServer::MakeCache(), {}, ScriptTestRuntime::Get(), logger};
    auto bridge = std::make_shared<ApplicationRequestBridge>(HttpSettings_s{});
    auto processor = ApplicationRequestProcessor{runner, bridge, std::chrono::steady_clock::now() - 1s};
    const auto submit = [&](std::string line)
    {
        const auto control = bridge->Reserve();
        bridge->Commit({control, ExecuteConsoleCommand_s{std::move(line)}});
        return control;
    };

    auto expired = submit("loglevel error");
    expired->deadline = std::chrono::steady_clock::now() - 1ms;

    auto help = submit("help");
    auto bad = submit("@missing status");
    CHECK_FALSE(help->engineDone);
    processor.Dispatch();
    CHECK(logger->GetLevel() == LogLevel_e::Info);
    CHECK_FALSE(help->engineDone);

    while (bridge->HasIncoming())
    {
        processor.Dispatch();
    }

    processor.Finalize();

    const auto results = bridge->TakeCompleted();
    REQUIRE(results.size() == 3);
    CHECK(results[0].outcome == "cancelled");
    CHECK(std::get<ConsoleCommandResult_s>(results[1].payload).output.find("Console commands") != std::string::npos);
    CHECK(results[2].outcome == "rejected");

    const auto status = bridge->Reserve();
    bridge->Commit({status, GetApplicationStatus_s{}});
    processor.Dispatch();

    const auto snapshot = bridge->TakeCompleted();
    REQUIRE(snapshot.size() == 1);
    CHECK(std::get<ApplicationStatus_s>(snapshot[0].payload).uptimeMs >= 1000);
    processor.Stop();
    processor.Stop();
}

TEST_CASE("Capture excludes other threads and nested I/O and preserves UTF8 boundaries", "[Http][ConsoleCapture]")
{
    auto loop = std::make_shared<AsioNetLoop>();
    auto capture = ConsoleCapture{1024};
    {
        const auto scope = ConsoleCaptureScope{&capture};
        ConsoleCaptureScope::Write("first\n");

        std::thread other{[]
        {
            ConsoleCaptureScope::Write("other thread");
        }};
        other.join();
        {
            const auto pause = ConsoleCaptureScope{nullptr};
            ConsoleCaptureScope::Write("I/O callback");
        }

        ConsoleCaptureScope::Write("last\n");
    }

    CHECK(capture.output == "first\nlast\n");

    auto limited = ConsoleCapture{3};
    limited.Append("ab\xc3\xa9");
    limited.Append("ignored");
    CHECK(limited.output == "ab");
    CHECK(limited.truncated);
}

TEST_CASE("Tracked script commands capture actual handler return and partial Python lines", "[Http][ScriptHost]")
{
    auto fixture = HostFixture{R"python(
console.command('echo', lambda command: print(command.text, end=''))
def boom(command):
    print('before error', end='')
    raise ValueError('broken')
console.command('boom', boom)
def loop():
    return 1000
)python"};
    fixture.capture.GetLogger()->SetSink(LogSinks::Make({}, {}, true));

    auto execution = std::make_shared<CommandExecution>(1024, std::chrono::steady_clock::now() + 10s);
    auto token = std::make_shared<CommandRecipient>(execution, "main");
    REQUIRE(fixture.host->ReceiveCommand({.name = "echo", .text = "only this command"}, token));
    execution->dispatched = true;
    CHECK_FALSE(execution->IsComplete());
    CHECK(execution->capture.output.empty());
    fixture.Step();
    CHECK(execution->IsComplete());
    CHECK(execution->recipients[0].outcome == "completed");
    CHECK(execution->capture.output.find("only this command") != std::string::npos);

    auto failure = std::make_shared<CommandExecution>(4096, std::chrono::steady_clock::now() + 10s);
    REQUIRE(fixture.host->ReceiveCommand({.name = "boom"}, std::make_shared<CommandRecipient>(failure, "main")));
    fixture.Step();
    CHECK(failure->recipients[0].outcome == "failed");
    CHECK(failure->capture.output.find("before error") != std::string::npos);
    CHECK(failure->capture.output.find("only this command") == std::string::npos);
}

TEST_CASE("Tracked script cancellation prevents invocation on expiry and host destruction", "[Http][ScriptHost]")
{
    auto fixture = HostFixture{"console.command('echo', lambda command: log('must not run'))\ndef loop():\n    return 1000\n"};
    auto execution = std::make_shared<CommandExecution>(1024, std::chrono::steady_clock::now() - 1ms);
    REQUIRE(fixture.host->ReceiveCommand({.name = "echo"}, std::make_shared<CommandRecipient>(execution, "main")));
    fixture.Step();
    CHECK(execution->recipients[0].outcome == "cancelled");
    CHECK_FALSE(execution->started);

    auto pending = std::make_shared<CommandExecution>(1024, std::chrono::steady_clock::now() + 10s);
    REQUIRE(fixture.host->ReceiveCommand({.name = "echo"}, std::make_shared<CommandRecipient>(pending, "main")));
    fixture.host.reset();
    CHECK(pending->recipients[0].outcome == "cancelled");
}

TEST_CASE("Tracked broadcasts wait for every recipient and preserve partial outcomes", "[Http][RequestProcessor]")
{
    auto first = HostFixture{"console.command('echo', lambda command: print('first'))\ndef loop():\n    return 1000\n"};
    auto second = HostFixture{"console.command('echo', lambda command: print('second'))\ndef loop():\n    return 1000\n"};
    first.capture.GetLogger()->SetSink(LogSinks::Make({}, {}, true));
    second.capture.GetLogger()->SetSink(LogSinks::Make({}, {}, true));

    auto execution = std::make_shared<CommandExecution>(4096, std::chrono::steady_clock::now() + 10s);
    REQUIRE(first.host->ReceiveCommand({.name = "echo"}, std::make_shared<CommandRecipient>(execution, "first")));
    REQUIRE(second.host->ReceiveCommand({.name = "echo"}, std::make_shared<CommandRecipient>(execution, "second")));
    execution->dispatched = true;
    first.Step();
    CHECK_FALSE(execution->IsComplete());
    CHECK(execution->capture.output.find("first") != std::string::npos);
    CHECK(execution->capture.output.find("second") == std::string::npos);
    second.Step();
    CHECK(execution->IsComplete());
    CHECK(execution->capture.output.find("second") != std::string::npos);
}

TEST_CASE("Removed commands and full script queues give terminal recipient outcomes", "[Http][ScriptHost]")
{
    auto fixture = HostFixture{R"python(
console.command('echo', lambda command: print('must not run'))
console.command('remove', lambda command: console.remove('echo'))
def loop():
    return 1000
)python"};

    auto execution = std::make_shared<CommandExecution>(4096, std::chrono::steady_clock::now() + 10s);
    REQUIRE(fixture.host->ReceiveCommand({.name = "remove"}));
    REQUIRE(fixture.host->ReceiveCommand({.name = "echo"}, std::make_shared<CommandRecipient>(execution, "main")));
    fixture.Step();
    CHECK(execution->recipients[0].outcome == "rejected");
    CHECK(execution->recipients[0].errorCode == "command_removed");

    for (std::size_t i = 0; i < ScriptHost::MAX_COMMANDS; ++i)
    {
        REQUIRE(fixture.host->ReceiveCommand({.name = "remove"}));
    }

    CHECK(fixture.host->QueueCommand({.name = "remove"}) == CommandQueueResult_e::QueueFull);
}

TEST_CASE("Reload cancels tracked invocations while local commands retain their behavior", "[Http][ScriptHost]")
{
    const auto script = "console.command('echo', lambda command: print('replacement'))\ndef loop():\n    return 1000\n";
    auto fixture = HostFixture{script, ScriptHostOptions_s{.watchFiles = true}};
    auto execution = std::make_shared<CommandExecution>(4096, std::chrono::steady_clock::now() + 10s);
    const auto now = std::chrono::steady_clock::now();
    fixture.host->Step(now);
    fixture.folder.RewriteFile("main.py", std::string{script} + "# changed\n");
    fixture.host->Step(now + ScriptHost::WATCH_INTERVAL);
    REQUIRE(fixture.host->ReceiveCommand({.name = "echo"}, std::make_shared<CommandRecipient>(execution, "main")));
    fixture.host->Step(now + 2 * ScriptHost::WATCH_INTERVAL);
    CHECK(execution->recipients[0].outcome == "cancelled");
    CHECK(execution->recipients[0].errorCode == "vm_reloaded");
    CHECK_FALSE(execution->started);
}

TEST_CASE("Nested real network callback dispatch pauses command attribution", "[Http][ConsoleCapture]")
{
    auto game = FakeGameServer{};
    const auto settings = game.MakeServerSettings();
    auto loop = NetLoop::Create();
    auto logger = std::make_shared<Logger>();
    logger->SetSink(LogSinks::Make({}, {}, true));

    auto link = loop->Open({.host = settings.host, .port = static_cast<u16>(settings.port)}, logger);
    auto capture = ConsoleCapture{4096};
    {
        const auto scope = ConsoleCaptureScope{&capture};
        ConsoleCaptureScope::Write("before\n");

        const auto deadline = std::chrono::steady_clock::now() + 2s;
        while (link->GetStatus().state == ConnectionState_e::Connecting && std::chrono::steady_clock::now() < deadline)
        {
            loop->Wait(std::chrono::steady_clock::now() + 1ms);
        }

        REQUIRE(link->GetStatus().state == ConnectionState_e::Open);
        ConsoleCaptureScope::Write("after\n");
    }

    CHECK(capture.output == "before\nafter\n");
    link->Close();
    loop->Settle(std::chrono::steady_clock::now() + 2s);
}

TEST_CASE("Request batches leave work queued between account scheduling passes", "[Http][RequestProcessor]")
{
    auto runner = AccountRunner{std::make_shared<const Config_s>(), FakeGameServer::MakeCache(), {}, ScriptTestRuntime::Get()};
    auto bridge = std::make_shared<ApplicationRequestBridge>(HttpSettings_s{});
    auto processor = ApplicationRequestProcessor{runner, bridge, std::chrono::steady_clock::now()};
    for (auto i = 0; i < 20; ++i)
    {
        bridge->Commit({bridge->Reserve(), GetApplicationStatus_s{}});
    }

    processor.Dispatch();

    const auto firstBatch = bridge->TakeCompleted();
    CHECK(firstBatch.size() <= 8);
    CHECK(bridge->HasIncoming());
    processor.Stop();
    CHECK_FALSE(bridge->HasIncoming());
}

TEST_CASE("Recipient aggregation distinguishes partial rejection failure and cancellation", "[Http][RequestProcessor]")
{
    auto runner = AccountRunner{std::make_shared<const Config_s>(), FakeGameServer::MakeCache(), {}, ScriptTestRuntime::Get()};
    for (const auto& outcomes : std::vector<std::array<std::string, 3>>{
             {"completed", "failed", "partial"}, {"failed", "failed", "failed"}, {"rejected", "rejected", "rejected"}, {"cancelled", "cancelled", "cancelled"}, {"completed", "completed", "completed"}})
    {
        INFO(outcomes[0] << ", " << outcomes[1]);

        auto bridge = std::make_shared<ApplicationRequestBridge>(HttpSettings_s{});
        auto processor = ApplicationRequestProcessor{runner, bridge, std::chrono::steady_clock::now()};
        auto control = bridge->Reserve();
        bridge->Commit({control, ExecuteConsoleCommand_s{"status"}});
        while (bridge->HasIncoming())
        {
            processor.Dispatch();
        }

        REQUIRE(control->execution);

        auto first = std::make_shared<CommandRecipient>(control->execution, "first");
        auto second = std::make_shared<CommandRecipient>(control->execution, "second");
        first->Finish(outcomes[0]);
        processor.Finalize();
        CHECK(bridge->TakeCompleted().empty());
        second->Finish(outcomes[1]);
        second->Finish("completed");
        processor.Finalize();

        const auto results = bridge->TakeCompleted();
        REQUIRE(results.size() == 1);
        CHECK(results[0].outcome == outcomes[2]);

        if (outcomes[2] == "failed" || outcomes[2] == "rejected" || outcomes[2] == "cancelled")
        {
            CHECK_FALSE(results[0].errorCode.empty());
        }

        processor.Finalize();
        CHECK(bridge->TakeCompleted().empty());
    }
}

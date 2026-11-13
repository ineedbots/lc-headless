#include "pch.hpp"
#include "Application/ApplicationRequestProcessor.hpp"
#include "Console/LogSinks.hpp"
#include "Io/NetLoop.hpp"
#include "Http/AsioHttpServer.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/TempFolder.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/use_future.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/write.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    namespace asio = boost::asio;
    namespace beast = boost::beast;
    namespace http = beast::http;
    using Json = nlohmann::json;
    using Response = http::response<http::string_body>;
    using Responses = std::vector<Response>;

    asio::awaitable<Responses> Client(u16 port, std::string wire, std::size_t count, std::chrono::seconds timeout, std::string host)
    {
        auto stream = beast::tcp_stream{co_await asio::this_coro::executor};
        stream.expires_after(timeout);
        co_await stream.async_connect({asio::ip::make_address(host), port}, asio::use_awaitable);
        co_await asio::async_write(stream, asio::buffer(wire), asio::use_awaitable);

        auto buffer = beast::flat_buffer{};
        auto results = Responses{};
        for (std::size_t i = 0; i < count; ++i)
        {
            auto response = Response{};
            co_await http::async_read(stream, buffer, response, asio::use_awaitable);
            results.push_back(std::move(response));
        }

        co_return results;
    }

    std::future<Responses> StartClient(u16 port, std::string wire, std::size_t count = 1, std::chrono::seconds timeout = 5s, std::string host = "127.0.0.1")
    {
        return std::async(std::launch::async, [port, wire = std::move(wire), count, timeout, host = std::move(host)]() mutable
        {
            auto io = asio::io_context{};
            auto result = asio::co_spawn(io, Client(port, std::move(wire), count, timeout, std::move(host)), asio::use_future);
            io.run();
            return result.get();
        });
    }

    std::string Request(std::string method, std::string path, std::string body = {}, std::string headers = {})
    {
        return method + " " + path + " HTTP/1.1\r\nHost: localhost\r\n" + headers +
            "Content-Length: " + std::to_string(body.size()) + "\r\n\r\n" + body;
    }

    std::string Command(std::string command)
    {
        return Request("POST", "/api/v1/console/commands", Json{{"command", command}}.dump(), "Content-Type: application/json\r\n");
    }

    class HttpFixture
    {
    public:
        explicit HttpFixture(HttpSettings_s options = {})
            : settings{std::move(options)}
            , net{NetLoop::Create()}
            , bridge{std::make_shared<ApplicationRequestBridge>(settings)}
            , logger{std::make_shared<Logger>()}
            , runner{std::make_shared<const Config_s>(), FakeGameServer::MakeCache(), {}, ScriptTestRuntime::Get(), logger, {}, net}
            , processor{runner, bridge, std::chrono::steady_clock::now()}
        {
            if (settings.host.empty())
            {
                settings.host = "127.0.0.1";
            }

            settings.port = 0; // Only the test seam uses an ephemeral port; production configuration rejects zero.
            server = net->ListenHttp(settings, bridge);
            logger->SetSink(LogSinks::Make({}, {}, true));
        }

        ~HttpFixture()
        {
            processor.Stop();
            server->Close();

            const auto deadline = std::chrono::steady_clock::now() + 1s;
            while (!server->IsDrained() && std::chrono::steady_clock::now() < deadline)
            {
                net->Poll();
            }
        }

        Responses Finish(std::future<Responses>& future, bool dispatch = true, std::chrono::seconds timeout = 6s)
        {
            const auto deadline = std::chrono::steady_clock::now() + timeout;
            while (future.wait_for(0ms) != std::future_status::ready && std::chrono::steady_clock::now() < deadline)
            {
                net->Wait(std::chrono::steady_clock::now() + 1ms);

                if (dispatch)
                {
                    processor.Dispatch();
                    processor.Finalize();
                }

                server->Deliver(bridge->TakeCompleted());
                server->Service();
            }

            REQUIRE(future.wait_for(0ms) == std::future_status::ready);
            return future.get();
        }

        void AwaitIncoming()
        {
            const auto deadline = std::chrono::steady_clock::now() + 2s;
            while (!bridge->HasIncoming() && std::chrono::steady_clock::now() < deadline)
            {
                net->Wait(std::chrono::steady_clock::now() + 1ms);
            }

            REQUIRE(bridge->HasIncoming());
        }

        HttpSettings_s settings;
        std::shared_ptr<NetLoop> net;
        std::shared_ptr<ApplicationRequestBridge> bridge;
        std::shared_ptr<Logger> logger;
        AccountRunner runner;
        ApplicationRequestProcessor processor;
        std::unique_ptr<HttpServer> server;
    };
}

TEST_CASE("Beast loopback commands use the safe point and return captured output", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto client = StartClient(fixture.server->GetPort(), Command("help"));
    fixture.AwaitIncoming();
    CHECK(client.wait_for(0ms) == std::future_status::timeout);
    CHECK(fixture.bridge->TakeCompleted().empty());

    auto responses = fixture.Finish(client);
    REQUIRE(responses.size() == 1);
    CHECK(responses[0].result_int() == 200);
    CHECK(responses[0][http::field::cache_control] == "no-store");

    const auto body = Json::parse(responses[0].body());
    CHECK(body["requestId"].is_string());
    CHECK(body["outcome"] == "completed");
    CHECK(body["output"].get<std::string>().find("Console commands") != std::string::npos);
    CHECK(body["outputTruncated"] == false);
}

TEST_CASE("Beast routes validate envelopes methods paths and content types", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    const auto cases = std::vector<std::pair<std::string, unsigned>>{
        {Request("GET", "/missing"), 404}, {Request("POST", "/api/v1/status"), 405}, {Request("GET", "/api/v1/status?x=1"), 200}, {Request("POST", "/api/v1/console/commands", "{}"), 415}, {Request("POST", "/api/v1/console/commands", "broken", "Content-Type: application/json\r\n"), 400}, {Request("POST", "/api/v1/console/commands", R"({"command":" "})", "Content-Type: application/json\r\n"), 400}, {Request("POST", "/api/v1/console/commands", R"({"command":"help\nquit"})", "Content-Type: application/json\r\n"), 400}, {Request("POST", "/api/v1/console/commands", R"({"command":"help","extra":1})", "Content-Type: application/json\r\n"), 400}, {Request("GET", "/api/v1/status", {}, "Expect: nope\r\n"), 417}, {Command("unknown_command"), 422}, {Command("@missing status"), 422}, {Command("loglevel invalid"), 422}, {"garbage\r\n\r\n", 400}};
    for (const auto& [wire, code] : cases)
    {
        INFO(wire);

        auto client = StartClient(fixture.server->GetPort(), wire);
        const auto responses = fixture.Finish(client);
        REQUIRE(responses.size() == 1);
        CHECK(responses[0].result_int() == code);

        if (code == 405)
        {
            CHECK(responses[0][http::field::allow] == "GET");
        }
    }
}

TEST_CASE("Beast keepalive preserves pipelined bytes and unique request IDs", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto client = StartClient(fixture.server->GetPort(), Command("help") + Command("loglevel") + Request("GET", "/api/v1/status", {}, "Connection: close\r\n"), 3);
    const auto responses = fixture.Finish(client);
    REQUIRE(responses.size() == 3);

    auto ids = std::unordered_set<std::string>{};
    for (const auto& response : responses)
    {
        CHECK(response.result_int() == 200);
        ids.insert(Json::parse(response.body())["requestId"].get<std::string>());
    }

    CHECK(ids.size() == 3);
    CHECK(Json::parse(responses[1].body())["output"].get<std::string>().find("Console commands") == std::string::npos);

    const auto status = Json::parse(responses[2].body());
    CHECK(status["application"]["state"] == "running");
    CHECK(status["accounts"].empty());
    CHECK_FALSE(responses[2].keep_alive());
}

TEST_CASE("Beast enforces fixed chunked and header limits before application admission", "[Http][Integration]")
{
    auto settings = HttpSettings_s{};
    settings.maxRequestBodyBytes = 16;

    auto fixture = HttpFixture{settings};
    for (const auto& wire : std::vector<std::string>{Command(std::string(50, 'a')),
                                                     "POST /api/v1/console/commands HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n20\r\n" + std::string(32, 'a') + "\r\n0\r\n\r\n"})
    {
        auto client = StartClient(fixture.server->GetPort(), wire);
        const auto responses = fixture.Finish(client);
        CHECK(responses[0].result_int() == 413);
        CHECK(fixture.bridge->Outstanding() == 0);
    }

    auto client = StartClient(fixture.server->GetPort(), Request("GET", "/api/v1/status", {}, "X-Large: " + std::string(20000, 'a') + "\r\n"));
    const auto responses = fixture.Finish(client);
    CHECK(responses[0].result_int() == 431);
}

TEST_CASE("Beast sends 100 continue before the terminal command response", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto client = StartClient(fixture.server->GetPort(), Request("POST", "/api/v1/console/commands", R"({"command":"help"})", "Content-Type: application/json\r\nExpect: 100-continue\r\n"), 2);
    const auto responses = fixture.Finish(client);
    REQUIRE(responses.size() == 2);
    CHECK(responses[0].result_int() == 100);
    CHECK(responses[1].result_int() == 200);
}

TEST_CASE("Beast deadline checks reject expired work even before timer callbacks dispatch", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto client = StartClient(fixture.server->GetPort(), Command("loglevel error"));
    fixture.AwaitIncoming();

    auto request = fixture.bridge->Take();
    REQUIRE(request);
    request->control->deadline = std::chrono::steady_clock::now() - 1ms;
    fixture.bridge->Commit(std::move(*request));
    fixture.processor.Dispatch();
    fixture.processor.Finalize();
    fixture.server->Deliver(fixture.bridge->TakeCompleted());

    const auto responses = fixture.Finish(client);
    CHECK(responses[0].result_int() == 504);
    CHECK(fixture.logger->GetLevel() == LogLevel_e::Info);
    CHECK(Json::parse(responses[0].body())["executionStarted"] == false);
}

TEST_CASE("Beast overload and shutdown retire reservations and operations", "[Http][Integration]")
{
    auto settings = HttpSettings_s{};
    settings.maxPendingRequests = 1;

    auto fixture = HttpFixture{settings};
    auto first = StartClient(fixture.server->GetPort(), Command("help"));
    fixture.AwaitIncoming();

    auto excess = StartClient(fixture.server->GetPort(), Command("help"));
    auto rejected = fixture.Finish(excess, false);
    CHECK(rejected[0].result_int() == 503);
    fixture.processor.Stop();
    fixture.server->Stop();
    fixture.server->Stop();
    fixture.server->Deliver(fixture.bridge->TakeCompleted());

    const auto responses = fixture.Finish(first, false);
    CHECK(responses[0].result_int() == 503);
    fixture.server->Close();

    const auto deadline = std::chrono::steady_clock::now() + 1s;
    while (!fixture.server->IsDrained() && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Poll();
    }

    CHECK(fixture.server->IsDrained());
    CHECK(fixture.bridge->Outstanding() == 0);
    fixture.net->Wake();
    CHECK_NOTHROW(fixture.net->Poll());
}

TEST_CASE("Disabled HTTP creates no listener and bind failure propagates synchronously", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    CHECK_FALSE(fixture.net->ListenHttp(HttpSettings_s{}, fixture.bridge));

    auto settings = fixture.settings;
    settings.port = fixture.server->GetPort();
    CHECK_THROWS(fixture.net->ListenHttp(settings, fixture.bridge));
}

TEST_CASE("Real runner HTTP broadcasts await script return and quit acknowledges before drain", "[Http][Integration][AccountRunner]")
{
    auto game = FakeGameServer{TestWorld::Send};
    auto otherGame = FakeGameServer{TestWorld::Send};
    auto folder = TempFolder{"http-runner"};
    folder.WriteFile("main.py", "console.command('echo', lambda command: print(command.text, end=''))\ndef loop():\n    return 1000\n");

    auto config = game.MakeConfig();
    config.scripting.scriptsDirectory = folder.GetPath().string();
    config.scripting.loginIntervalSeconds = 0s;

    auto net = NetLoop::Create();
    auto settings = HttpSettings_s{.host = "127.0.0.1", .port = 0};
    auto bridge = std::make_shared<ApplicationRequestBridge>(settings);
    auto logger = std::make_shared<Logger>();
    const auto mainThread = std::this_thread::get_id();
    auto wrongThread = false;
    const auto sink = LogSinks::Make({}, {}, true);
    logger->SetSink([&](const LogEntry_s& entry)
    {
        if (std::this_thread::get_id() != mainThread)
        {
            wrongThread = true;
        }

        sink(entry);
    });

    auto accounts = std::vector<AccountConfig_s>{};
    for (const auto name : {"first", "second"})
    {
        accounts.push_back({.name = name, .credentials = {.username = name, .password = "secret"}, .script = ScriptConfig_s{.file = "main.py"}});
    }

    accounts[1].server = otherGame.MakeServerSettings();

    auto runner = AccountRunner{std::make_shared<const Config_s>(config), FakeGameServer::MakeCache(), std::move(accounts), ScriptTestRuntime::Get(), logger, {}, net};
    auto processor = ApplicationRequestProcessor{runner, bridge, std::chrono::steady_clock::now()};
    auto server = net->ListenHttp(settings, bridge);
    auto client = StartClient(server->GetPort(), Command("echo broadcast output") + Command("@first echo targeted output") + Command("quit"), 3);
    const auto deadline = std::chrono::steady_clock::now() + 10s;
    auto passes = 0;
    const auto succeeded = runner.Run([&]
    {
        return std::chrono::steady_clock::now() >= deadline ? 2u : 0u;
    }, nullptr, [&](bool dispatch)
    {
        REQUIRE(std::this_thread::get_id() == mainThread);

        if (dispatch)
        {
            ++passes;
            processor.Dispatch();
        }
        else
        {
            processor.Finalize();
            server->Deliver(bridge->TakeCompleted());
            server->Service();
        }
    }, [&]
    {
        return bridge->HasIncoming();
    }, [&]
    {
        processor.Stop();
        server->Stop();
        server->Deliver(bridge->TakeCompleted());
    });
    CHECK(succeeded);
    CHECK(std::chrono::steady_clock::now() < deadline);

    const auto drainDeadline = std::chrono::steady_clock::now() + 2s;
    while ((!server->IsDrained() || !net->IsSettled()) && std::chrono::steady_clock::now() < drainDeadline)
    {
        net->Wait(std::chrono::steady_clock::now() + 1ms);
    }

    REQUIRE(client.wait_for(1s) == std::future_status::ready);

    const auto responses = client.get();
    REQUIRE(responses.size() == 3);

    const auto broadcast = Json::parse(responses[0].body());
    CHECK(responses[0].result_int() == 200);
    REQUIRE(broadcast["recipients"].size() == 2);
    CHECK(broadcast["recipients"][0]["outcome"] == "completed");
    CHECK(broadcast["recipients"][1]["outcome"] == "completed");
    CHECK(broadcast["output"].get<std::string>().find("broadcast output") != std::string::npos);

    const auto targeted = Json::parse(responses[1].body());
    REQUIRE(targeted["recipients"].size() == 1);
    CHECK(targeted["recipients"][0]["account"] == "first");
    CHECK(targeted["output"].get<std::string>().find("broadcast output") == std::string::npos);
    CHECK(responses[2].result_int() == 200);
    CHECK(server->IsDrained());
    CHECK(bridge->Outstanding() == 0);
    CHECK_FALSE(wrongThread);
    CHECK(passes > 1);
}

TEST_CASE("Beast disconnect before dispatch abandons queued work", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto io = asio::io_context{};
    auto socket = asio::ip::tcp::socket{io};
    socket.connect({asio::ip::make_address("127.0.0.1"), fixture.server->GetPort()});

    const auto wire = Command("loglevel error");
    asio::write(socket, asio::buffer(wire));
    fixture.AwaitIncoming();
    socket.close();

    const auto deadline = std::chrono::steady_clock::now() + 2s;
    while (fixture.bridge->Outstanding() && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Poll();

        auto queued = fixture.bridge->Take();
        REQUIRE(queued);

        if (queued->control->abandoned)
        {
            fixture.bridge->Commit(std::move(*queued));
            break;
        }

        fixture.bridge->Commit(std::move(*queued));
    }

    fixture.processor.Dispatch();
    fixture.processor.Finalize();
    fixture.server->Deliver(fixture.bridge->TakeCompleted());
    CHECK(fixture.logger->GetLevel() == LogLevel_e::Info);
    CHECK(fixture.bridge->Outstanding() == 0);
}

TEST_CASE("Beast caps idle pre-admission connections and retires their cancelled reads", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto io = asio::io_context{};
    auto sockets = std::vector<asio::ip::tcp::socket>{};
    for (auto i = 0; i < 129; ++i)
    {
        auto socket = asio::ip::tcp::socket{io};
        socket.connect({asio::ip::make_address("127.0.0.1"), fixture.server->GetPort()});
        sockets.push_back(std::move(socket));
        fixture.net->Poll();
    }

    auto& excess = sockets.back();
    excess.non_blocking(true);

    auto error = boost::system::error_code{};
    auto probe = char{};
    const auto deadline = std::chrono::steady_clock::now() + 2s;
    do
    {
        fixture.net->Poll();
        static_cast<void>(excess.read_some(asio::buffer(&probe, 1), error));
    } while ((error == asio::error::would_block || error == asio::error::try_again) && std::chrono::steady_clock::now() < deadline);
    CHECK((error == asio::error::eof || error == asio::error::connection_reset));
    CHECK(fixture.bridge->Outstanding() == 0);
    fixture.server->Close();

    while (!fixture.server->IsDrained() && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Poll();
    }

    CHECK(fixture.server->IsDrained());
}

TEST_CASE("Main thread stalls delay HTTP timers but an expired handler result cannot become success", "[Http][Integration]")
{
    auto settings = HttpSettings_s{};
    settings.requestTimeoutMs = 100ms;

    auto fixture = HttpFixture{settings};
    auto stalled = false;
    const auto sink = LogSinks::Make({}, {}, true);
    fixture.logger->SetSink([&](const LogEntry_s& entry)
    {
        if (!stalled && entry.message.starts_with("Console commands"))
        {
            stalled = true;
            // Deliberately stall the runner, without pumping I/O, past the request's real deadline.
            std::this_thread::sleep_for(120ms);
        }

        sink(entry);
    });

    auto client = StartClient(fixture.server->GetPort(), Command("help"));
    fixture.AwaitIncoming();
    fixture.processor.Dispatch();
    fixture.processor.Finalize();
    fixture.server->Deliver(fixture.bridge->TakeCompleted());

    const auto responses = fixture.Finish(client);
    CHECK(stalled);
    CHECK(responses[0].result_int() == 504);

    const auto body = Json::parse(responses[0].body());
    CHECK(body["executionStarted"] == true);
    CHECK(body["output"].get<std::string>().find("Console commands") != std::string::npos);

    // The client can finish reading before the server's write completion retires admission.
    const auto deadline = std::chrono::steady_clock::now() + 2s;
    while (fixture.bridge->Outstanding() != 0 && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Wait(std::chrono::steady_clock::now() + 1ms);
    }

    CHECK(fixture.bridge->Outstanding() == 0);
}

TEST_CASE("HTTP output truncation and filtering preserve quiet successful commands", "[Http][Integration]")
{
    auto settings = HttpSettings_s{};
    settings.maxOutputBytes = 40;

    auto fixture = HttpFixture{settings};
    auto client = StartClient(fixture.server->GetPort(), Command("help"));
    const auto responses = fixture.Finish(client);
    const auto body = Json::parse(responses[0].body());
    CHECK(body["outputTruncated"] == true);
    CHECK(body["output"].get<std::string>().size() <= 40);
    fixture.logger->SetLevel(LogLevel_e::Error);

    auto quiet = StartClient(fixture.server->GetPort(), Command("help"));
    const auto silent = fixture.Finish(quiet);
    CHECK(silent[0].result_int() == 200);
    CHECK(Json::parse(silent[0].body())["output"] == "");
}

TEST_CASE("HTTP response serialization replaces invalid UTF8 without dropping completion", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto client = StartClient(fixture.server->GetPort(), Command("help"));
    fixture.AwaitIncoming();

    auto request = fixture.bridge->Take();
    REQUIRE(request);
    fixture.bridge->Complete({.id = request->control->id,
                              .payload = ConsoleCommandResult_s{.output = std::string{"bad \xff", 5}}});
    fixture.server->Deliver(fixture.bridge->TakeCompleted());

    const auto responses = fixture.Finish(client);
    CHECK(responses[0].result_int() == 200);
    CHECK(Json::parse(responses[0].body())["output"] == "bad \xef\xbf\xbd");
}

TEST_CASE("Beast streams a valid body larger than its receive buffer", "[Http][Integration]")
{
    auto settings = HttpSettings_s{};
    settings.maxRequestBodyBytes = 65536;

    auto fixture = HttpFixture{settings};
    auto client = StartClient(fixture.server->GetPort(), Command("help " + std::string(60000, ' ')));
    const auto responses = fixture.Finish(client);
    CHECK(responses[0].result_int() == 200);
}

TEST_CASE("Beast closes an incomplete upload on its receive deadline without admission", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto client = StartClient(fixture.server->GetPort(), "POST /api/v1/console/commands HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{", 1, 12s);

    try
    {
        static_cast<void>(fixture.Finish(client, false, 13s));
        FAIL("The incomplete upload received a response");
    }
    catch (const boost::system::system_error& error)
    {
        CHECK((error.code() == http::error::end_of_stream || error.code() == asio::error::eof || error.code() == asio::error::connection_reset));
    }

    CHECK(fixture.bridge->Outstanding() == 0);
}

TEST_CASE("Beast accepts IPv6 loopback using the same main thread loop", "[Http][Integration]")
{
    auto fixture = HttpFixture{HttpSettings_s{.host = "::1"}};
    auto client = StartClient(fixture.server->GetPort(), Request("GET", "/api/v1/status"), 1, 5s, "::1");
    const auto responses = fixture.Finish(client);
    CHECK(responses[0].result_int() == 200);
}

TEST_CASE("Stopping during an asynchronous response retires owned storage and callbacks", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto client = StartClient(fixture.server->GetPort(), Command("help"));
    fixture.AwaitIncoming();

    auto request = fixture.bridge->Take();
    REQUIRE(request);
    fixture.bridge->Complete({.id = request->control->id, .payload = ConsoleCommandResult_s{.output = std::string(1048576, 'x')}});
    fixture.server->Deliver(fixture.bridge->TakeCompleted());
    fixture.server->Close();

    const auto deadline = std::chrono::steady_clock::now() + 2s;
    while (!fixture.server->IsDrained() && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Poll();
    }

    CHECK(fixture.server->IsDrained());
    CHECK(fixture.bridge->Outstanding() == 0);
    REQUIRE(client.wait_for(6s) == std::future_status::ready);

    try
    {
        static_cast<void>(client.get());
    }
    catch (const boost::system::system_error&)
    {
    }
}

TEST_CASE("Disconnect during a command holds admission until its handler returns", "[Http][Integration]")
{
    auto fixture = HttpFixture{HttpSettings_s{.maxPendingRequests = 1}};
    auto io = asio::io_context{};
    auto socket = asio::ip::tcp::socket{io};
    socket.connect({asio::ip::make_address("127.0.0.1"), fixture.server->GetPort()});

    const auto wire = Command("help");
    asio::write(socket, asio::buffer(wire));
    fixture.AwaitIncoming();

    auto request = fixture.bridge->Take();
    REQUIRE(request);

    const auto control = request->control;
    fixture.bridge->Commit(std::move(*request));

    auto heldWhileRunning = false;
    const auto sink = LogSinks::Make({}, {}, true);
    fixture.logger->SetSink([&](const LogEntry_s& entry)
    {
        if (socket.is_open())
        {
            socket.close();

            const auto deadline = std::chrono::steady_clock::now() + 1s;
            while (!control->abandoned && std::chrono::steady_clock::now() < deadline)
            {
                fixture.net->Wait(std::chrono::steady_clock::now() + 1ms);
            }

            heldWhileRunning = fixture.bridge->Outstanding() == 1 && !fixture.bridge->Reserve();
        }

        sink(entry);
    });
    fixture.processor.Dispatch();
    CHECK(heldWhileRunning);
    CHECK(control->abandoned);
    CHECK_FALSE(control->engineDone);
    fixture.processor.Finalize();
    fixture.server->Deliver(fixture.bridge->TakeCompleted());
    CHECK(fixture.bridge->Outstanding() == 0);
    CHECK(control->execution->started);
}

TEST_CASE("Concurrent HTTP commands isolate output from each other and a local command", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto first = StartClient(fixture.server->GetPort(), Command("help"));
    auto second = StartClient(fixture.server->GetPort(), Command("loglevel"));
    const auto deadline = std::chrono::steady_clock::now() + 2s;
    while (fixture.bridge->Outstanding() < 2 && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Wait(std::chrono::steady_clock::now() + 1ms);
    }

    REQUIRE(fixture.bridge->Outstanding() == 2);
    fixture.runner.HandleCommand("unknown_local_command");

    const auto responses = fixture.Finish(first);
    const auto others = fixture.Finish(second);
    const auto a = Json::parse(responses[0].body())["output"].get<std::string>();
    const auto b = Json::parse(others[0].body())["output"].get<std::string>();
    CHECK(a.find("Console commands") != std::string::npos);
    CHECK(a.find("log level is") == std::string::npos);
    CHECK(b.find("log level is") != std::string::npos);
    CHECK(b.find("Console commands") == std::string::npos);
    CHECK(a.find("unknown_local_command") == std::string::npos);
    CHECK(b.find("unknown_local_command") == std::string::npos);
}

TEST_CASE("Shutdown returns unavailable to a validated upload before admission", "[Http][Integration]")
{
    auto fixture = HttpFixture{};
    auto io = asio::io_context{};
    auto socket = asio::ip::tcp::socket{io};
    socket.connect({asio::ip::make_address("127.0.0.1"), fixture.server->GetPort()});

    const auto headers = std::string{"POST /api/v1/console/commands HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 100\r\nExpect: 100-continue\r\n\r\n"};
    asio::write(socket, asio::buffer(headers));
    socket.non_blocking(true);

    auto interim = std::string{};
    const auto deadline = std::chrono::steady_clock::now() + 2s;
    while (interim.find("\r\n\r\n") == std::string::npos && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Wait(std::chrono::steady_clock::now() + 1ms);

        auto bytes = std::array<char, 1024>{};
        auto error = boost::system::error_code{};
        const auto count = socket.read_some(asio::buffer(bytes), error);
        interim.append(bytes.data(), count);
    }

    REQUIRE(interim.starts_with("HTTP/1.1 100"));
    CHECK(fixture.bridge->Outstanding() == 0);
    socket.non_blocking(false);

    auto client = std::async(std::launch::async, [connection = std::move(socket)]() mutable
    {
        auto buffer = beast::flat_buffer{};
        auto response = Response{};
        http::read(connection, buffer, response);

        auto results = Responses{};
        results.push_back(std::move(response));
        return results;
    });
    fixture.server->Stop();

    const auto responses = fixture.Finish(client, false);
    CHECK(responses[0].result_int() == 503);
    CHECK_FALSE(responses[0].keep_alive());
}

TEST_CASE("Beast passes decoded template and query values to endpoint decoders over loopback", "[Http][Integration]")
{
    auto io = asio::io_context{};
    auto settings = HttpSettings_s{.host = "127.0.0.1", .port = 0};
    auto bridge = std::make_shared<ApplicationRequestBridge>(settings);
    const auto mainThread = std::this_thread::get_id();
    auto decode = +[](const HttpEndpointRequest_s& request) -> HttpDecodeResult
    {
        return ApplicationRequestPayload{ExecuteConsoleCommand_s{request.pathParameters.at("id") + ":" +
                                                                 request.queryParameters.at("something").at(0) + ":" + request.body}};
    };

    const auto respond = +[](const CompletedApplicationRequest_s& result) -> std::optional<HttpResponse_s>
    {
        return HttpResponse_s{.status = 201, .body = std::get<ConsoleCommandResult_s>(result.payload).output};
    };

    auto server = AsioHttpServer{io, settings, bridge, HttpRouter{{{.method = "POST", .path = "/api/v1/status/{id}", .decode = decode, .respond = respond}}}};
    auto client = StartClient(server.GetPort(), Request("POST", "/api/v1/status/alice%20smith?something=a%2Bb+c", "body bytes"));
    const auto deadline = std::chrono::steady_clock::now() + 3s;
    while (!bridge->HasIncoming() && std::chrono::steady_clock::now() < deadline)
    {
        io.poll();
    }

    REQUIRE(bridge->HasIncoming());
    CHECK(client.wait_for(0ms) == std::future_status::timeout);
    REQUIRE(std::this_thread::get_id() == mainThread);

    auto request = bridge->Take();
    REQUIRE(request);

    const auto command = std::get<ExecuteConsoleCommand_s>(request->payload).command;
    CHECK(command == "alice smith:a+b c:body bytes");
    bridge->Complete({.id = request->control->id, .payload = ConsoleCommandResult_s{.output = command}});
    server.Deliver(bridge->TakeCompleted());

    while (client.wait_for(0ms) != std::future_status::ready && std::chrono::steady_clock::now() < deadline)
    {
        io.poll();
    }

    REQUIRE(client.wait_for(0ms) == std::future_status::ready);

    const auto responses = client.get();
    CHECK(responses[0].result_int() == 201);
    CHECK(responses[0].body() == command);
    server.Close();

    while (!server.IsDrained() && std::chrono::steady_clock::now() < deadline)
    {
        io.poll();
    }

    CHECK(server.IsDrained());
    CHECK(bridge->Outstanding() == 0);
}

#include "pch.hpp"

#include "Application/ApplicationRequestBridge.hpp"
#include "Application/Events/ApplicationEventBridge.hpp"
#include "Accounts/Type/ProgressReport_s.hpp"
#include "Accounts/Type/AccountLogout_s.hpp"
#include "Application/Events/Type/ApplicationEvent_s.hpp"
#include "Console/Logger.hpp"
#include "Accounts/Account.hpp"
#include "Config/Type/AccountConfig_s.hpp"
#include "Config/Type/Config_s.hpp"
#include "Game/GameClient.hpp"
#include "Config/Type/HttpSettings_s.hpp"
#include "Http/HttpServer.hpp"
#include "Io/NetLoop.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"

#include <boost/asio/co_spawn.hpp>
#include <boost/asio/redirect_error.hpp>
#include <boost/asio/read.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/use_future.hpp>
#include <boost/asio/write.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>
#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    namespace asio = boost::asio;
    namespace beast = boost::beast;
    namespace websocket = beast::websocket;
    namespace http = beast::http;
    using Json = nlohmann::json;
    using Stream = websocket::stream<beast::tcp_stream>;

    constexpr auto SUBSCRIBE = R"({"version":1,"type":"subscribe","id":"s","events":["account.progress"]})"sv;

    asio::awaitable<Json> Read(Stream& stream)
    {
        auto buffer = beast::flat_buffer{};
        co_await stream.async_read(buffer, asio::use_awaitable);
        co_return Json::parse(beast::buffers_to_string(buffer.data()));
    }

    asio::awaitable<std::vector<Json>> Exchange(u16 port)
    {
        auto stream = Stream{co_await asio::this_coro::executor};
        beast::get_lowest_layer(stream).expires_after(5s);
        co_await beast::get_lowest_layer(stream).async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
        co_await stream.async_handshake("localhost", "/api/v1/events", asio::use_awaitable);
        stream.text(true);
        // Fragment the subscription across frames.
        co_await stream.async_write_some(false, asio::buffer(SUBSCRIBE.data(), 20), asio::use_awaitable);
        co_await stream.async_write_some(true, asio::buffer(SUBSCRIBE.data() + 20, SUBSCRIBE.size() - 20), asio::use_awaitable);

        auto results = std::vector<Json>{};
        results.push_back(co_await Read(stream));
        results.push_back(co_await Read(stream));
        results.push_back(co_await Read(stream));

        const auto unsubscribe = std::string{R"({"version":1,"type":"unsubscribe","id":"s"})"};
        co_await stream.async_write(asio::buffer(unsubscribe), asio::use_awaitable);
        results.push_back(co_await Read(stream));
        co_await stream.async_close(websocket::close_code::normal, asio::use_awaitable);
        co_return results;
    }

    class WebSocketFixture
    {
    public:
        std::shared_ptr<NetLoop> net = NetLoop::Create();
        std::shared_ptr<ApplicationEventBridge> events = std::make_shared<ApplicationEventBridge>(std::vector<std::string>{"bot1"});
        std::shared_ptr<ApplicationRequestBridge> requests = std::make_shared<ApplicationRequestBridge>(HttpSettings_s{});
        std::unique_ptr<HttpServer> server = net->ListenHttp(HttpSettings_s{.host = "127.0.0.1", .port = 0}, requests, events);

        ~WebSocketFixture()
        {
            server->Close();
            const auto deadline = std::chrono::steady_clock::now() + 1s;
            while (!server->IsDrained() && std::chrono::steady_clock::now() < deadline)
            {
                net->Poll();
            }
        }

        template <class Work>
        std::vector<Json> Run(Work work, const std::function<void()>& safePoint = {})
        {
            auto future = std::async(std::launch::async, [port = server->GetPort(), work = std::move(work)]() mutable
            {
                auto io = asio::io_context{};
                auto result = asio::co_spawn(io, work(port), asio::use_future);
                io.run();
                return result.get();
            });

            const auto deadline = std::chrono::steady_clock::now() + 8s;
            while (future.wait_for(0ms) != std::future_status::ready && std::chrono::steady_clock::now() < deadline)
            {
                net->Wait(std::chrono::steady_clock::now() + 1ms);
                events->Service();

                if (safePoint)
                {
                    safePoint();
                }

                server->Service();
            }

            if (future.wait_for(0ms) != std::future_status::ready)
            {
                server->Close();
                net->Poll();
            }

            REQUIRE(future.wait_for(1s) == std::future_status::ready);
            return future.get();
        }
    };
}

TEST_CASE("WebSocket loopback subscribes snapshots streams unsubscribes and reconnects", "[Events][Http][WebSocket]")
{
    auto fixture = WebSocketFixture{};
    for (int connection = 0; connection < 2; ++connection)
    {
        auto published = false;
        const auto results = fixture.Run(Exchange, [&]
        {
            if (!published && fixture.events->GetDiagnostics().subscriptions == 1)
            {
                published = true;
                REQUIRE(fixture.events->PublishProgress("bot1", {60s, {{"Reports", "1"}}}));
            }
        });
        REQUIRE(results.size() == 4);
        CHECK(results[0]["type"] == "ack");
        CHECK(results[1]["type"] == "snapshot");
        CHECK(results[1]["events"].size() == static_cast<std::size_t>(connection));
        CHECK(results[2]["event"] == "account.progress");
        CHECK(results[2]["account"] == "bot1");
        CHECK(results[2]["payload"]["rows"][0][1] == "1");
        CHECK(results[3]["action"] == "unsubscribe");
        CHECK(fixture.events->GetDiagnostics().subscriptions == 0);
    }

    fixture.server->Stop();
    const auto deadline = std::chrono::steady_clock::now() + 1s;
    while (!fixture.server->IsDrained() && std::chrono::steady_clock::now() < deadline)
    {
        fixture.net->Poll();
    }

    CHECK(fixture.server->IsDrained());
}

TEST_CASE("WebSocket rejects binary and oversized messages with protocol close codes", "[Events][Http][WebSocket]")
{
    for (const auto binary : {true, false})
    {
        auto fixture = WebSocketFixture{};
        const auto results = fixture.Run([binary](u16 port) -> asio::awaitable<std::vector<Json>>
        {
            auto stream = Stream{co_await asio::this_coro::executor};
            beast::get_lowest_layer(stream).expires_after(5s);
            co_await beast::get_lowest_layer(stream).async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
            co_await stream.async_handshake("localhost", "/api/v1/events", asio::use_awaitable);
            stream.binary(binary);
            const auto message = binary ? std::string{"binary"} : std::string(4097, 'a');
            co_await stream.async_write(asio::buffer(message), asio::use_awaitable);

            auto buffer = beast::flat_buffer{};
            auto error = boost::system::error_code{};
            co_await stream.async_read(buffer, asio::redirect_error(asio::use_awaitable, error));
            co_return std::vector<Json>{Json{{"closed", error == websocket::error::closed}, {"code", stream.reason().code}}};
        });
        CHECK(results[0]["closed"] == true);
        CHECK(results[0]["code"] == (binary ? 1003 : 1009));
    }
}

TEST_CASE("WebSocket validates Origin and upgrade policy on the existing HTTP listener", "[Events][Http][WebSocket]")
{
    auto fixture = WebSocketFixture{};
    for (const auto& headers : {std::string{}, std::string{"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\nOrigin: null\r\n"}})
    {
        const auto results = fixture.Run([headers](u16 port) -> asio::awaitable<std::vector<Json>>
        {
            auto stream = beast::tcp_stream{co_await asio::this_coro::executor};
            stream.expires_after(5s);
            co_await stream.async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
            const auto request = "GET /api/v1/events HTTP/1.1\r\nHost: localhost\r\n" + headers + "\r\n";
            co_await asio::async_write(stream, asio::buffer(request), asio::use_awaitable);

            auto buffer = beast::flat_buffer{};
            auto response = http::response<http::string_body>{};
            co_await http::async_read(stream, buffer, response, asio::use_awaitable);
            co_return std::vector<Json>{Json{{"status", response.result_int()}, {"body", Json::parse(response.body())}}};
        });
        CHECK(results[0]["status"] == 400);
        CHECK(fixture.events->GetDiagnostics().connections == 0);
    }
}

TEST_CASE("WebSocket preserves a subscription coalesced with its HTTP upgrade", "[Events][Http][WebSocket]")
{
    for (const auto padding : {std::pair{0, 0}, std::pair{3000, 0}, std::pair{0, 3000}, std::pair{3000, 3000}})
    {
        const auto [headerPadding, messagePadding] = padding;
        auto fixture = WebSocketFixture{};
        const auto results = fixture.Run([headerPadding, messagePadding](u16 port) -> asio::awaitable<std::vector<Json>>
        {
            auto stream = beast::tcp_stream{co_await asio::this_coro::executor};
            stream.expires_after(5s);
            co_await stream.async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);

            auto wire = std::string{"GET /api/v1/events HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\nX-Padding: "};
            wire.append(static_cast<std::size_t>(headerPadding), 'a');
            wire += "\r\n\r\n";

            const auto message = std::string{SUBSCRIBE} + std::string(static_cast<std::size_t>(messagePadding), ' ');
            wire.push_back(static_cast<char>(0x81));
            if (message.size() <= 125)
            {
                wire.push_back(static_cast<char>(0x80 | message.size()));
            }
            else
            {
                wire.push_back(static_cast<char>(0x80 | 126));
                wire.push_back(static_cast<char>(message.size() >> 8));
                wire.push_back(static_cast<char>(message.size() & 0xff));
            }

            wire.append(4, '\0');
            wire += message;
            co_await asio::async_write(stream, asio::buffer(wire), asio::use_awaitable);

            auto buffer = beast::flat_buffer{};
            auto response = http::response<http::string_body>{};
            co_await http::async_read(stream, buffer, response, asio::use_awaitable);
            auto results = std::vector<Json>{Json{{"status", response.result_int()}}};
            for (int frame = 0; frame < 2; ++frame)
            {
                while (buffer.size() < 2)
                {
                    const auto size = co_await stream.async_read_some(buffer.prepare(1024), asio::use_awaitable);
                    buffer.commit(size);
                }

                auto bytes = beast::buffers_to_string(buffer.data());
                auto header = std::size_t{2};
                auto length = static_cast<std::size_t>(static_cast<unsigned char>(bytes[1]) & 0x7f);
                if (length == 126)
                {
                    while (buffer.size() < 4)
                    {
                        const auto size = co_await stream.async_read_some(buffer.prepare(1024), asio::use_awaitable);
                        buffer.commit(size);
                    }

                    bytes = beast::buffers_to_string(buffer.data());
                    length = static_cast<std::size_t>(static_cast<unsigned char>(bytes[2])) * 256 + static_cast<unsigned char>(bytes[3]);
                    header = 4;
                }

                while (buffer.size() < header + length)
                {
                    const auto size = co_await stream.async_read_some(buffer.prepare(1024), asio::use_awaitable);
                    buffer.commit(size);
                }

                bytes = beast::buffers_to_string(buffer.data());
                results.push_back(Json::parse(bytes.substr(header, length)));
                buffer.consume(header + length);
            }

            co_return results;
        });
        CHECK(results[0]["status"] == 101);
        CHECK(results[1]["type"] == "ack");
        CHECK(results[2]["type"] == "snapshot");
    }
}

TEST_CASE("WebSocket fanout keeps REST progressing under a bounded multi-client workload", "[Events][Http][WebSocket][Load]")
{
    auto fixture = WebSocketFixture{};
    auto game = FakeGameServer{TestWorld::Send};
    auto account = Account{std::make_shared<const Config_s>(game.MakeConfig()), FakeGameServer::MakeCache(), AccountConfig_s{.name = "bot1", .credentials = {.username = "bot1", .password = "secret"}}, ScriptTestRuntime::Get(), std::make_shared<Logger>(), {}, nullptr, fixture.net};
    account.Start();
    auto published = false;
    auto passes = 0;
    auto publishedAt = std::atomic<s64>{0};
    const auto started = std::chrono::steady_clock::now();
    const auto results = fixture.Run([&](u16 port) -> asio::awaitable<std::vector<Json>>
    {
        auto streams = std::vector<std::unique_ptr<Stream>>{};
        for (int client = 0; client < 32; ++client)
        {
            auto stream = std::make_unique<Stream>(co_await asio::this_coro::executor);
            beast::get_lowest_layer(*stream).expires_after(5s);
            co_await beast::get_lowest_layer(*stream).async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
            co_await stream->async_handshake("localhost", "/api/v1/events", asio::use_awaitable);
            stream->text(true);
            co_await stream->async_write(asio::buffer(SUBSCRIBE), asio::use_awaitable);
            co_await Read(*stream);
            co_await Read(*stream);
            streams.push_back(std::move(stream));
        }

        auto rest = beast::tcp_stream{co_await asio::this_coro::executor};
        rest.expires_after(5s);
        co_await rest.async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
        const auto request = std::string{"GET /api/v1/status HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"};
        co_await asio::async_write(rest, asio::buffer(request), asio::use_awaitable);

        auto buffer = beast::flat_buffer{};
        auto response = http::response<http::string_body>{};
        co_await http::async_read(rest, buffer, response, asio::use_awaitable);
        auto ordered = true;
        auto count = 0;
        auto maxDeliveryMs = s64{0};
        for (auto& stream : streams)
        {
            for (int sequence = 1; sequence <= 20; ++sequence)
            {
                const auto event = co_await Read(*stream);
                ordered = ordered && event["sequence"] == sequence;
                maxDeliveryMs = std::max(maxDeliveryMs, (std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count() - publishedAt.load()) / 1000000);
                ++count;
            }

            co_await stream->async_close(websocket::close_code::normal, asio::use_awaitable);
        }

        co_return std::vector<Json>{Json{{"restStatus", response.result_int()}, {"ordered", ordered}, {"deliveries", count}, {"maxDeliveryMs", maxDeliveryMs}}};
    }, [&]
    {
        ++passes;
        account.Step(0ms);
        if (!published && fixture.events->GetDiagnostics().subscriptions == 32 && account.GetClient().IsInGame())
        {
            published = true;
            publishedAt = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
            for (int event = 0; event < 20; ++event)
            {
                REQUIRE(fixture.events->PublishProgress("bot1", {60s, {{"Reports", std::to_string(event)}}}));
            }
        }

        if (auto request = fixture.requests->Take())
        {
            fixture.requests->Complete({.id = request->control->id, .payload = ApplicationStatus_s{}});
        }

        fixture.server->Deliver(fixture.requests->TakeCompleted());
    });
    CHECK(results[0]["restStatus"] == 200);
    CHECK(results[0]["ordered"] == true);
    CHECK(results[0]["deliveries"] == 640);
    CHECK(passes > 20);
    CHECK(account.GetClient().IsInGame());
    CHECK(game.GetErrors().empty());

    const auto diagnostics = fixture.events->GetDiagnostics();
    CHECK(diagnostics.publisherResets == 0);
    CHECK(diagnostics.overflowDisconnects == 0);
    CHECK(diagnostics.clientHighWaterItems <= ApplicationEventBridge::MAX_OUTBOX_ITEMS);
    CHECK(diagnostics.clientHighWaterBytes <= ApplicationEventBridge::MAX_OUTBOX_BYTES);
    std::printf("Event load: clients=32 reports=20 deliveries=640 passes=%d elapsedMs=%lld journalHighItems=%zu journalHighBytes=%zu clientHighItems=%zu clientHighBytes=%zu maxQueueLagMs=%lld maxClientDeliveryMs=%lld\n",
                passes, static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count()),
                diagnostics.journalHighWaterItems, diagnostics.journalHighWaterBytes, diagnostics.clientHighWaterItems, diagnostics.clientHighWaterBytes,
                static_cast<long long>(diagnostics.maxDeliveryLagMs), static_cast<long long>(results[0]["maxDeliveryMs"].get<s64>()));
}

TEST_CASE("WebSocket performs close handshakes for shutdown and subscriber overflow", "[Events][Http][WebSocket]")
{
    for (const auto shutdown : {false, true})
    {
        auto fixture = WebSocketFixture{};
        auto ready = std::atomic<bool>{false};
        auto triggered = false;
        const auto results = fixture.Run([&](u16 port) -> asio::awaitable<std::vector<Json>>
        {
            auto stream = Stream{co_await asio::this_coro::executor};
            beast::get_lowest_layer(stream).expires_after(5s);
            co_await beast::get_lowest_layer(stream).async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
            co_await stream.async_handshake("localhost", "/api/v1/events", asio::use_awaitable);
            stream.text(true);
            co_await stream.async_write(asio::buffer(SUBSCRIBE), asio::use_awaitable);
            co_await Read(stream);
            co_await Read(stream);
            ready = true;

            auto buffer = beast::flat_buffer{};
            auto error = boost::system::error_code{};
            co_await stream.async_read(buffer, asio::redirect_error(asio::use_awaitable, error));
            co_return std::vector<Json>{Json{{"closed", error == websocket::error::closed}, {"code", stream.reason().code}}};
        }, [&]
        {
            if (triggered || !ready.load())
            {
                return;
            }

            triggered = true;
            if (shutdown)
            {
                fixture.server->Stop();
                return;
            }

            for (int i = 0; i < 70; ++i)
            {
                REQUIRE(fixture.events->PublishProgress("bot1", {1s, {}}));
            }

            while (fixture.events->HasIncoming())
            {
                fixture.events->Service();
            }
        });
        CHECK(results[0]["closed"] == true);
        CHECK(results[0]["code"] == (shutdown ? 1001 : 1013));
        CHECK(fixture.events->GetDiagnostics().subscriptions == 0);
    }
}

TEST_CASE("WebSocket messages return structured errors without replacing valid subscriptions", "[Events][Http][WebSocket]")
{
    auto fixture = WebSocketFixture{};
    const auto results = fixture.Run([](u16 port) -> asio::awaitable<std::vector<Json>>
    {
        auto stream = Stream{co_await asio::this_coro::executor};
        beast::get_lowest_layer(stream).expires_after(5s);
        co_await beast::get_lowest_layer(stream).async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
        co_await stream.async_handshake("localhost", "/api/v1/events", asio::use_awaitable);
        stream.text(true);
        co_await stream.async_write(asio::buffer(SUBSCRIBE), asio::use_awaitable);
        co_await Read(stream);
        co_await Read(stream);

        auto results = std::vector<Json>{};
        for (const auto& message : {std::string{"{"}, std::string{SUBSCRIBE}, std::string{R"({"version":99,"type":"subscribe","id":"s"})"}})
        {
            co_await stream.async_write(asio::buffer(message), asio::use_awaitable);
            results.push_back(co_await Read(stream));
        }

        const auto unsubscribe = std::string{R"({"version":1,"type":"unsubscribe","id":"s"})"};
        co_await stream.async_write(asio::buffer(unsubscribe), asio::use_awaitable);
        results.push_back(co_await Read(stream));
        co_await stream.async_close(websocket::close_code::normal, asio::use_awaitable);
        co_return results;
    });
    CHECK(results[0]["id"].is_null());
    CHECK(results[0]["code"] == "invalid_message");
    CHECK(results[1]["id"] == "s");
    CHECK(results[1]["code"] == "invalid_subscription");
    CHECK(results[2]["code"] == "unsupported_version");
    CHECK(results[3]["action"] == "unsubscribe");
}

TEST_CASE("HTTP and WebSocket sessions share one connection admission limit", "[Events][Http][WebSocket]")
{
    auto fixture = WebSocketFixture{};
    const auto results = fixture.Run([](u16 port) -> asio::awaitable<std::vector<Json>>
    {
        const auto executor = co_await asio::this_coro::executor;
        const auto endpoint = asio::ip::tcp::endpoint{asio::ip::make_address("127.0.0.1"), port};
        auto upgraded = std::vector<std::unique_ptr<Stream>>{};
        auto ordinary = std::vector<std::unique_ptr<beast::tcp_stream>>{};
        for (int i = 0; i < 64; ++i)
        {
            auto stream = std::make_unique<Stream>(executor);
            beast::get_lowest_layer(*stream).expires_after(5s);
            co_await beast::get_lowest_layer(*stream).async_connect(endpoint, asio::use_awaitable);
            co_await stream->async_handshake("localhost", "/api/v1/events", asio::use_awaitable);
            upgraded.push_back(std::move(stream));
        }

        for (int i = 0; i < 64; ++i)
        {
            auto stream = std::make_unique<beast::tcp_stream>(executor);
            stream->expires_after(5s);
            co_await stream->async_connect(endpoint, asio::use_awaitable);
            ordinary.push_back(std::move(stream));
        }

        auto excess = beast::tcp_stream{executor};
        excess.expires_after(5s);
        co_await excess.async_connect(endpoint, asio::use_awaitable);
        auto byte = std::array<char, 1>{};
        auto error = boost::system::error_code{};
        co_await excess.async_read_some(asio::buffer(byte), asio::redirect_error(asio::use_awaitable, error));
        co_return std::vector<Json>{Json{{"rejected", error == asio::error::eof || error == asio::error::connection_reset}}};
    });
    CHECK(results[0]["rejected"] == true);
}

TEST_CASE("Account logout reaches a WebSocket subscriber and is absent after reconnect", "[Account][Events][Http][WebSocket]")
{
    auto fixture = WebSocketFixture{};
    auto game = FakeGameServer{TestWorld::Send};
    const auto options = AccountOptions_s{.onLogout = [&](std::string_view name, const AccountLogout_s& logout)
    {
        fixture.events->Publish({std::string{name}, logout});
    }};
    auto account = Account{std::make_shared<const Config_s>(game.MakeConfig()), FakeGameServer::MakeCache(),
                           AccountConfig_s{.name = "bot1", .credentials = FakeGameServer::MakeAccount()}, ScriptTestRuntime::Get(), Logger::GetDefault(), options};
    account.Login();
    auto interrupted = false;
    for (const auto reconnect : {false, true})
    {
        const auto results = fixture.Run([reconnect](u16 port) -> asio::awaitable<std::vector<Json>>
        {
            auto stream = Stream{co_await asio::this_coro::executor};
            beast::get_lowest_layer(stream).expires_after(5s);
            co_await beast::get_lowest_layer(stream).async_connect({asio::ip::make_address("127.0.0.1"), port}, asio::use_awaitable);
            co_await stream.async_handshake("localhost", "/api/v1/events", asio::use_awaitable);
            stream.text(true);
            const auto subscribe = std::string{R"({"version":1,"type":"subscribe","id":"logout","events":["account.logout"],"accounts":["bot1"]})"};
            co_await stream.async_write(asio::buffer(subscribe), asio::use_awaitable);
            auto results = std::vector<Json>{};
            results.push_back(co_await Read(stream));
            results.push_back(co_await Read(stream));
            if (!reconnect)
            {
                results.push_back(co_await Read(stream));
            }
            co_await stream.async_close(websocket::close_code::normal, asio::use_awaitable);
            co_return results;
        }, [&]
        {
            if (!interrupted && fixture.events->GetDiagnostics().subscriptions == 1)
            {
                interrupted = true;
                account.Interrupt();
            }
            account.Step(0ms);
        });
        CHECK(results[0]["type"] == "ack");
        CHECK(results[1]["events"].empty());
        if (!reconnect)
        {
            CHECK(results[2]["event"] == "account.logout");
            CHECK(results[2]["account"] == "bot1");
            CHECK(results[2]["payload"] == Json{{"confirmed", true}});
        }
    }
    CHECK(account.Succeeded());
}

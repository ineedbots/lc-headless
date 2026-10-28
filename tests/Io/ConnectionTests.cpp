#include "pch.hpp"
#include "../Support/Io/FakeSocks5Proxy.hpp"
#include "../Support/Io/TestCertificate.hpp"
#include "../Support/Io/TestServer.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"

#include "Config/Transport_e.hpp"
#include "Console/LogLevel_e.hpp"
#include "Console/Logger.hpp"
#include "Io/Connection.hpp"
#include "Io/ConnectionOptions_s.hpp"
#include "Io/Error/ConnectionClosedError.hpp"
#include "Io/Error/ConnectionError.hpp"
#include "Io/Link.hpp"
#include "Io/NetLoop.hpp"
#include "Io/Socks5Handshake.hpp"

#include <boost/asio/awaitable.hpp>
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_tostring.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    using Clock = std::chrono::steady_clock;
    using Awaitable = boost::asio::awaitable<void>;

    constexpr auto LOOPBACK = "127.0.0.1";
    constexpr auto WAIT = 5s;
    constexpr auto AT_ONCE = 50ms;
    constexpr auto SERVER_DELAY = 300ms;
    constexpr auto WOKEN_WITHIN = 1500ms;
    constexpr auto SHORT_CONNECT_TIMEOUT = 300ms;
    constexpr auto DESTROY_ATTEMPTS = 20;
    constexpr auto LARGE_SEND_SIZE = std::size_t{4} * 1024 * 1024;
    constexpr auto CLOSE_CODE_NORMAL = u16{1000};
    constexpr auto CLOSE_CODE_UNSUPPORTED_DATA = u16{1003};

    enum class Outcome_e : u8
    {
        Returned,
        Closed,
        Failed,
    };

    std::shared_ptr<Logger> MakeConsoleLogger()
    {
        return std::make_shared<Logger>(LogLevel_e::Info);
    }

    ConnectionOptions_s MakeOptions(u16 port)
    {
        return {.host = LOOPBACK, .port = port};
    }

    ConnectionOptions_s MakeTcpOptions(u16 port)
    {
        return {.transport = Transport_e::Tcp, .host = LOOPBACK, .port = port};
    }

    template <typename TAction>
    Outcome_e GetOutcome(TAction action)
    {
        try
        {
            action();
            return Outcome_e::Returned;
        }
        catch (const ConnectionClosedError&)
        {
            return Outcome_e::Closed;
        }
        catch (const ConnectionError&)
        {
            return Outcome_e::Failed;
        }
    }

    template <typename TAction>
    std::string GetFailure(TAction action)
    {
        try
        {
            action();
        }
        catch (const ConnectionError& e)
        {
            return e.what();
        }

        return "";
    }

    template <typename TAction>
    Clock::duration Measure(TAction action)
    {
        const auto start = Clock::now();
        action();
        return Clock::now() - start;
    }

    std::vector<u8> ReadAll(Connection& connection)
    {
        auto bytes = std::vector<u8>(connection.Available());
        connection.Read(bytes);
        return bytes;
    }

    // What a TCP server has read, joined: the reads split and combine the sends as they please.
    std::vector<u8> GetStream(const TestServer& server)
    {
        auto stream = std::vector<u8>{};
        for (const auto& read : server.GetRecord().messages)
        {
            stream.insert(stream.end(), read.begin(), read.end());
        }

        return stream;
    }

    bool HasStreamSize(const TestServer& server, std::size_t size)
    {
        return server.WaitFor([size](const ServerRecord_s& record)
        {
            auto total = std::size_t{0};
            for (const auto& read : record.messages)
            {
                total += read.size();
            }

            return total >= size;
        });
    }

    bool HasFin(const TestServer& server)
    {
        return server.WaitFor([](const ServerRecord_s& record)
        {
            return record.fins > 0;
        });
    }

    bool HasCloseCode(const TestServer& server, u16 code)
    {
        return server.WaitFor([code](const ServerRecord_s& record)
        {
            return std::ranges::find(record.closeCodes, code) != record.closeCodes.end();
        });
    }

    Awaitable Echo(ServerSession& session)
    {
        co_await session.Echo();
    }

    Awaitable Silent(ServerSession& session)
    {
        co_await session.Delay(30s);
    }

    boost::asio::awaitable<bool> ReceiveProxyRequest(ServerSession& session, std::size_t expected)
    {
        auto received = std::size_t{0};
        while (received < expected)
        {
            const auto bytes = co_await session.Receive();
            if (!bytes) co_return false;
            received += bytes->size();
        }
        co_return received == expected;
    }

    // Stops at one of the five reads in a password-authenticated domain-name exchange. Returning
    // leaves the proxy session open, so the caller can either sever it or wait for client cancellation.
    Awaitable ReachProxyReply(ServerSession& session, int phase)
    {
        if (!co_await ReceiveProxyRequest(session, 4)) co_return;
        if (phase == 0) co_return;
        auto reply = std::vector<u8>{5, 2};
        co_await session.Send(reply);
        if (!co_await ReceiveProxyRequest(session, 8)) co_return;
        if (phase == 1) co_return;
        reply = {1, 0};
        co_await session.Send(reply);
        // example.invalid is 15 bytes: version, command, reserved, type, length, name, port.
        if (!co_await ReceiveProxyRequest(session, 22)) co_return;
        if (phase == 2) co_return;
        reply = {5, 0, 0, 3};
        co_await session.Send(reply);
        if (phase == 3) co_return;
        reply = {4};
        co_await session.Send(reply);
    }
}

static_assert(std::derived_from<ConnectionClosedError, ConnectionError>);

TEST_CASE("Connection reports proxy EOF and reset at every reply stage", "[Connection][ProxyFailureCoverage]")
{
    const auto phase = GENERATE(0, 1, 2, 3, 4);
    const auto reset = GENERATE(false, true);
    auto proxy = TestServer{[phase, reset](ServerSession& session) -> Awaitable
    {
        co_await ReachProxyReply(session, phase);
        if (reset) session.Reset();
        else session.Drop();
    }, ServerMode_e::Tcp};
    auto capture = LogCapture{};
    const auto loop = NetLoop::Create();
    auto options = MakeTcpOptions(43594);
    options.host = "example.invalid";
    options.proxy = Socks5Proxy_s{.host = LOOPBACK, .port = proxy.GetPort(), .username = "usr", .password = "pw"};
    auto connection = Connection{*loop, options, capture.GetLogger()};
    const auto failure = GetFailure([&] { static_cast<void>(connection.WaitOpen(WAIT)); });
    INFO(failure);
    CHECK_THAT(failure, Catch::Matchers::ContainsSubstring(std::format("SOCKS5 proxy {}:{}:", LOOPBACK, proxy.GetPort())));
    if (!reset) CHECK_THAT(failure, Catch::Matchers::ContainsSubstring("closed the connection during the exchange"));
    CHECK(failure.find("usr") == std::string::npos);
    CHECK(GetOutcome([&] { static_cast<void>(connection.Pump()); }) == Outcome_e::Failed);
}

TEST_CASE("Connection cancels a pending proxy reply at every handshake stage", "[Connection][ProxyFailureCoverage]")
{
    const auto phase = GENERATE(0, 1, 2, 3, 4);
    const auto reached = std::make_shared<std::atomic<bool>>(false);
    auto proxy = TestServer{[phase, reached](ServerSession& session) -> Awaitable
    {
        co_await ReachProxyReply(session, phase);
        reached->store(true);
        co_await session.ReceiveUntilClosed();
    }, ServerMode_e::Tcp};
    const auto loop = NetLoop::Create();
    auto options = MakeTcpOptions(43594);
    options.host = "example.invalid";
    options.proxy = Socks5Proxy_s{.host = LOOPBACK, .port = proxy.GetPort(), .username = "usr", .password = "pw"};
    auto connection = Connection{*loop, options, MakeConsoleLogger()};
    const auto deadline = Clock::now() + WAIT;
    while (!reached->load() && Clock::now() < deadline) static_cast<void>(connection.WaitOpen(10ms));
    REQUIRE(reached->load());
    CHECK_FALSE(connection.WaitOpen(10ms));
    connection.Close();
    CHECK(connection.WaitClosed(WAIT));
    CHECK(connection.Pump() == ConnectionState_e::Closed);
    CHECK(proxy.WaitFor([](const auto& record) { return record.ended == 1; }));
}

TEST_CASE("Connection rejects bad options before connecting", "[Connection]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    auto emptyHost = MakeOptions(80);
    emptyHost.host.clear();
    auto zeroPort = MakeOptions(0);
    auto zeroTimeout = MakeOptions(80);
    zeroTimeout.connectTimeout = 0ms;
    auto noCaFile = MakeOptions(443);
    noCaFile.transport = Transport_e::Wss;
    noCaFile.tlsCaFile.clear();
    auto emptyProxyHost = MakeOptions(80);
    emptyProxyHost.proxy = Socks5Proxy_s{.port = 1080};
    auto zeroProxyPort = MakeOptions(80);
    zeroProxyPort.proxy = Socks5Proxy_s{.host = LOOPBACK};

    for (const auto& options : {emptyHost, zeroPort, zeroTimeout, noCaFile, emptyProxyHost, zeroProxyPort})
    {
        CHECK_THROWS_AS(Connection(*loop, options, logger), std::invalid_argument);
    }
}

TEST_CASE("Connection opens and exchanges data", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    SECTION("opens")
    {
        const auto server = TestServer{};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        CHECK(connection.WaitOpen(WAIT));
        CHECK(connection.Pump() == ConnectionState_e::Open);
    }

    SECTION("sends the origin, the subprotocol and the host with its port")
    {
        const auto server = TestServer{};
        auto options = MakeOptions(server.GetPort());
        options.origin = "http://test";
        auto connection = Connection{*loop, options, logger};
        REQUIRE(connection.WaitOpen(WAIT));

        const auto record = server.GetRecord();
        REQUIRE(record.handshakes.size() == 1);
        CHECK(record.handshakes[0].origin == "http://test");
        CHECK(record.handshakes[0].subprotocol == "binary");
        CHECK(record.handshakes[0].host == std::format("{}:{}", LOOPBACK, server.GetPort()));
    }

    SECTION("sends no Origin header for an empty origin")
    {
        const auto server = TestServer{};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        const auto record = server.GetRecord();
        REQUIRE(record.handshakes.size() == 1);
        CHECK_FALSE(record.handshakes[0].origin.has_value());
    }

    SECTION("echoes")
    {
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3});
    }

    SECTION("echoes a message too long for a 16-bit frame length")
    {
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        auto sent = std::vector<u8>(65'536);
        for (auto i = std::size_t{0}; i < sent.size(); ++i)
        {
            sent[i] = static_cast<u8>(i & 0xFF);
        }

        connection.Send(sent);
        REQUIRE(connection.WaitAvailable(sent.size(), WAIT));
        CHECK(ReadAll(connection) == sent);
    }

    SECTION("each send is one message")
    {
        const auto server = TestServer{};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Send(std::array<u8, 2>{1, 2});
        connection.Send(std::array<u8, 1>{3});
        connection.Pump();

        REQUIRE(server.WaitFor([](const ServerRecord_s& record)
        {
            return record.messages.size() == 2;
        }));
        const auto messages = server.GetRecord().messages;
        CHECK(messages[0] == std::vector<u8>{1, 2});
        CHECK(messages[1] == std::vector<u8>{3});
    }

    SECTION("message boundaries are discarded")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Send({1, 2});
            co_await session.Send({3, 4});
            co_await session.Send({5, 6});
            co_await session.ReceiveUntilClosed();
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

        REQUIRE(connection.WaitAvailable(6, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3, 4, 5, 6});
    }
}

TEST_CASE("Connection reports a failure to connect", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    SECTION("nothing listening is a failure, not a close")
    {
        auto connection = Connection{*loop, MakeOptions(TestServer::FindClosedPort()), logger};
        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        }) == Outcome_e::Failed);
    }

    SECTION("a silent server leaves it connecting")
    {
        const auto server = TestServer{{}, ServerMode_e::Silent};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        CHECK_FALSE(connection.WaitOpen(200ms));
        CHECK(connection.Pump() == ConnectionState_e::Connecting);
    }

    SECTION("connectTimeout ends the attempt and names the stage")
    {
        const auto server = TestServer{{}, ServerMode_e::Silent};
        auto options = MakeOptions(server.GetPort());
        options.connectTimeout = SHORT_CONNECT_TIMEOUT;
        auto connection = Connection{*loop, options, logger};

        auto failure = std::string{};
        const auto elapsed = Measure([&]
        {
            failure = GetFailure([&]
            {
                static_cast<void>(connection.WaitOpen(WAIT));
            });
        });
        CHECK(elapsed < 1s);
        CHECK_THAT(failure, Catch::Matchers::ContainsSubstring("during the WebSocket upgrade"));
    }

    SECTION("a refused upgrade gives the HTTP status")
    {
        const auto server = TestServer{{}, ServerMode_e::Reject};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        const auto failure = GetFailure([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        });
        CHECK_THAT(failure, Catch::Matchers::ContainsSubstring("HTTP 403"));
    }
}

TEST_CASE("Connection waits time out and wake on events", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    SECTION("an idle server times a wait out")
    {
        const auto server = TestServer{};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        auto available = true;
        const auto elapsed = Measure([&]
        {
            available = connection.WaitAvailable(1, 200ms);
        });
        CHECK_FALSE(available);
        CHECK(elapsed >= 200ms);
        CHECK(elapsed < 2s);
        CHECK(connection.Pump() == ConnectionState_e::Open);

        CHECK_FALSE(connection.WaitAvailable(1, 0ms));
        CHECK_FALSE(connection.WaitAvailable(1, -5ms));
        CHECK_FALSE(connection.WaitClosed(200ms));
        CHECK(connection.Pump() == ConnectionState_e::Open);
    }

    const auto server = TestServer{[](ServerSession& session) -> Awaitable
    {
        co_await session.Delay(SERVER_DELAY);
        co_await session.Send({1, 2, 3, 4});
        co_await session.ReceiveUntilClosed();
    }};
    auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

    SECTION("data wakes the wait")
    {
        auto available = false;
        const auto elapsed = Measure([&]
        {
            available = connection.WaitAvailable(4, WAIT);
        });
        CHECK(available);
        CHECK(elapsed < WOKEN_WITHIN);
    }

    SECTION("the largest timeout waits forever instead of overflowing")
    {
        CHECK(connection.WaitAvailable(4, std::chrono::milliseconds::max()));
    }

    SECTION("the wait without a timeout returns")
    {
        connection.WaitAvailable(4);
        CHECK(connection.Available() == 4);
    }
}

TEST_CASE("Connection reports how the server ended it", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    SECTION("a close after data keeps the data readable")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Send({1, 2, 3, 4});
            co_await session.Close(CLOSE_CODE_NORMAL);
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitAvailable(5, WAIT));
        }) == Outcome_e::Closed);
        CHECK(connection.Available() == 4);
        CHECK(connection.WaitAvailable(4, 0ms));
        CHECK(connection.Pump() == ConnectionState_e::Closed);
        CHECK(GetOutcome([&]
        {
            connection.Send(std::array<u8, 1>{1});
        }) == Outcome_e::Closed);
    }

    SECTION("a close wakes WaitClosed")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Delay(SERVER_DELAY);
            co_await session.Close(CLOSE_CODE_NORMAL);
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed < WOKEN_WITHIN);
        CHECK(connection.Pump() == ConnectionState_e::Closed);
    }

    SECTION("a text message fails the connection and keeps the data before it")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Send({1, 2, 3, 4});
            co_await session.SendText("hello");
            co_await session.ReceiveUntilClosed();
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitAvailable(5, WAIT));
        }) == Outcome_e::Failed);
        CHECK(connection.Available() == 4);
        CHECK_THROWS_AS(connection.Pump(), ConnectionError);
        CHECK_THROWS_AS(connection.Pump(), ConnectionError);
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3, 4});
    }

    SECTION("a text message closes with 1003")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.SendText("hello");
            co_await session.ReceiveUntilClosed();
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitClosed(WAIT));
        }) == Outcome_e::Failed);
        CHECK(HasCloseCode(server, CLOSE_CODE_UNSUPPORTED_DATA));
    }

    SECTION("TCP ending without a close frame is a close")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            session.Drop();
            co_return;
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitAvailable(1, WAIT));
        }) == Outcome_e::Closed);
        CHECK(connection.Pump() == ConnectionState_e::Closed);
    }

    SECTION("a reset is a failure")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            session.Reset();
            co_return;
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};

        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitAvailable(1, WAIT));
        }) == Outcome_e::Failed);
    }
}

TEST_CASE("Connection closes without waiting", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    SECTION("Close returns at once and ends sending")
    {
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        CHECK(Measure([&]
        {
            connection.Close();
        }) < AT_ONCE);
        const auto state = connection.Pump();
        CHECK((state == ConnectionState_e::Closing || state == ConnectionState_e::Closed));
        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitOpen(0ms));
        }) == Outcome_e::Closed);
        CHECK(GetOutcome([&]
        {
            connection.Send(std::array<u8, 1>{1});
        }) == Outcome_e::Closed);
    }

    SECTION("the server sees a normal close")
    {
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Close();
        CHECK(connection.WaitClosed(WAIT));
        CHECK(connection.Pump() == ConnectionState_e::Closed);
        CHECK(HasCloseCode(server, CLOSE_CODE_NORMAL));
    }

    SECTION("pumping alone finishes a close")
    {
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Close();
        const auto deadline = Clock::now() + 1s;
        while (connection.Pump() != ConnectionState_e::Closed && Clock::now() < deadline)
        {
            std::this_thread::sleep_for(10ms);
        }

        CHECK(connection.Pump() == ConnectionState_e::Closed);
    }

    SECTION("bytes already received stay readable")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Send({1, 2});
            co_await session.ReceiveUntilClosed();
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitAvailable(2, WAIT));

        connection.Close();
        connection.Close();
        CHECK(connection.Available() == 2);
        CHECK(connection.WaitClosed(WAIT));
    }

    SECTION("a server that never answers the close frame is dropped after the close timeout")
    {
        const auto server = TestServer{Silent};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Close();
        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed > 800ms);
        CHECK(elapsed < 2s);
    }

    SECTION("a close while connecting is immediate")
    {
        const auto server = TestServer{{}, ServerMode_e::Silent};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        connection.Pump();

        CHECK(Measure([&]
        {
            connection.Close();
        }) < AT_ONCE);

        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed < 100ms);
    }

    SECTION("WaitOpen after a close while connecting throws at once")
    {
        const auto server = TestServer{{}, ServerMode_e::Silent};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        connection.Close();

        auto outcome = Outcome_e::Returned;
        const auto elapsed = Measure([&]
        {
            outcome = GetOutcome([&]
            {
                static_cast<void>(connection.WaitOpen(WAIT));
            });
        });
        CHECK(outcome == Outcome_e::Closed);
        CHECK(elapsed < AT_ONCE);
    }

    SECTION("a connection destroyed while connecting goes at once")
    {
        const auto server = TestServer{{}, ServerMode_e::Silent};
        for (auto attempt = 0; attempt < DESTROY_ATTEMPTS; ++attempt)
        {
            CHECK(Measure([&]
            {
                const auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
                loop->Poll();
            }) < AT_ONCE);
        }

        CHECK(Measure([&]
        {
            loop->Settle(Clock::now() + WAIT);
        }) < 100ms);
    }

    SECTION("a connection destroyed while open still closes cleanly")
    {
        const auto server = TestServer{Echo};
        {
            auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
            REQUIRE(connection.WaitOpen(WAIT));
        }

        loop->Settle(Clock::now() + 2s);
        CHECK(HasCloseCode(server, CLOSE_CODE_NORMAL));
    }
}

TEST_CASE("Connections share a loop", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    SECTION("waiting on one runs the other's I/O")
    {
        const auto firstServer = TestServer{Echo};
        const auto secondServer = TestServer{Echo};
        auto first = Connection{*loop, MakeOptions(firstServer.GetPort()), logger};
        auto second = Connection{*loop, MakeOptions(secondServer.GetPort()), logger};
        REQUIRE(first.WaitOpen(WAIT));
        REQUIRE(second.WaitOpen(WAIT));

        second.Send(std::array<u8, 3>{7, 8, 9});
        const auto deadline = Clock::now() + WAIT;
        while (second.Available() < 3 && Clock::now() < deadline)
        {
            static_cast<void>(first.WaitAvailable(1, 50ms));
        }

        CHECK(second.Available() == 3);
    }

    SECTION("Wake ends a Wait from another thread")
    {
        auto waker = std::jthread{[&loop]
        {
            std::this_thread::sleep_for(200ms);
            loop->Wake();
        }};

        CHECK(Measure([&]
        {
            loop->Wait(Clock::now() + WAIT);
        }) < 1s);
    }

    SECTION("Settle with nothing open returns at once")
    {
        CHECK(Measure([&]
        {
            loop->Settle(Clock::now() + WAIT);
        }) < AT_ONCE);
    }
}

TEST_CASE("Connection logs its lifecycle", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    auto capture = LogCapture{};

    const auto messagesAt = [&capture](LogLevel_e level)
    {
        auto messages = std::vector<std::string>{};
        for (const auto& entry : capture.GetEntries())
        {
            if (entry.level == level)
            {
                messages.push_back(entry.message);
            }
        }

        return messages;
    };

    const auto noWarnings = [&capture]
    {
        return std::ranges::none_of(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning || entry.level == LogLevel_e::Error;
        });
    };

    SECTION("an exchange and a local close")
    {
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), capture.GetLogger()};
        REQUIRE(connection.WaitOpen(WAIT));
        connection.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        connection.Close();
        connection.Close();
        REQUIRE(connection.WaitClosed(WAIT));

        const auto info = messagesAt(LogLevel_e::Info);
        REQUIRE(info.size() == 3);
        CHECK(info[0] == std::format("Connecting to ws://{}:{}", LOOPBACK, server.GetPort()));
        CHECK(info[1] == "Connection open");
        CHECK(info[2] == "Connection closing");

        const auto verbose = messagesAt(LogLevel_e::Verbose);
        CHECK(std::ranges::find(verbose, "Sending 3 bytes") != verbose.end());
        CHECK(std::ranges::find(verbose, "Received 3 bytes") != verbose.end());
        CHECK(noWarnings());
    }

    SECTION("a server's close")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Close(CLOSE_CODE_NORMAL);
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), capture.GetLogger()};
        REQUIRE(connection.WaitClosed(WAIT));

        const auto info = messagesAt(LogLevel_e::Info);
        REQUIRE(info.size() == 3);
        CHECK_THAT(info[2], Catch::Matchers::StartsWith("Server closed the connection (code 1000"));
        CHECK(noWarnings());
    }

    SECTION("a failure, at Verbose only")
    {
        auto connection = Connection{*loop, MakeOptions(TestServer::FindClosedPort()), capture.GetLogger()};
        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitClosed(WAIT));
        }) == Outcome_e::Failed);

        const auto verbose = messagesAt(LogLevel_e::Verbose);
        CHECK(std::ranges::any_of(verbose, [](const std::string& message)
        {
            return message.starts_with("Connection failed: Connecting to");
        }));
        CHECK(noWarnings());
    }

    SECTION("a text message")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.SendText("hello");
            co_await session.ReceiveUntilClosed();
        }};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), capture.GetLogger()};
        static_cast<void>(GetOutcome([&]
        {
            static_cast<void>(connection.WaitClosed(WAIT));
        }));

        const auto verbose = messagesAt(LogLevel_e::Verbose);
        CHECK(std::ranges::find(verbose, "Received a 5-byte text message") != verbose.end());
        CHECK(noWarnings());
    }
}

TEST_CASE("Connection over raw TCP", "[Connection][network]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();

    SECTION("opens and echoes")
    {
        const auto server = TestServer{Echo, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3});
    }

    SECTION("sends no upgrade, only the bytes it's given")
    {
        const auto server = TestServer{{}, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Send(std::array<u8, 2>{14, 0});
        REQUIRE(HasStreamSize(server, 2));
        CHECK(GetStream(server) == std::vector<u8>{14, 0});
    }

    SECTION("sends arrive in order as one stream")
    {
        const auto server = TestServer{{}, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Send(std::array<u8, 2>{1, 2});
        connection.Send(std::array<u8, 1>{3});
        connection.Pump();
        REQUIRE(HasStreamSize(server, 3));
        CHECK(GetStream(server) == std::vector<u8>{1, 2, 3});
    }

    SECTION("the server's writes read as one stream")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Send({1, 2});
            co_await session.Send({3, 4});
            co_await session.Send({5, 6});
            co_await session.ReceiveUntilClosed();
        }, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};

        REQUIRE(connection.WaitAvailable(6, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3, 4, 5, 6});
    }

    SECTION("a send larger than a read arrives whole")
    {
        const auto server = TestServer{Echo, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        auto sent = std::vector<u8>(65'536);
        for (auto i = std::size_t{0}; i < sent.size(); ++i)
        {
            sent[i] = static_cast<u8>(i & 0xFF);
        }

        connection.Send(sent);
        REQUIRE(connection.WaitAvailable(sent.size(), WAIT));
        CHECK(ReadAll(connection) == sent);
    }

    SECTION("the server's FIN is a close, and keeps the data before it")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Send({1, 2});
            co_await session.Close(0);
            co_await session.ReceiveUntilClosed();
        }, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};

        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitAvailable(3, WAIT));
        }) == Outcome_e::Closed);
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2});
        CHECK(connection.Pump() == ConnectionState_e::Closed);
    }

    SECTION("a reset is a failure")
    {
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            session.Reset();
            co_return;
        }, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};

        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitAvailable(1, WAIT));
        }) == Outcome_e::Failed);
    }

    SECTION("Close sends a FIN and finishes when the server closes")
    {
        const auto server = TestServer{Echo, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Close();
        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed < 800ms);
        CHECK(HasFin(server));
        CHECK(connection.Pump() == ConnectionState_e::Closed);
    }

    SECTION("Close lets the write in flight finish before the FIN")
    {
        const auto server = TestServer{{}, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Send(std::vector<u8>(LARGE_SEND_SIZE, 7));
        connection.Close();
        REQUIRE(connection.WaitClosed(WAIT));

        CHECK(HasFin(server));
        CHECK(GetStream(server) == std::vector<u8>(LARGE_SEND_SIZE, 7));
    }

    SECTION("a server that never closes is dropped after the close timeout")
    {
        const auto server = TestServer{Silent, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Close();
        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed > 800ms);
        CHECK(elapsed < 2s);
    }

    SECTION("a close while connecting is immediate")
    {
        const auto server = TestServer{{}, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};

        CHECK(Measure([&]
        {
            connection.Close();
        }) < AT_ONCE);

        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed < 100ms);
    }

    SECTION("a connection destroyed while open still sends its FIN")
    {
        const auto server = TestServer{Echo, ServerMode_e::Tcp};
        {
            auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), logger};
            REQUIRE(connection.WaitOpen(WAIT));
        }

        loop->Settle(Clock::now() + 2s);
        CHECK(HasFin(server));
    }

    SECTION("nothing listening is a failure")
    {
        auto connection = Connection{*loop, MakeTcpOptions(TestServer::FindClosedPort()), logger};
        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        }) == Outcome_e::Failed);
    }

    SECTION("logs its lifecycle")
    {
        auto capture = LogCapture{};
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Echo();
        }, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), capture.GetLogger()};
        REQUIRE(connection.WaitOpen(WAIT));
        connection.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        connection.Close();
        REQUIRE(connection.WaitClosed(WAIT));

        auto info = std::vector<std::string>{};
        auto verbose = std::vector<std::string>{};
        for (const auto& entry : capture.GetEntries())
        {
            CHECK(entry.level != LogLevel_e::Warning);
            CHECK(entry.level != LogLevel_e::Error);
            if (entry.level == LogLevel_e::Info)
            {
                info.push_back(entry.message);
            }
            else if (entry.level == LogLevel_e::Verbose)
            {
                verbose.push_back(entry.message);
            }
        }

        REQUIRE(info.size() == 3);
        CHECK(info[0] == std::format("Connecting to tcp://{}:{}", LOOPBACK, server.GetPort()));
        CHECK(info[1] == "Connection open");
        CHECK(info[2] == "Connection closing");
        CHECK(std::ranges::find(verbose, "Sending 3 bytes") != verbose.end());
        CHECK(std::ranges::find(verbose, "Received 3 bytes") != verbose.end());
    }

    SECTION("logs the server's close")
    {
        auto capture = LogCapture{};
        const auto server = TestServer{[](ServerSession& session) -> Awaitable
        {
            co_await session.Close(0);
            co_await session.ReceiveUntilClosed();
        }, ServerMode_e::Tcp};
        auto connection = Connection{*loop, MakeTcpOptions(server.GetPort()), capture.GetLogger()};
        REQUIRE(connection.WaitClosed(WAIT));

        const auto entries = capture.GetEntries();
        CHECK(std::ranges::any_of(entries, [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Info && entry.message == "Server closed the connection";
        }));
    }
}

TEST_CASE("Connection over TLS", "[Connection][network][tls]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();
    const auto folder = TempFolder{"rs2004-tls-tests"};
    folder.WriteFile("ca.pem", TestCertificate::Get().certificatePem);
    const auto caFile = (folder.GetPath() / "ca.pem").string();

    const auto server = TestServer{Echo, ServerMode_e::WebSocket, true};
    const auto makeOptions = [&](std::string host, std::string tlsCaFile)
    {
        return ConnectionOptions_s{.transport = Transport_e::Wss, .host = std::move(host), .port = server.GetPort(), .tlsCaFile = std::move(tlsCaFile)};
    };

    SECTION("opens with the certificate as the CA file, and sends the host as SNI")
    {
        auto connection = Connection{*loop, makeOptions(TestCertificate_s::HOST, caFile), logger};
        REQUIRE(connection.WaitOpen(WAIT));
        connection.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3});

        const auto record = server.GetRecord();
        REQUIRE(record.handshakes.size() == 1);
        CHECK(record.handshakes[0].serverName == TestCertificate_s::HOST);
    }

    SECTION("the system store doesn't trust it")
    {
        auto connection = Connection{*loop, makeOptions(TestCertificate_s::HOST, "SYSTEM"), logger};
        const auto failure = GetFailure([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        });
        CHECK_THAT(failure, Catch::Matchers::StartsWith("TLS handshake failed"));
    }

    SECTION("a certificate that doesn't name the host fails")
    {
        auto connection = Connection{*loop, makeOptions(LOOPBACK, caFile), logger};
        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        }) == Outcome_e::Failed);
    }

    SECTION("NONE verifies nothing")
    {
        auto connection = Connection{*loop, makeOptions(LOOPBACK, "NONE"), logger};
        CHECK(connection.WaitOpen(WAIT));
    }

    SECTION("a missing CA file fails the attempt, not the constructor")
    {
        auto connection = Connection{*loop, makeOptions(TestCertificate_s::HOST, (folder.GetPath() / "missing.pem").string()), logger};
        const auto failure = GetFailure([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        });
        CHECK_THAT(failure, Catch::Matchers::StartsWith("TLS setup failed"));
    }

    SECTION("closes through the TLS shutdown")
    {
        auto connection = Connection{*loop, makeOptions(TestCertificate_s::HOST, caFile), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Close();
        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed < 2s);
    }
}

TEST_CASE("Connection over TLS treats a truncated stream as a close", "[Connection][network][tls]")
{
    const auto loop = NetLoop::Create();
    const auto server = TestServer{[](ServerSession& session) -> Awaitable
    {
        session.Drop();
        co_return;
    },
        ServerMode_e::WebSocket, true};
    const auto options = ConnectionOptions_s{.transport = Transport_e::Wss, .host = LOOPBACK, .port = server.GetPort(), .tlsCaFile = "NONE"};
    auto connection = Connection{*loop, options, MakeConsoleLogger()};

    CHECK(GetOutcome([&]
    {
        static_cast<void>(connection.WaitAvailable(1, WAIT));
    }) == Outcome_e::Closed);
}

TEST_CASE("Connection through a SOCKS5 proxy", "[Connection][network][Socks5]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();
    auto proxy = FakeSocks5Proxy{};

    const auto through = [&proxy](ConnectionOptions_s options)
    {
        options.proxy = Socks5Proxy_s{.host = LOOPBACK, .port = proxy.GetPort()};
        return options;
    };

    SECTION("ws to an IPv4 address sends the address, and exchanges data")
    {
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, through(MakeOptions(server.GetPort())), logger};
        REQUIRE(connection.WaitOpen(WAIT));
        connection.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3});

        const auto record = proxy.GetRecord();
        CHECK(record.accepted == 1);
        REQUIRE(record.requests.size() == 1);
        CHECK(record.requests[0].type == Socks5AddressType_e::Ipv4);
        CHECK(record.requests[0].host == LOOPBACK);
        CHECK(record.requests[0].port == server.GetPort());
        CHECK(record.credentials.empty());
    }

    SECTION("a host name goes to the proxy unresolved")
    {
        const auto server = TestServer{Echo};
        auto options = MakeOptions(server.GetPort());
        options.host = "localhost";
        auto connection = Connection{*loop, through(options), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        const auto record = proxy.GetRecord();
        REQUIRE(record.requests.size() == 1);
        CHECK(record.requests[0].type == Socks5AddressType_e::DomainName);
        CHECK(record.requests[0].host == "localhost");
    }

    SECTION("wss checks the server's certificate, not the proxy's")
    {
        const auto folder = TempFolder{"rs2004-socks5-tests"};
        folder.WriteFile("ca.pem", TestCertificate::Get().certificatePem);
        const auto server = TestServer{Echo, ServerMode_e::WebSocket, true};
        const auto options = ConnectionOptions_s{
            .transport = Transport_e::Wss,
            .host = TestCertificate_s::HOST,
            .port = server.GetPort(),
            .tlsCaFile = (folder.GetPath() / "ca.pem").string(),
        };

        auto connection = Connection{*loop, through(options), logger};
        REQUIRE(connection.WaitOpen(WAIT));
        connection.Send(std::array<u8, 2>{4, 5});
        REQUIRE(connection.WaitAvailable(2, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{4, 5});
        REQUIRE(server.GetRecord().handshakes.size() == 1);
        CHECK(server.GetRecord().handshakes[0].serverName == TestCertificate_s::HOST);
    }

    SECTION("tcp exchanges data")
    {
        const auto server = TestServer{Echo, ServerMode_e::Tcp};
        auto connection = Connection{*loop, through(MakeTcpOptions(server.GetPort())), logger};
        REQUIRE(connection.WaitOpen(WAIT));
        connection.Send(std::array<u8, 3>{7, 8, 9});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{7, 8, 9});
    }

    SECTION("sends the credentials the proxy requires")
    {
        proxy.SetCredentials("b0tuser", "s3cret");
        const auto server = TestServer{Echo};
        auto options = through(MakeOptions(server.GetPort()));
        options.proxy->username = "b0tuser";
        options.proxy->password = "s3cret";
        auto connection = Connection{*loop, options, logger};
        REQUIRE(connection.WaitOpen(WAIT));

        const auto record = proxy.GetRecord();
        REQUIRE(record.credentials.size() == 1);
        CHECK(record.credentials[0].username == "b0tuser");
        CHECK(record.credentials[0].password == "s3cret");
    }

    SECTION("a wrong password fails without naming the credentials")
    {
        auto capture = LogCapture{};
        proxy.SetCredentials("b0tuser", "s3cret");
        const auto server = TestServer{Echo};
        auto options = through(MakeOptions(server.GetPort()));
        options.proxy->username = "b0tuser";
        options.proxy->password = "wr0ng";
        auto connection = Connection{*loop, options, capture.GetLogger()};

        const auto failure = GetFailure([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        });
        CHECK_THAT(failure, Catch::Matchers::ContainsSubstring("SOCKS5") && Catch::Matchers::ContainsSubstring("rejected"));

        const auto namesSecret = [](std::string_view text)
        {
            return text.find("b0tuser") != std::string_view::npos || text.find("wr0ng") != std::string_view::npos;
        };
        CHECK_FALSE(namesSecret(failure));
        for (const auto& entry : capture.GetEntries())
        {
            CHECK_FALSE(namesSecret(entry.message));
        }
    }

    SECTION("a refused connect gives the reply's meaning")
    {
        proxy.SetReply(5);
        const auto server = TestServer{Echo};
        auto connection = Connection{*loop, through(MakeOptions(server.GetPort())), logger};
        const auto failure = GetFailure([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        });
        CHECK_THAT(failure, Catch::Matchers::ContainsSubstring(std::format("SOCKS5 proxy {}:{}: connection refused (reply 5)", LOOPBACK, proxy.GetPort())));
    }

    SECTION("the reply is read to its end, so a server's first bytes come through")
    {
        const auto type = GENERATE(Socks5AddressType_e::DomainName, Socks5AddressType_e::Ipv6);
        proxy.SetBoundAddress(type);
        proxy.SetGreetingWithReply({9, 8, 7});
        const auto server = TestServer{Echo, ServerMode_e::Tcp};
        auto connection = Connection{*loop, through(MakeTcpOptions(server.GetPort())), logger};

        REQUIRE(connection.WaitAvailable(3, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{9, 8, 7});
        connection.Send(std::array<u8, 1>{6});
        REQUIRE(connection.WaitAvailable(1, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{6});
    }

    SECTION("a stalled proxy times out during the exchange")
    {
        proxy.SetStalled(true);
        auto options = through(MakeOptions(TestServer::FindClosedPort()));
        options.connectTimeout = 1s;
        auto connection = Connection{*loop, options, logger};

        auto failure = std::string{};
        const auto elapsed = Measure([&]
        {
            failure = GetFailure([&]
            {
                static_cast<void>(connection.WaitOpen(WAIT));
            });
        });
        CHECK(elapsed < 2s);
        CHECK_THAT(failure, Catch::Matchers::ContainsSubstring("during the SOCKS5 exchange"));
    }

    SECTION("a close during the exchange is immediate")
    {
        proxy.SetStalled(true);
        auto connection = Connection{*loop, through(MakeOptions(TestServer::FindClosedPort())), logger};
        const auto deadline = Clock::now() + WAIT;
        while (proxy.GetRecord().accepted == 0 && Clock::now() < deadline)
        {
            static_cast<void>(connection.WaitOpen(10ms));
        }

        REQUIRE(proxy.GetRecord().accepted == 1);
        CHECK(Measure([&]
        {
            connection.Close();
        }) < AT_ONCE);

        auto closed = false;
        const auto elapsed = Measure([&]
        {
            closed = connection.WaitClosed(WAIT);
        });
        CHECK(closed);
        CHECK(elapsed < 100ms);
    }

    SECTION("nothing listening on the proxy's port names the proxy")
    {
        const auto closedPort = TestServer::FindClosedPort();
        auto options = MakeOptions(80);
        options.proxy = Socks5Proxy_s{.host = LOOPBACK, .port = closedPort};
        auto connection = Connection{*loop, options, logger};
        const auto failure = GetFailure([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        });
        CHECK_THAT(failure, Catch::Matchers::ContainsSubstring(std::format("SOCKS5 proxy {}:{}", LOOPBACK, closedPort)));
    }

    SECTION("the connect line names the proxy, and not its credentials")
    {
        auto capture = LogCapture{};
        proxy.SetCredentials("b0tuser", "s3cret");
        const auto server = TestServer{Echo};
        auto options = through(MakeOptions(server.GetPort()));
        options.proxy->username = "b0tuser";
        options.proxy->password = "s3cret";
        auto connection = Connection{*loop, options, capture.GetLogger()};
        REQUIRE(connection.WaitOpen(WAIT));

        const auto entries = capture.GetEntries();
        REQUIRE_FALSE(entries.empty());
        CHECK(entries[0].message == std::format("Connecting to ws://{}:{} through SOCKS5 proxy {}:{}", LOOPBACK, server.GetPort(), LOOPBACK, proxy.GetPort()));
        for (const auto& entry : entries)
        {
            CHECK_THAT(entry.message, !(Catch::Matchers::ContainsSubstring("b0tuser") || Catch::Matchers::ContainsSubstring("s3cret")));
        }
    }
}

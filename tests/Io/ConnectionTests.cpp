#include "pch.hpp"
#include "../Support/Io/TestCertificate.hpp"
#include "../Support/Io/TestWebSocketServer.hpp"
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

#include <boost/asio/awaitable.hpp>
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_tostring.hpp>
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

    bool HasCloseCode(const TestWebSocketServer& server, u16 code)
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
}

static_assert(std::derived_from<ConnectionClosedError, ConnectionError>);

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

    for (const auto& options : {emptyHost, zeroPort, zeroTimeout, noCaFile})
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
        const auto server = TestWebSocketServer{};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        CHECK(connection.WaitOpen(WAIT));
        CHECK(connection.Pump() == ConnectionState_e::Open);
    }

    SECTION("sends the origin, the subprotocol and the host with its port")
    {
        const auto server = TestWebSocketServer{};
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
        const auto server = TestWebSocketServer{};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        const auto record = server.GetRecord();
        REQUIRE(record.handshakes.size() == 1);
        CHECK_FALSE(record.handshakes[0].origin.has_value());
    }

    SECTION("echoes")
    {
        const auto server = TestWebSocketServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(connection.WaitAvailable(3, WAIT));
        CHECK(ReadAll(connection) == std::vector<u8>{1, 2, 3});
    }

    SECTION("echoes a message too long for a 16-bit frame length")
    {
        const auto server = TestWebSocketServer{Echo};
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
        const auto server = TestWebSocketServer{};
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        auto connection = Connection{*loop, MakeOptions(TestWebSocketServer::FindClosedPort()), logger};
        CHECK(GetOutcome([&]
        {
            static_cast<void>(connection.WaitOpen(WAIT));
        }) == Outcome_e::Failed);
    }

    SECTION("a silent server leaves it connecting")
    {
        const auto server = TestWebSocketServer{{}, ServerMode_e::Silent};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        CHECK_FALSE(connection.WaitOpen(200ms));
        CHECK(connection.Pump() == ConnectionState_e::Connecting);
    }

    SECTION("connectTimeout ends the attempt and names the stage")
    {
        const auto server = TestWebSocketServer{{}, ServerMode_e::Silent};
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
        const auto server = TestWebSocketServer{{}, ServerMode_e::Reject};
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
        const auto server = TestWebSocketServer{};
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

    const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{Echo};
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
        const auto server = TestWebSocketServer{Echo};
        auto connection = Connection{*loop, MakeOptions(server.GetPort()), logger};
        REQUIRE(connection.WaitOpen(WAIT));

        connection.Close();
        CHECK(connection.WaitClosed(WAIT));
        CHECK(connection.Pump() == ConnectionState_e::Closed);
        CHECK(HasCloseCode(server, CLOSE_CODE_NORMAL));
    }

    SECTION("pumping alone finishes a close")
    {
        const auto server = TestWebSocketServer{Echo};
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        const auto server = TestWebSocketServer{Silent};
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
        const auto server = TestWebSocketServer{{}, ServerMode_e::Silent};
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
        const auto server = TestWebSocketServer{{}, ServerMode_e::Silent};
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
        const auto server = TestWebSocketServer{{}, ServerMode_e::Silent};
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
        const auto server = TestWebSocketServer{Echo};
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
        const auto firstServer = TestWebSocketServer{Echo};
        const auto secondServer = TestWebSocketServer{Echo};
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
        const auto server = TestWebSocketServer{Echo};
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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
        auto connection = Connection{*loop, MakeOptions(TestWebSocketServer::FindClosedPort()), capture.GetLogger()};
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
        const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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

TEST_CASE("Connection over TLS", "[Connection][network][tls]")
{
    const auto loop = NetLoop::Create();
    const auto logger = MakeConsoleLogger();
    const auto folder = TempFolder{"rs2004-tls-tests"};
    folder.WriteFile("ca.pem", TestCertificate::Get().certificatePem);
    const auto caFile = (folder.GetPath() / "ca.pem").string();

    const auto server = TestWebSocketServer{Echo, ServerMode_e::WebSocket, true};
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
    const auto server = TestWebSocketServer{[](ServerSession& session) -> Awaitable
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

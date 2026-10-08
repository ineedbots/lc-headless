#include "pch.hpp"
#include "../DefaultLoggerScope.hpp"
#include "../LogCapture.hpp"
#include "../LoopbackPort.hpp"

#include "Core/Logger.hpp"
#include "Io/NetSystem.hpp"
#include "Io/WebSocketClient.hpp"
#include "Io/WebSocketClosedError.hpp"
#include "Io/WebSocketError.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_tostring.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <ixwebsocket/IXConnectionState.h>
#include <ixwebsocket/IXSocket.h>
#include <ixwebsocket/IXSocketServer.h>
#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXWebSocketHttpHeaders.h>
#include <ixwebsocket/IXWebSocketMessage.h>
#include <ixwebsocket/IXWebSocketMessageType.h>
#include <ixwebsocket/IXWebSocketServer.h>

namespace
{
    using Clock = std::chrono::steady_clock;

    constexpr auto FIRST_PORT = 47000;
    constexpr auto LAST_PORT = 47099;
    // No test server listens in this range, so a free port here stays unused while a test relies on it.
    constexpr auto FIRST_UNUSED_PORT = 47900;
    constexpr auto LAST_UNUSED_PORT = 47999;
    constexpr auto LOOPBACK_HOST = "127.0.0.1";
    constexpr auto WAIT = 5s;
    constexpr auto AT_ONCE = 50ms;
    constexpr auto SERVER_DELAY = 300ms;
    constexpr auto SILENT_HANDSHAKE_TIMEOUT = 1s;
    constexpr auto WITHIN_HANDSHAKE_TIMEOUT = 3s;
    constexpr auto STOP_ATTEMPTS = 20;

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

    std::string ToText(std::span<const u8> bytes)
    {
        return std::string{reinterpret_cast<const char*>(bytes.data()), bytes.size()};
    }

    WebSocketOptions_s MakeOptions(const std::string& url, std::chrono::seconds handshakeTimeout = WAIT)
    {
        return {.url = url, .handshakeTimeout = handshakeTimeout};
    }

    template <typename TAction>
    Outcome_e GetOutcome(TAction action)
    {
        try
        {
            action();
            return Outcome_e::Returned;
        }
        catch (const WebSocketClosedError&)
        {
            return Outcome_e::Closed;
        }
        catch (const WebSocketError&)
        {
            return Outcome_e::Failed;
        }
    }

    template <typename TAction>
    Clock::duration Measure(TAction action)
    {
        const auto start = Clock::now();
        action();
        return Clock::now() - start;
    }

    template <typename TServer, typename TCreate>
    std::unique_ptr<TServer> ListenOnFreePort(TCreate create)
    {
        for (auto port = FIRST_PORT; port <= LAST_PORT; ++port)
        {
            if (!LoopbackPort::IsFree(port))
            {
                continue;
            }

            auto server = create(port);
            if (!server->listen().first)
            {
                continue;
            }

            server->start();
            return server;
        }

        throw std::runtime_error{"No free port for a test server"};
    }

    std::string GetUrl(int port)
    {
        return std::format("ws://{}:{}/", LOOPBACK_HOST, port);
    }

    class LoopbackServer
    {
    public:
        using Script = std::function<void(ix::WebSocket& connection)>;

        explicit LoopbackServer(Script onOpen = {}, bool echoes = false)
            : m_onOpen{std::move(onOpen)}
            , m_echoes{echoes}
        {
            m_server = ListenOnFreePort<ix::WebSocketServer>([this](int port)
            {
                auto server = std::make_unique<ix::WebSocketServer>(port, LOOPBACK_HOST);
                server->disablePerMessageDeflate();
                server->setOnClientMessageCallback([this](std::shared_ptr<ix::ConnectionState>, ix::WebSocket& connection, const ix::WebSocketMessagePtr& message)
                {
                    OnMessage(connection, *message);
                });

                return server;
            });
        }

        ~LoopbackServer()
        {
            m_server->stop();
        }

        LoopbackServer(const LoopbackServer&) = delete;
        LoopbackServer& operator=(const LoopbackServer&) = delete;

        [[nodiscard]] std::string Url() const
        {
            return GetUrl(m_server->getPort());
        }

        // What IXWebSocket sends when a client sets no origin of its own.
        [[nodiscard]] std::string DefaultOrigin() const
        {
            return std::format("ws://{}:{}", LOOPBACK_HOST, m_server->getPort());
        }

        [[nodiscard]] std::vector<std::string> GetMessages() const
        {
            const auto lock = std::scoped_lock{m_mutex};
            return m_messages;
        }

        [[nodiscard]] std::optional<std::string> GetHeader(const std::string& name) const
        {
            const auto lock = std::scoped_lock{m_mutex};
            const auto header = m_headers.find(name);
            if (header == m_headers.end())
            {
                return std::nullopt;
            }

            return header->second;
        }

        [[nodiscard]] bool WaitForOpen()
        {
            return WaitFor([this]
            {
                return m_isOpen;
            });
        }

        [[nodiscard]] bool WaitForMessages(std::size_t count)
        {
            return WaitFor([this, count]
            {
                return m_messages.size() >= count;
            });
        }

        [[nodiscard]] bool WaitForClose()
        {
            return WaitFor([this]
            {
                return m_isClosed;
            });
        }

    private:
        template <typename TCondition>
        bool WaitFor(TCondition condition)
        {
            auto lock = std::unique_lock{m_mutex};
            return m_changed.wait_for(lock, WAIT, condition);
        }

        void OnMessage(ix::WebSocket& connection, const ix::WebSocketMessage& message)
        {
            switch (message.type)
            {
            case ix::WebSocketMessageType::Open:
                {
                    const auto lock = std::scoped_lock{m_mutex};
                    m_headers = message.openInfo.headers;
                    m_isOpen = true;
                }

                m_changed.notify_all();
                if (m_onOpen)
                {
                    m_onOpen(connection);
                }
                return;

            case ix::WebSocketMessageType::Message:
                {
                    const auto lock = std::scoped_lock{m_mutex};
                    m_messages.push_back(message.str);
                }

                m_changed.notify_all();
                if (m_echoes)
                {
                    connection.sendBinary(message.str);
                }
                return;

            case ix::WebSocketMessageType::Close:
                {
                    const auto lock = std::scoped_lock{m_mutex};
                    m_isClosed = true;
                }

                m_changed.notify_all();
                return;

            default:
                return;
            }
        }

        NetSystem m_netSystem;
        Script m_onOpen;
        bool m_echoes;

        mutable std::mutex m_mutex;
        std::condition_variable m_changed;
        ix::WebSocketHttpHeaders m_headers;
        std::vector<std::string> m_messages;
        bool m_isOpen = false;
        bool m_isClosed = false;

        std::unique_ptr<ix::WebSocketServer> m_server;
    };

    class SilentSocketServer : public ix::SocketServer
    {
    public:
        explicit SilentSocketServer(int port)
            : ix::SocketServer{port, LOOPBACK_HOST}
        {
        }

        ~SilentSocketServer() override
        {
            {
                const auto lock = std::scoped_lock{m_mutex};
                m_isStopping = true;
            }

            m_stopping.notify_all();
            stop();
        }

        SilentSocketServer(const SilentSocketServer&) = delete;
        SilentSocketServer& operator=(const SilentSocketServer&) = delete;

    private:
        void handleConnection(std::unique_ptr<ix::Socket>, std::shared_ptr<ix::ConnectionState> connectionState) override
        {
            auto lock = std::unique_lock{m_mutex};
            m_stopping.wait(lock, [this]
            {
                return m_isStopping;
            });

            connectionState->setTerminated();
        }

        std::size_t getConnectedClientsCount() override
        {
            return 0;
        }

        std::mutex m_mutex;
        std::condition_variable m_stopping;
        bool m_isStopping = false;
    };

    class SilentServer
    {
    public:
        SilentServer()
            : m_server{ListenOnFreePort<SilentSocketServer>([](int port)
            {
                return std::make_unique<SilentSocketServer>(port);
            })}
        {
        }

        [[nodiscard]] std::string Url() const
        {
            return GetUrl(m_server->getPort());
        }

    private:
        NetSystem m_netSystem;
        std::unique_ptr<SilentSocketServer> m_server;
    };

    LoopbackServer MakeEchoServer()
    {
        return LoopbackServer{{}, true};
    }

    LoopbackServer::Script SendAfter(std::chrono::milliseconds delay, std::string bytes)
    {
        return [delay, bytes = std::move(bytes)](ix::WebSocket& connection)
        {
            std::this_thread::sleep_for(delay);
            connection.sendBinary(bytes);
        };
    }

    LoopbackServer::Script CloseAfter(std::chrono::milliseconds delay)
    {
        return [delay](ix::WebSocket& connection)
        {
            std::this_thread::sleep_for(delay);
            connection.close();
        };
    }

    std::string GetUnusedUrl()
    {
        for (auto port = FIRST_UNUSED_PORT; port <= LAST_UNUSED_PORT; ++port)
        {
            if (LoopbackPort::IsFree(port))
            {
                return GetUrl(port);
            }
        }

        throw std::runtime_error{"No unused port for a refused connection"};
    }

    void CheckEcho(WebSocketClient& client, std::vector<u8> bytes)
    {
        client.Send(bytes);
        REQUIRE(client.WaitAvailable(bytes.size(), WAIT));
        auto received = std::vector<u8>(bytes.size());
        client.Read(received);
        CHECK(received == bytes);
    }

    void ConnectAndWaitOpen(WebSocketClient& client, const std::string& url)
    {
        client.Connect(MakeOptions(url));
        REQUIRE(client.WaitOpen(WAIT));
    }

    std::vector<std::string> GetMessages(const LogCapture& capture, LogLevel_e level)
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
    }

    bool HasMessage(const LogCapture& capture, LogLevel_e level, std::string_view fragment)
    {
        return std::ranges::any_of(GetMessages(capture, level), [fragment](const std::string& message)
        {
            return message.find(fragment) != std::string::npos;
        });
    }

    bool HasWarningOrError(const LogCapture& capture)
    {
        return std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level >= LogLevel_e::Warning;
        });
    }
}

CATCH_REGISTER_ENUM(WebSocketState_e, WebSocketState_e::Closed, WebSocketState_e::Connecting, WebSocketState_e::Open, WebSocketState_e::Closing)
CATCH_REGISTER_ENUM(Outcome_e, Outcome_e::Returned, Outcome_e::Closed, Outcome_e::Failed)

static_assert(std::derived_from<WebSocketClosedError, WebSocketError>);

TEST_CASE("WebSocketClient receive buffer", "[WebSocketClient]")
{
    auto client = WebSocketClient{MakeConsoleLogger()};

    SECTION("starts empty")
    {
        CHECK(client.Available() == 0);
    }

    SECTION("appended bytes are available")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        CHECK(client.Available() == 3);
    }

    SECTION("reads continue across appends")
    {
        client.Append(std::array<u8, 2>{1, 2});
        client.Append(std::array<u8, 1>{3});
        client.Append(std::span<const u8>{});
        auto destination = std::array<u8, 3>{};
        client.Read(destination);
        CHECK(destination == std::array<u8, 3>{1, 2, 3});
        CHECK(client.Available() == 0);
    }

    SECTION("read returns the span it was given")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        auto destination = std::array<u8, 3>{};
        const auto partial = client.Read(std::span{destination}.first(2));
        CHECK(partial.data() == destination.data());
        CHECK(partial.size() == 2);

        const auto rest = client.Read(std::span{destination}.subspan(2));
        CHECK(rest.data() == destination.data() + 2);
        CHECK(rest.size() == 1);
    }

    SECTION("peek doesn't consume")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        auto destination = std::array<u8, 2>{};
        client.Peek(destination);
        CHECK(destination == std::array<u8, 2>{1, 2});
        CHECK(client.Available() == 3);
    }

    SECTION("peek then read give the same bytes")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        auto peeked = std::array<u8, 2>{};
        auto read = std::array<u8, 2>{};
        client.Peek(peeked);
        client.Read(read);
        CHECK(peeked == std::array<u8, 2>{1, 2});
        CHECK(read == std::array<u8, 2>{1, 2});
        CHECK(client.Available() == 1);
    }

    SECTION("consecutive reads")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        auto first = std::array<u8, 2>{};
        auto second = std::array<u8, 1>{};
        client.Read(first);
        client.Read(second);
        CHECK(first == std::array<u8, 2>{1, 2});
        CHECK(second == std::array<u8, 1>{3});
        CHECK(client.Available() == 0);
    }

    SECTION("a short read throws and consumes nothing")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        auto destination = std::array<u8, 4>{9, 9, 9, 9};
        CHECK_THROWS_AS(client.Read(destination), std::out_of_range);
        CHECK(destination == std::array<u8, 4>{9, 9, 9, 9});
        CHECK(client.Available() == 3);
    }

    SECTION("a short peek throws")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        auto destination = std::array<u8, 4>{9, 9, 9, 9};
        CHECK_THROWS_AS(client.Peek(destination), std::out_of_range);
        CHECK(destination == std::array<u8, 4>{9, 9, 9, 9});
    }

    SECTION("empty reads and peeks are no-ops")
    {
        CHECK_NOTHROW(client.Read(std::span<u8>{}));
        CHECK_NOTHROW(client.Peek(std::span<u8>{}));
    }

    SECTION("clear drops read and unread bytes")
    {
        client.Append(std::array<u8, 3>{1, 2, 3});
        auto first = std::array<u8, 1>{};
        client.Read(first);
        client.Clear();
        client.Append(std::array<u8, 1>{9});
        auto next = std::array<u8, 1>{};
        client.Read(next);
        CHECK(next == std::array<u8, 1>{9});
    }
}

TEST_CASE("WebSocketClient receive buffer compacts without losing bytes", "[WebSocketClient]")
{
    constexpr auto TOTAL = std::size_t{20'000};
    constexpr auto CHUNK = std::size_t{1000};
    constexpr auto READ_SIZE = std::size_t{7};
    constexpr auto READS_PER_CHUNK = 120;

    auto client = WebSocketClient{MakeConsoleLogger()};
    auto nextWritten = std::size_t{0};
    auto nextRead = std::size_t{0};
    auto mismatches = 0;
    const auto readPiece = [&](std::size_t size)
    {
        auto piece = std::vector<u8>(size);
        client.Read(piece);
        for (const auto byte : piece)
        {
            if (byte != static_cast<u8>(nextRead & 0xFF))
            {
                ++mismatches;
            }

            ++nextRead;
        }
    };

    while (nextWritten < TOTAL)
    {
        auto chunk = std::vector<u8>(CHUNK);
        for (auto& byte : chunk)
        {
            byte = static_cast<u8>(nextWritten++ & 0xFF);
        }

        client.Append(chunk);
        for (auto read = 0; read < READS_PER_CHUNK && client.Available() >= READ_SIZE; ++read)
        {
            readPiece(READ_SIZE);
        }
    }

    readPiece(client.Available());
    CHECK(nextRead == TOTAL);
    CHECK(mismatches == 0);
    CHECK(client.Available() == 0);
}

TEST_CASE("WebSocketClient before connecting", "[WebSocketClient]")
{
    auto client = WebSocketClient{MakeConsoleLogger()};

    SECTION("pumps as closed")
    {
        CHECK(client.Pump() == WebSocketState_e::Closed);
    }

    SECTION("waiting to open throws")
    {
        CHECK(GetOutcome([&]
        {
            client.WaitOpen();
        }) == Outcome_e::Closed);
        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitOpen(1s));
        }) == Outcome_e::Closed);
    }

    SECTION("waiting for data throws unless it's buffered")
    {
        CHECK(GetOutcome([&]
        {
            client.WaitAvailable(1);
        }) == Outcome_e::Closed);
        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitAvailable(1, 1s));
        }) == Outcome_e::Closed);

        CHECK_NOTHROW(client.WaitAvailable(0));
        CHECK(client.WaitAvailable(0, 0ms));

        client.Append(std::array<u8, 1>{1});
        CHECK(client.WaitAvailable(1, 0ms));
    }

    SECTION("waiting to close returns")
    {
        CHECK_NOTHROW(client.WaitClosed());
        CHECK(client.WaitClosed(0ms));
    }

    SECTION("sending throws")
    {
        CHECK(GetOutcome([&]
        {
            client.Send(std::array<u8, 1>{1});
        }) == Outcome_e::Closed);
    }

    SECTION("closing and stopping are no-ops")
    {
        client.Close();
        client.Close();
        CHECK(client.Pump() == WebSocketState_e::Closed);

        client.Stop();
        client.Stop();
        CHECK(client.Pump() == WebSocketState_e::Closed);
    }

    SECTION("bad options are rejected")
    {
        for (const auto* const url : {"", "localhost:43594", "http://localhost/", "ftp://localhost/"})
        {
            CAPTURE(url);
            CHECK_THROWS_AS(client.Connect(MakeOptions(url)), std::invalid_argument);
        }

        CHECK_THROWS_AS(client.Connect(MakeOptions("ws://localhost/", 0s)), std::invalid_argument);
        CHECK(client.Pump() == WebSocketState_e::Closed);
    }
}

TEST_CASE("WebSocketClient connects and exchanges data", "[WebSocketClient][network]")
{
    SECTION("opens")
    {
        auto server = LoopbackServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(server.Url()));
        CHECK(client.WaitOpen(WAIT));
        CHECK(client.Pump() == WebSocketState_e::Open);
    }

    SECTION("sends the origin and the binary subprotocol")
    {
        auto server = LoopbackServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        auto options = MakeOptions(server.Url());
        options.origin = "http://test";
        client.Connect(options);
        REQUIRE(client.WaitOpen(WAIT));
        REQUIRE(server.WaitForOpen());
        CHECK(server.GetHeader("Origin") == "http://test");
        CHECK(server.GetHeader("Sec-WebSocket-Protocol") == "binary");
    }

    SECTION("leaves IXWebSocket's default origin when it's empty")
    {
        auto server = LoopbackServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        REQUIRE(server.WaitForOpen());
        CHECK(server.GetHeader("Origin") == server.DefaultOrigin());
    }

    SECTION("echoes data")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        CheckEcho(client, {1, 2, 3});
    }

    SECTION("echoes a message with a 64-bit length")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        auto bytes = std::vector<u8>(65'536);
        for (std::size_t i = 0; i < bytes.size(); ++i)
        {
            bytes[i] = static_cast<u8>(i & 0xFF);
        }

        CheckEcho(client, bytes);
    }

    SECTION("each send is one message")
    {
        auto server = LoopbackServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        client.Send(std::array<u8, 2>{1, 2});
        client.Send(std::array<u8, 1>{3});
        REQUIRE(server.WaitForMessages(2));
        CHECK(server.GetMessages() == std::vector<std::string>{"\x01\x02", "\x03"});
    }

    SECTION("message boundaries are discarded")
    {
        auto server = LoopbackServer{[](ix::WebSocket& connection)
        {
            connection.sendBinary(std::string{"\x01\x02"});
            connection.sendBinary(std::string{"\x03\x04"});
            connection.sendBinary(std::string{"\x05\x06"});
        }};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        REQUIRE(client.WaitAvailable(6, WAIT));
        auto received = std::array<u8, 6>{};
        client.Read(received);
        CHECK(received == std::array<u8, 6>{1, 2, 3, 4, 5, 6});
    }

    SECTION("a refused connection fails")
    {
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(GetUnusedUrl()));
        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitOpen(WAIT));
        }) == Outcome_e::Failed);
    }

    SECTION("a silent server keeps it connecting")
    {
        auto server = SilentServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(server.Url(), SILENT_HANDSHAKE_TIMEOUT));
        CHECK_FALSE(client.WaitOpen(200ms));
        CHECK(client.Pump() == WebSocketState_e::Connecting);
    }

    SECTION("the handshake timeout ends the attempt")
    {
        auto server = SilentServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(server.Url(), SILENT_HANDSHAKE_TIMEOUT));
        auto outcome = Outcome_e::Returned;
        const auto elapsed = Measure([&]
        {
            outcome = GetOutcome([&]
            {
                static_cast<void>(client.WaitOpen(WAIT));
            });
        });
        CHECK(outcome == Outcome_e::Failed);
        CHECK(elapsed < WITHIN_HANDSHAKE_TIMEOUT);
    }
}

TEST_CASE("WebSocketClient timeouts and wake-ups", "[WebSocketClient][network]")
{
    SECTION("waiting for data times out")
    {
        auto server = LoopbackServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        auto isAvailable = true;
        const auto elapsed = Measure([&]
        {
            isAvailable = client.WaitAvailable(1, 200ms);
        });
        CHECK_FALSE(isAvailable);
        CHECK(elapsed >= 200ms);
        CHECK(elapsed < 2s);
        CHECK(client.Pump() == WebSocketState_e::Open);
    }

    SECTION("a zero or negative timeout polls")
    {
        auto server = LoopbackServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        auto results = std::array<bool, 2>{true, true};
        const auto elapsed = Measure([&]
        {
            results[0] = client.WaitAvailable(1, 0ms);
            results[1] = client.WaitAvailable(1, -5ms);
        });
        CHECK(results == std::array<bool, 2>{false, false});
        CHECK(elapsed < AT_ONCE);
    }

    SECTION("waiting to close times out")
    {
        auto server = LoopbackServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        CHECK_FALSE(client.WaitClosed(200ms));
        CHECK(client.Pump() == WebSocketState_e::Open);
    }

    SECTION("arriving data wakes the wait")
    {
        auto server = LoopbackServer{SendAfter(SERVER_DELAY, "\x01\x02\x03\x04")};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        auto isAvailable = false;
        const auto elapsed = Measure([&]
        {
            isAvailable = client.WaitAvailable(4, WAIT);
        });
        CHECK(isAvailable);
        CHECK(elapsed < 1500ms);
    }

    SECTION("the longest timeout waits forever instead of overflowing")
    {
        auto server = LoopbackServer{SendAfter(SERVER_DELAY, "\x01\x02\x03\x04")};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        CHECK(client.WaitAvailable(4, std::chrono::milliseconds::max()));
    }

    SECTION("the wait without a timeout returns")
    {
        auto server = LoopbackServer{SendAfter(SERVER_DELAY, "\x01\x02\x03\x04")};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        client.WaitAvailable(4);
        CHECK(client.Available() == 4);
    }
}

TEST_CASE("WebSocketClient peer close and failure", "[WebSocketClient][network]")
{
    SECTION("bytes before a peer close stay readable")
    {
        auto server = LoopbackServer{[](ix::WebSocket& connection)
        {
            connection.sendBinary(std::string{"\x01\x02\x03\x04"});
            connection.close();
        }};
        auto client = WebSocketClient{MakeConsoleLogger()};
        // No WaitOpen: the server ends the connection as it opens, so a first pump may already see it ended.
        client.Connect(MakeOptions(server.Url()));

        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitAvailable(5, WAIT));
        }) == Outcome_e::Closed);
        CHECK(client.Available() == 4);
        CHECK(client.WaitAvailable(4, 0ms));
        CHECK(client.Pump() == WebSocketState_e::Closed);
        CHECK(GetOutcome([&]
        {
            client.Send(std::array<u8, 1>{1});
        }) == Outcome_e::Closed);
    }

    SECTION("waiting for a peer close")
    {
        auto server = LoopbackServer{CloseAfter(SERVER_DELAY)};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        auto isClosed = false;
        const auto elapsed = Measure([&]
        {
            isClosed = client.WaitClosed(WAIT);
        });
        CHECK(isClosed);
        CHECK(elapsed < 1500ms);
        CHECK(client.Pump() == WebSocketState_e::Closed);
    }

    SECTION("a text message fails the connection, keeping earlier bytes")
    {
        auto server = LoopbackServer{[](ix::WebSocket& connection)
        {
            connection.sendBinary(std::string{"\x01\x02\x03\x04"});
            connection.sendText("text");
        }};
        auto client = WebSocketClient{MakeConsoleLogger()};
        // No WaitOpen: the server ends the connection as it opens, so a first pump may already see it ended.
        client.Connect(MakeOptions(server.Url()));

        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitAvailable(5, WAIT));
        }) == Outcome_e::Failed);
        CHECK(client.Available() == 4);
        CHECK(GetOutcome([&]
        {
            client.Pump();
        }) == Outcome_e::Failed);
        CHECK(GetOutcome([&]
        {
            client.Pump();
        }) == Outcome_e::Failed);

        auto received = std::array<u8, 4>{};
        client.Read(received);
        CHECK(received == std::array<u8, 4>{1, 2, 3, 4});
    }

    SECTION("a text message closes the connection")
    {
        auto server = LoopbackServer{[](ix::WebSocket& connection)
        {
            connection.sendText("text");
        }};
        auto client = WebSocketClient{MakeConsoleLogger()};
        // No WaitOpen: the server ends the connection as it opens, so a first pump may already see it ended.
        client.Connect(MakeOptions(server.Url()));

        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitClosed(WAIT));
        }) == Outcome_e::Failed);
        CHECK(server.WaitForClose());
    }
}

TEST_CASE("WebSocketClient local close", "[WebSocketClient][network]")
{
    SECTION("Close returns at once")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());

        CHECK(Measure([&]
        {
            client.Close();
        }) < AT_ONCE);

        const auto state = client.Pump();
        CHECK((state == WebSocketState_e::Closing || state == WebSocketState_e::Closed));
        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitOpen(0ms));
        }) == Outcome_e::Closed);
        CHECK(GetOutcome([&]
        {
            client.Send(std::array<u8, 1>{1});
        }) == Outcome_e::Closed);
    }

    SECTION("Close, then wait for it to finish")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());

        client.Close();
        CHECK(client.WaitClosed(WAIT));
        CHECK(client.Pump() == WebSocketState_e::Closed);
        CHECK(server.WaitForClose());
    }

    SECTION("Close, then pump until closed")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());

        client.Close();
        const auto deadline = Clock::now() + 1s;
        auto state = client.Pump();
        while (state != WebSocketState_e::Closed && Clock::now() < deadline)
        {
            std::this_thread::sleep_for(10ms);
            state = client.Pump();
        }

        CHECK(state == WebSocketState_e::Closed);
    }

    SECTION("Close ends a connection attempt within the handshake timeout")
    {
        auto server = SilentServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(server.Url(), SILENT_HANDSHAKE_TIMEOUT));

        CHECK(Measure([&]
        {
            client.Close();
        }) < WITHIN_HANDSHAKE_TIMEOUT);
        CHECK(client.WaitClosed(WAIT));
    }

    SECTION("WaitOpen after Close during Connecting throws at once")
    {
        auto server = SilentServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(server.Url(), SILENT_HANDSHAKE_TIMEOUT));
        client.Close();

        auto outcome = Outcome_e::Returned;
        const auto elapsed = Measure([&]
        {
            outcome = GetOutcome([&]
            {
                static_cast<void>(client.WaitOpen(WAIT));
            });
        });
        CHECK(outcome == Outcome_e::Closed);
        CHECK(elapsed < AT_ONCE);
    }

    SECTION("WaitOpen sees the state as of its first pump")
    {
        auto server = LoopbackServer{CloseAfter(0ms)};
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(server.Url()));
        std::this_thread::sleep_for(500ms);
        CHECK(GetOutcome([&]
        {
            static_cast<void>(client.WaitOpen(WAIT));
        }) == Outcome_e::Closed);
    }

    SECTION("destroying a connecting client")
    {
        auto server = SilentServer{};
        auto client = std::make_unique<WebSocketClient>(MakeConsoleLogger());
        client->Connect(MakeOptions(server.Url(), SILENT_HANDSHAKE_TIMEOUT));
        CHECK_NOTHROW(client.reset());
    }

    SECTION("Close leaves pumped bytes readable")
    {
        auto server = LoopbackServer{SendAfter(0ms, "\x01\x02")};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        REQUIRE(client.WaitAvailable(2, WAIT));
        client.Close();
        CHECK(client.Available() == 2);
    }
}

TEST_CASE("WebSocketClient Stop", "[WebSocketClient][network]")
{
    SECTION("stops an open connection")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());

        CHECK(Measure([&]
        {
            client.Stop();
        }) < 1s);
        CHECK(client.Pump() == WebSocketState_e::Closed);
        CHECK(server.WaitForClose());
    }

    SECTION("stops a closing connection")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());

        client.Close();
        CHECK(Measure([&]
        {
            client.Stop();
        }) < 1s);
        CHECK(client.Pump() == WebSocketState_e::Closed);
    }

    SECTION("stops a connection attempt within the handshake timeout")
    {
        auto server = SilentServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        client.Connect(MakeOptions(server.Url(), SILENT_HANDSHAKE_TIMEOUT));

        CHECK(Measure([&]
        {
            client.Stop();
        }) < WITHIN_HANDSHAKE_TIMEOUT);
        CHECK(client.Pump() == WebSocketState_e::Closed);
    }

    SECTION("stops right after connecting, every time")
    {
        auto server = SilentServer{};
        auto client = WebSocketClient{MakeConsoleLogger()};
        auto closedCount = 0;
        for (auto attempt = 0; attempt < STOP_ATTEMPTS; ++attempt)
        {
            client.Connect(MakeOptions(server.Url(), SILENT_HANDSHAKE_TIMEOUT));
            client.Stop();
            if (client.Pump() == WebSocketState_e::Closed)
            {
                ++closedCount;
            }
        }

        CHECK(closedCount == STOP_ATTEMPTS);
    }

    SECTION("returns at once when already closed")
    {
        auto server = LoopbackServer{CloseAfter(SERVER_DELAY)};
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        REQUIRE(client.WaitClosed(WAIT));

        CHECK(Measure([&]
        {
            client.Stop();
        }) < AT_ONCE);
    }

    SECTION("forgets a failure")
    {
        auto server = LoopbackServer{[](ix::WebSocket& connection)
        {
            connection.sendText("text");
        }};
        auto client = WebSocketClient{MakeConsoleLogger()};
        // No WaitOpen: the server ends the connection as it opens, so a first pump may already see it ended.
        client.Connect(MakeOptions(server.Url()));
        REQUIRE(GetOutcome([&]
        {
            static_cast<void>(client.WaitAvailable(1, WAIT));
        }) == Outcome_e::Failed);

        client.Stop();
        CHECK(client.Pump() == WebSocketState_e::Closed);
    }
}

TEST_CASE("WebSocketClient reconnects", "[WebSocketClient][network]")
{
    SECTION("after Stop")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        CheckEcho(client, {1});
        client.Stop();

        CHECK(Measure([&]
        {
            client.Connect(MakeOptions(server.Url()));
        }) < AT_ONCE);
        REQUIRE(client.WaitOpen(WAIT));
        CheckEcho(client, {2});
    }

    SECTION("after Close and WaitClosed")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        CheckEcho(client, {1});
        client.Close();
        REQUIRE(client.WaitClosed(WAIT));

        CHECK(Measure([&]
        {
            client.Connect(MakeOptions(server.Url()));
        }) < AT_ONCE);
        CHECK(client.Available() == 0);
        REQUIRE(client.WaitOpen(WAIT));
        CheckEcho(client, {2});
    }

    SECTION("without closing first")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());
        CheckEcho(client, {1});

        CHECK(Measure([&]
        {
            client.Connect(MakeOptions(server.Url()));
        }) < 1s);
        REQUIRE(client.WaitOpen(WAIT));
        CheckEcho(client, {2});
    }

    SECTION("bad options keep the current connection")
    {
        auto server = MakeEchoServer();
        auto client = WebSocketClient{MakeConsoleLogger()};
        ConnectAndWaitOpen(client, server.Url());

        CHECK_THROWS_AS(client.Connect(MakeOptions("http://x")), std::invalid_argument);
        CheckEcho(client, {1});
    }
}

TEST_CASE("WebSocketClient logs through the default logger when given none", "[WebSocketClient][network]")
{
    auto capture = LogCapture{LogLevel_e::Verbose};
    const auto scope = DefaultLoggerScope{capture.GetLogger()};
    auto server = LoopbackServer{};
    auto client = WebSocketClient{};

    ConnectAndWaitOpen(client, server.Url());

    CHECK(HasMessage(capture, LogLevel_e::Info, "connecting to"));
    CHECK(HasMessage(capture, LogLevel_e::Info, "WebSocket open"));
}

TEST_CASE("WebSocketClient logging", "[WebSocketClient][network]")
{
    auto capture = LogCapture{LogLevel_e::Verbose};
    auto client = WebSocketClient{capture.GetLogger()};

    SECTION("a whole session")
    {
        auto server = MakeEchoServer();
        client.Connect(MakeOptions(server.Url()));
        REQUIRE(client.WaitOpen(WAIT));
        client.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(client.WaitAvailable(3, WAIT));
        client.Close();
        REQUIRE(client.WaitClosed(WAIT));

        const auto info = GetMessages(capture, LogLevel_e::Info);
        REQUIRE(info.size() == 4);
        CHECK_THAT(info[0], Catch::Matchers::ContainsSubstring("connecting to") && Catch::Matchers::ContainsSubstring(server.Url()));
        CHECK_THAT(info[1], Catch::Matchers::ContainsSubstring("open"));
        CHECK_THAT(info[2], Catch::Matchers::ContainsSubstring("closing"));
        CHECK_THAT(info[3], Catch::Matchers::ContainsSubstring("closed (code 1000"));
        CHECK(HasMessage(capture, LogLevel_e::Verbose, "sending 3 bytes"));
        CHECK(HasMessage(capture, LogLevel_e::Verbose, "received 3 bytes"));
        CHECK_FALSE(HasWarningOrError(capture));
    }

    SECTION("each event is logged before the wait it satisfies returns")
    {
        auto server = MakeEchoServer();
        client.Connect(MakeOptions(server.Url()));
        REQUIRE(client.WaitOpen(WAIT));
        CHECK(HasMessage(capture, LogLevel_e::Info, "WebSocket open"));

        client.Send(std::array<u8, 3>{1, 2, 3});
        REQUIRE(client.WaitAvailable(3, WAIT));
        CHECK(HasMessage(capture, LogLevel_e::Verbose, "received 3 bytes"));

        client.Close();
        REQUIRE(client.WaitClosed(WAIT));
        CHECK(HasMessage(capture, LogLevel_e::Info, "WebSocket closed"));
    }

    SECTION("a peer close")
    {
        auto server = LoopbackServer{CloseAfter(SERVER_DELAY)};
        client.Connect(MakeOptions(server.Url()));
        REQUIRE(client.WaitClosed(WAIT));

        const auto info = GetMessages(capture, LogLevel_e::Info);
        REQUIRE(info.size() == 3);
        CHECK_THAT(info[0], Catch::Matchers::ContainsSubstring("connecting to"));
        CHECK_THAT(info[1], Catch::Matchers::ContainsSubstring("open"));
        CHECK_THAT(info[2], Catch::Matchers::ContainsSubstring("closed (code 1000"));
    }

    SECTION("a refused connection")
    {
        client.Connect(MakeOptions(GetUnusedUrl()));
        REQUIRE(GetOutcome([&]
        {
            static_cast<void>(client.WaitOpen(WAIT));
        }) == Outcome_e::Failed);

        CHECK(HasMessage(capture, LogLevel_e::Verbose, "error event"));
        CHECK_FALSE(HasWarningOrError(capture));
    }

    SECTION("a text message")
    {
        auto server = LoopbackServer{[](ix::WebSocket& connection)
        {
            connection.sendText("text");
        }};
        client.Connect(MakeOptions(server.Url()));
        REQUIRE(GetOutcome([&]
        {
            static_cast<void>(client.WaitClosed(WAIT));
        }) == Outcome_e::Failed);

        CHECK(HasMessage(capture, LogLevel_e::Verbose, "text message"));
        CHECK_FALSE(HasWarningOrError(capture));
    }

    SECTION("repeated closes log one line")
    {
        auto server = MakeEchoServer();
        client.Connect(MakeOptions(server.Url()));
        REQUIRE(client.WaitOpen(WAIT));
        client.Close();
        client.Close();
        client.Stop();

        const auto info = GetMessages(capture, LogLevel_e::Info);
        CHECK(std::ranges::count_if(info, [](const std::string& message)
        {
            return message.find("closing") != std::string::npos;
        }) == 1);
    }
}

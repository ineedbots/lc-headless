#pragma once

#include "ServerThread.hpp"

#include <boost/asio/any_io_executor.hpp>
#include <boost/asio/awaitable.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ssl/context.hpp>

struct ServerHandshake_s
{
    std::optional<std::string> origin;
    std::string subprotocol;
    std::string host;
    // The TLS server name the client sent; empty without TLS.
    std::string serverName;
};

// What a test server has seen. Read through TestWebSocketServer's getters, which copy it under the lock.
struct ServerRecord_s
{
    std::size_t accepted = 0;
    std::size_t ended = 0;
    std::vector<ServerHandshake_s> handshakes;
    std::vector<std::vector<u8>> messages;
    std::vector<u16> closeCodes;
};

// One accepted WebSocket connection, as a script sees it. Every call runs on the server's thread.
class ServerSession
{
public:
    virtual ~ServerSession() = default;

    virtual boost::asio::awaitable<void> Send(std::vector<u8> bytes) = 0;
    virtual boost::asio::awaitable<void> SendText(std::string text) = 0;
    // Nullopt once the connection has ended; a close frame's code is recorded first.
    virtual boost::asio::awaitable<std::optional<std::vector<u8>>> Receive() = 0;
    virtual boost::asio::awaitable<void> Close(u16 code) = 0;
    // Ends TCP without a close frame or a TLS close_notify.
    virtual void Drop() = 0;
    // Ends TCP with a reset.
    virtual void Reset() = 0;
    [[nodiscard]] virtual boost::asio::any_io_executor GetExecutor() = 0;

    boost::asio::awaitable<void> Delay(std::chrono::milliseconds delay);
    // Reads, recording what arrives, until the connection ends.
    boost::asio::awaitable<void> ReceiveUntilClosed();
    boost::asio::awaitable<void> Echo();

protected:
    ServerSession() = default;
};

enum class ServerMode_e : u8
{
    // Accepts the upgrade and runs the script.
    WebSocket,
    // Accepts TCP and never answers.
    Silent,
    // Answers the upgrade with HTTP 403.
    Reject,
};

// A scripted WebSocket server on 127.0.0.1, on a port the system picks, with TLS when asked. Without a script, a
// connection reads until it ends.
class TestWebSocketServer
{
public:
    using Script = std::function<boost::asio::awaitable<void>(ServerSession& session)>;

    explicit TestWebSocketServer(Script script = {}, ServerMode_e mode = ServerMode_e::WebSocket, bool tls = false);
    ~TestWebSocketServer();

    TestWebSocketServer(const TestWebSocketServer&) = delete;
    TestWebSocketServer& operator=(const TestWebSocketServer&) = delete;

    // A loopback port that nothing listens on, at least for a moment.
    [[nodiscard]] static u16 FindClosedPort();

    [[nodiscard]] u16 GetPort() const;
    [[nodiscard]] ServerRecord_s GetRecord() const;
    // Waits up to timeout for the record to satisfy condition.
    [[nodiscard]] bool WaitFor(const std::function<bool(const ServerRecord_s&)>& condition, std::chrono::milliseconds timeout = 5s) const;

    void Record(const std::function<void(ServerRecord_s&)>& change);
    [[nodiscard]] const Script& GetScript() const;

private:
    boost::asio::awaitable<void> Accept();
    boost::asio::awaitable<void> Serve(boost::asio::ip::tcp::socket socket);

    Script m_script;
    ServerMode_e m_mode;
    std::optional<boost::asio::ssl::context> m_tls;

    mutable std::mutex m_mutex;
    mutable std::condition_variable m_changed;
    ServerRecord_s m_record;

    ServerThread m_thread;
    boost::asio::ip::tcp::acceptor m_acceptor;
    // Read once here: the acceptor belongs to the server's thread once it accepts.
    u16 m_port = 0;
    // Silent connections, held open until the server goes.
    std::vector<boost::asio::ip::tcp::socket> m_silent;
};

#pragma once

#include "../Console/Logger.hpp"
#include "AsioNetLoop.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"

#include <boost/asio/awaitable.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ssl/context.hpp>
#include <boost/asio/ssl/stream.hpp>
#include <boost/asio/steady_timer.hpp>
#include <boost/beast/core/flat_buffer.hpp>
#include <boost/beast/websocket/rfc6455.hpp>
#include <boost/beast/websocket/stream.hpp>
#include <boost/system/error_code.hpp>

// A link over Asio: the lookup and TCP, then for a WebSocket, TLS and the upgrade, run by one coroutine on the loop's
// thread. Its handlers touch only this link and its logger, never a Connection, a GameClient or a script, which is
// what makes one loop safe to share.
class AsioLink : public Link, public std::enable_shared_from_this<AsioLink>
{
public:
    AsioLink(AsioNetLoop& loop, boost::asio::io_context& io, ConnectionOptions_s options, std::shared_ptr<Logger> logger);
    ~AsioLink() override;

    // Not in the constructor: the coroutine holds a shared_ptr to the link, which shared_from_this can't give yet.
    void Start();
    void Close() noexcept override;
    void Send(std::span<const u8> data) override;

private:
    using Tcp = boost::asio::ip::tcp;
    using PlainWebSocket = boost::beast::websocket::stream<Tcp::socket>;
    using SecureWebSocket = boost::beast::websocket::stream<boost::asio::ssl::stream<Tcp::socket>>;

    static constexpr auto READ_CHUNK_SIZE = std::size_t{4096};

    static boost::asio::awaitable<void> Run(std::shared_ptr<AsioLink> self);
    boost::asio::awaitable<void> RunWebSocket(PlainWebSocket& socket);
    boost::asio::awaitable<void> RunWebSocket(SecureWebSocket& socket);
    boost::asio::awaitable<void> RunTcp(Tcp::socket& socket);
    template <typename TSocket>
    boost::asio::awaitable<void> Connect(TSocket& socket);
    boost::asio::awaitable<void> NegotiateProxy(Tcp::socket& tcp);
    // False when Close or the timer has ended the attempt.
    boost::asio::awaitable<bool> WriteToProxy(Tcp::socket& tcp, std::vector<u8> bytes);
    boost::asio::awaitable<bool> ReadFromProxy(Tcp::socket& tcp, std::span<u8> bytes);
    [[nodiscard]] bool CheckProxyStep(boost::system::error_code error) const;
    template <typename TSocket>
    boost::asio::awaitable<void> Upgrade(TSocket& socket);
    template <typename TSocket>
    boost::asio::awaitable<void> ReadMessages(TSocket& socket);
    boost::asio::awaitable<void> ReadStream(Tcp::socket& socket);
    template <typename TFunction>
    void VisitSocket(TFunction function);

    void FinishConnecting();
    void EndRead(boost::system::error_code error, std::string_view closeReason);
    void EndStream(boost::system::error_code error);
    void End(std::string reason);
    void Fail(std::string reason);
    void StartWrite();
    void OnWrite(boost::system::error_code error);
    // The code goes in a WebSocket's close frame; TCP has none.
    void StartClose(boost::beast::websocket::close_code code);
    void ShutdownTcp() noexcept;
    void ArmTimer(std::chrono::milliseconds timeout);
    void OnTimer();
    void Abort() noexcept;

    AsioNetLoop& m_loop;
    ConnectionOptions_s m_options;
    std::shared_ptr<Logger> m_logger;
    Tcp::resolver m_resolver;
    boost::asio::steady_timer m_timer;
    std::string_view m_stage;
    // Before the socket, which holds a reference to it.
    std::optional<boost::asio::ssl::context> m_tls;
    // Empty until the coroutine starts, so a TLS setup failure is the attempt's failure, not the constructor's.
    std::variant<std::monostate, PlainWebSocket, SecureWebSocket, Tcp::socket> m_socket;
    boost::beast::flat_buffer m_frame;
    std::array<u8, READ_CHUNK_SIZE> m_chunk{};
    std::deque<std::vector<u8>> m_outgoing;
    bool m_writing = false;
};

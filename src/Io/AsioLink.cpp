#include "pch.hpp"
#include "AsioLink.hpp"

#include "../Config/TransportNames.hpp"
#include "../Config/Transport_e.hpp"
#include "../Console/Logger.hpp"
#include "AsioNetLoop.hpp"
#include "ConnectionOptions_s.hpp"
#include "Error/ConnectionError.hpp"
#include "Link.hpp"
#include "TrustStore.hpp"

#include <boost/asio/as_tuple.hpp>
#include <boost/asio/buffer.hpp>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/connect.hpp>
#include <boost/asio/error.hpp>
#include <boost/asio/ssl/error.hpp>
#include <boost/asio/ssl/host_name_verification.hpp>
#include <boost/asio/ssl/stream_base.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/write.hpp>
#include <boost/beast/core/stream_traits.hpp>
#include <boost/beast/http/field.hpp>
#include <boost/beast/websocket/error.hpp>
#include <boost/beast/websocket/ssl.hpp>
#include <boost/beast/websocket/stream_base.hpp>
#include <openssl/ssl.h>
#include <openssl/x509.h>

namespace
{
    namespace websocket = boost::beast::websocket;

    constexpr auto CLOSE_TIMEOUT = std::chrono::milliseconds{1s};
    constexpr auto HTTP_PORT = u16{80};
    constexpr auto HTTPS_PORT = u16{443};
    constexpr auto TARGET = "/"sv;

    const auto AS_TUPLE = boost::asio::as_tuple(boost::asio::use_awaitable);

    template <typename TSocket>
    constexpr auto IS_TCP = std::same_as<std::remove_cvref_t<TSocket>, boost::asio::ip::tcp::socket>;

    void ThrowIfFailed(boost::system::error_code error, std::string_view step)
    {
        if (error)
        {
            throw ConnectionError{std::format("{} failed: {}", step, error.message())};
        }
    }

    // Browsers send the port only when it isn't the scheme's own.
    std::string MakeHostHeader(const ConnectionOptions_s& options)
    {
        const auto defaultPort = options.transport == Transport_e::Wss ? HTTPS_PORT : HTTP_PORT;
        if (options.port == defaultPort)
        {
            return options.host;
        }

        return std::format("{}:{}", options.host, options.port);
    }

    // OpenSSL's own message only says the verification failed; the verify result says why.
    std::string DescribeTlsFailure(boost::system::error_code error, SSL* ssl)
    {
        auto description = std::format("TLS handshake failed: {}", error.message());
        const auto verifyResult = SSL_get_verify_result(ssl);
        if (verifyResult != X509_V_OK)
        {
            std::format_to(std::back_inserter(description), " ({})", X509_verify_cert_error_string(verifyResult));
        }

        return description;
    }

    void ConfigureTls(boost::asio::ssl::context& context, const std::string& caFile)
    {
        SSL_CTX_set_min_proto_version(context.native_handle(), TLS1_2_VERSION);

        try
        {
            TrustStore::Configure(context, caFile);
        }
        catch (const std::runtime_error& e)
        {
            throw ConnectionError{std::format("TLS setup failed: {}", e.what())};
        }
    }
}

AsioLink::AsioLink(AsioNetLoop& loop, boost::asio::io_context& io, ConnectionOptions_s options, std::shared_ptr<Logger> logger)
    : m_loop{loop}
    , m_options{std::move(options)}
    , m_logger{std::move(logger)}
    , m_resolver{io}
    , m_timer{io}
{
    assert(m_logger && "AsioLink needs a logger");
    m_loop.AddLink();
}

AsioLink::~AsioLink()
{
    m_loop.RemoveLink();
}

void AsioLink::Start()
{
    m_logger->Info("Connecting to {}://{}:{}", TransportNames::GetName(m_options.transport), m_options.host, m_options.port);
    ArmTimer(m_options.connectTimeout);

    // Run takes the shared_ptr as a parameter, so the coroutine frame keeps the link alive through every suspension;
    // a member coroutine on this, or a lambda capture, would not.
    boost::asio::co_spawn(m_resolver.get_executor(), Run(shared_from_this()), [](std::exception_ptr error)
    {
        assert(!error && "AsioLink::Run let an exception escape");
        static_cast<void>(error);
    });
}

void AsioLink::Close() noexcept
{
    if (!IsConnecting() && !IsOpen())
    {
        ForgetFailure();
        return;
    }

    const auto wasOpen = IsOpen();
    MarkClosing();

    try
    {
        m_logger->Info("Connection closing");
        if (wasOpen)
        {
            StartClose(websocket::close_code::normal);
            return;
        }
    }
    catch (const std::exception&)
    {
        // Only an allocation can fail; dropping the socket still ends the connection.
    }

    Abort();
}

void AsioLink::Send(std::span<const u8> data)
{
    m_logger->Verbose("Sending {} bytes", data.size());
    m_outgoing.emplace_back(data.begin(), data.end());
    if (!m_writing)
    {
        StartWrite();
    }
}

boost::asio::awaitable<void> AsioLink::Run(std::shared_ptr<AsioLink> self)
{
    try
    {
        // A Close before the loop first ran the coroutine leaves nothing to connect.
        if (self->IsConnecting())
        {
            const auto executor = self->m_resolver.get_executor();
            switch (self->m_options.transport)
            {
            case Transport_e::Ws:
                co_await self->RunWebSocket(self->m_socket.emplace<PlainWebSocket>(executor));
                break;
            case Transport_e::Wss:
            {
                auto& context = self->m_tls.emplace(boost::asio::ssl::context::tls_client);
                ConfigureTls(context, self->m_options.tlsCaFile);
                co_await self->RunWebSocket(self->m_socket.emplace<SecureWebSocket>(executor, context));
                break;
            }
            case Transport_e::Tcp:
                co_await self->RunTcp(self->m_socket.emplace<Tcp::socket>(executor));
                break;
            }
        }
    }
    catch (const std::exception& e)
    {
        self->Fail(e.what());
    }

    self->Abort();
    self->MarkClosed();
}

boost::asio::awaitable<void> AsioLink::RunWebSocket(PlainWebSocket& socket)
{
    co_await Connect(socket);
    if (!IsConnecting())
    {
        co_return;
    }

    co_await Upgrade(socket);
}

boost::asio::awaitable<void> AsioLink::RunWebSocket(SecureWebSocket& socket)
{
    co_await Connect(socket);
    if (!IsConnecting())
    {
        co_return;
    }

    m_stage = "during the TLS handshake"sv;
    auto& tls = socket.next_layer();
    if (SSL_set_tlsext_host_name(tls.native_handle(), m_options.host.c_str()) != 1)
    {
        throw ConnectionError{"TLS handshake failed: couldn't set the server name"};
    }

    if (m_options.tlsCaFile != TrustStore::NONE)
    {
        tls.set_verify_callback(boost::asio::ssl::host_name_verification{m_options.host});
    }

    const auto [handshakeError] = co_await tls.async_handshake(boost::asio::ssl::stream_base::client, AS_TUPLE);
    if (!IsConnecting())
    {
        co_return;
    }

    if (handshakeError)
    {
        throw ConnectionError{DescribeTlsFailure(handshakeError, tls.native_handle())};
    }

    co_await Upgrade(socket);
}

boost::asio::awaitable<void> AsioLink::RunTcp(Tcp::socket& socket)
{
    co_await Connect(socket);
    if (!IsConnecting())
    {
        co_return;
    }

    FinishConnecting();
    co_await ReadStream(socket);
}

template <typename TSocket>
boost::asio::awaitable<void> AsioLink::Connect(TSocket& socket)
{
    m_stage = "looking up the host"sv;
    const auto [lookupError, endpoints] = co_await m_resolver.async_resolve(m_options.host, std::to_string(m_options.port), AS_TUPLE);
    if (!IsConnecting())
    {
        co_return;
    }

    ThrowIfFailed(lookupError, std::format("Looking up {}", m_options.host));

    m_stage = "connecting"sv;
    auto& tcp = boost::beast::get_lowest_layer(socket);
    const auto [connectError, endpoint] = co_await boost::asio::async_connect(tcp, endpoints, AS_TUPLE);
    if (!IsConnecting())
    {
        co_return;
    }

    ThrowIfFailed(connectError, std::format("Connecting to {}:{}", m_options.host, m_options.port));
    tcp.set_option(Tcp::no_delay{true});
}

template <typename TSocket>
boost::asio::awaitable<void> AsioLink::Upgrade(TSocket& socket)
{
    m_stage = "during the WebSocket upgrade"sv;
    socket.set_option(websocket::stream_base::decorator([origin = m_options.origin, subprotocol = m_options.subprotocol](websocket::request_type& request)
    {
        request.set(boost::beast::http::field::sec_websocket_protocol, subprotocol);
        if (!origin.empty())
        {
            request.set(boost::beast::http::field::origin, origin);
        }
    }));
    socket.binary(true);

    auto response = websocket::response_type{};
    const auto [upgradeError] = co_await socket.async_handshake(response, MakeHostHeader(m_options), TARGET, AS_TUPLE);
    if (!IsConnecting())
    {
        co_return;
    }

    if (upgradeError == websocket::error::upgrade_declined)
    {
        throw ConnectionError{std::format("WebSocket upgrade refused (HTTP {})", response.result_int())};
    }

    ThrowIfFailed(upgradeError, "WebSocket upgrade");

    FinishConnecting();
    co_await ReadMessages(socket);
}

template <typename TSocket>
boost::asio::awaitable<void> AsioLink::ReadMessages(TSocket& socket)
{
    while (true)
    {
        const auto [error, size] = co_await socket.async_read(m_frame, AS_TUPLE);
        if (error)
        {
            const auto& closeReason = socket.reason();
            const auto reasonText = std::string_view{closeReason.reason.data(), closeReason.reason.size()};
            EndRead(error, std::format("code {}: {}", static_cast<u16>(closeReason.code), reasonText));
            co_return;
        }

        const auto bytes = std::span{static_cast<const u8*>(m_frame.cdata().data()), size};
        if (!socket.got_binary())
        {
            m_logger->Verbose("Received a {}-byte text message", size);
            if (IsOpen())
            {
                // The protocol is binary, so a text frame means the wrong endpoint.
                Fail("Received a text message");
                StartClose(websocket::close_code::unknown_data);
            }
        }
        else if (IsOpen())
        {
            m_logger->Verbose("Received {} bytes", size);
            Receive(bytes);
        }

        m_frame.consume(size);
    }
}

// Each read passes on whatever has arrived. Reading goes on while closing, dropping what arrives, until the server's
// FIN answers ours.
boost::asio::awaitable<void> AsioLink::ReadStream(Tcp::socket& socket)
{
    while (true)
    {
        const auto [error, size] = co_await socket.async_read_some(boost::asio::buffer(m_chunk), AS_TUPLE);
        if (error)
        {
            EndStream(error);
            co_return;
        }

        if (IsOpen())
        {
            m_logger->Verbose("Received {} bytes", size);
            Receive(std::span{m_chunk}.first(size));
        }
    }
}

template <typename TFunction>
void AsioLink::VisitSocket(TFunction function)
{
    if (auto* const plain = std::get_if<PlainWebSocket>(&m_socket))
    {
        function(*plain);
        return;
    }

    if (auto* const secure = std::get_if<SecureWebSocket>(&m_socket))
    {
        function(*secure);
        return;
    }

    if (auto* const tcp = std::get_if<Tcp::socket>(&m_socket))
    {
        function(*tcp);
    }
}

void AsioLink::FinishConnecting()
{
    m_timer.cancel();
    MarkOpen();
    m_logger->Info("Connection open");
}

void AsioLink::EndRead(boost::system::error_code error, std::string_view closeReason)
{
    if (!IsOpen())
    {
        return;
    }

    if (error == websocket::error::closed)
    {
        End(std::format("Server closed the connection ({})", closeReason));
        return;
    }

    // IXWebSocket reported a connection that ended without a close frame as a close, not a failure, and so does this.
    if (error == boost::asio::error::eof || error == boost::asio::ssl::error::stream_truncated)
    {
        End("Server closed the connection without a close frame"s);
        return;
    }

    Fail(std::format("Read failed: {}", error.message()));
}

void AsioLink::EndStream(boost::system::error_code error)
{
    if (!IsOpen())
    {
        return;
    }

    if (error == boost::asio::error::eof)
    {
        End("Server closed the connection"s);
        return;
    }

    Fail(std::format("Read failed: {}", error.message()));
}

void AsioLink::End(std::string reason)
{
    m_logger->Info("{}", reason);
    MarkEnded(std::move(reason));
}

void AsioLink::Fail(std::string reason)
{
    if (!IsConnecting() && !IsOpen())
    {
        return;
    }

    m_logger->Verbose("Connection failed: {}", reason);
    MarkFailed(std::move(reason));
}

void AsioLink::StartWrite()
{
    m_writing = true;
    VisitSocket([this](auto& socket)
    {
        auto onWrite = [self = shared_from_this()](boost::system::error_code error, std::size_t)
        {
            self->OnWrite(error);
        };

        const auto bytes = boost::asio::buffer(m_outgoing.front());
        if constexpr (IS_TCP<decltype(socket)>)
        {
            boost::asio::async_write(socket, bytes, std::move(onWrite));
        }
        else
        {
            socket.async_write(bytes, std::move(onWrite));
        }
    });
}

void AsioLink::OnWrite(boost::system::error_code error)
{
    m_writing = false;
    if (error)
    {
        if (IsOpen())
        {
            Fail(std::format("Send failed: {}", error.message()));
            Abort();
        }

        return;
    }

    m_outgoing.pop_front();
    if (IsOpen() && !m_outgoing.empty())
    {
        StartWrite();
        return;
    }

    // The FIN that StartClose held back until this write was done.
    if (!IsOpen() && std::holds_alternative<Tcp::socket>(m_socket))
    {
        ShutdownTcp();
    }
}

// Beast lets the close run beside the pending read and a write already in flight. The read ends once the peer's
// close frame has arrived and the connection is torn down, or when the timer drops the socket. TCP closes with a FIN
// instead, and its read ends at the server's FIN.
void AsioLink::StartClose(websocket::close_code code)
{
    const auto unsent = m_outgoing.begin() + (m_writing ? 1 : 0);
    m_outgoing.erase(unsent, m_outgoing.end());

    VisitSocket([this, code](auto& socket)
    {
        if constexpr (IS_TCP<decltype(socket)>)
        {
            // A FIN now could cut the write in flight short, so OnWrite sends it once that write is done.
            if (!m_writing)
            {
                ShutdownTcp();
            }
        }
        else
        {
            socket.async_close(code, [self = shared_from_this()](boost::system::error_code error)
            {
                if (error)
                {
                    self->Abort();
                }
            });
        }
    });

    ArmTimer(CLOSE_TIMEOUT);
}

void AsioLink::ShutdownTcp() noexcept
{
    // A socket that can't shut down has already failed; the read ends with that, or the close timer drops it.
    auto ignored = boost::system::error_code{};
    std::get<Tcp::socket>(m_socket).shutdown(Tcp::socket::shutdown_send, ignored);
}

void AsioLink::ArmTimer(std::chrono::milliseconds timeout)
{
    m_timer.expires_after(timeout);
    m_timer.async_wait([self = shared_from_this()](boost::system::error_code error)
    {
        if (!error)
        {
            self->OnTimer();
        }
    });
}

void AsioLink::OnTimer()
{
    // The connect timer can fire just as the connection opens, after the cancel came too late to stop its handler.
    if (IsOpen())
    {
        return;
    }

    if (IsConnecting())
    {
        Fail(std::format("Timed out after {} ms {}", m_options.connectTimeout.count(), m_stage));
    }

    Abort();
}

void AsioLink::Abort() noexcept
{
    try
    {
        m_resolver.cancel();
        m_timer.cancel();
    }
    catch (const std::exception&)
    {
        // Cancelling only fails if the system does, and closing the socket below still ends the connection.
    }

    VisitSocket([](auto& socket)
    {
        auto ignored = boost::system::error_code{};
        boost::beast::get_lowest_layer(socket).close(ignored);
    });
}

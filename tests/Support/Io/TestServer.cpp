#include "pch.hpp"
#include "TestServer.hpp"

#include "ServerThread.hpp"
#include "TestCertificate.hpp"

#include <boost/asio/as_tuple.hpp>
#include <boost/asio/buffer.hpp>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>
#include <boost/asio/error.hpp>
#include <boost/asio/ssl/stream.hpp>
#include <boost/asio/steady_timer.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/write.hpp>
#include <boost/beast/core/flat_buffer.hpp>
#include <boost/beast/core/stream_traits.hpp>
#include <boost/beast/http/field.hpp>
#include <boost/beast/http/message.hpp>
#include <boost/beast/http/read.hpp>
#include <boost/beast/http/status.hpp>
#include <boost/beast/http/string_body.hpp>
#include <boost/beast/http/write.hpp>
#include <boost/beast/websocket/error.hpp>
#include <boost/beast/websocket/ssl.hpp>
#include <boost/beast/websocket/stream.hpp>
#include <openssl/ssl.h>

namespace
{
    namespace asio = boost::asio;
    namespace beast = boost::beast;
    namespace http = beast::http;
    namespace websocket = beast::websocket;
    using Tcp = asio::ip::tcp;

    constexpr auto LOOPBACK = "127.0.0.1";
    constexpr auto SUBPROTOCOL = "binary";
    constexpr auto READ_SIZE = std::size_t{4096};

    const auto AS_TUPLE = asio::as_tuple(asio::use_awaitable);

    template <typename TSocket>
    class Session : public ServerSession
    {
    public:
        Session(TSocket& socket, TestServer& server)
            : m_socket{socket}
            , m_server{server}
        {
        }

        asio::awaitable<void> Send(std::vector<u8> bytes) override
        {
            m_socket.binary(true);
            co_await m_socket.async_write(asio::buffer(bytes), AS_TUPLE);
        }

        asio::awaitable<void> SendText(std::string text) override
        {
            m_socket.text(true);
            co_await m_socket.async_write(asio::buffer(text), AS_TUPLE);
        }

        asio::awaitable<std::optional<std::vector<u8>>> Receive() override
        {
            auto buffer = beast::flat_buffer{};
            const auto [error, size] = co_await m_socket.async_read(buffer, AS_TUPLE);
            if (error)
            {
                if (error == websocket::error::closed)
                {
                    const auto code = static_cast<u16>(m_socket.reason().code);
                    m_server.Record([code](ServerRecord_s& record)
                    {
                        record.closeCodes.push_back(code);
                    });
                }

                co_return std::nullopt;
            }

            const auto* const data = static_cast<const u8*>(buffer.cdata().data());
            auto message = std::vector<u8>(data, data + size);
            m_server.Record([&message](ServerRecord_s& record)
            {
                record.messages.push_back(message);
            });

            co_return message;
        }

        asio::awaitable<void> Close(u16 code) override
        {
            co_await m_socket.async_close(static_cast<websocket::close_code>(code), AS_TUPLE);
        }

        void Drop() override
        {
            auto ignored = boost::system::error_code{};
            beast::get_lowest_layer(m_socket).close(ignored);
        }

        void Reset() override
        {
            auto ignored = boost::system::error_code{};
            auto& socket = beast::get_lowest_layer(m_socket);
            socket.set_option(asio::socket_base::linger{true, 0}, ignored);
            socket.close(ignored);
        }

        asio::any_io_executor GetExecutor() override
        {
            return m_socket.get_executor();
        }

    private:
        TSocket& m_socket;
        TestServer& m_server;
    };

    class TcpSession : public ServerSession
    {
    public:
        TcpSession(Tcp::socket& socket, TestServer& server)
            : m_socket{socket}
            , m_server{server}
        {
        }

        asio::awaitable<void> Send(std::vector<u8> bytes) override
        {
            co_await asio::async_write(m_socket, asio::buffer(bytes), AS_TUPLE);
        }

        asio::awaitable<void> SendText(std::string text) override
        {
            assert(false && "TCP has no text messages");
            co_await Send({text.begin(), text.end()});
        }

        asio::awaitable<std::optional<std::vector<u8>>> Receive() override
        {
            auto bytes = std::vector<u8>(READ_SIZE);
            const auto [error, size] = co_await m_socket.async_read_some(asio::buffer(bytes), AS_TUPLE);
            if (error)
            {
                if (error == asio::error::eof)
                {
                    m_server.Record([](ServerRecord_s& record)
                    {
                        ++record.fins;
                    });
                }

                co_return std::nullopt;
            }

            bytes.resize(size);
            m_server.Record([&bytes](ServerRecord_s& record)
            {
                record.messages.push_back(bytes);
            });

            co_return bytes;
        }

        asio::awaitable<void> Close(u16) override
        {
            auto ignored = boost::system::error_code{};
            m_socket.shutdown(Tcp::socket::shutdown_send, ignored);
            co_return;
        }

        void Drop() override
        {
            auto ignored = boost::system::error_code{};
            m_socket.close(ignored);
        }

        void Reset() override
        {
            auto ignored = boost::system::error_code{};
            m_socket.set_option(asio::socket_base::linger{true, 0}, ignored);
            m_socket.close(ignored);
        }

        asio::any_io_executor GetExecutor() override
        {
            return m_socket.get_executor();
        }

    private:
        Tcp::socket& m_socket;
        TestServer& m_server;
    };

    ServerHandshake_s ReadHandshake(const http::request<http::string_body>& request)
    {
        auto handshake = ServerHandshake_s{
            .subprotocol = std::string{request[http::field::sec_websocket_protocol]},
            .host = std::string{request[http::field::host]},
        };

        if (request.find(http::field::origin) != request.end())
        {
            handshake.origin = std::string{request[http::field::origin]};
        }

        return handshake;
    }

    asio::ssl::context MakeTlsContext()
    {
        const auto& certificate = TestCertificate::Get();
        auto context = asio::ssl::context{asio::ssl::context::tls_server};
        context.use_certificate_chain(asio::buffer(certificate.certificatePem));
        context.use_private_key(asio::buffer(certificate.privateKeyPem), asio::ssl::context::pem);
        return context;
    }

    // The rest of a connection after TCP and TLS: the upgrade, then the script.
    template <typename TSocket>
    asio::awaitable<void> ServeWebSocket(TSocket& socket, TestServer& server, ServerMode_e mode, std::string serverName)
    {
        auto buffer = beast::flat_buffer{};
        auto request = http::request<http::string_body>{};
        const auto [readError, size] = co_await http::async_read(socket.next_layer(), buffer, request, AS_TUPLE);
        if (readError)
        {
            co_return;
        }

        auto handshake = ReadHandshake(request);
        handshake.serverName = std::move(serverName);
        server.Record([&handshake](ServerRecord_s& record)
        {
            record.handshakes.push_back(handshake);
        });

        if (mode == ServerMode_e::Reject)
        {
            auto response = http::response<http::string_body>{http::status::forbidden, request.version()};
            response.prepare_payload();
            co_await http::async_write(socket.next_layer(), response, AS_TUPLE);
            co_return;
        }

        socket.set_option(websocket::stream_base::decorator([](websocket::response_type& response)
        {
            response.set(http::field::sec_websocket_protocol, SUBPROTOCOL);
        }));

        const auto [acceptError] = co_await socket.async_accept(request, AS_TUPLE);
        if (acceptError)
        {
            co_return;
        }

        auto session = Session<TSocket>{socket, server};
        if (server.GetScript())
        {
            co_await server.GetScript()(session);
            co_return;
        }

        co_await session.ReceiveUntilClosed();
    }
}

asio::awaitable<void> ServerSession::Delay(std::chrono::milliseconds delay)
{
    auto timer = asio::steady_timer{GetExecutor(), delay};
    co_await timer.async_wait(AS_TUPLE);
}

asio::awaitable<void> ServerSession::ReceiveUntilClosed()
{
    while (co_await Receive())
    {
    }
}

asio::awaitable<void> ServerSession::Echo()
{
    while (auto message = co_await Receive())
    {
        co_await Send(std::move(*message));
    }
}

TestServer::TestServer(Script script, ServerMode_e mode, bool tls)
    : m_script{std::move(script)}
    , m_mode{mode}
    , m_acceptor{m_thread.GetContext(), Tcp::endpoint{asio::ip::make_address(LOOPBACK), 0}}
{
    m_port = m_acceptor.local_endpoint().port();
    assert(!(tls && mode == ServerMode_e::Tcp) && "TestServer has no TLS over raw TCP");
    if (tls)
    {
        m_tls.emplace(MakeTlsContext());
    }

    asio::co_spawn(m_thread.GetContext(), Accept(), asio::detached);
}

TestServer::~TestServer()
{
    m_thread.Stop();
}

u16 TestServer::FindClosedPort()
{
    auto io = asio::io_context{};
    auto acceptor = Tcp::acceptor{io, Tcp::endpoint{asio::ip::make_address(LOOPBACK), 0}};
    return acceptor.local_endpoint().port();
}

u16 TestServer::GetPort() const
{
    return m_port;
}

ServerRecord_s TestServer::GetRecord() const
{
    const auto lock = std::scoped_lock{m_mutex};
    return m_record;
}

bool TestServer::WaitFor(const std::function<bool(const ServerRecord_s&)>& condition, std::chrono::milliseconds timeout) const
{
    auto lock = std::unique_lock{m_mutex};
    return m_changed.wait_for(lock, timeout, [&]
    {
        return condition(m_record);
    });
}

void TestServer::Record(const std::function<void(ServerRecord_s&)>& change)
{
    {
        const auto lock = std::scoped_lock{m_mutex};
        change(m_record);
    }

    m_changed.notify_all();
}

const TestServer::Script& TestServer::GetScript() const
{
    return m_script;
}

asio::awaitable<void> TestServer::Accept()
{
    while (true)
    {
        auto [error, socket] = co_await m_acceptor.async_accept(AS_TUPLE);
        if (error)
        {
            co_return;
        }

        asio::co_spawn(m_acceptor.get_executor(), Serve(std::move(socket)), asio::detached);
    }
}

asio::awaitable<void> TestServer::Serve(Tcp::socket socket)
{
    Record([](ServerRecord_s& record)
    {
        ++record.accepted;
    });

    if (m_mode == ServerMode_e::Silent)
    {
        m_silent.push_back(std::move(socket));
        co_return;
    }

    if (m_mode == ServerMode_e::Tcp)
    {
        auto session = TcpSession{socket, *this};
        if (m_script)
        {
            co_await m_script(session);
        }
        else
        {
            co_await session.ReceiveUntilClosed();
        }
    }
    else if (m_tls)
    {
        auto secure = websocket::stream<asio::ssl::stream<Tcp::socket>>{std::move(socket), *m_tls};
        const auto [handshakeError] = co_await secure.next_layer().async_handshake(asio::ssl::stream_base::server, AS_TUPLE);
        if (!handshakeError)
        {
            const auto* const serverName = SSL_get_servername(secure.next_layer().native_handle(), TLSEXT_NAMETYPE_host_name);
            co_await ServeWebSocket(secure, *this, m_mode, serverName != nullptr ? serverName : "");
        }
    }
    else
    {
        auto plain = websocket::stream<Tcp::socket>{std::move(socket)};
        co_await ServeWebSocket(plain, *this, m_mode, "");
    }

    Record([](ServerRecord_s& record)
    {
        ++record.ended;
    });
}

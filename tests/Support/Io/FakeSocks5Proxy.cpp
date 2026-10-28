#include "pch.hpp"
#include "FakeSocks5Proxy.hpp"

#include "ServerThread.hpp"
#include "Io/Socks5Handshake.hpp"

#include <boost/asio/as_tuple.hpp>
#include <boost/asio/buffer.hpp>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/connect.hpp>
#include <boost/asio/detached.hpp>
#include <boost/asio/error.hpp>
#include <boost/asio/ip/address.hpp>
#include <boost/asio/read.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/write.hpp>

namespace
{
    namespace asio = boost::asio;
    using Tcp = asio::ip::tcp;

    constexpr auto LOOPBACK = "127.0.0.1";
    constexpr auto BOUND_NAME = "localhost"sv;
    constexpr auto IPV6_SIZE = std::size_t{16};
    constexpr auto RELAY_SIZE = std::size_t{4096};
    constexpr auto CONNECTION_REFUSED = u8{5};
    constexpr auto PASSWORD_REJECTED = u8{1};

    const auto AS_TUPLE = asio::as_tuple(asio::use_awaitable);

    struct RelayPair_s
    {
        Tcp::socket client;
        Tcp::socket target;
    };

    asio::awaitable<bool> ReadExactly(Tcp::socket& socket, std::span<u8> bytes)
    {
        const auto [error, size] = co_await asio::async_read(socket, asio::buffer(bytes), AS_TUPLE);
        co_return !error;
    }

    asio::awaitable<bool> ReadText(Tcp::socket& socket, std::string& text, std::size_t size)
    {
        text.resize(size);
        const auto [error, read] = co_await asio::async_read(socket, asio::buffer(text), AS_TUPLE);
        co_return !error;
    }

    asio::awaitable<bool> Write(Tcp::socket& socket, std::vector<u8> bytes)
    {
        const auto [error, size] = co_await asio::async_write(socket, asio::buffer(bytes), AS_TUPLE);
        co_return !error;
    }

    std::vector<u8> MakeFailureReply(u8 code)
    {
        return {Socks5Handshake::VERSION, code, 0, static_cast<u8>(Socks5AddressType_e::Ipv4), 0, 0, 0, 0, 0, 0};
    }

    std::vector<u8> MakeSuccessReply(Socks5AddressType_e type, u16 boundPort)
    {
        auto reply = std::vector<u8>{Socks5Handshake::VERSION, Socks5Handshake::SUCCEEDED, 0, static_cast<u8>(type)};
        switch (type)
        {
        case Socks5AddressType_e::Ipv4:
            reply.insert(reply.end(), {127, 0, 0, 1});
            break;
        case Socks5AddressType_e::DomainName:
            reply.push_back(static_cast<u8>(BOUND_NAME.size()));
            reply.insert(reply.end(), BOUND_NAME.begin(), BOUND_NAME.end());
            break;
        case Socks5AddressType_e::Ipv6:
            reply.insert(reply.end(), IPV6_SIZE, 0);
            break;
        }

        reply.push_back(static_cast<u8>(boundPort >> 8));
        reply.push_back(static_cast<u8>(boundPort & 0xFF));
        return reply;
    }

    // Copies one direction until it ends. A FIN is passed on as a FIN; anything else drops both sockets.
    asio::awaitable<void> Relay(std::shared_ptr<RelayPair_s> pair, Tcp::socket& from, Tcp::socket& to)
    {
        auto buffer = std::array<u8, RELAY_SIZE>{};
        auto ignored = boost::system::error_code{};
        while (true)
        {
            const auto [readError, size] = co_await from.async_read_some(asio::buffer(buffer), AS_TUPLE);
            if (readError == asio::error::eof)
            {
                to.shutdown(Tcp::socket::shutdown_send, ignored);
                co_return;
            }

            if (readError)
            {
                break;
            }

            const auto [writeError, written] = co_await asio::async_write(to, asio::buffer(buffer.data(), size), AS_TUPLE);
            if (writeError)
            {
                break;
            }
        }

        pair->client.close(ignored);
        pair->target.close(ignored);
    }
}

FakeSocks5Proxy::FakeSocks5Proxy()
    : m_acceptor{m_thread.GetContext(), Tcp::endpoint{asio::ip::make_address(LOOPBACK), 0}}
    , m_port{m_acceptor.local_endpoint().port()}
{
    asio::co_spawn(m_thread.GetContext(), Accept(), asio::detached);
}

FakeSocks5Proxy::~FakeSocks5Proxy()
{
    m_thread.Stop();
}

u16 FakeSocks5Proxy::GetPort() const
{
    return m_port;
}

ProxyRecord_s FakeSocks5Proxy::GetRecord() const
{
    const auto lock = std::scoped_lock{m_mutex};
    return m_record;
}

void FakeSocks5Proxy::SetCredentials(std::string username, std::string password)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_settings.credentials = Socks5Credentials_s{.username = std::move(username), .password = std::move(password)};
}

void FakeSocks5Proxy::SetReply(u8 code)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_settings.reply = code;
}

void FakeSocks5Proxy::SetBoundAddress(Socks5AddressType_e type)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_settings.boundAddress = type;
}

void FakeSocks5Proxy::SetStalled(bool stalled)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_settings.stalled = stalled;
}

void FakeSocks5Proxy::SetGreetingWithReply(std::vector<u8> bytes)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_settings.greeting = std::move(bytes);
}

void FakeSocks5Proxy::SetForwardPort(u16 port)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_settings.forwardPort = port;
}

asio::awaitable<void> FakeSocks5Proxy::Accept()
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

asio::awaitable<void> FakeSocks5Proxy::Serve(Tcp::socket client)
{
    auto settings = Settings_s{};
    {
        const auto lock = std::scoped_lock{m_mutex};
        ++m_record.accepted;
        settings = m_settings;
    }

    if (settings.stalled)
    {
        m_stalled.push_back(std::move(client));
        co_return;
    }

    const auto request = co_await Negotiate(client, settings);
    if (!request)
    {
        co_return;
    }

    const auto executor = client.get_executor();
    auto resolver = Tcp::resolver{executor};
    auto target = Tcp::socket{executor};
    auto [connectError, endpoints] = co_await resolver.async_resolve(Tcp::v4(), request->host, std::to_string(settings.forwardPort.value_or(request->port)), AS_TUPLE);
    if (!connectError)
    {
        const auto [error, endpoint] = co_await asio::async_connect(target, endpoints, AS_TUPLE);
        connectError = error;
    }

    if (connectError)
    {
        co_await Write(client, MakeFailureReply(CONNECTION_REFUSED));
        co_return;
    }

    auto reply = MakeSuccessReply(settings.boundAddress, m_port);
    reply.insert(reply.end(), settings.greeting.begin(), settings.greeting.end());
    if (!co_await Write(client, std::move(reply)))
    {
        co_return;
    }

    auto pair = std::make_shared<RelayPair_s>(std::move(client), std::move(target));
    asio::co_spawn(executor, Relay(pair, pair->target, pair->client), asio::detached);
    co_await Relay(pair, pair->client, pair->target);
}

asio::awaitable<std::optional<Socks5Request_s>> FakeSocks5Proxy::Negotiate(Tcp::socket& client, const Settings_s& settings)
{
    auto header = std::array<u8, 2>{};
    if (!co_await ReadExactly(client, header) || header[0] != Socks5Handshake::VERSION)
    {
        co_return std::nullopt;
    }

    auto methods = std::vector<u8>(header[1]);
    if (!co_await ReadExactly(client, methods))
    {
        co_return std::nullopt;
    }

    const auto wanted = settings.credentials ? Socks5Method_e::UsernamePassword : Socks5Method_e::NoAuthentication;
    if (std::ranges::find(methods, static_cast<u8>(wanted)) == methods.end())
    {
        co_await Write(client, {Socks5Handshake::VERSION, Socks5Handshake::NO_ACCEPTABLE_METHOD});
        co_return std::nullopt;
    }

    if (!co_await Write(client, {Socks5Handshake::VERSION, static_cast<u8>(wanted)}))
    {
        co_return std::nullopt;
    }

    if (settings.credentials)
    {
        auto sent = Socks5Credentials_s{};
        auto length = std::array<u8, 2>{};
        if (!co_await ReadExactly(client, length))
        {
            co_return std::nullopt;
        }

        if (!co_await ReadText(client, sent.username, length[1]))
        {
            co_return std::nullopt;
        }

        auto passwordLength = std::array<u8, 1>{};
        if (!co_await ReadExactly(client, passwordLength))
        {
            co_return std::nullopt;
        }

        if (!co_await ReadText(client, sent.password, passwordLength[0]))
        {
            co_return std::nullopt;
        }

        const auto accepted = sent.username == settings.credentials->username && sent.password == settings.credentials->password;
        Record([&sent](ProxyRecord_s& record)
        {
            record.credentials.push_back(sent);
        });

        if (!co_await Write(client, {Socks5Handshake::PASSWORD_VERSION, accepted ? Socks5Handshake::SUCCEEDED : PASSWORD_REJECTED}) || !accepted)
        {
            co_return std::nullopt;
        }
    }

    auto requestHeader = std::array<u8, Socks5Handshake::CONNECT_REPLY_SIZE>{};
    if (!co_await ReadExactly(client, requestHeader))
    {
        co_return std::nullopt;
    }

    auto request = Socks5Request_s{.type = static_cast<Socks5AddressType_e>(requestHeader[3])};
    if (request.type == Socks5AddressType_e::Ipv4)
    {
        auto address = std::array<u8, 4>{};
        if (!co_await ReadExactly(client, address))
        {
            co_return std::nullopt;
        }

        request.host = std::format("{}.{}.{}.{}", address[0], address[1], address[2], address[3]);
    }
    else if (request.type == Socks5AddressType_e::DomainName)
    {
        auto nameLength = std::array<u8, 1>{};
        if (!co_await ReadExactly(client, nameLength))
        {
            co_return std::nullopt;
        }

        if (!co_await ReadText(client, request.host, nameLength[0]))
        {
            co_return std::nullopt;
        }
    }
    else
    {
        co_return std::nullopt;
    }

    auto port = std::array<u8, 2>{};
    if (!co_await ReadExactly(client, port))
    {
        co_return std::nullopt;
    }

    request.port = static_cast<u16>((port[0] << 8) | port[1]);
    Record([&request](ProxyRecord_s& record)
    {
        record.requests.push_back(request);
    });

    if (settings.reply != Socks5Handshake::SUCCEEDED)
    {
        co_await Write(client, MakeFailureReply(settings.reply));
        co_return std::nullopt;
    }

    co_return request;
}

void FakeSocks5Proxy::Record(const std::function<void(ProxyRecord_s&)>& change)
{
    const auto lock = std::scoped_lock{m_mutex};
    change(m_record);
}

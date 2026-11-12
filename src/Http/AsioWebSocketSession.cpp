#include "pch.hpp"
#include "AsioWebSocketSession.hpp"

#include "../Application/Events/ApplicationEventBridge.hpp"

#include <boost/asio/steady_timer.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>

namespace asio = boost::asio;
namespace beast = boost::beast;
namespace websocket = beast::websocket;
using Tcp = asio::ip::tcp;

struct AsioWebSocketSession::State : std::enable_shared_from_this<State>
{
    websocket::stream<beast::tcp_stream> stream;
    beast::flat_buffer input{ApplicationEventBridge::MAX_MESSAGE_BYTES * 2};
    asio::steady_timer writeTimer;
    std::string handshake;
    std::shared_ptr<ApplicationEventBridge> bridge;
    u64 client = 0;
    std::size_t operations = 0;
    bool accepted = false;
    bool writing = false;
    bool closing = false;
    bool closed = false;
    bool stopping = false;
    u16 closeCode = 0;
    std::string closeReason;

    State(Tcp::socket socket, std::string header, std::shared_ptr<ApplicationEventBridge> events)
        : stream{std::move(socket)}
        , writeTimer{stream.get_executor()}
        , handshake{std::move(header)}
        , bridge{std::move(events)}
    {
        client = bridge->Connect();
    }

    template <class Callback>
    auto Track(Callback callback)
    {
        ++operations;
        return [self = shared_from_this(), callback = std::move(callback)](auto... args) mutable
        {
            --self->operations;
            callback(std::move(args)...);
        };
    }

    void Close()
    {
        if (closed)
        {
            return;
        }

        closed = true;
        bridge->Disconnect(client);
        writeTimer.cancel();

        auto error = boost::system::error_code{};
        auto& socket = beast::get_lowest_layer(stream).socket();
        socket.cancel(error);
        socket.shutdown(Tcp::socket::shutdown_both, error);
        socket.close(error);
    }

    void Start()
    {
        if (!client)
        {
            Close();
            return;
        }

        beast::get_lowest_layer(stream).expires_never();
        auto timeout = websocket::stream_base::timeout{};
        timeout.handshake_timeout = 10s;
        timeout.idle_timeout = 60s;
        timeout.keep_alive_pings = true;
        stream.set_option(timeout);
        stream.read_message_max(ApplicationEventBridge::MAX_MESSAGE_BYTES);
        stream.async_accept(asio::buffer(handshake), Track([self = shared_from_this()](boost::system::error_code error)
        {
            self->handshake.clear();
            if (error || self->closed)
            {
                self->Close();
                return;
            }

            self->accepted = true;
            self->Read();
            self->Service();
        }));
    }

    void Read()
    {
        if (closed || closing || closeCode != 0)
        {
            return;
        }

        stream.async_read(input, Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
        {
            if (error || self->closed)
            {
                self->Close();
                return;
            }

            if (!self->stream.got_text())
            {
                self->BeginClose(1003, "text messages required");
                return;
            }

            self->bridge->Enqueue(self->client, beast::buffers_to_string(self->input.data()));
            self->input.consume(self->input.size());
            self->Service();
            self->Read();
        }));
    }

    void BeginClose(u16 code, std::string_view reason)
    {
        if (closed || closing)
        {
            return;
        }

        closeCode = code;
        closeReason = reason;

        if (writing)
        {
            return;
        }

        closing = true;
        bridge->Disconnect(client);
        if (!accepted)
        {
            Close();
            return;
        }

        auto close = websocket::close_reason{};
        close.code = code;
        close.reason = reason;
        stream.async_close(close, Track([self = shared_from_this()](boost::system::error_code)
        {
            self->Close();
        }));
    }

    void Service()
    {
        if (closed || closing || !accepted || writing)
        {
            return;
        }

        if (closeCode != 0)
        {
            BeginClose(closeCode, closeReason);
            return;
        }

        if (stopping || bridge->IsClosing(client))
        {
            BeginClose(stopping || bridge->IsStopping() ? 1001 : 1013, stopping || bridge->IsStopping() ? "application stopping" : "event overflow");
            return;
        }

        auto text = bridge->Front(client);
        if (!text)
        {
            return;
        }

        writing = true;
        stream.text(true);
        writeTimer.expires_after(10s);
        writeTimer.async_wait(Track([self = shared_from_this()](boost::system::error_code error)
        {
            if (!error)
            {
                self->Close();
            }
        }));
        // The captured immutable frame owns its bytes even after bridge cleanup.
        const auto buffers = asio::buffer(*text);
        stream.async_write(buffers, Track([self = shared_from_this(), text = std::move(text)](boost::system::error_code error, std::size_t)
        {
            static_cast<void>(text);
            self->writeTimer.cancel();
            self->writing = false;

            if (error || self->closed)
            {
                self->Close();
                return;
            }

            self->bridge->Pop(self->client);
            self->Service();
        }));
    }
};

AsioWebSocketSession::AsioWebSocketSession(Tcp::socket socket, std::string handshake, std::shared_ptr<ApplicationEventBridge> bridge)
    : m_state{std::make_shared<State>(std::move(socket), std::move(handshake), std::move(bridge))}
{
}

AsioWebSocketSession::~AsioWebSocketSession()
{
    Close();
}

void AsioWebSocketSession::Start()
{
    m_state->Start();
}

void AsioWebSocketSession::Service()
{
    m_state->Service();
}

void AsioWebSocketSession::Stop()
{
    m_state->stopping = true;
    if (!m_state->accepted)
    {
        m_state->Close();
    }

    m_state->Service();
}

void AsioWebSocketSession::Close()
{
    m_state->Close();
}

bool AsioWebSocketSession::IsDrained() const
{
    return m_state->closed && m_state->operations == 0;
}

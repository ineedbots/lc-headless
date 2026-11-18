#include "pch.hpp"
#include "AsioHttpServer.hpp"

#include "Websockets/AsioWebSocketSession.hpp"
#include "Websockets/Events/ApplicationEventBridge.hpp"
#include "HttpRouter.hpp"
#include "OperatorListenerPolicy.hpp"
#include "AsioHttpSession.hpp"
#include "HttpSessionOwner.hpp"
#include "Type/HttpSessionContext_s.hpp"

#include <boost/asio/ip/tcp.hpp>

namespace asio = boost::asio;
using Tcp = asio::ip::tcp;

struct AsioHttpServer::State : HttpSessionOwner, std::enable_shared_from_this<State>
{
    Tcp::acceptor acceptor;
    HttpSessionContext_s context;
    std::vector<std::unique_ptr<AsioWebSocketSession>> webSockets;
    std::unordered_map<u64, std::shared_ptr<AsioHttpSession>> sessions;
    std::unordered_map<u64, std::weak_ptr<AsioHttpSession>> pending;
    std::size_t operations = 0;
    u64 nextSession = 0;
    u16 port;

    State(asio::io_context& io, HttpSettings_s options, std::shared_ptr<ApplicationRequestBridge> requests, HttpRouter routes, std::shared_ptr<ApplicationEventBridge> eventBridge)
        : acceptor{io}
        , context{std::move(options), std::move(routes), std::move(requests), std::move(eventBridge)}
    {
        const auto address = asio::ip::make_address(context.settings.host == "localhost" ? "127.0.0.1" : context.settings.host);
        const auto endpoint = Tcp::endpoint{address, static_cast<u16>(context.settings.port)};
        acceptor.open(endpoint.protocol());
        acceptor.bind(endpoint);
        acceptor.listen();
        port = acceptor.local_endpoint().port();
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

    const HttpSessionContext_s& GetContext() const override
    {
        return context;
    }

    void RegisterRequest(u64 request, u64 session) override
    {
        pending.emplace(request, sessions.at(session));
    }

    void RetireRequest(u64 request) override
    {
        pending.erase(request);
    }

    void RetireSession(u64 session) override
    {
        sessions.erase(session);
    }

    void UpgradeSession(u64 session, std::unique_ptr<AsioWebSocketSession> upgraded) override
    {
        sessions.erase(session);
        webSockets.push_back(std::move(upgraded));
        webSockets.back()->Start();
    }

    void StartOperation() override
    {
        ++operations;
    }

    void FinishOperation() override
    {
        assert(operations > 0);
        --operations;
    }

    void Accept();
    void Stop();
    void Close();
};

void AsioHttpServer::State::Accept()
{
    if (context.stopping)
    {
        return;
    }

    acceptor.async_accept(Track([self = shared_from_this()](boost::system::error_code error, Tcp::socket socket)
    {
        if (!error && !self->context.stopping && self->sessions.size() + self->webSockets.size() < OperatorListenerPolicy::MAX_CONNECTIONS)
        {
            auto session = std::make_shared<AsioHttpSession>(self, ++self->nextSession, std::move(socket));
            self->sessions.emplace(self->nextSession, session);
            session->Start();
        }

        if (!self->context.stopping)
        {
            self->Accept();
        }
    }));
}

void AsioHttpServer::State::Stop()
{
    if (context.stopping)
    {
        return;
    }

    context.stopping = true;
    context.shutdownDeadline = std::chrono::steady_clock::now() + OperatorListenerPolicy::SHUTDOWN_TIMEOUT;
    context.bridge->Close();

    if (context.events)
    {
        context.events->Stop();
    }

    for (const auto& session : webSockets)
    {
        session->Stop();
    }

    auto error = boost::system::error_code{};
    acceptor.cancel(error);
    acceptor.close(error);

    const auto copy = sessions;
    for (const auto& [key, session] : copy)
    {
        static_cast<void>(key);
        session->Stop();
    }
}

void AsioHttpServer::State::Close()
{
    Stop();

    for (const auto& session : webSockets)
    {
        session->Close();
    }

    const auto copy = sessions;
    for (const auto& [key, session] : copy)
    {
        static_cast<void>(key);
        session->Close();
    }
}

AsioHttpServer::AsioHttpServer(asio::io_context& io, const HttpSettings_s& settings, std::shared_ptr<ApplicationRequestBridge> bridge, HttpRouter routes, std::shared_ptr<ApplicationEventBridge> events)
    : m_state{std::make_shared<State>(io, settings, std::move(bridge), std::move(routes), std::move(events))}
{
    m_state->Accept();
}

AsioHttpServer::~AsioHttpServer()
{
    Close();
}

void AsioHttpServer::Stop()
{
    m_state->Stop();
}

void AsioHttpServer::Close()
{
    m_state->Close();
}

bool AsioHttpServer::IsDrained() const
{
    return m_state->sessions.empty() && m_state->operations == 0 && std::ranges::all_of(m_state->webSockets, [](const auto& session)
    {
        return session->IsDrained();
    });
}

u16 AsioHttpServer::GetPort() const
{
    return m_state->port;
}

void AsioHttpServer::Service()
{
    for (const auto& session : m_state->webSockets)
    {
        session->Service();
    }

    std::erase_if(m_state->webSockets, [](const auto& session)
    {
        return session->IsDrained();
    });

    const auto copy = m_state->sessions;
    for (const auto& [key, session] : copy)
    {
        static_cast<void>(key);
        session->Service();
    }
}

void AsioHttpServer::Deliver(std::vector<CompletedApplicationRequest_s> results)
{
    for (auto& result : results)
    {
        const auto it = m_state->pending.find(result.id);
        if (it == m_state->pending.end())
        {
            continue;
        }

        if (const auto session = it->second.lock())
        {
            session->Deliver(std::move(result));
        }
    }
}

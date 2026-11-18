#include "pch.hpp"
#include "AsioHttpSession.hpp"

#include "HttpResponses.hpp"
#include "OperatorListenerPolicy.hpp"
#include "HttpRouter.hpp"
#include "Type/HttpRouteMatch_s.hpp"
#include "Type/HttpResponse_s.hpp"
#include "Type/HttpSessionContext_s.hpp"
#include "Application/ApplicationRequestBridge.hpp"
#include "Application/Type/ApplicationRequest_s.hpp"
#include "Application/Type/CompletedApplicationRequest_s.hpp"
#include "Application/Type/RequestControl_s.hpp"
#include "Config/Type/HttpSettings_s.hpp"
#include "Console/CommandExecution.hpp"
#include "Websockets/AsioWebSocketSession.hpp"

#include <boost/asio/steady_timer.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/websocket.hpp>

namespace asio = boost::asio;
namespace beast = boost::beast;
namespace http = beast::http;
using Tcp = asio::ip::tcp;

AsioHttpSession::AsioHttpSession(std::shared_ptr<HttpSessionOwner> owner, u64 id, Tcp::socket socket)
    : m_owner{std::move(owner)}
    , m_id{id}
    , m_stream{std::move(socket)}
    , m_timer{m_stream.get_executor()}
{
    m_stream.socket().non_blocking(true);
}

void AsioHttpSession::Start()
{
    Read();
}

void AsioHttpSession::Stop()
{
    if (m_control || m_phase == Phase_e::Writing || m_interim)
    {
        return;
    }

    if (m_parser && m_parser->is_header_done())
    {
        Error(503, "stopping", "Application stopping", true);
    }
    else
    {
        Close();
    }
}

void AsioHttpSession::Close()
{
    if (m_phase == Phase_e::Closed)
    {
        return;
    }

    m_phase = Phase_e::Closed;
    m_timer.cancel();

    auto error = boost::system::error_code{};
    m_stream.socket().cancel(error);
    m_stream.socket().shutdown(Tcp::socket::shutdown_both, error);
    m_stream.socket().close(error);

    if (m_control)
    {
        m_owner->RetireRequest(m_control->id);
        m_owner->GetContext().bridge->Abandon(m_control->id);
        m_owner->GetContext().bridge->RetireHttp(m_control->id);
        m_control.reset();
    }

    m_owner->RetireSession(m_id);
}

void AsioHttpSession::Error(unsigned code, std::string error, std::string message, bool close)
{
    Respond(HttpResponses::Error(code, error, message, m_control ? std::optional{m_control->id} : std::nullopt, close));
}

void AsioHttpSession::Respond(HttpResponse_s reply)
{
    if (m_phase == Phase_e::Closed || m_phase == Phase_e::Writing)
    {
        return;
    }

    m_phase = Phase_e::Writing;
    m_timer.cancel();

    auto cancelError = boost::system::error_code{};
    m_stream.socket().cancel(cancelError);

    if (m_control)
    {
        m_owner->RetireRequest(m_control->id);
    }

    m_response.emplace(static_cast<http::status>(reply.status), 11);
    m_response->set(http::field::content_type, "application/json");
    m_response->set(http::field::cache_control, "no-store");

    if (!reply.allow.empty())
    {
        m_response->set(http::field::allow, reply.allow);
    }

    m_response->keep_alive(m_keepAlive && !reply.close && !m_owner->GetContext().stopping);
    m_response->body() = std::move(reply.body);
    m_response->prepare_payload();
    m_stream.expires_at(std::min(std::chrono::steady_clock::now() + OperatorListenerPolicy::HTTP_WRITE_TIMEOUT, m_owner->GetContext().shutdownDeadline));
    http::async_write(m_stream, *m_response, Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
    {
        if (self->m_phase == Phase_e::Closed)
        {
            return;
        }

        if (self->m_control)
        {
            self->m_owner->GetContext().bridge->RetireHttp(self->m_control->id);
            self->m_control.reset();
        }

        if (error || self->m_response->need_eof() || self->m_owner->GetContext().stopping)
        {
            self->Close();
            return;
        }

        self->m_response.reset();
        self->m_phase = Phase_e::Reading;
        self->Read();
    }));
}

bool AsioHttpSession::CheckRead(boost::system::error_code error)
{
    if (m_phase == Phase_e::Closed || m_phase == Phase_e::Writing)
    {
        return false;
    }

    if (!error)
    {
        return true;
    }

    if (error == http::error::body_limit)
    {
        Error(413, "body_too_large", "Request body exceeds limit", true);
    }
    else if (error == http::error::header_limit || error == http::error::buffer_overflow)
    {
        Error(431, "headers_too_large", "Request headers exceed limit", true);
    }
    else if (error == http::error::end_of_stream || error == asio::error::operation_aborted || error == beast::error::timeout)
    {
        Close();
    }
    else
    {
        Error(400, "malformed_http", "Malformed HTTP request", true);
    }

    return false;
}

void AsioHttpSession::Read()
{
    if (m_phase == Phase_e::Closed)
    {
        return;
    }

    if (m_owner->GetContext().stopping)
    {
        Close();
        return;
    }

    m_timedOut = false;
    m_route.reset();
    m_parser.emplace();
    m_parser->body_limit(static_cast<u64>(m_owner->GetContext().settings.maxRequestBodyBytes));
    m_parser->header_limit(OperatorListenerPolicy::MAX_HEADER_BYTES);
    m_stream.expires_after(OperatorListenerPolicy::HTTP_READ_TIMEOUT);
    http::async_read_header(m_stream, m_buffer, *m_parser, Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
    {
        if (!self->CheckRead(error))
        {
            return;
        }

        self->Headers();
    }));
}

void AsioHttpSession::Headers()
{
    const auto& request = m_parser->get();
    m_keepAlive = request.keep_alive();

    if (request.version() != 11)
    {
        Error(400, "http_version", "HTTP/1.1 required", true);
        return;
    }

    auto match = m_owner->GetContext().router.Match(request.method_string(), request.target(), request[http::field::content_type]);
    if (const auto error = std::get_if<HttpResponse_s>(&match))
    {
        Respond(std::move(*error));
        return;
    }

    m_route = std::get<HttpRouteMatch_s>(std::move(match));

    if (m_route->route.webSocket)
    {
        Upgrade();
        return;
    }

    if (m_owner->GetContext().stopping)
    {
        Error(503, "stopping", "Application stopping", true);
        return;
    }

    const auto expect = request[http::field::expect];
    if (!expect.empty())
    {
        if (!beast::iequals(expect, "100-continue"))
        {
            Error(417, "expectation_failed", "Unsupported expectation", true);
            return;
        }

        m_interim.emplace(http::status::continue_, 11);
        http::async_write(m_stream, *m_interim, Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
        {
            if (self->m_phase == Phase_e::Closed)
            {
                return;
            }

            if (error)
            {
                self->Close();
                return;
            }

            self->m_interim.reset();

            if (self->m_owner->GetContext().stopping)
            {
                self->Error(503, "stopping", "Application stopping", true);
                return;
            }

            self->Body();
        }));
        return;
    }

    Body();
}

void AsioHttpSession::Upgrade()
{
    if (!m_owner->GetContext().events)
    {
        Error(503, "events_unavailable", "Application event servicing is unavailable", true);
        return;
    }

    const auto& request = m_parser->get();
    if (m_owner->GetContext().stopping || !beast::websocket::is_upgrade(request) || request.method() != http::verb::get ||
        request.find(http::field::origin) != request.end() || !m_route->request.queryParameters.empty() ||
        request.chunked() || m_parser->content_length().value_or(0) != 0 || !request[http::field::expect].empty())
    {
        Error(400, "invalid_upgrade", "Native WebSocket upgrade without Origin, query or body required", true);
        return;
    }

    auto upgraded = std::make_unique<AsioWebSocketSession>(std::move(m_stream.socket()), std::move(m_parser->get()), beast::buffers_to_string(m_buffer.data()), m_owner->GetContext().events);
    m_phase = Phase_e::Closed;
    m_timer.cancel();
    m_owner->UpgradeSession(m_id, std::move(upgraded));
}

void AsioHttpSession::Body()
{
    http::async_read(m_stream, m_buffer, *m_parser, Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
    {
        if (!self->CheckRead(error))
        {
            return;
        }

        self->Admit();
    }));
}

void AsioHttpSession::Admit()
{
    const auto& request = m_parser->get();
    if (request.body().size() > static_cast<std::size_t>(m_owner->GetContext().settings.maxRequestBodyBytes))
    {
        Error(413, "body_too_large", "Request body exceeds limit", true);
        return;
    }

    assert(m_route);

    auto decoded = m_route->Decode(std::move(m_parser->get().body()));
    if (const auto error = std::get_if<HttpResponse_s>(&decoded))
    {
        Respond(std::move(*error));
        return;
    }

    auto payload = std::get<ApplicationRequestPayload>(std::move(decoded));
    m_control = m_owner->GetContext().bridge->Reserve();
    if (!m_control)
    {
        Error(503, "unavailable", "Application stopping or request capacity exhausted");
        return;
    }

    try
    {
        m_owner->RegisterRequest(m_control->id, m_id);
        m_owner->GetContext().bridge->Commit({m_control, std::move(payload)});
    }
    catch (...)
    {
        m_owner->GetContext().bridge->Complete({.id = m_control->id, .outcome = "failed", .errorCode = "admission_failed"});
        Close();
        throw;
    }

    m_phase = Phase_e::AwaitingResult;
    m_stream.expires_never();
    m_timer.expires_at(m_control->deadline);
    m_timer.async_wait(Track([self = shared_from_this(), id = m_control->id](boost::system::error_code error)
    {
        if (error || self->m_phase != Phase_e::AwaitingResult || !self->m_control)
        {
            return;
        }

        if (self->m_control->id != id)
        {
            return;
        }

        self->m_timedOut = true;
        self->m_owner->GetContext().bridge->Abandon(self->m_control->id);
    }));

    // Observe a disconnected client while its application request waits. Buffered pipeline bytes
    // remain untouched; their request is read only after this exchange has completed.
    m_stream.socket().async_wait(Tcp::socket::wait_read, Track([self = shared_from_this(), id = m_control->id](boost::system::error_code error)
    {
        if (error || self->m_phase != Phase_e::AwaitingResult || !self->m_control)
        {
            return;
        }

        if (self->m_control->id != id)
        {
            return;
        }

        auto probe = char{};
        auto ec = boost::system::error_code{};
        const auto count = self->m_stream.socket().receive(asio::buffer(&probe, 1), Tcp::socket::message_peek, ec);
        if (ec != asio::error::would_block && ec != asio::error::try_again && (count == 0 || ec))
        {
            self->Close();
        }
    }));
}

void AsioHttpSession::Timeout(const CompletedApplicationRequest_s* result)
{
    m_owner->GetContext().bridge->Abandon(m_control->id);
    Respond(HttpResponses::Timeout(m_control->id, m_control->execution && m_control->execution->started, result));
}

void AsioHttpSession::Service()
{
    if (!m_control || m_phase != Phase_e::AwaitingResult)
    {
        return;
    }

    if (m_timedOut || std::chrono::steady_clock::now() >= m_control->deadline)
    {
        Timeout();
    }
}

void AsioHttpSession::Deliver(CompletedApplicationRequest_s result)
{
    if (m_phase != Phase_e::AwaitingResult || !m_control || result.id != m_control->id)
    {
        return;
    }

    if (m_timedOut || std::chrono::steady_clock::now() >= m_control->deadline)
    {
        Timeout(&result);
        return;
    }

    if (m_route && m_route->route.respond)
    {
        if (auto encoded = m_route->route.respond(result))
        {
            Respond(std::move(*encoded));
            return;
        }
    }

    Respond(HttpResponses::Complete(result));
}

#include "pch.hpp"
#include "AsioHttpServer.hpp"
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/steady_timer.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include "HttpRouter.hpp"
#include "HttpResponses.hpp"

namespace asio = boost::asio;
namespace beast = boost::beast;
namespace http = beast::http;
using Tcp = asio::ip::tcp;

struct AsioHttpServer::State : std::enable_shared_from_this<State>
{
    struct Session;
    Tcp::acceptor acceptor;
    HttpSettings_s settings;
    HttpRouter router;
    std::shared_ptr<ApplicationRequestBridge> bridge;
    std::unordered_map<Session*, std::shared_ptr<Session>> sessions;
    std::unordered_map<u64, std::weak_ptr<Session>> pending;
    std::size_t operations = 0;
    bool stopping = false;
    u16 port;
    std::chrono::steady_clock::time_point shutdownDeadline = std::chrono::steady_clock::time_point::max();

    State(asio::io_context& io, HttpSettings_s options, std::shared_ptr<ApplicationRequestBridge> requests, HttpRouter routes)
        : acceptor{io}
        , settings{std::move(options)}
        , router{std::move(routes)}
        , bridge{std::move(requests)}
    {
        const auto address = asio::ip::make_address(settings.host == "localhost" ? "127.0.0.1" : settings.host);
        const auto endpoint = Tcp::endpoint{address, static_cast<u16>(settings.port)};
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

    void Accept();
    void Stop();
    void Close();
};

struct AsioHttpServer::State::Session : std::enable_shared_from_this<Session>
{
    std::shared_ptr<State> state;
    beast::tcp_stream stream;
    beast::flat_buffer buffer{16384};
    asio::steady_timer timer;
    std::optional<http::request_parser<http::string_body>> parser;
    std::optional<http::response<http::string_body>> response;
    std::optional<http::response<http::empty_body>> interim;
    std::shared_ptr<RequestControl_s> control;
    std::optional<HttpRouteMatch_s> route;
    bool closed = false;
    bool writing = false;
    bool keepAlive = false;
    bool timedOut = false;

    Session(std::shared_ptr<State> owner, Tcp::socket socket)
        : state{std::move(owner)}
        , stream{std::move(socket)}
        , timer{stream.get_executor()}
    {
        stream.socket().non_blocking(true);
    }

    void Close()
    {
        if (closed)
        {
            return;
        }

        closed = true;
        timer.cancel();

        auto error = boost::system::error_code{};
        stream.socket().cancel(error);
        stream.socket().shutdown(Tcp::socket::shutdown_both, error);
        stream.socket().close(error);

        if (control)
        {
            state->pending.erase(control->id);
            state->bridge->Abandon(control->id);
            state->bridge->RetireHttp(control->id);
            control.reset();
        }

        state->sessions.erase(this);
    }

    void Error(unsigned code, std::string error, std::string message, bool close = false)
    {
        Respond(HttpResponses::Error(code, error, message, control ? std::optional{control->id} : std::nullopt, close));
    }

    void Respond(HttpResponse_s reply)
    {
        if (closed || writing)
        {
            return;
        }

        writing = true;
        timer.cancel();

        auto cancelError = boost::system::error_code{};
        stream.socket().cancel(cancelError);

        if (control)
        {
            state->pending.erase(control->id);
        }

        response.emplace(static_cast<http::status>(reply.status), 11);
        response->set(http::field::content_type, "application/json");
        response->set(http::field::cache_control, "no-store");

        if (!reply.allow.empty())
        {
            response->set(http::field::allow, reply.allow);
        }

        response->keep_alive(keepAlive && !reply.close && !state->stopping);
        response->body() = std::move(reply.body);
        response->prepare_payload();
        stream.expires_at(std::min(std::chrono::steady_clock::now() + 5s, state->shutdownDeadline));
        http::async_write(stream, *response, state->Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
        {
            if (self->closed)
            {
                return;
            }

            if (self->control)
            {
                self->state->bridge->RetireHttp(self->control->id);
                self->control.reset();
            }

            if (error || self->response->need_eof() || self->state->stopping)
            {
                self->Close();
                return;
            }

            self->response.reset();
            self->writing = false;
            self->Read();
        }));
    }

    bool CheckRead(boost::system::error_code error)
    {
        if (closed || writing)
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

    void Read()
    {
        if (closed)
        {
            return;
        }

        if (state->stopping)
        {
            Close();
            return;
        }

        timedOut = false;
        route.reset();
        parser.emplace();
        parser->body_limit(static_cast<u64>(state->settings.maxRequestBodyBytes));
        parser->header_limit(16384);
        stream.expires_after(10s);
        http::async_read_header(stream, buffer, *parser, state->Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
        {
            if (!self->CheckRead(error))
            {
                return;
            }

            self->Headers();
        }));
    }

    void Headers()
    {
        const auto& request = parser->get();
        keepAlive = request.keep_alive();

        if (request.version() != 11)
        {
            Error(400, "http_version", "HTTP/1.1 required", true);
            return;
        }

        auto match = state->router.Match(request.method_string(), request.target(), request[http::field::content_type]);
        if (const auto error = std::get_if<HttpResponse_s>(&match))
        {
            Respond(std::move(*error));
            return;
        }

        route = std::get<HttpRouteMatch_s>(std::move(match));

        if (state->stopping)
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

            interim.emplace(http::status::continue_, 11);
            http::async_write(stream, *interim, state->Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
            {
                if (self->closed)
                {
                    return;
                }

                if (error)
                {
                    self->Close();
                    return;
                }

                self->interim.reset();

                if (self->state->stopping)
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

    void Body()
    {
        http::async_read(stream, buffer, *parser, state->Track([self = shared_from_this()](boost::system::error_code error, std::size_t)
        {
            if (!self->CheckRead(error))
            {
                return;
            }

            self->Admit();
        }));
    }

    void Admit()
    {
        const auto& request = parser->get();
        if (request.body().size() > static_cast<std::size_t>(state->settings.maxRequestBodyBytes))
        {
            Error(413, "body_too_large", "Request body exceeds limit", true);
            return;
        }

        assert(route);

        auto decoded = route->Decode(std::move(parser->get().body()));
        if (const auto error = std::get_if<HttpResponse_s>(&decoded))
        {
            Respond(std::move(*error));
            return;
        }

        auto payload = std::get<ApplicationRequestPayload>(std::move(decoded));
        control = state->bridge->Reserve();
        if (!control)
        {
            Error(503, "unavailable", "Application stopping or request capacity exhausted");
            return;
        }

        try
        {
            state->pending.emplace(control->id, weak_from_this());
            state->bridge->Commit({control, std::move(payload)});
        }
        catch (...)
        {
            state->bridge->Complete({.id = control->id, .outcome = "failed", .errorCode = "admission_failed"});
            Close();
            throw;
        }

        stream.expires_never();
        timer.expires_at(control->deadline);
        timer.async_wait(state->Track([self = shared_from_this(), id = control->id](boost::system::error_code error)
        {
            if (error || self->closed || !self->control || self->writing)
            {
                return;
            }

            if (self->control->id != id)
            {
                return;
            }

            self->timedOut = true;
            self->state->bridge->Abandon(self->control->id);
        }));
        // Observe a disconnected client while its application request waits. Buffered pipeline bytes
        // remain untouched; their request is read only after this exchange has completed.
        stream.socket().async_wait(Tcp::socket::wait_read, state->Track([self = shared_from_this(), id = control->id](boost::system::error_code error)
        {
            if (error || self->closed || !self->control || self->writing)
            {
                return;
            }

            if (self->control->id != id)
            {
                return;
            }

            auto probe = char{};
            auto ec = boost::system::error_code{};
            const auto count = self->stream.socket().receive(asio::buffer(&probe, 1), Tcp::socket::message_peek, ec);
            if (ec != asio::error::would_block && ec != asio::error::try_again && (count == 0 || ec))
            {
                self->Close();
            }
        }));
    }

    void Timeout(const CompletedApplicationRequest_s* result = nullptr)
    {
        state->bridge->Abandon(control->id);
        Respond(HttpResponses::Timeout(control->id, control->execution && control->execution->started, result));
    }

    void Service()
    {
        if (!control || closed || writing)
        {
            return;
        }

        if (timedOut || std::chrono::steady_clock::now() >= control->deadline)
        {
            Timeout();
        }
    }

    void Deliver(CompletedApplicationRequest_s result)
    {
        if (closed || writing || !control || result.id != control->id)
        {
            return;
        }

        if (timedOut || std::chrono::steady_clock::now() >= control->deadline)
        {
            Timeout(&result);
            return;
        }

        Respond(HttpResponses::Complete(result));
    }
};

void AsioHttpServer::State::Accept()
{
    if (stopping)
    {
        return;
    }

    acceptor.async_accept(Track([self = shared_from_this()](boost::system::error_code error, Tcp::socket socket)
    {
        if (!error && !self->stopping && self->sessions.size() < 128)
        {
            auto session = std::make_shared<Session>(self, std::move(socket));
            self->sessions.emplace(session.get(), session);
            session->Read();
        }

        if (!self->stopping)
        {
            self->Accept();
        }
    }));
}

void AsioHttpServer::State::Stop()
{
    if (stopping)
    {
        return;
    }

    stopping = true;
    shutdownDeadline = std::chrono::steady_clock::now() + 2s;
    bridge->Close();

    auto error = boost::system::error_code{};
    acceptor.cancel(error);
    acceptor.close(error);

    const auto copy = sessions;
    for (const auto& [key, session] : copy)
    {
        static_cast<void>(key);

        if (!session->control && !session->writing && !session->interim)
        {
            if (session->parser && session->parser->is_header_done())
            {
                session->Error(503, "stopping", "Application stopping", true);
            }
            else
            {
                session->Close();
            }
        }
    }
}

void AsioHttpServer::State::Close()
{
    Stop();

    const auto copy = sessions;
    for (const auto& [key, session] : copy)
    {
        static_cast<void>(key);
        session->Close();
    }
}

AsioHttpServer::AsioHttpServer(asio::io_context& io, const HttpSettings_s& settings, std::shared_ptr<ApplicationRequestBridge> bridge, HttpRouter routes)
    : m_state{std::make_shared<State>(io, settings, std::move(bridge), std::move(routes))}
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
    return m_state->sessions.empty() && m_state->operations == 0;
}

u16 AsioHttpServer::GetPort() const
{
    return m_state->port;
}

void AsioHttpServer::Service()
{
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

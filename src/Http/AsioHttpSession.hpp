#pragma once

#include "HttpSessionOwner.hpp"
#include "OperatorListenerPolicy.hpp"
#include "Type/HttpRouteMatch_s.hpp"
#include "Type/HttpResponse_s.hpp"
#include "Application/Requests/Type/CompletedApplicationRequest_s.hpp"
#include "Application/Requests/Type/RequestControl_s.hpp"

#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/steady_timer.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>

class AsioHttpSession : public std::enable_shared_from_this<AsioHttpSession>
{
public:
    AsioHttpSession(std::shared_ptr<HttpSessionOwner> owner, u64 id, boost::asio::ip::tcp::socket socket);

    void Start();
    void Stop();
    void Close();
    void Service();
    void Deliver(CompletedApplicationRequest_s result);

private:
    template <typename TCallback>
    auto Track(TCallback callback)
    {
        m_owner->StartOperation();
        return [self = shared_from_this(), callback = std::move(callback)](auto... args) mutable
        {
            self->m_owner->FinishOperation();
            callback(std::move(args)...);
        };
    }

    void Error(unsigned code, std::string error, std::string message, bool close = false);
    void Respond(HttpResponse_s reply);
    bool CheckRead(boost::system::error_code error);
    void Read();
    void Headers();
    void Upgrade();
    void Body();
    void Admit();
    void Timeout(const CompletedApplicationRequest_s* result = nullptr);

    std::shared_ptr<HttpSessionOwner> m_owner;
    u64 m_id;
    boost::beast::tcp_stream m_stream;
    boost::beast::flat_buffer m_buffer{OperatorListenerPolicy::MAX_BUFFERED_BYTES};
    boost::asio::steady_timer m_timer;
    std::optional<boost::beast::http::request_parser<boost::beast::http::string_body>> m_parser;
    std::optional<boost::beast::http::response<boost::beast::http::string_body>> m_response;
    std::optional<boost::beast::http::response<boost::beast::http::empty_body>> m_interim;
    std::shared_ptr<RequestControl_s> m_control;
    std::optional<HttpRouteMatch_s> m_route;
    enum class Phase_e
    {
        Reading,
        AwaitingResult,
        Writing,
        Closed,
    };

    Phase_e m_phase = Phase_e::Reading;
    bool m_keepAlive = false;
    bool m_timedOut = false;
};

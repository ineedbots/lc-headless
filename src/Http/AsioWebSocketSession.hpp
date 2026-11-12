#pragma once

#include "../Application/Events/ApplicationEventBridge.hpp"

#include <boost/asio/ip/tcp.hpp>
#include <boost/beast/http.hpp>

class AsioWebSocketSession
{
public:
    AsioWebSocketSession(boost::asio::ip::tcp::socket socket, boost::beast::http::request<boost::beast::http::string_body> request, std::string buffered, std::shared_ptr<ApplicationEventBridge> bridge);
    ~AsioWebSocketSession();
    void Start();
    void Service();
    void Stop();
    void Close();
    bool IsDrained() const;

private:
    struct State;
    std::shared_ptr<State> m_state;
};

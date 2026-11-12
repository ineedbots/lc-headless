#pragma once
#include "HttpServer.hpp"
#include "HttpRouter.hpp"
#include <boost/asio/io_context.hpp>

class AsioHttpServer : public HttpServer
{
public:
    AsioHttpServer(boost::asio::io_context& io, const HttpSettings_s& settings, std::shared_ptr<ApplicationRequestBridge> bridge, HttpRouter routes = {});
    ~AsioHttpServer() override;
    void Deliver(std::vector<CompletedApplicationRequest_s> results) override;
    void Service() override;
    void Stop() override;
    void Close() override;
    bool IsDrained() const override;
    u16 GetPort() const override;

private:
    struct State;
    std::shared_ptr<State> m_state;
};

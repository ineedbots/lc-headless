#include "pch.hpp"
#include "NetLoop.hpp"

#include "AsioNetLoop.hpp"

std::shared_ptr<NetLoop> NetLoop::Create()
{
    return std::make_shared<AsioNetLoop>();
}

std::unique_ptr<HttpServer> NetLoop::ListenHttp(const HttpSettings_s&, std::shared_ptr<ApplicationRequestBridge>)
{
    throw std::runtime_error{"HTTP is unavailable on this loop"};
}

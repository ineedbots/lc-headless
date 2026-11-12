#include "pch.hpp"
#include "NetLoop.hpp"

#include "AsioNetLoop.hpp"
#include "../Application/Events/ApplicationEventBridge.hpp"

std::shared_ptr<NetLoop> NetLoop::Create()
{
    return std::make_shared<AsioNetLoop>();
}

std::unique_ptr<HttpServer> NetLoop::ListenHttp(const HttpSettings_s&, std::shared_ptr<ApplicationRequestBridge>, std::shared_ptr<ApplicationEventBridge>)
{
    throw std::runtime_error{"HTTP is unavailable on this loop"};
}

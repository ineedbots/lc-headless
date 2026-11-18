#pragma once

#include "Application/ApplicationRequestBridge.hpp"
#include "Config/Type/HttpSettings_s.hpp"
#include "Http/HttpRouter.hpp"
#include "Websockets/Events/ApplicationEventBridge.hpp"

// The listener updates shutdown state; sessions only read this shared context.
struct HttpSessionContext_s
{
    HttpSettings_s settings;
    HttpRouter router;
    std::shared_ptr<ApplicationRequestBridge> bridge;
    std::shared_ptr<ApplicationEventBridge> events;
    bool stopping = false;
    std::chrono::steady_clock::time_point shutdownDeadline = std::chrono::steady_clock::time_point::max();
};

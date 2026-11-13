#pragma once

#include "ApplicationEvents_s.hpp"

struct ApplicationEvent_s
{
    std::optional<std::string> account;
    ApplicationEventPayload payload;
    std::chrono::system_clock::time_point timestamp = std::chrono::system_clock::now();
};

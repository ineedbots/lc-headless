#pragma once

#include "Application/Requests/Type/CompletedApplicationRequest_s.hpp"
#include "Application/Requests/Type/RequestControl_s.hpp"

class ConsoleCommandCompletion
{
public:
    ConsoleCommandCompletion() = delete;

    static std::optional<CompletedApplicationRequest_s> TryComplete(RequestControl_s& control, bool stopping);
};

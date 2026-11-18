#pragma once

#include "../Type/GetApplicationStatus_s.hpp"
#include "../Type/ApplicationStatus_s.hpp"
#include "../Type/RequestControl_s.hpp"
#include "../Type/ApplicationRequestContext_s.hpp"

class ApplicationStatusOperation
{
public:
    ApplicationStatusOperation() = delete;
    using Payload = GetApplicationStatus_s;
    using Result = ApplicationStatus_s;
    // A missing result leaves completion with RequestControl_s::execution.
    static std::optional<Result> Execute(const ApplicationRequestContext_s& context, const std::shared_ptr<RequestControl_s>& control, const Payload& request);
};

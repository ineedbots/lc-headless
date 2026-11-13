#pragma once

#include "ApplicationOperations_s.hpp"
#include "RequestControl_s.hpp"

struct ApplicationRequest_s
{
    std::shared_ptr<RequestControl_s> control;
    ApplicationRequestPayload payload;
};

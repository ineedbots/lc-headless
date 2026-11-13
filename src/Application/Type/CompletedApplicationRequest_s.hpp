#pragma once

#include "ApplicationOperations_s.hpp"

struct CompletedApplicationRequest_s
{
    u64 id;
    std::string outcome = "completed";
    std::string errorCode;
    ApplicationOperations_s::Result payload;
};

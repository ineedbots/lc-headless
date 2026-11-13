#pragma once

#include "../../Accounts/AccountControl.hpp"

struct ApplicationRequestContext_s
{
    AccountControl& runner;
    std::chrono::steady_clock::time_point started;
    std::size_t maxOutputBytes;
};

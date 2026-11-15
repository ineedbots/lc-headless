#pragma once

#include <nlohmann/json.hpp>

struct HttpError_s
{
    std::string code;
    std::string message;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(HttpError_s, code, message)

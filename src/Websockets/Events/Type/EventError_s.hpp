#pragma once

#include <nlohmann/json.hpp>

struct EventError_s
{
    s32 version = 1;
    std::string type = "error";
    std::optional<std::string> id;
    std::string code;
};

inline void to_json(nlohmann::json& value, const EventError_s& error)
{
    value = {{"version", error.version}, {"type", error.type}, {"id", error.id ? nlohmann::json(*error.id) : nlohmann::json(nullptr)}, {"code", error.code}};
}

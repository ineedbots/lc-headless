#pragma once

#include <nlohmann/json.hpp>

struct PublishedScriptEvent_s
{
    std::string name;
    std::string dataJson;
};

void to_json(nlohmann::json& value, const PublishedScriptEvent_s& event);

#include "pch.hpp"
#include "AccountProgressEvent.hpp"

#include "../../../Accounts/Type/ProgressReport_s.hpp"
#include "../EventPayloadJson.hpp"

#include <nlohmann/json.hpp>

std::optional<std::size_t> AccountProgressEvent::Measure(const ProgressReport_s& payload)
{
    if (payload.rows.size() > 64)
    {
        return {};
    }

    auto total = std::size_t{0};
    for (const auto& [name, value] : payload.rows)
    {
        if (name.size() > 4096 - total || value.size() > 4096 - total - name.size())
        {
            return {};
        }

        total += name.size() + value.size();
    }

    return total + payload.rows.size() * sizeof(std::pair<std::string, std::string>) + sizeof(ProgressReport_s);
}

nlohmann::json AccountProgressEvent::Serialize(const ProgressReport_s& payload)
{
    return payload;
}

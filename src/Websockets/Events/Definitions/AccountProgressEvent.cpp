#include "pch.hpp"
#include "AccountProgressEvent.hpp"

#include "Accounts/Reporting/Type/ProgressReport_s.hpp"

#include <nlohmann/json.hpp>

std::optional<std::size_t> AccountProgressEvent::ValidateAndMeasureOwnedBytes(const ProgressReport_s& payload)
{
    if (payload.rows.size() > MAX_ROWS)
    {
        return {};
    }

    auto total = std::size_t{0};
    for (const auto& [name, value] : payload.rows)
    {
        if (name.size() > MAX_TOTAL_ROW_TEXT_BYTES - total || value.size() > MAX_TOTAL_ROW_TEXT_BYTES - total - name.size())
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

#include "pch.hpp"
#include "AccountIdleSummaryEvent.hpp"

#include "Accounts/Reporting/Type/IdleSummaryNpc_s.hpp"
#include "Accounts/Reporting/Type/IdleSummary_s.hpp"

#include <nlohmann/json.hpp>

std::optional<std::size_t> AccountIdleSummaryEvent::ValidateAndMeasureOwnedBytes(const IdleSummary_s& payload)
{
    if (payload.nearestNpcs.size() > IdleSummary_s::MAX_NEAREST_NPCS)
    {
        return {};
    }

    return sizeof(IdleSummary_s) + payload.nearestNpcs.size() * sizeof(IdleSummaryNpc_s);
}

nlohmann::json AccountIdleSummaryEvent::Serialize(const IdleSummary_s& payload)
{
    return payload;
}

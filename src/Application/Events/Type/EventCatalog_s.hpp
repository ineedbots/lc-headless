#pragma once

#include "../../../Utils/Type/TypeCatalog_s.hpp"
#include "../EventLimits.hpp"
#include "EventScope_e.hpp"

template <typename... Events>
struct EventCatalog_s : TypeCatalog_s<Events...>
{
    static constexpr std::array NAMES = {Events::NAME...};
    static constexpr std::size_t RETAINED_BYTES_PER_ACCOUNT = (std::size_t{0} + ... + (Events::RETAINS_LATEST && Events::SCOPE == EventScope_e::Account ? Events::MAX_SERIALIZED_BYTES + 1 : 0));

    static constexpr std::size_t RETAINED_GLOBAL_BYTES = (std::size_t{0} + ... + (Events::RETAINS_LATEST && Events::SCOPE == EventScope_e::Global ? Events::MAX_SERIALIZED_BYTES + 1 : 0));

    static constexpr bool IsValid()
    {
        for (std::size_t i = 0; i < NAMES.size(); ++i)
        {
            if (NAMES[i].empty() || NAMES[i].size() > EventLimits::MAX_FILTER_NAME_BYTES)
            {
                return false;
            }

            for (const auto c : NAMES[i])
            {
                if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-'))
                {
                    return false;
                }
            }

            for (std::size_t j = 0; j < i; ++j)
            {
                if (NAMES[i] == NAMES[j])
                {
                    return false;
                }
            }
        }

        return ((Events::MAX_SERIALIZED_BYTES > 0 && Events::MAX_SERIALIZED_BYTES <= EventLimits::MAX_EVENT_BYTES && (Events::SCOPE == EventScope_e::Account || Events::SCOPE == EventScope_e::Global)) && ...);
    }

    static constexpr bool FitsSnapshot(std::size_t accounts, std::size_t outboxBytes = EventLimits::MAX_OUTBOX_BYTES)
    {
        if (outboxBytes < EventLimits::SNAPSHOT_OVERHEAD_BYTES || RETAINED_GLOBAL_BYTES > outboxBytes - EventLimits::SNAPSHOT_OVERHEAD_BYTES)
        {
            return false;
        }

        const auto available = outboxBytes - EventLimits::SNAPSHOT_OVERHEAD_BYTES - RETAINED_GLOBAL_BYTES;
        return RETAINED_BYTES_PER_ACCOUNT == 0 || accounts <= available / RETAINED_BYTES_PER_ACCOUNT;
    }

    static bool IsKnown(std::string_view name)
    {
        return std::ranges::find(NAMES, name) != NAMES.end();
    }
};

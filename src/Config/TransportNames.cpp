#include "pch.hpp"
#include "TransportNames.hpp"

#include "Transport_e.hpp"

namespace
{
    struct TransportName_s
    {
        Transport_e transport;
        std::string_view name;
    };

    constexpr auto NAMES = std::array{
        TransportName_s{Transport_e::Ws, "ws"},
        TransportName_s{Transport_e::Wss, "wss"},
    };
}

std::optional<Transport_e> TransportNames::Find(std::string_view name)
{
    const auto entry = std::ranges::find(NAMES, name, &TransportName_s::name);
    if (entry == NAMES.end())
    {
        return std::nullopt;
    }

    return entry->transport;
}

std::string_view TransportNames::GetName(Transport_e transport)
{
    const auto entry = std::ranges::find(NAMES, transport, &TransportName_s::transport);
    assert(entry != NAMES.end() && "Transport_e value missing from TransportNames");
    return entry->name;
}

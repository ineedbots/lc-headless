#pragma once

#include "Transport_e.hpp"

// The names client.jsonc uses for server.transport, and the log's connect line.
class TransportNames
{
public:
    static constexpr auto CHOICES = "ws or wss"sv;

    TransportNames() = delete;

    // Exactly as written, in lowercase.
    [[nodiscard]] static std::optional<Transport_e> Find(std::string_view name);
    [[nodiscard]] static std::string_view GetName(Transport_e transport);
};

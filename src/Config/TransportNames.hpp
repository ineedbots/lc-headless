#pragma once

#include "Type/Transport_e.hpp"

#include <nlohmann/json.hpp>

// The names client.jsonc uses for server.transport, and the log's connect line.
class TransportNames
{
public:
    static constexpr auto CHOICES = "ws, wss or tcp"sv;

    TransportNames() = delete;

    // Exactly as written, in lowercase.
    [[nodiscard]] static std::optional<Transport_e> Find(std::string_view name);
    [[nodiscard]] static std::string_view GetName(Transport_e transport);
};

namespace nlohmann
{
    // Reject unknown names instead of silently selecting the first enum value.
    template <>
    struct adl_serializer<Transport_e>
    {
        static void from_json(const json& value, Transport_e& result)
        {
            const auto transport = TransportNames::Find(value.get<std::string>());
            if (!transport)
            {
                throw json::type_error::create(302, std::format("must be {}", TransportNames::CHOICES), &value);
            }

            result = *transport;
        }

        static void to_json(ordered_json& value, Transport_e transport)
        {
            value = std::string{TransportNames::GetName(transport)};
        }
    };
}

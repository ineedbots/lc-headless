#pragma once

#include <nlohmann/json.hpp>

namespace nlohmann
{
    template <>
    struct adl_serializer<std::chrono::seconds>
    {
        static void from_json(const json& value, std::chrono::seconds& result)
        {
            result = std::chrono::seconds{value.get<s64>()};
        }

        static void to_json(ordered_json& value, std::chrono::seconds source)
        {
            value = source.count();
        }
    };

    template <>
    struct adl_serializer<std::chrono::minutes>
    {
        static void from_json(const json& value, std::chrono::minutes& result)
        {
            result = std::chrono::minutes{value.get<s64>()};
        }

        static void to_json(ordered_json& value, std::chrono::minutes source)
        {
            value = source.count();
        }
    };

    template <>
    struct adl_serializer<std::chrono::milliseconds>
    {
        static void from_json(const json& value, std::chrono::milliseconds& result)
        {
            result = std::chrono::milliseconds{value.get<s64>()};
        }

        static void to_json(ordered_json& value, std::chrono::milliseconds source)
        {
            value = source.count();
        }
    };
}

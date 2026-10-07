#pragma once

class Base37
{
public:
    static constexpr std::size_t MAX_LENGTH = 12;
    static constexpr auto INVALID_NAME = "invalid_name"sv;

    Base37() = delete;

    [[nodiscard]] static u64 Encode(std::string_view name);
    [[nodiscard]] static std::string Decode(u64 value);
    [[nodiscard]] static std::string ToDisplayName(std::string_view rawName);
    [[nodiscard]] static std::string DecodeDisplayName(u64 value);
};

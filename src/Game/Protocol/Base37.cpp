#include "pch.hpp"
#include "Base37.hpp"

namespace
{
    constexpr auto RADIX = u64{37};
    constexpr auto ALPHABET = "_abcdefghijklmnopqrstuvwxyz0123456789"sv;
    constexpr auto WHITESPACE = " \t\n\v\f\r"sv;
    constexpr auto FIRST_DIGIT_CODE = u64{27};

    constexpr auto LIMIT = []
    {
        auto limit = u64{1};
        for (std::size_t i = 0; i < Base37::MAX_LENGTH; ++i)
        {
            limit *= RADIX;
        }

        return limit;
    }();

    std::string_view Trim(std::string_view text)
    {
        const auto first = text.find_first_not_of(WHITESPACE);
        if (first == std::string_view::npos)
        {
            return {};
        }

        const auto last = text.find_last_not_of(WHITESPACE);
        return text.substr(first, last - first + 1);
    }

    u64 GetCode(char character)
    {
        if (character >= 'a' && character <= 'z')
        {
            return static_cast<u64>(character - 'a') + 1;
        }

        if (character >= 'A' && character <= 'Z')
        {
            return static_cast<u64>(character - 'A') + 1;
        }

        if (character >= '0' && character <= '9')
        {
            return static_cast<u64>(character - '0') + FIRST_DIGIT_CODE;
        }

        return 0;
    }

    bool IsLowercase(char character)
    {
        return character >= 'a' && character <= 'z';
    }

    char ToUppercase(char character)
    {
        return static_cast<char>(character - 'a' + 'A');
    }
}

u64 Base37::Encode(std::string_view name)
{
    const auto trimmed = Trim(name).substr(0, MAX_LENGTH);
    auto value = u64{0};
    for (const auto character : trimmed)
    {
        value = value * RADIX + GetCode(character);
    }

    while (value != 0 && value % RADIX == 0)
    {
        value /= RADIX;
    }

    return value;
}

std::string Base37::Decode(u64 value)
{
    if (value >= LIMIT || value % RADIX == 0)
    {
        return std::string{INVALID_NAME};
    }

    auto name = std::string{};
    while (value != 0)
    {
        name.push_back(ALPHABET[value % RADIX]);
        value /= RADIX;
    }

    std::ranges::reverse(name);
    return name;
}

std::string Base37::ToDisplayName(std::string_view rawName)
{
    auto name = std::string{rawName};
    for (std::size_t i = 0; i < name.size(); ++i)
    {
        if (name[i] != '_')
        {
            continue;
        }

        name[i] = ' ';
        if (i + 1 < name.size() && IsLowercase(name[i + 1]))
        {
            name[i + 1] = ToUppercase(name[i + 1]);
        }
    }

    if (!name.empty() && IsLowercase(name[0]))
    {
        name[0] = ToUppercase(name[0]);
    }

    return name;
}

std::string Base37::DecodeDisplayName(u64 value)
{
    return ToDisplayName(Decode(value));
}

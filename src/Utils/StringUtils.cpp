#include "pch.hpp"
#include "StringUtils.hpp"

namespace
{
    constexpr auto FIRST_PRINTABLE = '\x20';
    constexpr auto LAST_PRINTABLE = '\x7E';
}

char StringUtils::ToLowerChar(char character)
{
    if (character >= 'A' && character <= 'Z')
    {
        return static_cast<char>(character - 'A' + 'a');
    }

    return character;
}

std::string StringUtils::ToLower(std::string_view text)
{
    auto lower = std::string{text};
    std::ranges::transform(lower, lower.begin(), ToLowerChar);
    return lower;
}

bool StringUtils::EqualsIgnoringCase(std::string_view left, std::string_view right)
{
    return std::ranges::equal(left, right, [](char a, char b)
    {
        return ToLowerChar(a) == ToLowerChar(b);
    });
}

std::string_view StringUtils::Trim(std::string_view text, std::string_view characters)
{
    const auto first = text.find_first_not_of(characters);
    if (first == std::string_view::npos)
    {
        return {};
    }

    return TrimEnd(text.substr(first), characters);
}

std::string_view StringUtils::TrimEnd(std::string_view text, std::string_view characters)
{
    return text.substr(0, text.find_last_not_of(characters) + 1);
}

std::string StringUtils::TrimTrailingNewlines(std::string text)
{
    text.resize(TrimEnd(text, "\r\n").size());

    return text;
}

std::pair<std::string_view, std::string_view> StringUtils::SplitFirstWord(std::string_view text)
{
    text = Trim(text);

    const auto end = text.find_first_of(WHITESPACE);
    if (end == std::string_view::npos)
    {
        return {text, {}};
    }

    return {text.substr(0, end), Trim(text.substr(end))};
}

std::vector<std::string_view> StringUtils::SplitWords(std::string_view text)
{
    auto words = std::vector<std::string_view>{};
    while (true)
    {
        const auto [word, rest] = SplitFirstWord(text);
        if (word.empty())
        {
            return words;
        }

        words.push_back(word);
        text = rest;
    }
}

std::string StringUtils::Join(std::span<const std::string> parts, std::string_view separator)
{
    auto text = std::string{};
    for (auto i = std::size_t{0}; i < parts.size(); ++i)
    {
        if (i > 0)
        {
            text += separator;
        }

        text += parts[i];
    }

    return text;
}

bool StringUtils::IsPrintableAscii(std::string_view text)
{
    return std::ranges::all_of(text, [](char character)
    {
        return character >= FIRST_PRINTABLE && character <= LAST_PRINTABLE;
    });
}

int StringUtils::HexDigitValue(unsigned char value)
{
    if (value >= '0' && value <= '9')
    {
        return value - '0';
    }

    if (value >= 'a' && value <= 'f')
    {
        return value - 'a' + 10;
    }

    if (value >= 'A' && value <= 'F')
    {
        return value - 'A' + 10;
    }

    return -1;
}

bool StringUtils::IsUtf8(std::string_view text)
{
    for (std::size_t i = 0; i < text.size();)
    {
        const auto first = static_cast<unsigned char>(text[i++]);
        if (first < 0x80)
        {
            continue;
        }

        auto remaining = 0;
        auto code = u32{0};
        auto minimum = u32{0};
        if (first >= 0xc2 && first <= 0xdf)
        {
            remaining = 1;
            code = first & 0x1f;
            minimum = 0x80;
        }
        else if (first >= 0xe0 && first <= 0xef)
        {
            remaining = 2;
            code = first & 0x0f;
            minimum = 0x800;
        }
        else if (first >= 0xf0 && first <= 0xf4)
        {
            remaining = 3;
            code = first & 0x07;
            minimum = 0x10000;
        }
        else
        {
            return false;
        }

        for (auto n = 0; n < remaining; ++n)
        {
            if (i == text.size())
            {
                return false;
            }

            const auto next = static_cast<unsigned char>(text[i++]);
            if ((next & 0xc0) != 0x80)
            {
                return false;
            }

            code = (code << 6) | (next & 0x3f);
        }

        if (code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff))
        {
            return false;
        }
    }

    return true;
}

bool StringUtils::IsIdentifierAscii(std::string_view name)
{
    const auto letter = [](unsigned char c)
    {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
    };
    return !name.empty() && letter(static_cast<unsigned char>(name.front())) &&
        std::ranges::all_of(name, [&](unsigned char c)
    {
        return letter(c) || (c >= '0' && c <= '9');
    });
}

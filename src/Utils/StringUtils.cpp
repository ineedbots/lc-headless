#include "pch.hpp"
#include "StringUtils.hpp"

namespace
{
    constexpr auto FIRST_PRINTABLE = '\x20';
    constexpr auto LAST_PRINTABLE = '\x7E';

    char ToLowerChar(char character)
    {
        return static_cast<char>(std::tolower(static_cast<unsigned char>(character)));
    }
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

std::string_view StringUtils::Trim(std::string_view text)
{
    const auto first = text.find_first_not_of(WHITESPACE);
    if (first == std::string_view::npos)
    {
        return {};
    }

    const auto last = text.find_last_not_of(WHITESPACE);
    return text.substr(first, last - first + 1);
}

std::string StringUtils::TrimTrailingNewlines(std::string text)
{
    while (!text.empty() && (text.back() == '\n' || text.back() == '\r'))
    {
        text.pop_back();
    }

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

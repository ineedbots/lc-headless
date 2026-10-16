#include "pch.hpp"
#include "ConsoleCommandParser.hpp"

#include "../Utils/StringUtils.hpp"
#include "ConsoleCommand_s.hpp"

std::optional<ConsoleLine_s> ConsoleCommandParser::Parse(std::string_view line)
{
    auto rest = StringUtils::Trim(line);
    if (rest.empty())
    {
        return std::nullopt;
    }

    auto parsed = ConsoleLine_s{};
    if (rest.front() == TARGET_PREFIX)
    {
        const auto [target, after] = StringUtils::SplitFirstWord(rest.substr(1));
        parsed.target = std::string{target};
        rest = after;
    }

    const auto [name, text] = StringUtils::SplitFirstWord(rest);
    const auto words = StringUtils::SplitWords(text);
    parsed.command = ConsoleCommand_s{.name = StringUtils::ToLower(name), .text = std::string{text}, .args = {words.begin(), words.end()}};
    return parsed;
}

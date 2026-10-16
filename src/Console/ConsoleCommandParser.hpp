#pragma once

#include "ConsoleCommand_s.hpp"

struct ConsoleLine_s
{
    // Without the prefix; nullopt when the line wasn't sent to one account.
    std::optional<std::string> target;
    // Its name is empty when the line held only the target.
    ConsoleCommand_s command;
};

// "[@target] name args...": the name is lower-cased, and the text after it trimmed and split into words.
class ConsoleCommandParser
{
public:
    static constexpr auto TARGET_PREFIX = '@';

    ConsoleCommandParser() = delete;

    // Nullopt for a blank line.
    [[nodiscard]] static std::optional<ConsoleLine_s> Parse(std::string_view line);
};

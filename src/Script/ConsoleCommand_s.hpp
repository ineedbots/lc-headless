#pragma once

// The command's name is lower-cased.
struct ConsoleCommand_s
{
    std::string name;
    // Trimmed.
    std::string text;
    // text split at whitespace.
    std::vector<std::string> args;
};

// As help lists it.
struct ScriptCommand_s
{
    std::string name;
    // Empty when the script gave none.
    std::string help;
};

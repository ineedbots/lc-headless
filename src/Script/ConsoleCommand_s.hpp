#pragma once

// A console line for a script: the command's name, lower-cased, and what followed it.
struct ConsoleCommand_s
{
    std::string name;
    // The rest of the line, trimmed.
    std::string text;
    // text split at whitespace.
    std::vector<std::string> args;
};

// A command a script has added, as help lists it.
struct ScriptCommand_s
{
    std::string name;
    // Empty when the script gave none.
    std::string help;
};

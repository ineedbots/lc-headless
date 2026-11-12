#pragma once

// A console command a script added, as help lists it.
struct ScriptCommand_s
{
    std::string name;
    // Empty when the script gave none.
    std::string help;
};

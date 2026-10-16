#pragma once

#include "ServerSettings_s.hpp"

struct AccountSettings_s
{
    std::string username;
    std::string password;
};

struct ScriptConfig_s
{
    std::string file;
    // A define_bot script reads only the object under its name, so one file can keep the settings of several.
    std::string settings = "{}";
    // Zero turns reports off.
    std::chrono::minutes progressReportMinutes{0};
};

// One account file. A server section replaces client.jsonc's for this account.
struct AccountConfig_s
{
    std::string name;
    // Where a define_bot script's default settings are added; empty for one made in code.
    std::filesystem::path file;
    AccountSettings_s credentials;
    bool enabled = true;
    std::optional<ServerSettings_s> server;
    std::optional<ScriptConfig_s> script;
    // Zero idles until interrupted.
    std::chrono::seconds idleSeconds{0};
    bool randomEvents = true;
    // Zero turns the stall guard off.
    std::chrono::minutes stallMinutes{10};
    // Turns run back on once energy reaches runEnergyMin, as rs2b0t's run manager does.
    bool runAuto = true;
    s32 runEnergyMin = 20;
};

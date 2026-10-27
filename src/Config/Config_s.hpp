#pragma once

#include "../Console/LogLevel_e.hpp"
#include "../Utils/BigUInt.hpp"
#include "ProxySettings_s.hpp"
#include "Revision_e.hpp"
#include "ServerSettings_s.hpp"

struct LoginSettings_s
{
    static constexpr auto SUPPORTED_REVISIONS = std::to_array({Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289});

    BigUInt rsaModulus;
    BigUInt rsaExponent;
    bool lowMemory = false;
    Revision_e revision = Revision_e::Rev289;
};

struct ClientSettings_s
{
    LogLevel_e logLevel = LogLevel_e::Info;
    std::string cacheDirectory = "data/cache";
    // rs2b0t's walker data, exported by tools/nav/export_rs2b0t.ts.
    std::string navDirectory = "data/nav";
    // Empty for no file.
    std::string logFile;
};

struct ScriptingSettings_s
{
    std::string accountsDirectory = "accounts";
    std::string scriptsDirectory = "scripts";
    std::chrono::milliseconds callTimeoutMs = 1000ms;
    std::chrono::milliseconds pollIntervalMs = 10ms;
    std::chrono::seconds loginIntervalSeconds = 2s;
    std::chrono::seconds killGraceSeconds = 30s;
    // Per login or reconnect; the waits between them double from 2 s up to 30 s.
    s32 connectAttempts = 10;
    std::chrono::seconds reloginDelaySeconds = 60s;
    std::string progressDirectory = "progress";
    // Where each account's skill experience is logged: experience/<account>.jsonl, one sample per line.
    // Empty, or an interval of 0, turns it off.
    std::string experienceDirectory = "experience";
    std::chrono::minutes experienceIntervalMinutes = 1min;
    // Where a bank's contents are written when one opens: bank/<account>.jsonl and .json. Empty turns it off.
    std::string bankLogDirectory = "bank";
    // Where an account's backpack is written when it changes: inventory/<account>.jsonl. Empty turns it off.
    std::string inventoryDirectory = "inventory";
    // The least time between two lines; 0 records every change.
    std::chrono::seconds inventoryIntervalSeconds = 5s;
    // Where an account's worn equipment is written when it changes: equipment/<account>.jsonl. Empty turns it off.
    std::string equipmentDirectory = "equipment";
};

// client.jsonc.
struct Config_s
{
    ServerSettings_s server;
    ProxySettings_s proxy;
    LoginSettings_s login;
    ClientSettings_s client;
    ScriptingSettings_s scripting;
};

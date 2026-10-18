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

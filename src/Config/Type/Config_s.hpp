#pragma once

#include "../../Console/LogLevelNames.hpp"
#include "../../Utils/BigUInt.hpp"
#include "ConfigDurationJson.hpp"
#include "ProxySettings_s.hpp"
#include "HttpSettings_s.hpp"
#include "Revision_e.hpp"
#include "ServerSettings_s.hpp"

#include <nlohmann/json.hpp>

struct LoginSettings_s
{
    static constexpr auto SUPPORTED_REVISIONS = std::to_array({Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289});

    BigUInt rsaModulus;
    BigUInt rsaExponent;
    bool lowMemory = false;
    Revision_e revision = Revision_e::Rev289;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(LoginSettings_s, rsaModulus, rsaExponent, lowMemory, revision)

struct ClientSettings_s
{
    LogLevel_e logLevel = LogLevel_e::Info;
    std::string cacheDirectory = "data/cache";
    // rs2b0t's walker data, exported by tools/nav/export_rs2b0t.ts.
    std::string navDirectory = "data/nav";
    // Empty for no file.
    std::string logFile;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ClientSettings_s, logLevel, cacheDirectory, navDirectory, logFile)

struct ScriptingSettings_s
{
    static constexpr auto MAX_CONNECT_ATTEMPTS = 100;

    std::string accountsDirectory = "accounts";
    std::string scriptsDirectory = "scripts";
    std::chrono::milliseconds callTimeoutMs = 1000ms;
    std::chrono::milliseconds pollIntervalMs = 10ms;
    std::chrono::seconds loginIntervalSeconds = 2s;
    std::chrono::seconds killGraceSeconds = 30s;
    // Per login or reconnect; 0 disables retries and reconnects, MAX_CONNECT_ATTEMPTS retries forever.
    // The waits between attempts double from minRetryDelaySeconds up to maxRetryDelaySeconds.
    s32 connectAttempts = 10;
    std::chrono::seconds minRetryDelaySeconds = 2s;
    std::chrono::seconds maxRetryDelaySeconds = 30s;
    std::chrono::seconds reloginDelaySeconds = 60s;
    std::string progressDirectory = "progress";
    std::string fleetDatabasePath = "data/fleet.sqlite";
    bool accountDataLogEnabled = true;
    bool experienceLogEnabled = true;
    bool bankLogEnabled = true;
    bool inventoryLogEnabled = true;
    bool equipmentLogEnabled = true;
    std::chrono::minutes experienceIntervalMinutes = 1min;
    // The least time between two lines; 0 records every change.
    std::chrono::seconds inventoryIntervalSeconds = 5s;
    std::chrono::seconds accountDataIntervalSeconds = 5s;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ScriptingSettings_s, accountsDirectory, scriptsDirectory, callTimeoutMs, pollIntervalMs, loginIntervalSeconds, killGraceSeconds, connectAttempts, minRetryDelaySeconds, maxRetryDelaySeconds, reloginDelaySeconds, progressDirectory, fleetDatabasePath, accountDataLogEnabled, experienceLogEnabled, bankLogEnabled, inventoryLogEnabled, equipmentLogEnabled, experienceIntervalMinutes, inventoryIntervalSeconds, accountDataIntervalSeconds)

// client.jsonc.
struct Config_s
{
    ServerSettings_s server;
    ProxySettings_s proxy;
    LoginSettings_s login;
    ClientSettings_s client;
    ScriptingSettings_s scripting;
    HttpSettings_s http;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Config_s, server, proxy, login, client, scripting, http)

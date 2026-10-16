#pragma once

#include "../Console/LogLevel_e.hpp"
#include "../Console/Logger.hpp"
#include "../Utils/BigUInt.hpp"

struct ServerSettings_s
{
    std::string url;
    std::string origin;
    std::string tlsCaFile = "SYSTEM";
};

struct AccountSettings_s
{
    std::string username;
    std::string password;
};

struct LoginSettings_s
{
    static constexpr u16 SUPPORTED_REVISION = 289;

    BigUInt rsaModulus;
    BigUInt rsaExponent;
    bool lowMemory = false;
    u16 revision = SUPPORTED_REVISION;
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

struct Config_s
{
    ServerSettings_s server;
    LoginSettings_s login;
    ClientSettings_s client;
    ScriptingSettings_s scripting;
};

struct ScriptConfig_s
{
    std::string file;
    // A define_bot script reads only the object under its name, so one file can keep the settings of several.
    std::string settings = "{}";
    // Zero turns reports off.
    std::chrono::minutes progressReportMinutes{0};
};

// A server section replaces client.jsonc's for this account.
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

class ConfigFile
{
public:
    static constexpr auto DEFAULT_PATH = "client.jsonc";
    static constexpr auto ACCOUNT_EXTENSION = ".jsonc";

    ConfigFile() = delete;

    [[nodiscard]] static Config_s Load(const std::filesystem::path& path, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static Config_s Parse(std::string_view text, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static std::string Serialize(const Config_s& config);

    // The account's name is the file's name without its extension.
    [[nodiscard]] static AccountConfig_s LoadAccount(const std::filesystem::path& path);
    [[nodiscard]] static AccountConfig_s ParseAccount(std::string_view text, std::string name);
    // Keeps the file's comments and layout, and rewrites it only when a key is added.
    [[nodiscard]] static std::vector<std::string> AddScriptSettings(const std::filesystem::path& path, std::string_view botName, std::string_view settingsJson);
};

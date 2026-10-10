#pragma once

#include "BigUInt.hpp"
#include "Logger.hpp"

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
    std::chrono::seconds idleSeconds = 5s;
    std::string cacheDirectory = "cache";
    // rs2b0t's walker data, exported by tools/nav/export_rs2b0t.ts.
    std::string navDirectory = "data/nav";
};

struct ScriptingSettings_s
{
    std::string accountsDirectory = "accounts";
    std::string scriptsDirectory = "scripts";
    std::chrono::milliseconds callTimeoutMs = 1000ms;
    std::chrono::milliseconds pollIntervalMs = 10ms;
    std::chrono::seconds loginIntervalSeconds = 2s;
    std::chrono::seconds killGraceSeconds = 30s;
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
    // The settings object as JSON text; the script reads it as its settings global.
    std::string settings = "{}";
    // How often on_progress_report is called; zero turns reports off.
    std::chrono::minutes progressReportMinutes{0};
};

// One account file. Without a script, the account logs in and idles. A server section replaces
// client.jsonc's for this account, to log it into another world.
struct AccountConfig_s
{
    std::string name;
    AccountSettings_s credentials;
    bool enabled = true;
    std::optional<ServerSettings_s> server;
    std::optional<ScriptConfig_s> script;
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
};

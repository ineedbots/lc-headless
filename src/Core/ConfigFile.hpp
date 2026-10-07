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
    static constexpr std::size_t CRC_COUNT = 9;
    static constexpr u16 SUPPORTED_REVISION = 289;

    std::array<s32, CRC_COUNT> crcs{};
    BigUInt rsaModulus;
    BigUInt rsaExponent;
    bool lowMemory = false;
    u16 revision = SUPPORTED_REVISION;
};

struct ClientSettings_s
{
    u16 logoutComponent = 2458;
    LogLevel_e logLevel = LogLevel_e::Info;
    std::chrono::seconds idleSeconds = 5s;
};

struct Config_s
{
    ServerSettings_s server;
    AccountSettings_s account;
    LoginSettings_s login;
    ClientSettings_s client;
};

class ConfigFile
{
public:
    static constexpr auto DEFAULT_PATH = "client.jsonc";

    ConfigFile() = delete;

    [[nodiscard]] static Config_s Load(const std::filesystem::path& path, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static Config_s Parse(std::string_view text, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static std::string Serialize(const Config_s& config);
};

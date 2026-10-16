#pragma once

#include "../Console/Logger.hpp"
#include "Config_s.hpp"

// client.jsonc.
class ConfigFile
{
public:
    static constexpr auto DEFAULT_PATH = "client.jsonc";

    ConfigFile() = delete;

    [[nodiscard]] static Config_s Load(const std::filesystem::path& path, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static Config_s Parse(std::string_view text, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static std::string Serialize(const Config_s& config);
};

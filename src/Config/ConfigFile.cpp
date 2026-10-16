#include "pch.hpp"
#include "ConfigFile.hpp"

#include "../Console/Logger.hpp"
#include "../Utils/FileUtils.hpp"
#include "ConfigJson.hpp"
#include "ConfigValidator.hpp"
#include "Config_s.hpp"
#include "Error/ConfigError.hpp"

Config_s ConfigFile::Load(const std::filesystem::path& path, Logger& logger)
{
    if (!std::filesystem::exists(path))
    {
        throw ConfigError{std::format("{}: not found; copy client.jsonc.sample there and fill it in", path.string())};
    }

    const auto text = FileUtils::ReadText(path);
    if (!text)
    {
        throw ConfigError{std::format("Failed to read config file {}", path.string())};
    }

    try
    {
        return Parse(*text, logger);
    }
    catch (const ConfigError& e)
    {
        throw ConfigError{std::format("{}: {}", path.string(), e.what())};
    }
}

Config_s ConfigFile::Parse(std::string_view text, Logger& logger)
{
    auto config = ConfigJson::ParseConfig(text);
    ConfigValidator::Validate(config);
    ConfigValidator::Warn(config, logger);
    return config;
}

std::string ConfigFile::Serialize(const Config_s& config)
{
    return ConfigJson::SerializeConfig(config);
}

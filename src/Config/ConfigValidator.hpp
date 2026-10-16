#pragma once

#include "../Console/Logger.hpp"
#include "AccountConfig_s.hpp"
#include "Config_s.hpp"

// The rules a config must keep; each one broken throws a ConfigError naming the key.
class ConfigValidator
{
public:
    ConfigValidator() = delete;

    static void Validate(const Config_s& config);
    static void ValidateAccount(const AccountConfig_s& account);
    // What's allowed but probably a mistake.
    static void Warn(const Config_s& config, Logger& logger);
};

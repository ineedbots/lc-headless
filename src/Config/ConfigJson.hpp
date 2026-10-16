#pragma once

#include "AccountConfig_s.hpp"
#include "Config_s.hpp"

// The only place that reads or writes the config as JSON. Errors are ConfigErrors that name the key and never
// quote the text, which can hold the password.
class ConfigJson
{
public:
    ConfigJson() = delete;

    [[nodiscard]] static Config_s ParseConfig(std::string_view text);
    // Without its name or file, which come from the file's path.
    [[nodiscard]] static AccountConfig_s ParseAccount(std::string_view text);
    [[nodiscard]] static std::string SerializeConfig(const Config_s& config);
    // For the parser's error, which says where the text is wrong.
    static void CheckObject(std::string_view text);
};

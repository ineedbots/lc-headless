#pragma once

#include "AccountConfig_s.hpp"
#include "Config_s.hpp"

class ConfigOverrides
{
public:
    ConfigOverrides() = delete;

    // client.jsonc's config with the account's own sections in place of its; the same config when the account
    // replaces nothing.
    [[nodiscard]] static std::shared_ptr<const Config_s> ForAccount(std::shared_ptr<const Config_s> config, const AccountConfig_s& account);
};

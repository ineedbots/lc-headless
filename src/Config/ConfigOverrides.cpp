#include "pch.hpp"
#include "ConfigOverrides.hpp"

#include "AccountConfig_s.hpp"
#include "Config_s.hpp"

std::shared_ptr<const Config_s> ConfigOverrides::ForAccount(std::shared_ptr<const Config_s> config, const AccountConfig_s& account)
{
    if (!account.server)
    {
        return config;
    }

    auto own = *config;
    own.server = *account.server;
    return std::make_shared<const Config_s>(std::move(own));
}

#include "pch.hpp"
#include "ConfigOverrides.hpp"

#include "Type/AccountConfig_s.hpp"
#include "Type/Config_s.hpp"

std::shared_ptr<const Config_s> ConfigOverrides::ForAccount(std::shared_ptr<const Config_s> config, const AccountConfig_s& account)
{
    if (!account.server && !account.proxy)
    {
        return config;
    }

    auto own = *config;
    if (account.server)
    {
        own.server = *account.server;
    }

    if (account.proxy)
    {
        own.proxy = *account.proxy;
    }

    return std::make_shared<const Config_s>(std::move(own));
}

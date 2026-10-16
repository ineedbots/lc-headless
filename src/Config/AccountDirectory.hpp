#pragma once

#include "AccountConfig_s.hpp"

// The accounts folder.
class AccountDirectory
{
public:
    AccountDirectory() = delete;

    // Every enabled account file in the folder, in name order. Throws a ConfigError when none is enabled, or
    // when two share a username: the server lets a username log in once, so the second would only be kicked.
    [[nodiscard]] static std::vector<AccountConfig_s> LoadEnabled(const std::filesystem::path& directory);
};

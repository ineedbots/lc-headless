#include "pch.hpp"
#include "AccountDirectory.hpp"

#include "../Utils/StringUtils.hpp"
#include "AccountConfig_s.hpp"
#include "AccountFile.hpp"
#include "Error/ConfigError.hpp"

namespace
{
    std::vector<std::filesystem::path> FindAccountFiles(const std::filesystem::path& directory)
    {
        auto files = std::vector<std::filesystem::path>{};
        for (const auto& entry : std::filesystem::directory_iterator{directory})
        {
            if (entry.is_regular_file() && entry.path().extension() == AccountFile::EXTENSION)
            {
                files.push_back(entry.path());
            }
        }

        std::ranges::sort(files);
        return files;
    }

    void CheckUsernamesAreUnique(const std::vector<AccountConfig_s>& accounts)
    {
        for (auto i = std::size_t{0}; i < accounts.size(); ++i)
        {
            for (auto j = i + 1; j < accounts.size(); ++j)
            {
                if (StringUtils::EqualsIgnoringCase(accounts[i].credentials.username, accounts[j].credentials.username))
                {
                    throw ConfigError{std::format("Accounts {} and {} have the same username", accounts[i].name, accounts[j].name)};
                }
            }
        }
    }
}

std::vector<AccountConfig_s> AccountDirectory::LoadEnabled(const std::filesystem::path& directory)
{
    auto enabled = std::vector<AccountConfig_s>{};
    for (const auto& file : FindAccountFiles(directory))
    {
        auto account = AccountFile::Load(file);
        if (account.enabled)
        {
            enabled.push_back(std::move(account));
        }
    }

    if (enabled.empty())
    {
        throw ConfigError{std::format("{}: no enabled account files", directory.string())};
    }

    CheckUsernamesAreUnique(enabled);
    return enabled;
}

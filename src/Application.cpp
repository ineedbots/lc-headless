#include "pch.hpp"
#include "Application.hpp"

#include "Accounts/AccountRunner.hpp"
#include "Core/ConfigError.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Script/ScriptRuntime.hpp"

namespace
{
    std::atomic<u32> interruptCount{0};

    void SignalHandler(int signalNum)
    {
        if (signalNum == SIGINT)
        {
            ++interruptCount;
        }
    }

    std::vector<std::filesystem::path> FindAccountFiles(const std::filesystem::path& directory)
    {
        if (!std::filesystem::is_directory(directory))
        {
            throw ConfigError{std::format("{}: no accounts folder; add one file per account (see accounts/example.jsonc.sample), or pass {} <file>", directory.string(), Application::ACCOUNT_OPTION)};
        }

        auto files = std::vector<std::filesystem::path>{};
        for (const auto& entry : std::filesystem::directory_iterator{directory})
        {
            if (entry.is_regular_file() && entry.path().extension() == ConfigFile::ACCOUNT_EXTENSION)
            {
                files.push_back(entry.path());
            }
        }

        std::ranges::sort(files);
        return files;
    }

    std::string ToLower(std::string_view text)
    {
        auto lower = std::string{text};
        std::ranges::transform(lower, lower.begin(), [](char character)
        {
            return static_cast<char>(std::tolower(static_cast<unsigned char>(character)));
        });

        return lower;
    }

    // The server lets a username log in once, so a second file for the same one would only be kicked.
    void CheckUsernamesAreUnique(const std::vector<AccountConfig_s>& accounts)
    {
        for (std::size_t i = 0; i < accounts.size(); ++i)
        {
            for (std::size_t j = i + 1; j < accounts.size(); ++j)
            {
                if (ToLower(accounts[i].credentials.username) == ToLower(accounts[j].credentials.username))
                {
                    throw ConfigError{std::format("Accounts {} and {} have the same username", accounts[i].name, accounts[j].name)};
                }
            }
        }
    }
}

Application::Application(const std::filesystem::path& configPath, std::optional<std::filesystem::path> accountPath, std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
    , m_accountPath{std::move(accountPath)}
{
    assert(m_logger && "Application needs a logger");
    m_config = std::make_shared<const Config_s>(ConfigFile::Load(configPath, *m_logger));
    m_logger->SetLevel(m_config->client.logLevel);
    m_logger->Info("Config loaded from {}", configPath.string());
}

int Application::Run()
{
    std::signal(SIGINT, SignalHandler);

    auto runtime = ScriptRuntime{};
    auto runner = AccountRunner{m_config, LoadAccounts(), runtime, m_logger};
    const auto succeeded = runner.Run([]
    {
        return interruptCount.load();
    });

    return succeeded ? EXIT_SUCCESS : EXIT_FAILURE;
}

std::vector<AccountConfig_s> Application::LoadAccounts() const
{
    if (m_accountPath)
    {
        auto accounts = std::vector<AccountConfig_s>{};
        accounts.push_back(ConfigFile::LoadAccount(*m_accountPath));
        return accounts;
    }

    const auto directory = std::filesystem::path{m_config->scripting.accountsDirectory};
    auto enabled = std::vector<AccountConfig_s>{};
    for (const auto& file : FindAccountFiles(directory))
    {
        auto account = ConfigFile::LoadAccount(file);
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

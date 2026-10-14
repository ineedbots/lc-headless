#include "pch.hpp"
#include "Application.hpp"

#include "Accounts/Account.hpp"
#include "Accounts/AccountRunner.hpp"
#include "Cache/CacheLoader.hpp"
#include "Cache/GameCache_s.hpp"
#include "Core/ConfigError.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/ConsoleInput.hpp"
#include "Core/LogFile.hpp"
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

    // Log lines go through the console while the scope lasts. On the way out, even by an exception, the
    // prompt is erased, the terminal put back and the sink installed again without the console.
    class ConsoleLogScope
    {
    public:
        using Install = std::function<void(std::shared_ptr<ConsoleInput>)>;

        ConsoleLogScope(Install install, std::shared_ptr<ConsoleInput> console)
            : m_install{std::move(install)}
            , m_console{std::move(console)}
        {
            m_install(m_console);
        }

        ~ConsoleLogScope()
        {
            if (m_console)
            {
                m_console->Close();
            }

            m_install(nullptr);
        }

        ConsoleLogScope(const ConsoleLogScope&) = delete;
        ConsoleLogScope& operator=(const ConsoleLogScope&) = delete;

    private:
        Install m_install;
        std::shared_ptr<ConsoleInput> m_console;
    };

    // The server lets a username log in once, so a second file for the same one would only be kicked.
    void CheckUsernamesAreUnique(const std::vector<AccountConfig_s>& accounts)
    {
        for (auto i = std::size_t{0}; i < accounts.size(); ++i)
        {
            for (auto j = i + 1; j < accounts.size(); ++j)
            {
                if (ToLower(accounts[i].credentials.username) == ToLower(accounts[j].credentials.username))
                {
                    throw ConfigError{std::format("Accounts {} and {} have the same username", accounts[i].name, accounts[j].name)};
                }
            }
        }
    }
}

CommandLine_s Application::ParseCommandLine(std::span<char* const> args)
{
    auto commandLine = CommandLine_s{};
    for (auto i = std::size_t{0}; i < args.size(); ++i)
    {
        const auto arg = std::string_view{args[i]};
        if (arg == ACCOUNT_OPTION)
        {
            if (i + 1 >= args.size())
            {
                throw std::invalid_argument{std::format("{} needs an account file path", ACCOUNT_OPTION)};
            }

            commandLine.accountPath = args[++i];
        }
        else if (arg == WATCH_OPTION)
        {
            commandLine.watch = true;
        }
        else if (arg == DEBUGGER_OPTION)
        {
            commandLine.debugger = true;
        }
        else if (arg == RAW_CONSOLE_OPTION)
        {
            commandLine.rawConsole = true;
        }
        else if (arg.starts_with("--"))
        {
            throw std::invalid_argument{std::format("Unknown option {}; {}", arg, USAGE)};
        }
        else
        {
            commandLine.configPath = arg;
        }
    }

    if (commandLine.watch && commandLine.debugger)
    {
        throw std::invalid_argument{std::format("{} and {} can't be combined: a reload would replace the script the debugger is attached to", WATCH_OPTION, DEBUGGER_OPTION)};
    }

    if (commandLine.debugger && !commandLine.accountPath)
    {
        throw std::invalid_argument{std::format("{} needs {}: a script paused in the debugger pauses every account in the process", DEBUGGER_OPTION, ACCOUNT_OPTION)};
    }

    return commandLine;
}

Application::Application(CommandLine_s commandLine, std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
    , m_commandLine{std::move(commandLine)}
{
    assert(m_logger && "Application needs a logger");
    // Before the config loads, so a raw console has no colors from the first line.
    InstallLogSink(nullptr);
    m_config = std::make_shared<const Config_s>(ConfigFile::Load(m_commandLine.configPath, *m_logger));
    m_logger->SetLevel(m_config->client.logLevel);
    if (!m_config->client.logFile.empty())
    {
        m_logFile = std::make_shared<LogFile>(m_config->client.logFile);
        InstallLogSink(nullptr);
        m_logger->Info("Logging to {} too", m_logFile->GetPath().string());
    }

    m_logger->Info("Config loaded from {}", m_commandLine.configPath.string());
    m_cache = std::make_shared<const GameCache_s>(CacheLoader::Load(m_config->client.cacheDirectory, *m_logger));
    const auto started = std::chrono::steady_clock::now();
    m_navigation = std::make_shared<const Navigation_s>(*m_cache, m_config->client.navDirectory);
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started);
    m_logger->Info("Walking map built and walker graph loaded from {} in {} ms: {:.1f} MB, {} edges",
                   m_config->client.navDirectory, elapsed.count(), static_cast<double>(m_navigation->map.GetMemoryBytes()) / (1024.0 * 1024.0), m_navigation->graph.GetEdgeCount());
}

int Application::Run()
{
    auto runtime = ScriptRuntime{};
    const auto& scripting = m_config->scripting;
    const auto options = AccountOptions_s{
        .client = {.connectAttempts = static_cast<u32>(scripting.connectAttempts)},
        .watchScripts = m_commandLine.watch,
        .waitForDebugger = m_commandLine.debugger,
        .navigation = m_navigation,
        .reloginDelay = scripting.reloginDelaySeconds,
    };
    auto runner = AccountRunner{m_config, m_cache, LoadAccounts(), runtime, m_logger, options};
    if (m_commandLine.watch)
    {
        m_logger->Info("Watching the scripts: each reloads when its files change, and one that fails waits for a fix");
    }

    // Installed only once the scripts have loaded, so Ctrl+C still ends the process while it waits for the debugger.
    std::signal(SIGINT, SignalHandler);
    const auto console = m_commandLine.rawConsole ? nullptr : ConsoleInput::ReadStdin();
    const auto consoleLog = ConsoleLogScope{[this](std::shared_ptr<ConsoleInput> current)
    {
        InstallLogSink(std::move(current));
    }, console};

    if (console)
    {
        m_logger->Info("Type {} for the console commands", AccountRunner::COMMAND_HELP);
    }

    const auto succeeded = runner.Run([]
    {
        return interruptCount.load();
    }, console.get());

    return succeeded ? EXIT_SUCCESS : EXIT_FAILURE;
}

void Application::InstallLogSink(std::shared_ptr<ConsoleInput> console)
{
    if (console && !console->IsInteractive())
    {
        console.reset();
    }

    m_logger->SetSink([file = m_logFile, console = std::move(console), raw = m_commandLine.rawConsole](const LogEntry_s& entry)
    {
        if (file)
        {
            file->Write(entry);
        }

        if (console)
        {
            console->Print(Logger::GetConsoleStream(entry.level), Logger::FormatConsoleLine(entry));
        }
        else if (raw)
        {
            Logger::WritePlainToConsole(entry);
        }
        else
        {
            Logger::WriteToConsole(entry);
        }
    });
}

std::vector<AccountConfig_s> Application::LoadAccounts() const
{
    if (m_commandLine.accountPath)
    {
        auto accounts = std::vector<AccountConfig_s>{};
        accounts.push_back(ConfigFile::LoadAccount(*m_commandLine.accountPath));
        if (m_commandLine.debugger && !accounts.front().script)
        {
            throw ConfigError{std::format("{}: {} needs an account with a script", m_commandLine.accountPath->string(), DEBUGGER_OPTION)};
        }

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

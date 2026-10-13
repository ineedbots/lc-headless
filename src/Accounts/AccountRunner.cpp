#include "pch.hpp"
#include "AccountRunner.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Core/ConfigFile.hpp"
#include "../Core/ConsoleInput.hpp"
#include "../Core/Logger.hpp"
#include "../Game/Protocol/WordPack.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/ConsoleCommand_s.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "Account.hpp"

namespace
{
    constexpr auto TARGET_PREFIX = '@';
    constexpr auto WHITESPACE = " \t"sv;

    struct LogLevelName_s
    {
        LogLevel_e level;
        std::string_view name;
    };

    constexpr auto LOG_LEVEL_NAMES = std::array{
        LogLevelName_s{LogLevel_e::Verbose, "verbose"},
        LogLevelName_s{LogLevel_e::Info, "info"},
        LogLevelName_s{LogLevel_e::Warning, "warning"},
        LogLevelName_s{LogLevel_e::Error, "error"},
    };

    std::string ToLower(std::string_view text)
    {
        auto lower = std::string{text};
        std::ranges::transform(lower, lower.begin(), [](char character)
        {
            return static_cast<char>(std::tolower(static_cast<unsigned char>(character)));
        });

        return lower;
    }

    std::string_view Trim(std::string_view text)
    {
        const auto first = text.find_first_not_of(WHITESPACE);
        if (first == std::string_view::npos)
        {
            return {};
        }

        return text.substr(first, text.find_last_not_of(WHITESPACE) - first + 1);
    }

    // The text's first word, and the rest of it, trimmed.
    std::pair<std::string_view, std::string_view> SplitFirstWord(std::string_view text)
    {
        text = Trim(text);
        const auto end = text.find_first_of(WHITESPACE);
        if (end == std::string_view::npos)
        {
            return {text, {}};
        }

        return {text.substr(0, end), Trim(text.substr(end))};
    }

    std::vector<std::string> SplitWords(std::string_view text)
    {
        auto words = std::vector<std::string>{};
        while (!text.empty())
        {
            const auto [word, rest] = SplitFirstWord(text);
            words.emplace_back(word);
            text = rest;
        }

        return words;
    }

    bool HasCommand(const std::vector<ScriptCommand_s>& commands, std::string_view name)
    {
        return std::ranges::find(commands, name, &ScriptCommand_s::name) != commands.end();
    }
}

AccountRunner::AccountRunner(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, AccountOptions_s options)
    : m_config{std::move(config)}
    , m_cache{std::move(cache)}
    , m_logger{std::move(logger)}
{
    assert(m_cache && "AccountRunner needs a cache");
    for (auto& account : accounts)
    {
        m_accounts.push_back(std::make_unique<Account>(m_config, m_cache, std::move(account), runtime, m_logger, options, &m_messenger));
    }
}

bool AccountRunner::Run(const InterruptCount& interrupts, ConsoleInput* console)
{
    m_loginTurns = 0;
    m_nextLogin = m_accounts.empty() ? std::nullopt : std::optional{Clock::now()};
    auto handledInterrupts = interrupts();

    m_logger->Info("Running {} account{}", m_accounts.size(), m_accounts.size() == 1 ? "" : "s");
    while (true)
    {
        // Before the steps, so a command queued for a script runs in this pass.
        if (console != nullptr)
        {
            for (const auto& line : console->TakeLines())
            {
                HandleCommand(line);
            }
        }

        const auto now = Clock::now();
        if (m_nextLogin && now >= *m_nextLogin)
        {
            StartNextLogin(now);
        }

        for (const auto& account : m_accounts)
        {
            account->Step(0ms);
        }

        for (const auto count = interrupts(); handledInterrupts < count; ++handledInterrupts)
        {
            InterruptAll();
        }

        const auto running = std::ranges::any_of(m_accounts, [](const std::unique_ptr<Account>& account)
        {
            return account->IsStarted() && !account->IsFinished();
        });

        if (!running && !m_nextLogin)
        {
            break;
        }

        Wait(now, console);
    }

    return LogOutcomes();
}

void AccountRunner::HandleCommand(std::string_view line)
{
    auto rest = Trim(line);
    if (rest.empty())
    {
        return;
    }

    Account* target = nullptr;
    if (rest.front() == TARGET_PREFIX)
    {
        const auto [name, after] = SplitFirstWord(rest.substr(1));
        target = FindAccount(name);
        if (target == nullptr)
        {
            auto names = std::string{};
            for (const auto& account : m_accounts)
            {
                names += names.empty() ? account->GetName() : ", " + account->GetName();
            }

            m_logger->Warning("No account is named {}; the accounts are {}", name, names);
            return;
        }

        if (after.empty())
        {
            m_logger->Warning("{}{} needs a command after it, such as {}{} {}", TARGET_PREFIX, name, TARGET_PREFIX, name, COMMAND_HELP);
            return;
        }

        rest = after;
    }

    const auto [name, text] = SplitFirstWord(rest);
    const auto command = ConsoleCommand_s{.name = ToLower(name), .text = std::string{text}, .args = SplitWords(text)};
    if (command.name == COMMAND_HELP)
    {
        ShowHelp(target);
    }
    else if (command.name == COMMAND_STATUS)
    {
        ShowStatus(target);
    }
    else if (command.name == COMMAND_QUIT || command.name == COMMAND_EXIT)
    {
        Quit(target);
    }
    else if (command.name == COMMAND_LOG_LEVEL)
    {
        SetLogLevel(target, command.args);
    }
    else if (command.name == COMMAND_SAY)
    {
        Say(target, command.text);
    }
    else
    {
        SendToScripts(target, command);
    }
}

std::size_t AccountRunner::GetAccountCount() const
{
    return m_accounts.size();
}

const Account& AccountRunner::GetAccount(std::size_t index) const
{
    assert(index < m_accounts.size() && "Account index out of range");
    return *m_accounts[index];
}

// Accounts quit from the console before their turn give it up to the next.
void AccountRunner::StartNextLogin(Clock::time_point now)
{
    while (m_loginTurns < m_accounts.size() && m_cancelled.contains(m_accounts[m_loginTurns].get()))
    {
        ++m_loginTurns;
    }

    if (m_loginTurns < m_accounts.size())
    {
        m_accounts[m_loginTurns]->Start();
        ++m_loginTurns;
    }

    const auto waiting = m_loginTurns < m_accounts.size();
    m_nextLogin = waiting ? std::optional{now + m_config->scripting.loginIntervalSeconds} : std::nullopt;
}

void AccountRunner::InterruptAll()
{
    if (m_nextLogin)
    {
        const auto waiting = m_accounts.size() - m_loginTurns;
        m_logger->Info("Interrupted; {} account{} won't log in", waiting, waiting == 1 ? "" : "s");
        m_nextLogin.reset();
    }

    for (const auto& account : m_accounts)
    {
        account->Interrupt();
    }
}

Account* AccountRunner::FindAccount(std::string_view name) const
{
    const auto lower = ToLower(name);
    for (const auto& account : m_accounts)
    {
        if (ToLower(account->GetName()) == lower || ToLower(account->GetUsername()) == lower)
        {
            return account.get();
        }
    }

    return nullptr;
}

void AccountRunner::ShowHelp(const Account* target) const
{
    if (target == nullptr)
    {
        m_logger->Info("Console commands: {}, {}, {} (or {}; as Ctrl+C), {} [verbose|info|warning|error], {} <text>. Start a line with {}<account> to send it to that account only",
                       COMMAND_HELP, COMMAND_STATUS, COMMAND_QUIT, COMMAND_EXIT, COMMAND_LOG_LEVEL, COMMAND_SAY, TARGET_PREFIX);
    }

    auto any = false;
    for (const auto& account : m_accounts)
    {
        if (target != nullptr && account.get() != target)
        {
            continue;
        }

        for (const auto& command : account->GetCommands())
        {
            any = true;
            if (command.help.empty())
            {
                m_logger->Info("{}: {}", account->GetName(), command.name);
            }
            else
            {
                m_logger->Info("{}: {} - {}", account->GetName(), command.name, command.help);
            }
        }
    }

    if (any)
    {
        return;
    }

    if (target == nullptr)
    {
        m_logger->Info("No script has added a console command");
    }
    else
    {
        m_logger->Info("{}: no console commands", target->GetName());
    }
}

void AccountRunner::ShowStatus(const Account* target) const
{
    for (const auto& account : m_accounts)
    {
        if (target == nullptr || account.get() == target)
        {
            m_logger->Info("{}: {}", account->GetName(), account->DescribeStatus());
        }
    }
}

void AccountRunner::Quit(Account* target)
{
    if (target == nullptr)
    {
        InterruptAll();
        return;
    }

    if (target->IsStarted())
    {
        target->Interrupt();
        return;
    }

    if (m_cancelled.insert(target).second)
    {
        m_logger->Info("{} won't log in", target->GetName());
    }
}

void AccountRunner::SetLogLevel(const Account* target, std::span<const std::string> args)
{
    if (target != nullptr)
    {
        m_logger->Warning("{} applies to every account; leave out the {}", COMMAND_LOG_LEVEL, TARGET_PREFIX);
        return;
    }

    if (args.empty())
    {
        const auto current = std::ranges::find(LOG_LEVEL_NAMES, m_logger->GetLevel(), &LogLevelName_s::level);
        m_logger->Warning("The log level is {}", current->name);
        return;
    }

    const auto chosen = std::ranges::find(LOG_LEVEL_NAMES, ToLower(args.front()), &LogLevelName_s::name);
    if (args.size() > 1 || chosen == LOG_LEVEL_NAMES.end())
    {
        m_logger->Warning("{} takes one of verbose, info, warning or error", COMMAND_LOG_LEVEL);
        return;
    }

    m_logger->SetLevel(chosen->level);
    // A warning, so it shows at every level but error.
    m_logger->Warning("The log level is now {}", chosen->name);
}

void AccountRunner::Say(Account* target, std::string_view text)
{
    if (text.empty())
    {
        m_logger->Warning("{} needs the text to say", COMMAND_SAY);
        return;
    }

    if (text.size() > WordPack::MAX_PACK_LENGTH)
    {
        m_logger->Warning("Public chat holds {} characters; the rest is cut off", WordPack::MAX_PACK_LENGTH);
        text = text.substr(0, WordPack::MAX_PACK_LENGTH);
    }

    if (target != nullptr)
    {
        if (target->Say(text))
        {
            m_logger->Info("{} says: {}", target->GetName(), text);
        }
        else
        {
            m_logger->Warning("{} isn't in game to say it", target->GetName());
        }

        return;
    }

    auto said = false;
    for (const auto& account : m_accounts)
    {
        if (account->Say(text))
        {
            said = true;
            m_logger->Info("{} says: {}", account->GetName(), text);
        }
    }

    if (!said)
    {
        m_logger->Warning("No account is in game to say it");
    }
}

void AccountRunner::SendToScripts(Account* target, const ConsoleCommand_s& command)
{
    if (target != nullptr)
    {
        if (!HasCommand(target->GetCommands(), command.name))
        {
            m_logger->Warning("{} has no console command {}; type {}{} {} for its commands", target->GetName(), command.name, TARGET_PREFIX, target->GetName(), COMMAND_HELP);
        }
        else if (!target->SendCommand(command))
        {
            m_logger->Warning("{} can't take more console commands until it has run the ones waiting", target->GetName());
        }

        return;
    }

    auto found = false;
    for (const auto& account : m_accounts)
    {
        if (!HasCommand(account->GetCommands(), command.name))
        {
            continue;
        }

        found = true;
        if (!account->SendCommand(command))
        {
            m_logger->Warning("{} can't take more console commands until it has run the ones waiting", account->GetName());
        }
    }

    if (!found)
    {
        m_logger->Warning("Unknown command {}; type {} for the commands", command.name, COMMAND_HELP);
    }
}

void AccountRunner::Wait(Clock::time_point now, ConsoleInput* console) const
{
    auto wake = now + m_config->scripting.pollIntervalMs;
    if (m_nextLogin)
    {
        wake = std::min(wake, *m_nextLogin);
    }

    for (const auto& account : m_accounts)
    {
        if (const auto nextLoop = account->GetNextLoop())
        {
            wake = std::min(wake, *nextLoop);
        }
    }

    if (console != nullptr)
    {
        console->WaitUntil(wake);
        return;
    }

    std::this_thread::sleep_until(wake);
}

bool AccountRunner::LogOutcomes() const
{
    auto succeeded = true;
    for (const auto& account : m_accounts)
    {
        if (!account->IsStarted())
        {
            continue;
        }

        succeeded = succeeded && account->Succeeded();
        m_logger->Info("{}: {}", account->GetName(), account->DescribeOutcome());
    }

    return succeeded;
}

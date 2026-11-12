#include "pch.hpp"
#include "AccountCommands.hpp"

#include "../Console/ConsoleCommandParser.hpp"
#include "../Console/ConsoleCommand_s.hpp"
#include "../Console/LogLevelNames.hpp"
#include "../Console/LogLevel_e.hpp"
#include "../Console/Logger.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/Protocol/WordPack.hpp"
#include "../Script/ScriptCommand_s.hpp"
#include "../Utils/StringUtils.hpp"
#include "Account.hpp"

namespace
{
    constexpr auto TARGET_PREFIX = ConsoleCommandParser::TARGET_PREFIX;

    bool HasCommand(const std::vector<ScriptCommand_s>& commands, std::string_view name)
    {
        return std::ranges::find(commands, name, &ScriptCommand_s::name) != commands.end();
    }
}

AccountCommands::AccountCommands(const std::vector<std::unique_ptr<Account>>& accounts, Logger& logger)
    : m_accounts{accounts}
    , m_logger{logger}
{
}

Account* AccountCommands::FindAccount(std::string_view name) const
{
    for (const auto& account : m_accounts)
    {
        if (StringUtils::EqualsIgnoringCase(account->GetName(), name) || StringUtils::EqualsIgnoringCase(account->GetUsername(), name))
        {
            return account.get();
        }
    }

    return nullptr;
}

void AccountCommands::ShowHelp(const Account* target) const
{
    if (target == nullptr)
    {
        m_logger.Info("Console commands: {}, {}, {} (or {}; as Ctrl+C), {} [verbose|info|warning|error], {} <text>, and every script's {} and {}. Start a line with {}<account> to send it to that account only",
                      HELP, STATUS, QUIT, EXIT, LOG_LEVEL, SAY, PAUSE, RESUME, TARGET_PREFIX);
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
            if (command.name == PAUSE || command.name == RESUME)
            {
                continue;
            }

            any = true;

            if (command.help.empty())
            {
                m_logger.Info("{}: {}", account->GetName(), command.name);
            }
            else
            {
                m_logger.Info("{}: {} - {}", account->GetName(), command.name, command.help);
            }
        }
    }

    if (any)
    {
        return;
    }

    if (target == nullptr)
    {
        m_logger.Info("No script has added a console command");
    }
    else
    {
        m_logger.Info("{}: no console commands", target->GetName());
    }
}

void AccountCommands::ShowStatus(const Account* target) const
{
    for (const auto& account : m_accounts)
    {
        if (target == nullptr || account.get() == target)
        {
            m_logger.Info("{}: {}", account->GetName(), account->DescribeStatus());
        }
    }
}

bool AccountCommands::SetLogLevel(const Account* target, std::span<const std::string> args) const
{
    if (target != nullptr)
    {
        m_logger.Warning("{} applies to every account; leave out the {}", LOG_LEVEL, TARGET_PREFIX);
        return false;
    }

    if (args.empty())
    {
        m_logger.Warning("The log level is {}", LogLevelNames::GetName(m_logger.GetLevel()));
        return true;
    }

    const auto chosen = LogLevelNames::Find(StringUtils::ToLower(args.front()));
    if (args.size() > 1 || !chosen)
    {
        m_logger.Warning("{} takes one of {}", LOG_LEVEL, LogLevelNames::CHOICES);
        return false;
    }

    m_logger.SetLevel(*chosen);
    // A warning, so it shows at every level but error.
    m_logger.Warning("The log level is now {}", LogLevelNames::GetName(*chosen));
    return true;
}

bool AccountCommands::Say(Account* target, std::string_view text) const
{
    if (text.empty())
    {
        m_logger.Warning("{} needs the text to say", SAY);
        return false;
    }

    const auto isCommand = text.starts_with("::");
    if (isCommand && (text.size() == 2 || text.size() - 2 > ClientPackets::MAX_CHEAT_LENGTH || text.find('\n') != std::string_view::npos))
    {
        m_logger.Warning("A :: command needs 1 to {} characters on one line", ClientPackets::MAX_CHEAT_LENGTH);
        return false;
    }

    if (!isCommand && text.size() > WordPack::MAX_PACK_LENGTH)
    {
        m_logger.Warning("Public chat holds {} characters; the rest is cut off", WordPack::MAX_PACK_LENGTH);
        text = text.substr(0, WordPack::MAX_PACK_LENGTH);
    }

    if (target != nullptr)
    {
        const auto said = target->Say(text);
        if (said)
        {
            m_logger.Info("{} says: {}", target->GetName(), text);
        }
        else
        {
            m_logger.Warning("{} isn't in game to say it", target->GetName());
        }

        return said;
    }

    auto said = false;
    for (const auto& account : m_accounts)
    {
        if (account->Say(text))
        {
            said = true;
            m_logger.Info("{} says: {}", account->GetName(), text);
        }
    }

    if (!said)
    {
        m_logger.Warning("No account is in game to say it");
    }
    return said;
}

bool AccountCommands::SendToScripts(Account* target, const ConsoleCommand_s& command, std::shared_ptr<CommandExecution> execution) const
{
    auto accepted = false;
    auto found = false;
    for (const auto& account : m_accounts)
    {
        if (target && account.get() != target)
        {
            continue;
        }
        const auto has = HasCommand(account->GetCommands(), command.name);
        if (!has && !target)
        {
            continue;
        }
        found = true;
        auto token = execution ? std::make_shared<CommandRecipient>(execution, account->GetName()) : nullptr;
        if (!has)
        {
            m_logger.Warning("{} has no console command {}; type {}{} {} for its commands", account->GetName(), command.name, TARGET_PREFIX, account->GetName(), HELP);
            if (token)
            {
                token->Finish("rejected", account->IsFinished() ? "account_unavailable" : "unknown_command");
            }
        }
        else
        {
            const auto queued = account->QueueCommand(command, token);
            if (queued == CommandQueueResult_e::Accepted)
            {
                accepted = true;
            }
            else
            {
                m_logger.Warning("{} can't take more console commands until it has run the ones waiting", account->GetName());
                if (token)
                {
                    token->Finish("rejected", queued == CommandQueueResult_e::QueueFull ? "script_queue_full" : "account_unavailable");
                }
            }
        }
    }
    if (!found)
    {
        m_logger.Warning("Unknown command {}; type {} for the commands", command.name, HELP);
    }
    return accepted;
}

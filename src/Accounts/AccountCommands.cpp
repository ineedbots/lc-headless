#include "pch.hpp"
#include "AccountCommands.hpp"

#include "../Console/ConsoleCommandParser.hpp"
#include "../Console/ConsoleCommand_s.hpp"
#include "../Console/LogLevelNames.hpp"
#include "../Console/LogLevel_e.hpp"
#include "../Console/Logger.hpp"
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
        m_logger.Info("Console commands: {}, {}, {} (or {}; as Ctrl+C), {} [verbose|info|warning|error], {} <text>. Start a line with {}<account> to send it to that account only",
                      HELP, STATUS, QUIT, EXIT, LOG_LEVEL, SAY, TARGET_PREFIX);
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

void AccountCommands::SetLogLevel(const Account* target, std::span<const std::string> args) const
{
    if (target != nullptr)
    {
        m_logger.Warning("{} applies to every account; leave out the {}", LOG_LEVEL, TARGET_PREFIX);
        return;
    }

    if (args.empty())
    {
        m_logger.Warning("The log level is {}", LogLevelNames::GetName(m_logger.GetLevel()));
        return;
    }

    const auto chosen = LogLevelNames::Find(StringUtils::ToLower(args.front()));
    if (args.size() > 1 || !chosen)
    {
        m_logger.Warning("{} takes one of {}", LOG_LEVEL, LogLevelNames::CHOICES);
        return;
    }

    m_logger.SetLevel(*chosen);
    // A warning, so it shows at every level but error.
    m_logger.Warning("The log level is now {}", LogLevelNames::GetName(*chosen));
}

void AccountCommands::Say(Account* target, std::string_view text) const
{
    if (text.empty())
    {
        m_logger.Warning("{} needs the text to say", SAY);
        return;
    }

    if (text.size() > WordPack::MAX_PACK_LENGTH)
    {
        m_logger.Warning("Public chat holds {} characters; the rest is cut off", WordPack::MAX_PACK_LENGTH);
        text = text.substr(0, WordPack::MAX_PACK_LENGTH);
    }

    if (target != nullptr)
    {
        if (target->Say(text))
        {
            m_logger.Info("{} says: {}", target->GetName(), text);
        }
        else
        {
            m_logger.Warning("{} isn't in game to say it", target->GetName());
        }

        return;
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
}

void AccountCommands::SendToScripts(Account* target, const ConsoleCommand_s& command) const
{
    if (target != nullptr)
    {
        if (!HasCommand(target->GetCommands(), command.name))
        {
            m_logger.Warning("{} has no console command {}; type {}{} {} for its commands", target->GetName(), command.name, TARGET_PREFIX, target->GetName(), HELP);
        }
        else if (!target->SendCommand(command))
        {
            m_logger.Warning("{} can't take more console commands until it has run the ones waiting", target->GetName());
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
            m_logger.Warning("{} can't take more console commands until it has run the ones waiting", account->GetName());
        }
    }

    if (!found)
    {
        m_logger.Warning("Unknown command {}; type {} for the commands", command.name, HELP);
    }
}

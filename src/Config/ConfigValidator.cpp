#include "pch.hpp"
#include "ConfigValidator.hpp"

#include "../Console/Logger.hpp"
#include "../Io/WebSocketUrl.hpp"
#include "../Utils/BigUInt.hpp"
#include "../Utils/StringUtils.hpp"
#include "AccountConfig_s.hpp"
#include "Config_s.hpp"
#include "Error/ConfigError.hpp"
#include "Revision_e.hpp"
#include "ServerSettings_s.hpp"

namespace
{
    constexpr auto MAX_USERNAME_LENGTH = std::size_t{12};
    constexpr auto MAX_PASSWORD_LENGTH = std::size_t{20};
    constexpr auto MAX_IDLE_SECONDS = std::chrono::seconds{24 * 60 * 60};
    constexpr auto MIN_CALL_TIMEOUT = 10ms;
    constexpr auto MAX_CALL_TIMEOUT = 60000ms;
    constexpr auto MIN_POLL_INTERVAL = 1ms;
    constexpr auto MAX_POLL_INTERVAL = 1000ms;
    constexpr auto MAX_LOGIN_INTERVAL = 60s;
    constexpr auto MAX_KILL_GRACE = 600s;
    constexpr auto MAX_CONNECT_ATTEMPTS = 100;
    constexpr auto MAX_RELOGIN_DELAY = 3600s;
    constexpr auto MAX_PROGRESS_REPORT_INTERVAL = std::chrono::minutes{24 * 60};
    constexpr auto MAX_STALL_MINUTES = std::chrono::minutes{24 * 60};
    constexpr auto MAX_RUN_ENERGY = 100;
    constexpr auto NO_TLS_VERIFICATION = "NONE"sv;

    void Check(bool valid, std::string_view path, std::string_view rule)
    {
        if (valid)
        {
            return;
        }

        throw ConfigError{std::format("{}: {}", path, rule)};
    }

    bool IsCredential(std::string_view text, std::size_t maxLength)
    {
        return !text.empty() && text.size() <= maxLength && StringUtils::IsPrintableAscii(text);
    }

    bool IsSupported(Revision_e revision)
    {
        const auto& revisions = LoginSettings_s::SUPPORTED_REVISIONS;
        return std::ranges::find(revisions, revision) != revisions.end();
    }

    // "must be 225 or 289", from the supported list.
    std::string DescribeSupportedRevisions()
    {
        const auto& revisions = LoginSettings_s::SUPPORTED_REVISIONS;
        auto text = "must be "s;
        for (auto i = std::size_t{0}; i < revisions.size(); ++i)
        {
            if (i > 0)
            {
                text += i + 1 == revisions.size() ? " or " : ", ";
            }

            text += std::to_string(static_cast<u16>(revisions[i]));
        }

        return text;
    }

    void ValidateServer(const ServerSettings_s& server)
    {
        Check(WebSocketUrl::IsValid(server.url), "server.url", "must be a ws:// or wss:// URL");
        Check(server.origin.empty() || StringUtils::IsPrintableAscii(server.origin), "server.origin", "must be empty or printable ASCII");
        Check(!server.tlsCaFile.empty(), "server.tlsCaFile", "must be a PEM file path, SYSTEM or NONE");
    }
}

void ConfigValidator::Validate(const Config_s& config)
{
    ValidateServer(config.server);

    const auto& login = config.login;
    const auto one = BigUInt::Parse("1");
    Check(login.rsaModulus > one, "login.rsaModulus", "must be greater than 1");
    Check(login.rsaExponent > BigUInt{}, "login.rsaExponent", "must be greater than 0");
    Check(IsSupported(login.revision), "login.revision", DescribeSupportedRevisions());

    const auto& client = config.client;
    Check(!client.cacheDirectory.empty(), "client.cacheDirectory", "must not be empty");
    Check(!client.navDirectory.empty(), "client.navDirectory", "must not be empty");

    const auto& scripting = config.scripting;
    Check(!scripting.accountsDirectory.empty(), "scripting.accountsDirectory", "must be a folder path");
    Check(!scripting.scriptsDirectory.empty(), "scripting.scriptsDirectory", "must be a folder path");
    Check(scripting.callTimeoutMs >= MIN_CALL_TIMEOUT && scripting.callTimeoutMs <= MAX_CALL_TIMEOUT, "scripting.callTimeoutMs", std::format("must be from {} to {}", MIN_CALL_TIMEOUT.count(), MAX_CALL_TIMEOUT.count()));
    Check(scripting.pollIntervalMs >= MIN_POLL_INTERVAL && scripting.pollIntervalMs <= MAX_POLL_INTERVAL, "scripting.pollIntervalMs", std::format("must be from {} to {}", MIN_POLL_INTERVAL.count(), MAX_POLL_INTERVAL.count()));
    Check(scripting.loginIntervalSeconds >= 0s && scripting.loginIntervalSeconds <= MAX_LOGIN_INTERVAL, "scripting.loginIntervalSeconds", std::format("must be from 0 to {}", MAX_LOGIN_INTERVAL.count()));
    Check(scripting.killGraceSeconds >= 0s && scripting.killGraceSeconds <= MAX_KILL_GRACE, "scripting.killGraceSeconds", std::format("must be from 0 to {}", MAX_KILL_GRACE.count()));
    Check(scripting.connectAttempts >= 1 && scripting.connectAttempts <= MAX_CONNECT_ATTEMPTS, "scripting.connectAttempts", std::format("must be from 1 to {}", MAX_CONNECT_ATTEMPTS));
    Check(scripting.reloginDelaySeconds >= 0s && scripting.reloginDelaySeconds <= MAX_RELOGIN_DELAY, "scripting.reloginDelaySeconds", std::format("must be from 0 to {}", MAX_RELOGIN_DELAY.count()));
    Check(!scripting.progressDirectory.empty(), "scripting.progressDirectory", "must be a folder path");
}

void ConfigValidator::ValidateAccount(const AccountConfig_s& account)
{
    const auto& credentials = account.credentials;
    Check(IsCredential(credentials.username, MAX_USERNAME_LENGTH), "username", std::format("must be 1 to {} printable ASCII characters", MAX_USERNAME_LENGTH));
    Check(IsCredential(credentials.password, MAX_PASSWORD_LENGTH), "password", std::format("must be 1 to {} printable ASCII characters", MAX_PASSWORD_LENGTH));
    Check(account.idleSeconds >= 0s && account.idleSeconds <= MAX_IDLE_SECONDS, "idleSeconds", std::format("must be from 0 (idle until interrupted) to {}", MAX_IDLE_SECONDS.count()));
    Check(account.stallMinutes >= std::chrono::minutes{0} && account.stallMinutes <= MAX_STALL_MINUTES, "stallMinutes", std::format("must be from 0 to {}", MAX_STALL_MINUTES.count()));
    Check(account.runEnergyMin >= 0 && account.runEnergyMin <= MAX_RUN_ENERGY, "runEnergyMin", std::format("must be from 0 to {}", MAX_RUN_ENERGY));

    if (account.server)
    {
        ValidateServer(*account.server);
    }

    if (account.script)
    {
        const auto& script = *account.script;
        Check(!script.file.empty(), "script.file", "must name a script file in the scripts directory");
        Check(script.progressReportMinutes >= std::chrono::minutes{0} && script.progressReportMinutes <= MAX_PROGRESS_REPORT_INTERVAL, "script.progressReportMinutes",
              std::format("must be from 0 (no reports) to {}", MAX_PROGRESS_REPORT_INTERVAL.count()));
    }
}

void ConfigValidator::Warn(const Config_s& config, Logger& logger)
{
    if (WebSocketUrl::GetScheme(config.server.url) != WebSocketUrl::SECURE_SCHEME || config.server.tlsCaFile != NO_TLS_VERIFICATION)
    {
        return;
    }

    logger.Warning("Config disables TLS certificate verification (server.tlsCaFile is NONE)");
}

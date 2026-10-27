#include "pch.hpp"
#include "ConfigJson.hpp"

#include "../Console/LogLevelNames.hpp"
#include "../Console/LogLevel_e.hpp"
#include "../Utils/BigUInt.hpp"
#include "AccountConfig_s.hpp"
#include "Config_s.hpp"
#include "Error/ConfigError.hpp"
#include "ProxySettings_s.hpp"
#include "ServerSettings_s.hpp"
#include "TransportNames.hpp"
#include "Transport_e.hpp"

#include <nlohmann/json.hpp>

namespace
{
    constexpr auto INDENT = 4;
    constexpr auto ALLOW_EXCEPTIONS = true;
    constexpr auto IGNORE_COMMENTS = true;
    constexpr auto TYPE_ERROR_ID = 302;

    struct TextPosition_s
    {
        std::size_t line;
        std::size_t column;
    };

    TextPosition_s GetTextPosition(std::string_view text, std::size_t byte)
    {
        // nlohmann's byte is 1-based and counts the end of input, so it can be one past the text.
        const auto offset = std::min(byte > 0 ? byte - 1 : 0, text.size());
        const auto before = text.substr(0, offset);
        const auto line = 1 + static_cast<std::size_t>(std::ranges::count(before, '\n'));
        const auto lineStart = before.find_last_of('\n');
        const auto column = lineStart == std::string_view::npos ? offset + 1 : offset - lineStart;
        return {.line = line, .column = column};
    }

    nlohmann::json ParseJson(std::string_view text)
    {
        try
        {
            return nlohmann::json::parse(text, nullptr, ALLOW_EXCEPTIONS, IGNORE_COMMENTS);
        }
        catch (const nlohmann::json::parse_error& e)
        {
            // Not e.what(): lexer errors quote the text they stopped in, which can be part of the password.
            const auto position = GetTextPosition(text, e.byte);
            throw ConfigError{std::format("invalid JSON at line {}, column {}", position.line, position.column)};
        }
    }

    std::string DescribeConversionError(const nlohmann::json::exception& e)
    {
        auto message = std::string_view{e.what()};
        const auto idEnd = message.find("] ");
        if (idEnd != std::string_view::npos)
        {
            message.remove_prefix(idEnd + 2);
        }

        const auto pointerEnd = message.find(") ");
        if (!message.starts_with('(') || pointerEnd == std::string_view::npos)
        {
            return std::string{message};
        }

        auto path = std::string{message.substr(1, pointerEnd - 1)};
        if (path.starts_with('/'))
        {
            path.erase(0, 1);
        }

        std::ranges::replace(path, '/', '.');
        return std::format("{}: {}", path, message.substr(pointerEnd + 2));
    }

    nlohmann::json ParseRootObject(std::string_view text)
    {
        auto root = ParseJson(text);
        if (!root.is_object())
        {
            throw ConfigError{"the top level must be an object"};
        }

        return root;
    }
}

namespace nlohmann
{
    template <>
    struct adl_serializer<BigUInt>
    {
        static void from_json(const json& value, BigUInt& result)
        {
            try
            {
                result = BigUInt::Parse(value.get<std::string>());
            }
            catch (const std::invalid_argument&)
            {
                throw json::type_error::create(TYPE_ERROR_ID, "must be a decimal or 0x-hex number", &value);
            }
        }

        static void to_json(ordered_json& value, const BigUInt& source)
        {
            value = source.ToHexString();
        }
    };

    template <>
    struct adl_serializer<LogLevel_e>
    {
        static void from_json(const json& value, LogLevel_e& result)
        {
            const auto level = LogLevelNames::Find(value.get<std::string>());
            if (!level)
            {
                throw json::type_error::create(TYPE_ERROR_ID, std::format("must be {}", LogLevelNames::CHOICES), &value);
            }

            result = *level;
        }

        static void to_json(ordered_json& value, LogLevel_e level)
        {
            value = std::string{LogLevelNames::GetName(level)};
        }
    };

    // Not NLOHMANN_JSON_SERIALIZE_ENUM: it reads an unknown name as the first value, so "wws" would quietly mean ws.
    template <>
    struct adl_serializer<Transport_e>
    {
        static void from_json(const json& value, Transport_e& result)
        {
            const auto transport = TransportNames::Find(value.get<std::string>());
            if (!transport)
            {
                throw json::type_error::create(TYPE_ERROR_ID, std::format("must be {}", TransportNames::CHOICES), &value);
            }

            result = *transport;
        }

        static void to_json(ordered_json& value, Transport_e transport)
        {
            value = std::string{TransportNames::GetName(transport)};
        }
    };

    template <>
    struct adl_serializer<std::chrono::seconds>
    {
        static void from_json(const json& value, std::chrono::seconds& result)
        {
            result = std::chrono::seconds{value.get<s64>()};
        }

        static void to_json(ordered_json& value, std::chrono::seconds source)
        {
            value = source.count();
        }
    };

    template <>
    struct adl_serializer<std::chrono::minutes>
    {
        static void from_json(const json& value, std::chrono::minutes& result)
        {
            result = std::chrono::minutes{value.get<s64>()};
        }

        static void to_json(ordered_json& value, std::chrono::minutes source)
        {
            value = source.count();
        }
    };

    template <>
    struct adl_serializer<std::chrono::milliseconds>
    {
        static void from_json(const json& value, std::chrono::milliseconds& result)
        {
            result = std::chrono::milliseconds{value.get<s64>()};
        }

        static void to_json(ordered_json& value, std::chrono::milliseconds source)
        {
            value = source.count();
        }
    };
}

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ServerSettings_s, transport, host, port, origin, tlsCaFile)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ProxySettings_s, host, port, username, password)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(AccountSettings_s, username, password)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(LoginSettings_s, rsaModulus, rsaExponent, lowMemory, revision)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ClientSettings_s, logLevel, cacheDirectory, navDirectory, logFile)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ScriptingSettings_s, accountsDirectory, scriptsDirectory, callTimeoutMs, pollIntervalMs, loginIntervalSeconds, killGraceSeconds, connectAttempts, reloginDelaySeconds, progressDirectory, experienceDirectory, experienceIntervalMinutes, bankLogDirectory, inventoryDirectory, inventoryIntervalSeconds, equipmentDirectory)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Config_s, server, proxy, login, client, scripting)

// An account's own copy of a client.jsonc section. Missing or null keeps client.jsonc's, and a key the object leaves
// out takes the section's default.
template <typename TSection>
std::optional<TSection> ReadSection(const nlohmann::json& account, std::string_view key)
{
    const auto section = account.find(key);
    if (section == account.end() || section->is_null())
    {
        return std::nullopt;
    }

    if (!section->is_object())
    {
        throw nlohmann::json::type_error::create(TYPE_ERROR_ID, "must be an object", &*section);
    }

    return section->get<TSection>();
}

// Account files are only read, and a script's settings can be any object, so they convert by hand.
void from_json(const nlohmann::json& value, ScriptConfig_s& script)
{
    script.file = value.value("file", std::string{});
    script.progressReportMinutes = std::chrono::minutes{value.value("progressReportMinutes", s64{0})};

    const auto settings = value.find("settings");
    if (settings == value.end())
    {
        return;
    }

    if (!settings->is_object())
    {
        throw nlohmann::json::type_error::create(TYPE_ERROR_ID, "must be an object", &*settings);
    }

    script.settings = settings->dump();
}

void from_json(const nlohmann::json& value, AccountConfig_s& account)
{
    value.get_to(account.credentials);
    account.enabled = value.value("enabled", account.enabled);
    account.idleSeconds = value.value("idleSeconds", account.idleSeconds);
    account.randomEvents = value.value("randomEvents", account.randomEvents);
    account.stallMinutes = value.value("stallMinutes", account.stallMinutes);
    account.runAuto = value.value("runAuto", account.runAuto);
    account.runEnergyMin = value.value("runEnergyMin", account.runEnergyMin);

    account.server = ReadSection<ServerSettings_s>(value, "server");
    account.proxy = ReadSection<ProxySettings_s>(value, "proxy");

    const auto script = value.find("script");
    if (script == value.end() || script->is_null())
    {
        return;
    }

    if (!script->is_object())
    {
        throw nlohmann::json::type_error::create(TYPE_ERROR_ID, "must be an object", &*script);
    }

    account.script = script->get<ScriptConfig_s>();
}

Config_s ConfigJson::ParseConfig(std::string_view text)
{
    const auto root = ParseRootObject(text);
    auto config = Config_s{};
    try
    {
        root.get_to(config);
    }
    catch (const nlohmann::json::exception& e)
    {
        throw ConfigError{DescribeConversionError(e)};
    }

    return config;
}

AccountConfig_s ConfigJson::ParseAccount(std::string_view text)
{
    const auto root = ParseRootObject(text);
    auto account = AccountConfig_s{};
    try
    {
        root.get_to(account);
    }
    catch (const nlohmann::json::exception& e)
    {
        throw ConfigError{DescribeConversionError(e)};
    }

    return account;
}

std::string ConfigJson::SerializeConfig(const Config_s& config)
{
    // Parentheses, not braces: a braced ordered_json is an array holding the config.
    const auto document = nlohmann::ordered_json(config);
    return document.dump(INDENT) + '\n';
}

void ConfigJson::CheckObject(std::string_view text)
{
    static_cast<void>(ParseRootObject(text));
}

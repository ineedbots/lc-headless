#include "pch.hpp"
#include "ConfigFile.hpp"

#include "BigUInt.hpp"
#include "ConfigError.hpp"
#include "Logger.hpp"

#include <ixwebsocket/IXUrlParser.h>
#include <nlohmann/json.hpp>

namespace
{
    constexpr auto INDENT = 4;
    constexpr auto ALLOW_EXCEPTIONS = true;
    constexpr auto IGNORE_COMMENTS = true;
    constexpr auto TYPE_ERROR_ID = 302;
    constexpr auto SAMPLE_HEADER =
        "// Sample config, written because none was found.\n"
        "// Set server.url and the login RSA key, put the server's cache in client.cacheDirectory, then run again.\n"
        "// Each account goes in its own file in scripting.accountsDirectory.\n"sv;
    constexpr auto MAX_USERNAME_LENGTH = std::size_t{12};
    constexpr auto MAX_PASSWORD_LENGTH = std::size_t{20};
    constexpr auto MIN_IDLE_SECONDS = 1s;
    constexpr auto MAX_IDLE_SECONDS = 300s;
    constexpr auto MIN_CALL_TIMEOUT = 10ms;
    constexpr auto MAX_CALL_TIMEOUT = 60000ms;
    constexpr auto MIN_POLL_INTERVAL = 1ms;
    constexpr auto MAX_POLL_INTERVAL = 1000ms;
    constexpr auto MAX_LOGIN_INTERVAL = 60s;
    constexpr auto MAX_KILL_GRACE = 600s;
    constexpr auto MAX_PROGRESS_REPORT_INTERVAL = std::chrono::minutes{24 * 60};
    constexpr auto LEGACY_ACCOUNT_KEY = "account";
    constexpr auto FIRST_PRINTABLE = '\x20';
    constexpr auto LAST_PRINTABLE = '\x7E';
    constexpr auto SECURE_SCHEME = "wss"sv;
    constexpr auto NO_TLS_VERIFICATION = "NONE"sv;

    struct LogLevelName_s
    {
        LogLevel_e level;
        std::string_view name;
    };

    // Keys that moved to the cache, which a config written before then still has.
    struct LegacyKey_s
    {
        std::string_view section;
        std::string_view key;
        std::string_view replacement;
    };

    constexpr auto LEGACY_KEYS = std::array{
        LegacyKey_s{"login", "crcs", "the CRCs come from the cache in client.cacheDirectory"},
        LegacyKey_s{"client", "logoutComponent", "the logout button comes from the cache in client.cacheDirectory"},
    };

    constexpr auto LOG_LEVEL_NAMES = std::array{
        LogLevelName_s{LogLevel_e::Verbose, "verbose"},
        LogLevelName_s{LogLevel_e::Info, "info"},
        LogLevelName_s{LogLevel_e::Warning, "warning"},
        LogLevelName_s{LogLevel_e::Error, "error"},
    };

    struct TextPosition_s
    {
        std::size_t line;
        std::size_t column;
    };

    std::string FormatHex(const BigUInt& value)
    {
        const auto bytes = value.ToBytesBigEndian();
        const auto first = std::ranges::find_if(bytes, [](u8 byte)
        {
            return byte != 0;
        });

        if (first == bytes.end())
        {
            return "0x0";
        }

        auto text = std::format("0x{:x}", *first);
        for (auto byte = std::next(first); byte != bytes.end(); ++byte)
        {
            std::format_to(std::back_inserter(text), "{:02x}", *byte);
        }

        return text;
    }

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

    void Check(bool valid, std::string_view path, std::string_view rule)
    {
        if (valid)
        {
            return;
        }

        throw ConfigError{std::format("{}: {}", path, rule)};
    }

    bool IsPrintableAscii(std::string_view text)
    {
        return std::ranges::all_of(text, [](char character)
        {
            return character >= FIRST_PRINTABLE && character <= LAST_PRINTABLE;
        });
    }

    bool IsCredential(std::string_view text, std::size_t maxLength)
    {
        return !text.empty() && text.size() <= maxLength && IsPrintableAscii(text);
    }

    std::optional<std::string> GetUrlScheme(const std::string& url)
    {
        auto protocol = std::string{};
        auto host = std::string{};
        auto path = std::string{};
        auto query = std::string{};
        auto port = 0;
        if (!ix::UrlParser::parse(url, protocol, host, path, query, port))
        {
            return std::nullopt;
        }

        return protocol;
    }

    bool IsWebSocketUrl(const std::string& url)
    {
        const auto scheme = GetUrlScheme(url);
        return scheme == "ws" || scheme == SECURE_SCHEME;
    }

    void ValidateServer(const ServerSettings_s& server)
    {
        Check(IsWebSocketUrl(server.url), "server.url", "must be a ws:// or wss:// URL");
        Check(server.origin.empty() || IsPrintableAscii(server.origin), "server.origin", "must be empty or printable ASCII");
        Check(!server.tlsCaFile.empty(), "server.tlsCaFile", "must be a PEM file path, SYSTEM or NONE");
    }

    void Validate(const Config_s& config)
    {
        ValidateServer(config.server);

        const auto& login = config.login;
        const auto one = BigUInt::Parse("1");
        Check(login.rsaModulus > one, "login.rsaModulus", "must be greater than 1");
        Check(login.rsaExponent > BigUInt{}, "login.rsaExponent", "must be greater than 0");
        Check(login.revision == LoginSettings_s::SUPPORTED_REVISION, "login.revision", std::format("must be {}", LoginSettings_s::SUPPORTED_REVISION));

        const auto& client = config.client;
        Check(client.idleSeconds >= MIN_IDLE_SECONDS && client.idleSeconds <= MAX_IDLE_SECONDS, "client.idleSeconds", std::format("must be from {} to {}", MIN_IDLE_SECONDS.count(), MAX_IDLE_SECONDS.count()));
        Check(!client.cacheDirectory.empty(), "client.cacheDirectory", "must not be empty");
        Check(!client.navDirectory.empty(), "client.navDirectory", "must not be empty");

        const auto& scripting = config.scripting;
        Check(!scripting.accountsDirectory.empty(), "scripting.accountsDirectory", "must be a folder path");
        Check(!scripting.scriptsDirectory.empty(), "scripting.scriptsDirectory", "must be a folder path");
        Check(scripting.callTimeoutMs >= MIN_CALL_TIMEOUT && scripting.callTimeoutMs <= MAX_CALL_TIMEOUT, "scripting.callTimeoutMs", std::format("must be from {} to {}", MIN_CALL_TIMEOUT.count(), MAX_CALL_TIMEOUT.count()));
        Check(scripting.pollIntervalMs >= MIN_POLL_INTERVAL && scripting.pollIntervalMs <= MAX_POLL_INTERVAL, "scripting.pollIntervalMs", std::format("must be from {} to {}", MIN_POLL_INTERVAL.count(), MAX_POLL_INTERVAL.count()));
        Check(scripting.loginIntervalSeconds >= 0s && scripting.loginIntervalSeconds <= MAX_LOGIN_INTERVAL, "scripting.loginIntervalSeconds", std::format("must be from 0 to {}", MAX_LOGIN_INTERVAL.count()));
        Check(scripting.killGraceSeconds >= 0s && scripting.killGraceSeconds <= MAX_KILL_GRACE, "scripting.killGraceSeconds", std::format("must be from 0 to {}", MAX_KILL_GRACE.count()));
        Check(!scripting.progressDirectory.empty(), "scripting.progressDirectory", "must be a folder path");
    }

    void ValidateAccount(const AccountConfig_s& account)
    {
        const auto& credentials = account.credentials;
        Check(IsCredential(credentials.username, MAX_USERNAME_LENGTH), "username", std::format("must be 1 to {} printable ASCII characters", MAX_USERNAME_LENGTH));
        Check(IsCredential(credentials.password, MAX_PASSWORD_LENGTH), "password", std::format("must be 1 to {} printable ASCII characters", MAX_PASSWORD_LENGTH));
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

    void WarnIfLegacyAccount(const nlohmann::json& root, Logger& logger)
    {
        if (!root.contains(LEGACY_ACCOUNT_KEY))
        {
            return;
        }

        logger.Warning("Config has an account section, which is no longer read; move it to its own file in scripting.accountsDirectory");
    }

    void WarnIfLegacyKeys(const nlohmann::json& root, Logger& logger)
    {
        for (const auto& legacy : LEGACY_KEYS)
        {
            const auto section = root.find(legacy.section);
            if (section == root.end() || !section->is_object() || !section->contains(legacy.key))
            {
                continue;
            }

            logger.Warning("Config has {}.{}, which is no longer read; {}", legacy.section, legacy.key, legacy.replacement);
        }
    }

    void WarnIfTlsVerificationDisabled(const Config_s& config, Logger& logger)
    {
        if (GetUrlScheme(config.server.url) != SECURE_SCHEME || config.server.tlsCaFile != NO_TLS_VERIFICATION)
        {
            return;
        }

        logger.Warning("Config disables TLS certificate verification (server.tlsCaFile is NONE)");
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

    std::string ReadFile(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path, std::ios::binary};
        if (!file)
        {
            throw ConfigError{std::format("Failed to open config file {}", path.string())};
        }

        auto text = std::string{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
        if (file.bad())
        {
            throw ConfigError{std::format("Failed to read config file {}", path.string())};
        }

        return text;
    }

    void WriteSample(const std::filesystem::path& path)
    {
        // A stream that failed to open ignores the writes, so one check covers opening and writing.
        auto file = std::ofstream{path, std::ios::binary};
        file << SAMPLE_HEADER << ConfigFile::Serialize(Config_s{});
        file.flush();
        if (!file)
        {
            throw ConfigError{std::format("{}: not found, and a sample couldn't be written there", path.string())};
        }
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
            value = FormatHex(source);
        }
    };

    template <>
    struct adl_serializer<LogLevel_e>
    {
        static void from_json(const json& value, LogLevel_e& result)
        {
            const auto name = value.get<std::string>();
            const auto entry = std::ranges::find(LOG_LEVEL_NAMES, name, &LogLevelName_s::name);
            if (entry == LOG_LEVEL_NAMES.end())
            {
                throw json::type_error::create(TYPE_ERROR_ID, "must be verbose, info, warning or error", &value);
            }

            result = entry->level;
        }

        static void to_json(ordered_json& value, LogLevel_e level)
        {
            const auto entry = std::ranges::find(LOG_LEVEL_NAMES, level, &LogLevelName_s::level);
            assert(entry != LOG_LEVEL_NAMES.end() && "LogLevel_e value missing from LOG_LEVEL_NAMES");
            value = std::string{entry->name};
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

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ServerSettings_s, url, origin, tlsCaFile)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(AccountSettings_s, username, password)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(LoginSettings_s, rsaModulus, rsaExponent, lowMemory, revision)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ClientSettings_s, logLevel, idleSeconds, cacheDirectory, navDirectory)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ScriptingSettings_s, accountsDirectory, scriptsDirectory, callTimeoutMs, pollIntervalMs, loginIntervalSeconds, killGraceSeconds, progressDirectory)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Config_s, server, login, client, scripting)

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
    account.enabled = value.value("enabled", true);
    const auto server = value.find("server");
    if (server != value.end() && !server->is_null())
    {
        if (!server->is_object())
        {
            throw nlohmann::json::type_error::create(TYPE_ERROR_ID, "must be an object", &*server);
        }

        account.server = server->get<ServerSettings_s>();
    }

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

Config_s ConfigFile::Load(const std::filesystem::path& path, Logger& logger)
{
    if (!std::filesystem::exists(path))
    {
        WriteSample(path);
        throw ConfigError{std::format("{}: not found, so a sample was written there; fill it in and run again", path.string())};
    }

    const auto text = ReadFile(path);
    try
    {
        return Parse(text, logger);
    }
    catch (const ConfigError& e)
    {
        throw ConfigError{std::format("{}: {}", path.string(), e.what())};
    }
}

Config_s ConfigFile::Parse(std::string_view text, Logger& logger)
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

    Validate(config);
    WarnIfTlsVerificationDisabled(config, logger);
    WarnIfLegacyAccount(root, logger);
    WarnIfLegacyKeys(root, logger);
    return config;
}

std::string ConfigFile::Serialize(const Config_s& config)
{
    // Parentheses, not braces: a braced ordered_json is an array holding the config.
    const auto document = nlohmann::ordered_json(config);
    return document.dump(INDENT) + '\n';
}

AccountConfig_s ConfigFile::LoadAccount(const std::filesystem::path& path)
{
    if (!std::filesystem::exists(path))
    {
        throw ConfigError{std::format("{}: account file not found", path.string())};
    }

    const auto text = ReadFile(path);
    try
    {
        return ParseAccount(text, path.stem().string());
    }
    catch (const ConfigError& e)
    {
        throw ConfigError{std::format("{}: {}", path.string(), e.what())};
    }
}

AccountConfig_s ConfigFile::ParseAccount(std::string_view text, std::string name)
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

    account.name = std::move(name);
    ValidateAccount(account);
    return account;
}

#include "pch.hpp"
#include "../DefaultLoggerScope.hpp"
#include "../LogCapture.hpp"
#include "../TempFolder.hpp"

#include "Core/BigUInt.hpp"
#include "Core/ConfigError.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_tostring.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <nlohmann/json.hpp>

namespace
{
    constexpr auto EXAMPLE = R"json({
    "server": {
        "url": "ws://localhost:80",
        // "url": "ws://127.0.0.1:80",
        // "origin": "http://localhost",
        // "url": "wss://w1.rs2b2t.com:443",
        "origin": "https://w1.rs2b2t.com",
        "tlsCaFile": "SYSTEM"
    },
    "login": {
        "rsaModulus": "0x88c38748a58228f7261cdc340b5691d7d0975dee0ecdb717609e6bf971eb3fe723ef9d130e4686813739768ad9472eb46d8bfcc042c1a5fcb05e931f632eea5d",
        "rsaExponent": "0x81f390b2cf8ca7039ee507975951d5a0b15a87bf8b3f99c966834118c50fd94d",
        /*
        "rsaModulus": "0xa7366d28aee360c6a5a49fadaac884826573f09870f3a031aece6d146277d85b6f79dae141769b16210046f6739d23b4b0d1160ef94c44771b9e6ecbd1917ba64eca7aab1c0265c8ef0205ab4f1033440fd9fe719f01554b9c50aa17cb8bd6cc5c7602831f94ae49121a8755ee9e76697b9af7848c85da834ca6ae9a1e33d32d",
        "rsaExponent": "0x10001",
        */
        "lowMemory": false,
        "revision": 289
    },
    "client": {
        "logLevel": "verbose",
        "idleSeconds": 5,
        "cacheDirectory": "../289server/engine/data/pack"
    },
    "scripting": {
        "accountsDirectory": "bots",
        "scriptsDirectory": "my-scripts",
        "callTimeoutMs": 500,
        "pollIntervalMs": 20,
        "loginIntervalSeconds": 5,
        "killGraceSeconds": 60,
        "progressDirectory": "reports"
    }
}
)json"sv;

    constexpr auto SAMPLE_HEADER =
        "// Sample config, written because none was found.\n"
        "// Set server.url and the login RSA key, put the server's cache in client.cacheDirectory, then run again.\n"
        "// Each account goes in its own file in scripting.accountsDirectory.\n"sv;

    constexpr auto SAMPLE_BODY = R"json({
    "server": {
        "url": "",
        "origin": "",
        "tlsCaFile": "SYSTEM"
    },
    "login": {
        "rsaModulus": "0x0",
        "rsaExponent": "0x0",
        "lowMemory": false,
        "revision": 289
    },
    "client": {
        "logLevel": "info",
        "idleSeconds": 5,
        "cacheDirectory": "cache",
        "navDirectory": "data/nav"
    },
    "scripting": {
        "accountsDirectory": "accounts",
        "scriptsDirectory": "scripts",
        "callTimeoutMs": 1000,
        "pollIntervalMs": 10,
        "loginIntervalSeconds": 2,
        "killGraceSeconds": 30,
        "progressDirectory": "progress",
        "randomEvents": true
    }
}
)json"sv;

    constexpr auto MINIMAL = R"json({
    "server": {"url": "ws://localhost:80"},
    "login": {
        "rsaModulus": "0x88c38748a58228f7261cdc340b5691d7d0975dee0ecdb717609e6bf971eb3fe723ef9d130e4686813739768ad9472eb46d8bfcc042c1a5fcb05e931f632eea5d",
        "rsaExponent": "0x81f390b2cf8ca7039ee507975951d5a0b15a87bf8b3f99c966834118c50fd94d"
    }
})json"sv;

    constexpr auto ACCOUNT_EXAMPLE = R"json({
    // The account and what it runs.
    "username": "bot1",
    "password": "s3cret-pw",
    "enabled": false,
    "script": {
        "file": "examples/chicken_killer.py",
        "progressReportMinutes": 20,
        "settings": {"npc_ids": [41], "loot": true, "area": {"x": 3230, "z": 3298}, "name": "chickens"}
    }
})json"sv;

    constexpr auto EXAMPLE_MODULUS = "0x88c38748a58228f7261cdc340b5691d7d0975dee0ecdb717609e6bf971eb3fe723ef9d130e4686813739768ad9472eb46d8bfcc042c1a5fcb05e931f632eea5d";
    constexpr auto EXAMPLE_EXPONENT = "0x81f390b2cf8ca7039ee507975951d5a0b15a87bf8b3f99c966834118c50fd94d";
    constexpr auto SECRET_PASSWORD = "s3cret-pw";
    constexpr auto UTF8_E_ACUTE = "\xC3\xA9";
    constexpr auto BOM = "\xEF\xBB\xBF"sv;

    struct KeyPath_s
    {
        std::string section;
        std::string key;

        [[nodiscard]] std::string GetPath() const
        {
            return std::format("{}.{}", section, key);
        }
    };

    struct Rejection_s
    {
        KeyPath_s key;
        nlohmann::json value;
    };

    struct WrittenForm_s
    {
        std::string_view description;
        std::function<void(Config_s&)> set;
        std::string pointer;
        std::string written;
    };

    const auto MUST_SET_KEYS = std::vector<KeyPath_s>{
        {"server", "url"},
        {"login", "rsaModulus"},
        {"login", "rsaExponent"},
    };

    const auto OPTIONAL_KEYS = std::vector<KeyPath_s>{
        {"server", "origin"},
        {"server", "tlsCaFile"},
        {"login", "lowMemory"},
        {"login", "revision"},
        {"client", "logLevel"},
        {"client", "idleSeconds"},
        {"client", "cacheDirectory"},
        {"scripting", "accountsDirectory"},
        {"scripting", "scriptsDirectory"},
        {"scripting", "callTimeoutMs"},
        {"scripting", "pollIntervalMs"},
        {"scripting", "loginIntervalSeconds"},
        {"scripting", "killGraceSeconds"},
        {"scripting", "progressDirectory"},
    };

    nlohmann::json ParseJsonWithComments(std::string_view text)
    {
        return nlohmann::json::parse(text, nullptr, true, true);
    }

    nlohmann::json MakeBase()
    {
        return ParseJsonWithComments(EXAMPLE);
    }

    std::string EditBase(const std::function<void(nlohmann::json&)>& edit)
    {
        auto json = MakeBase();
        edit(json);
        return json.dump();
    }

    std::string SetKey(const KeyPath_s& key, nlohmann::json value)
    {
        return EditBase([&](nlohmann::json& json)
        {
            json[key.section][key.key] = std::move(value);
        });
    }

    std::string RemoveKey(const KeyPath_s& key)
    {
        return EditBase([&](nlohmann::json& json)
        {
            json[key.section].erase(key.key);
        });
    }

    std::string ReplaceAll(std::string text, std::string_view from, std::string_view to)
    {
        for (auto pos = text.find(from); pos != std::string::npos; pos = text.find(from, pos + to.size()))
        {
            text.replace(pos, from.size(), to);
        }

        return text;
    }

    std::string ToUpper(std::string text)
    {
        std::ranges::transform(text, text.begin(), [](char character)
        {
            return character >= 'a' && character <= 'z' ? static_cast<char>(character - 'a' + 'A') : character;
        });

        return text;
    }

    bool HasSecret(std::string_view text)
    {
        return text.find(SECRET_PASSWORD) != std::string_view::npos;
    }

    bool HasSecret(const LogCapture& capture)
    {
        return std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return HasSecret(entry.message);
        });
    }

    Config_s ParseAccepted(std::string_view text)
    {
        auto capture = LogCapture{};
        auto config = ConfigFile::Parse(text, *capture.GetLogger());
        CHECK(capture.GetEntries().empty());
        return config;
    }

    void CheckRejected(std::string_view text, const std::string& path)
    {
        auto capture = LogCapture{};
        const auto logger = capture.GetLogger();
        CHECK_THROWS_AS(ConfigFile::Parse(text, *logger), ConfigError);
        CHECK_THROWS_WITH(ConfigFile::Parse(text, *logger), Catch::Matchers::ContainsSubstring(path) && !Catch::Matchers::ContainsSubstring(SECRET_PASSWORD));
        CHECK_FALSE(HasSecret(capture));
    }

    void CheckSyntaxError(std::string_view text, std::string_view position = {})
    {
        auto capture = LogCapture{};
        CHECK_THROWS_AS(ConfigFile::Parse(text, *capture.GetLogger()), ConfigError);
        if (!position.empty())
        {
            CHECK_THROWS_WITH(ConfigFile::Parse(text, *capture.GetLogger()), Catch::Matchers::ContainsSubstring(std::string{position}));
        }
    }

    void CheckExampleMembers(const Config_s& config)
    {
        CHECK(config.server.url == "ws://localhost:80");
        CHECK(config.server.origin == "https://w1.rs2b2t.com");
        CHECK(config.server.tlsCaFile == "SYSTEM");
        CHECK(config.login.rsaModulus == BigUInt::Parse(EXAMPLE_MODULUS));
        CHECK(config.login.rsaExponent == BigUInt::Parse(EXAMPLE_EXPONENT));
        CHECK_FALSE(config.login.lowMemory);
        CHECK(config.login.revision == 289);
        CHECK(config.client.logLevel == LogLevel_e::Verbose);
        CHECK(config.client.idleSeconds == 5s);
        CHECK(config.client.cacheDirectory == "../289server/engine/data/pack");
        CHECK(config.scripting.accountsDirectory == "bots");
        CHECK(config.scripting.scriptsDirectory == "my-scripts");
        CHECK(config.scripting.callTimeoutMs == 500ms);
        CHECK(config.scripting.pollIntervalMs == 20ms);
        CHECK(config.scripting.loginIntervalSeconds == 5s);
        CHECK(config.scripting.killGraceSeconds == 60s);
        CHECK(config.scripting.progressDirectory == "reports");
    }

    void CheckScriptingDefaults(const ScriptingSettings_s& scripting)
    {
        CHECK(scripting.accountsDirectory == "accounts");
        CHECK(scripting.scriptsDirectory == "scripts");
        CHECK(scripting.callTimeoutMs == 1000ms);
        CHECK(scripting.pollIntervalMs == 10ms);
        CHECK(scripting.loginIntervalSeconds == 2s);
        CHECK(scripting.killGraceSeconds == 30s);
        CHECK(scripting.progressDirectory == "progress");
    }

    void CheckOptionalDefaults(const Config_s& config)
    {
        CHECK(config.server.origin.empty());
        CHECK(config.server.tlsCaFile == "SYSTEM");
        CHECK_FALSE(config.login.lowMemory);
        CHECK(config.login.revision == 289);
        CHECK(config.client.logLevel == LogLevel_e::Info);
        CHECK(config.client.idleSeconds == 5s);
        CHECK(config.client.cacheDirectory == "cache");
        CheckScriptingDefaults(config.scripting);
    }

    std::string EditAccount(const std::function<void(nlohmann::json&)>& edit)
    {
        auto json = ParseJsonWithComments(ACCOUNT_EXAMPLE);
        edit(json);
        return json.dump();
    }

    std::string SetAccountKey(const std::string& key, nlohmann::json value)
    {
        return EditAccount([&](nlohmann::json& json)
        {
            json[key] = std::move(value);
        });
    }

    std::string SetScriptKey(const std::string& key, nlohmann::json value)
    {
        return EditAccount([&](nlohmann::json& json)
        {
            json["script"][key] = std::move(value);
        });
    }

    void CheckAccountRejected(std::string_view text, const std::string& path)
    {
        CHECK_THROWS_AS(ConfigFile::ParseAccount(text, "bot1"), ConfigError);
        CHECK_THROWS_WITH(ConfigFile::ParseAccount(text, "bot1"), Catch::Matchers::ContainsSubstring(path) && !Catch::Matchers::ContainsSubstring(SECRET_PASSWORD));
    }

    void WriteFile(const std::filesystem::path& path, std::string_view text)
    {
        auto file = std::ofstream{path, std::ios::binary};
        file << text;
    }

    std::string ReadFile(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path, std::ios::binary};
        return std::string{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
    }
}

CATCH_REGISTER_ENUM(LogLevel_e, LogLevel_e::Verbose, LogLevel_e::Info, LogLevel_e::Warning, LogLevel_e::Error)

TEST_CASE("ConfigFile parses the complete example", "[ConfigFile]")
{
    CheckExampleMembers(ParseAccepted(EXAMPLE));
}

TEST_CASE("ConfigFile parses a file with only the keys that must be set", "[ConfigFile]")
{
    const auto config = ParseAccepted(MINIMAL);

    CHECK(config.server.url == "ws://localhost:80");
    CHECK(config.login.rsaModulus == BigUInt::Parse(EXAMPLE_MODULUS));
    CHECK(config.login.rsaExponent == BigUInt::Parse(EXAMPLE_EXPONENT));
    CheckOptionalDefaults(config);
}

TEST_CASE("ConfigFile syntax", "[ConfigFile]")
{
    SECTION("comments on their own lines, after values, and across lines")
    {
        const auto text = ReplaceAll(std::string{EXAMPLE}, "\"tlsCaFile\": \"SYSTEM\"", "\"tlsCaFile\": \"SYSTEM\" // trailing comment\n        /* a comment\n           over two lines */");
        CheckExampleMembers(ParseAccepted(text));
    }

    SECTION("a line comment at the end without a newline")
    {
        CheckExampleMembers(ParseAccepted(std::string{EXAMPLE} + "// the end"));
    }

    SECTION("a UTF-8 byte order mark")
    {
        CheckExampleMembers(ParseAccepted(std::string{BOM} + std::string{EXAMPLE}));
    }

    SECTION("CRLF line endings")
    {
        CheckExampleMembers(ParseAccepted(ReplaceAll(std::string{EXAMPLE}, "\n", "\r\n")));
    }

    SECTION("a # comment is an error")
    {
        CheckSyntaxError("# comment\n" + std::string{EXAMPLE});
    }

    SECTION("JSON5 forms are errors")
    {
        CheckSyntaxError("{'a': 1}");
        CheckSyntaxError("{a: 1}");
        CheckSyntaxError("{\"a\": 1 /* unclosed");
    }

    SECTION("errors give the line and column")
    {
        CheckSyntaxError("", "line 1, column 1");
        CheckSyntaxError("{\n\"a\": 1,\n}", "line 3, column 1");
        CheckSyntaxError("// first\n{\n\"a\": 1,\n}", "line 4, column 1");
        CheckSyntaxError("{\r\n\"a\": 1,\r\n}", "line 3, column 1");
    }

    SECTION("the top level must be an object")
    {
        CheckSyntaxError("[]");
        CheckSyntaxError("5");
        CheckSyntaxError("\"x\"");
        CheckSyntaxError("null");
    }
}

TEST_CASE("ConfigFile structure", "[ConfigFile]")
{
    SECTION("each key that must be set fails when missing")
    {
        for (const auto& key : MUST_SET_KEYS)
        {
            CAPTURE(key.GetPath());
            CheckRejected(RemoveKey(key), key.GetPath());
        }
    }

    SECTION("each other key takes its default when missing")
    {
        for (const auto& key : OPTIONAL_KEYS)
        {
            CAPTURE(key.GetPath());
            const auto config = ParseAccepted(RemoveKey(key));
            if (key.key == "origin")
            {
                CHECK(config.server.origin.empty());
            }
            else if (key.key == "tlsCaFile")
            {
                CHECK(config.server.tlsCaFile == "SYSTEM");
            }
            else if (key.key == "lowMemory")
            {
                CHECK_FALSE(config.login.lowMemory);
            }
            else if (key.key == "revision")
            {
                CHECK(config.login.revision == 289);
            }
            else if (key.key == "logLevel")
            {
                CHECK(config.client.logLevel == LogLevel_e::Info);
            }
            else if (key.key == "idleSeconds")
            {
                CHECK(config.client.idleSeconds == 5s);
            }
            else if (key.key == "cacheDirectory")
            {
                CHECK(config.client.cacheDirectory == "cache");
            }
            else if (key.key == "accountsDirectory")
            {
                CHECK(config.scripting.accountsDirectory == "accounts");
            }
            else if (key.key == "scriptsDirectory")
            {
                CHECK(config.scripting.scriptsDirectory == "scripts");
            }
            else if (key.key == "callTimeoutMs")
            {
                CHECK(config.scripting.callTimeoutMs == 1000ms);
            }
            else if (key.key == "pollIntervalMs")
            {
                CHECK(config.scripting.pollIntervalMs == 10ms);
            }
            else if (key.key == "loginIntervalSeconds")
            {
                CHECK(config.scripting.loginIntervalSeconds == 2s);
            }
            else if (key.key == "killGraceSeconds")
            {
                CHECK(config.scripting.killGraceSeconds == 30s);
            }
            else if (key.key == "progressDirectory")
            {
                CHECK(config.scripting.progressDirectory == "progress");
            }
        }
    }

    SECTION("a missing section fails on the first rule its defaults break")
    {
        const auto removeSection = [](std::string section)
        {
            return EditBase([&](nlohmann::json& json)
            {
                json.erase(section);
            });
        };

        CheckRejected(removeSection("server"), "server.url");
        CheckRejected(removeSection("login"), "login.rsaModulus");

        const auto config = ParseAccepted(removeSection("client"));
        CHECK(config.client.logLevel == LogLevel_e::Info);
        CHECK(config.client.idleSeconds == 5s);
        CHECK(config.client.cacheDirectory == "cache");

        CheckScriptingDefaults(ParseAccepted(removeSection("scripting")).scripting);
    }

    SECTION("an empty object fails on server.url")
    {
        CheckRejected("{}", "server.url");
    }

    SECTION("a section that isn't an object")
    {
        CheckRejected(EditBase([](nlohmann::json& json)
        {
            json["server"] = nlohmann::json::array();
        }), "server");
        CheckRejected(EditBase([](nlohmann::json& json)
        {
            json["login"] = "x";
        }), "login");
    }

    SECTION("a key set to null is a wrong type")
    {
        auto allKeys = MUST_SET_KEYS;
        allKeys.insert(allKeys.end(), OPTIONAL_KEYS.begin(), OPTIONAL_KEYS.end());
        for (const auto& key : allKeys)
        {
            CAPTURE(key.GetPath());
            CheckRejected(SetKey(key, nullptr), key.GetPath());
        }
    }

    SECTION("unknown sections and keys are ignored")
    {
        const auto config = ParseAccepted(EditBase([](nlohmann::json& json)
        {
            json["extra"] = {{"url", "x"}};
        }));
        CheckExampleMembers(config);
    }

    SECTION("a misspelled key is ignored, and its member keeps the default")
    {
        const auto config = ParseAccepted(EditBase([](nlohmann::json& json)
        {
            json["client"].erase("idleSeconds");
            json["client"]["idleSecond"] = 30;
        }));
        CHECK(config.client.idleSeconds == 5s);

        CheckRejected(EditBase([](nlohmann::json& json)
        {
            json["server"].erase("url");
            json["server"]["uri"] = "ws://localhost:80";
        }), "server.url");
    }

    SECTION("section names are case-sensitive")
    {
        CheckRejected(EditBase([](nlohmann::json& json)
        {
            json["Server"] = json["server"];
            json.erase("server");
        }), "server.url");
    }

    SECTION("a repeated key takes its last value")
    {
        const auto text = ReplaceAll(std::string{EXAMPLE}, "\"tlsCaFile\": \"SYSTEM\"", "\"tlsCaFile\": \"SYSTEM\",\n        \"url\": \"ws://other:80\"");
        CHECK(ParseAccepted(text).server.url == "ws://other:80");
    }

    SECTION("wss with TLS verification turned off logs a warning")
    {
        const auto text = EditBase([](nlohmann::json& json)
        {
            json["server"]["url"] = "wss://w1.example.com:443";
            json["server"]["tlsCaFile"] = "NONE";
        });

        auto capture = LogCapture{};
        const auto config = ConfigFile::Parse(text, *capture.GetLogger());
        CHECK(config.server.tlsCaFile == "NONE");
        const auto entries = capture.GetEntries();
        REQUIRE(entries.size() == 1);
        CHECK(entries[0].level == LogLevel_e::Warning);
        CHECK_THAT(entries[0].message, Catch::Matchers::ContainsSubstring("server.tlsCaFile"));
    }

    SECTION("wss with the system trust store logs nothing")
    {
        ParseAccepted(SetKey({"server", "url"}, "wss://w1.example.com:443"));
    }

    SECTION("ws stores tlsCaFile as written, without a warning")
    {
        for (const auto* const caFile : {"NONE", "certs/ca.pem"})
        {
            CAPTURE(caFile);
            CHECK(ParseAccepted(SetKey({"server", "tlsCaFile"}, caFile)).server.tlsCaFile == caFile);
        }
    }
}

TEST_CASE("ConfigFile accepts valid values", "[ConfigFile]")
{
    SECTION("server")
    {
        for (const auto* const url : {"ws://localhost:80", "wss://w1.example.com:443/path"})
        {
            CHECK(ParseAccepted(SetKey({"server", "url"}, url)).server.url == url);
        }

        for (const auto* const origin : {"", "http://localhost"})
        {
            CHECK(ParseAccepted(SetKey({"server", "origin"}, origin)).server.origin == origin);
        }

        for (const auto* const caFile : {"SYSTEM", "NONE", "certs/ca.pem"})
        {
            CHECK(ParseAccepted(SetKey({"server", "tlsCaFile"}, caFile)).server.tlsCaFile == caFile);
        }
    }

    SECTION("scripting")
    {
        CHECK(ParseAccepted(SetKey({"scripting", "accountsDirectory"}, "C:/bots/accounts")).scripting.accountsDirectory == "C:/bots/accounts");
        CHECK(ParseAccepted(SetKey({"scripting", "scriptsDirectory"}, "../scripts")).scripting.scriptsDirectory == "../scripts");
        CHECK(ParseAccepted(SetKey({"scripting", "callTimeoutMs"}, 10)).scripting.callTimeoutMs == 10ms);
        CHECK(ParseAccepted(SetKey({"scripting", "callTimeoutMs"}, 60000)).scripting.callTimeoutMs == 60000ms);
        CHECK(ParseAccepted(SetKey({"scripting", "pollIntervalMs"}, 1)).scripting.pollIntervalMs == 1ms);
        CHECK(ParseAccepted(SetKey({"scripting", "pollIntervalMs"}, 1000)).scripting.pollIntervalMs == 1000ms);
        CHECK(ParseAccepted(SetKey({"scripting", "loginIntervalSeconds"}, 0)).scripting.loginIntervalSeconds == 0s);
        CHECK(ParseAccepted(SetKey({"scripting", "loginIntervalSeconds"}, 60)).scripting.loginIntervalSeconds == 60s);
        CHECK(ParseAccepted(SetKey({"scripting", "killGraceSeconds"}, 0)).scripting.killGraceSeconds == 0s);
        CHECK(ParseAccepted(SetKey({"scripting", "killGraceSeconds"}, 600)).scripting.killGraceSeconds == 600s);
        CHECK(ParseAccepted(SetKey({"scripting", "progressDirectory"}, "logs/progress")).scripting.progressDirectory == "logs/progress");
    }

    SECTION("login RSA values")
    {
        for (const auto* const modulus : {"3233", "0xca1", "0xCA1", "0XcA1"})
        {
            CAPTURE(modulus);
            CHECK(ParseAccepted(SetKey({"login", "rsaModulus"}, modulus)).login.rsaModulus == BigUInt::Parse("3233"));
        }

        for (const auto* const exponent : {"1", "0x10001"})
        {
            CAPTURE(exponent);
            CHECK(ParseAccepted(SetKey({"login", "rsaExponent"}, exponent)).login.rsaExponent == BigUInt::Parse(exponent));
        }
    }

    SECTION("login flags and revision")
    {
        CHECK(ParseAccepted(SetKey({"login", "lowMemory"}, true)).login.lowMemory);
        CHECK_FALSE(ParseAccepted(SetKey({"login", "lowMemory"}, false)).login.lowMemory);
        CHECK(ParseAccepted(SetKey({"login", "revision"}, 289)).login.revision == 289);
    }

    SECTION("client")
    {
        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "verbose")).client.logLevel == LogLevel_e::Verbose);
        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "info")).client.logLevel == LogLevel_e::Info);
        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "warning")).client.logLevel == LogLevel_e::Warning);
        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "error")).client.logLevel == LogLevel_e::Error);

        CHECK(ParseAccepted(SetKey({"client", "idleSeconds"}, 1)).client.idleSeconds == 1s);
        CHECK(ParseAccepted(SetKey({"client", "idleSeconds"}, 300)).client.idleSeconds == 300s);

        CHECK(ParseAccepted(SetKey({"client", "cacheDirectory"}, "C:/rs/pack")).client.cacheDirectory == "C:/rs/pack");
    }
}

TEST_CASE("ConfigFile rejects invalid values", "[ConfigFile]")
{
    const auto rejections = std::vector<Rejection_s>{
        {{"server", "url"}, "http://localhost:80"},
        {{"server", "url"}, "localhost:80"},
        {{"server", "url"}, ""},
        {{"server", "url"}, 80},
        {{"server", "origin"}, "http://ex\xC3\xA4mple"},
        {{"server", "origin"}, "a\tb"},
        {{"server", "origin"}, true},
        {{"server", "tlsCaFile"}, ""},
        {{"server", "tlsCaFile"}, 5},
        {{"login", "rsaModulus"}, "0"},
        {{"login", "rsaModulus"}, "1"},
        {{"login", "rsaModulus"}, ""},
        {{"login", "rsaModulus"}, "0xzz"},
        {{"login", "rsaModulus"}, 3233},
        {{"login", "rsaExponent"}, "0"},
        {{"login", "rsaExponent"}, ""},
        {{"login", "rsaExponent"}, 65537},
        {{"login", "lowMemory"}, 0},
        {{"login", "lowMemory"}, 1},
        {{"login", "lowMemory"}, "true"},
        {{"login", "revision"}, 288},
        {{"login", "revision"}, 290},
        {{"login", "revision"}, "289"},
        {{"login", "revision"}, true},
        {{"client", "logLevel"}, "warn"},
        {{"client", "logLevel"}, "Info"},
        {{"client", "logLevel"}, "debug"},
        {{"client", "logLevel"}, ""},
        {{"client", "logLevel"}, 2},
        {{"client", "idleSeconds"}, 0},
        {{"client", "idleSeconds"}, 301},
        {{"client", "idleSeconds"}, -5},
        {{"client", "idleSeconds"}, "5"},
        {{"client", "cacheDirectory"}, ""},
        {{"client", "cacheDirectory"}, 5},
        {{"scripting", "accountsDirectory"}, ""},
        {{"scripting", "accountsDirectory"}, 5},
        {{"scripting", "scriptsDirectory"}, ""},
        {{"scripting", "callTimeoutMs"}, 9},
        {{"scripting", "callTimeoutMs"}, 60001},
        {{"scripting", "callTimeoutMs"}, "1000"},
        {{"scripting", "pollIntervalMs"}, 0},
        {{"scripting", "pollIntervalMs"}, 1001},
        {{"scripting", "loginIntervalSeconds"}, -1},
        {{"scripting", "loginIntervalSeconds"}, 61},
        {{"scripting", "killGraceSeconds"}, -1},
        {{"scripting", "killGraceSeconds"}, 601},
        {{"scripting", "progressDirectory"}, ""},
        {{"scripting", "progressDirectory"}, 5},
    };

    for (const auto& rejection : rejections)
    {
        CAPTURE(rejection.key.GetPath(), rejection.value.dump());
        CheckRejected(SetKey(rejection.key, rejection.value), rejection.key.GetPath());
    }
}

TEST_CASE("ConfigFile warns about an account section left in the config", "[ConfigFile]")
{
    const auto text = EditBase([](nlohmann::json& json)
    {
        json["account"] = {{"username", "test"}, {"password", SECRET_PASSWORD}};
    });

    auto capture = LogCapture{};
    const auto config = ConfigFile::Parse(text, *capture.GetLogger());
    CheckExampleMembers(config);
    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 1);
    CHECK(entries[0].level == LogLevel_e::Warning);
    CHECK_THAT(entries[0].message, Catch::Matchers::ContainsSubstring("scripting.accountsDirectory"));
    CHECK_FALSE(HasSecret(capture));
}

TEST_CASE("ConfigFile warns about login.crcs left in the config", "[ConfigFile]")
{
    const auto text = SetKey({"login", "crcs"}, nlohmann::json::array({"0x00000000", "0xde5b3345"}));

    auto capture = LogCapture{};
    const auto config = ConfigFile::Parse(text, *capture.GetLogger());
    CheckExampleMembers(config);
    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 1);
    CHECK(entries[0].level == LogLevel_e::Warning);
    CHECK(entries[0].message == "Config has login.crcs, which is no longer read; the CRCs come from the cache in client.cacheDirectory");
}

TEST_CASE("ConfigFile warns about client.logoutComponent left in the config", "[ConfigFile]")
{
    const auto text = SetKey({"client", "logoutComponent"}, 2458);

    auto capture = LogCapture{};
    const auto config = ConfigFile::Parse(text, *capture.GetLogger());
    CheckExampleMembers(config);
    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 1);
    CHECK(entries[0].level == LogLevel_e::Warning);
    CHECK(entries[0].message == "Config has client.logoutComponent, which is no longer read; the logout button comes from the cache in client.cacheDirectory");
}

TEST_CASE("ConfigFile parses an account file", "[ConfigFile][AccountFile]")
{
    const auto account = ConfigFile::ParseAccount(ACCOUNT_EXAMPLE, "bot1");
    CHECK(account.name == "bot1");
    CHECK(account.credentials.username == "bot1");
    CHECK(account.credentials.password == SECRET_PASSWORD);
    CHECK_FALSE(account.enabled);
    REQUIRE(account.script.has_value());
    CHECK(account.script->file == "examples/chicken_killer.py");
    CHECK(account.script->progressReportMinutes == std::chrono::minutes{20});
    CHECK(nlohmann::json::parse(account.script->settings) == nlohmann::json::parse(R"json({"npc_ids": [41], "loot": true, "area": {"x": 3230, "z": 3298}, "name": "chickens"})json"));

    SECTION("only the credentials are required")
    {
        const auto minimal = ConfigFile::ParseAccount(R"json({"username": "bot2", "password": "pw"})json", "bot2");
        CHECK(minimal.enabled);
        CHECK_FALSE(minimal.script.has_value());
    }

    SECTION("a null script means no script")
    {
        CHECK_FALSE(ConfigFile::ParseAccount(SetAccountKey("script", nullptr), "bot1").script.has_value());
    }

    SECTION("a script without settings gets an empty object")
    {
        const auto text = EditAccount([](nlohmann::json& json)
        {
            json["script"].erase("settings");
        });
        CHECK(ConfigFile::ParseAccount(text, "bot1").script->settings == "{}");
    }

    SECTION("progress reports are off unless asked for, and allowed up to a day apart")
    {
        const auto text = EditAccount([](nlohmann::json& json)
        {
            json["script"].erase("progressReportMinutes");
        });
        CHECK(ConfigFile::ParseAccount(text, "bot1").script->progressReportMinutes == std::chrono::minutes{0});
        CHECK(ConfigFile::ParseAccount(SetScriptKey("progressReportMinutes", 1), "bot1").script->progressReportMinutes == std::chrono::minutes{1});
        CHECK(ConfigFile::ParseAccount(SetScriptKey("progressReportMinutes", 1440), "bot1").script->progressReportMinutes == std::chrono::minutes{1440});
    }

    SECTION("usernames and passwords at their limits")
    {
        for (const auto& username : {std::string{"a"}, std::string(12, 'a'), std::string{"a b"}})
        {
            CHECK(ConfigFile::ParseAccount(SetAccountKey("username", username), "bot1").credentials.username == username);
        }

        for (const auto& password : {std::string{"a"}, std::string(20, 'a')})
        {
            CHECK(ConfigFile::ParseAccount(SetAccountKey("password", password), "bot1").credentials.password == password);
        }
    }
}

TEST_CASE("ConfigFile reads an account's own server", "[ConfigFile][AccountFile]")
{
    CHECK_FALSE(ConfigFile::ParseAccount(ACCOUNT_EXAMPLE, "bot1").server.has_value());

    const auto account = ConfigFile::ParseAccount(SetAccountKey("server", {{"url", "wss://w2.example.com:443"}, {"origin", "https://w2.example.com"}}), "bot1");
    REQUIRE(account.server.has_value());
    CHECK(account.server->url == "wss://w2.example.com:443");
    CHECK(account.server->origin == "https://w2.example.com");
    CHECK(account.server->tlsCaFile == "SYSTEM");

    CheckAccountRejected(SetAccountKey("server", {{"url", "http://w2.example.com"}}), "server.url");
    CheckAccountRejected(SetAccountKey("server", nlohmann::json::object()), "server.url");
    CheckAccountRejected(SetAccountKey("server", "ws://w2.example.com"), "server");
}

TEST_CASE("ConfigFile rejects invalid account files", "[ConfigFile][AccountFile]")
{
    const auto rejections = std::vector<std::pair<std::string, nlohmann::json>>{
        {"username", ""},
        {"username", std::string(13, 'a')},
        {"username", "tab\there"},
        {"username", UTF8_E_ACUTE},
        {"username", 5},
        {"password", ""},
        {"password", std::string(21, 'a')},
        {"password", std::string{"nul\0x", 5}},
        {"password", UTF8_E_ACUTE},
        {"password", 5},
        {"enabled", "yes"},
        {"script", "examples/chicken_killer.py"},
    };

    for (const auto& [key, value] : rejections)
    {
        CAPTURE(key, value.dump());
        CheckAccountRejected(SetAccountKey(key, value), key);
    }

    CheckAccountRejected(SetScriptKey("file", ""), "script.file");
    CheckAccountRejected(SetScriptKey("file", 5), "script.file");
    CheckAccountRejected(SetScriptKey("settings", nlohmann::json::array({41})), "script.settings");
    CheckAccountRejected(SetScriptKey("progressReportMinutes", -1), "script.progressReportMinutes");
    CheckAccountRejected(SetScriptKey("progressReportMinutes", 1441), "script.progressReportMinutes");
    CheckAccountRejected(SetScriptKey("progressReportMinutes", "20"), "script.progressReportMinutes");
    CheckAccountRejected(EditAccount([](nlohmann::json& json)
    {
        json["script"].erase("file");
    }), "script.file");
    CheckAccountRejected(EditAccount([](nlohmann::json& json)
    {
        json.erase("password");
    }), "password");
    CHECK_THROWS_AS(ConfigFile::ParseAccount("[]", "bot1"), ConfigError);
}

TEST_CASE("ConfigFile messages never contain credentials", "[ConfigFile][AccountFile]")
{
    SECTION("rejected usernames and passwords aren't quoted")
    {
        for (const auto* const key : {"username", "password"})
        {
            for (const auto& value : {std::string(21, 'q'), std::string{"tab\there"}, std::string{UTF8_E_ACUTE}, std::string{"nul\0x", 5}})
            {
                CHECK_THROWS_WITH(ConfigFile::ParseAccount(SetAccountKey(key, value), "bot1"), !Catch::Matchers::ContainsSubstring(value));
            }
        }
    }

    SECTION("a syntax error inside the password doesn't quote it")
    {
        for (const auto* const text : {R"json({"username": "bot1", "password": "hunter\q2"})json", R"json({"username": "bot1", "password": "hunter2)json"})
        {
            CAPTURE(text);
            CHECK_THROWS_AS(ConfigFile::ParseAccount(text, "bot1"), ConfigError);
            CHECK_THROWS_WITH(ConfigFile::ParseAccount(text, "bot1"), !Catch::Matchers::ContainsSubstring("hunter"));
        }
    }
}

TEST_CASE("ConfigFile::LoadAccount", "[ConfigFile][AccountFile]")
{
    const auto folder = TempFolder{"rs2004-config-tests"};
    const auto path = folder.GetPath() / "bot1.jsonc";

    SECTION("names the account after the file")
    {
        WriteFile(path, ACCOUNT_EXAMPLE);
        const auto account = ConfigFile::LoadAccount(path);
        CHECK(account.name == "bot1");
        CHECK(account.credentials.username == "bot1");
    }

    SECTION("puts the file's path in front of the message")
    {
        WriteFile(path, SetAccountKey("username", ""));
        CHECK_THROWS_WITH(ConfigFile::LoadAccount(path), Catch::Matchers::StartsWith(path.string() + ": ") && Catch::Matchers::ContainsSubstring("username"));
    }

    SECTION("a missing file is an error, and no sample is written")
    {
        CHECK_THROWS_WITH(ConfigFile::LoadAccount(path), Catch::Matchers::ContainsSubstring(path.string()) && Catch::Matchers::ContainsSubstring("not found"));
        CHECK_FALSE(std::filesystem::exists(path));
    }
}

TEST_CASE("ConfigFile::Serialize", "[ConfigFile]")
{
    SECTION("the defaults serialize to the sample")
    {
        CHECK(ConfigFile::Serialize(Config_s{}) == SAMPLE_BODY);
    }

    SECTION("a parsed file round-trips")
    {
        const auto serialized = ConfigFile::Serialize(ParseAccepted(EXAMPLE));
        const auto reparsed = ParseAccepted(serialized);
        CheckExampleMembers(reparsed);
        CHECK(ConfigFile::Serialize(reparsed) == serialized);
    }

    SECTION("each type has its written form")
    {
        const auto forms = std::vector<WrittenForm_s>{
            {"modulus 0", [](Config_s& config) { config.login.rsaModulus = BigUInt{}; }, "/login/rsaModulus", "0x0"},
            {"modulus 3233", [](Config_s& config) { config.login.rsaModulus = BigUInt::Parse("3233"); }, "/login/rsaModulus", "0xca1"},
            {"no leading zeros", [](Config_s& config) { config.login.rsaModulus = BigUInt::Parse("0x0000ff"); }, "/login/rsaModulus", "0xff"},
            {"no sign padding", [](Config_s& config) { config.login.rsaModulus = BigUInt::Parse("0x80"); }, "/login/rsaModulus", "0x80"},
            {"example modulus", [](Config_s& config) { config.login.rsaModulus = BigUInt::Parse(EXAMPLE_MODULUS); }, "/login/rsaModulus", EXAMPLE_MODULUS},
            {"verbose", [](Config_s& config) { config.client.logLevel = LogLevel_e::Verbose; }, "/client/logLevel", "verbose"},
            {"info", [](Config_s& config) { config.client.logLevel = LogLevel_e::Info; }, "/client/logLevel", "info"},
            {"warning", [](Config_s& config) { config.client.logLevel = LogLevel_e::Warning; }, "/client/logLevel", "warning"},
            {"error", [](Config_s& config) { config.client.logLevel = LogLevel_e::Error; }, "/client/logLevel", "error"},
        };

        for (const auto& form : forms)
        {
            CAPTURE(form.description);
            auto config = ParseAccepted(EXAMPLE);
            form.set(config);
            const auto serialized = ConfigFile::Serialize(config);
            CHECK(nlohmann::json::parse(serialized).at(nlohmann::json::json_pointer{form.pointer}) == form.written);

            // A modulus of 0 is a valid written form but breaks Validate, so it reads back through BigUInt directly.
            if (form.pointer == "/login/rsaModulus")
            {
                CHECK(BigUInt::Parse(form.written) == config.login.rsaModulus);
                continue;
            }

            const auto reparsed = ParseAccepted(serialized);
            CHECK(reparsed.client.logLevel == config.client.logLevel);
        }

        auto config = ParseAccepted(EXAMPLE);
        config.client.idleSeconds = 300s;
        const auto serialized = ConfigFile::Serialize(config);
        CHECK(nlohmann::json::parse(serialized).at("client").at("idleSeconds") == 300);
        CHECK(ParseAccepted(serialized).client.idleSeconds == 300s);
    }

    SECTION("hex is read in any case and written in lower case")
    {
        const auto upper = ReplaceAll(std::string{EXAMPLE}, EXAMPLE_MODULUS, ToUpper(EXAMPLE_MODULUS));
        const auto config = ParseAccepted(upper);
        CheckExampleMembers(config);

        const auto serialized = ConfigFile::Serialize(config);
        CHECK_THAT(serialized, Catch::Matchers::ContainsSubstring(std::format("\"{}\"", EXAMPLE_MODULUS)));
    }

    SECTION("the sample works once filled in")
    {
        auto sample = ParseJsonWithComments(std::string{SAMPLE_HEADER} + std::string{SAMPLE_BODY});
        sample["server"]["url"] = "ws://localhost:80";
        sample["login"]["rsaModulus"] = "3233";
        sample["login"]["rsaExponent"] = "17";

        const auto config = ParseAccepted(sample.dump());
        CHECK(config.server.url == "ws://localhost:80");
        CHECK(config.login.rsaModulus == BigUInt::Parse("3233"));
        CHECK(config.login.rsaExponent == BigUInt::Parse("17"));
        CheckOptionalDefaults(config);
    }
}

TEST_CASE("ConfigFile logs through the default logger when given none", "[ConfigFile]")
{
    auto capture = LogCapture{};
    const auto scope = DefaultLoggerScope{capture.GetLogger()};
    const auto text = EditBase([](nlohmann::json& json)
    {
        json["server"]["url"] = "wss://w1.example.com:443";
        json["server"]["tlsCaFile"] = "NONE";
    });

    SECTION("Parse")
    {
        static_cast<void>(ConfigFile::Parse(text));
    }

    SECTION("Load")
    {
        const auto folder = TempFolder{"rs2004-config-tests"};
        const auto path = folder.GetPath() / "client.jsonc";
        WriteFile(path, text);
        static_cast<void>(ConfigFile::Load(path));
    }

    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 1);
    CHECK(entries[0].level == LogLevel_e::Warning);
    CHECK_THAT(entries[0].message, Catch::Matchers::ContainsSubstring("server.tlsCaFile"));
}

TEST_CASE("ConfigFile::Load", "[ConfigFile]")
{
    const auto folder = TempFolder{"rs2004-config-tests"};
    const auto path = folder.GetPath() / "client.jsonc";
    auto capture = LogCapture{};
    auto& logger = *capture.GetLogger();

    SECTION("loads a file")
    {
        WriteFile(path, EXAMPLE);
        CheckExampleMembers(ConfigFile::Load(path, logger));
    }

    SECTION("loads a file with CRLF line endings and a byte order mark")
    {
        WriteFile(path, std::string{BOM} + ReplaceAll(std::string{EXAMPLE}, "\n", "\r\n"));
        CheckExampleMembers(ConfigFile::Load(path, logger));
    }

    SECTION("puts the file's path in front of the message")
    {
        auto json = ParseJsonWithComments(EXAMPLE);
        json["client"]["idleSeconds"] = 0;
        WriteFile(path, json.dump());

        CHECK_THROWS_AS(ConfigFile::Load(path, logger), ConfigError);
        CHECK_THROWS_WITH(ConfigFile::Load(path, logger), Catch::Matchers::StartsWith(path.string() + ": ") && Catch::Matchers::ContainsSubstring("client.idleSeconds"));
    }

    SECTION("writes a sample on the first run")
    {
        CHECK_THROWS_AS(ConfigFile::Load(path, logger), ConfigError);
        REQUIRE(std::filesystem::exists(path));
        CHECK(ReadFile(path) == std::string{SAMPLE_HEADER} + std::string{SAMPLE_BODY});

        std::filesystem::remove(path);
        CHECK_THROWS_WITH(ConfigFile::Load(path, logger), Catch::Matchers::ContainsSubstring(path.string()) && Catch::Matchers::ContainsSubstring("sample"));

        const auto edited = ReadFile(path) + "// edited\n";
        WriteFile(path, edited);
        CHECK_THROWS_WITH(ConfigFile::Load(path, logger), Catch::Matchers::ContainsSubstring("server.url"));
        CHECK(ReadFile(path) == edited);
    }

    SECTION("doesn't create a missing folder for the sample")
    {
        const auto missingFolder = folder.GetPath() / "missing";
        const auto missingPath = missingFolder / "client.jsonc";

        CHECK_THROWS_AS(ConfigFile::Load(missingPath, logger), ConfigError);
        CHECK_THROWS_WITH(ConfigFile::Load(missingPath, logger), Catch::Matchers::ContainsSubstring(missingPath.string()));
        CHECK_FALSE(std::filesystem::exists(missingFolder));
    }

    CHECK(capture.GetEntries().empty());
}

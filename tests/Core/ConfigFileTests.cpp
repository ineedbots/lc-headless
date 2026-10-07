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
    "account": {
        "username": "test",
        "password": "test"
    },
    "login": {
        "crcs": ["0x00000000", "0xde5b3345", "0x6026f8fe", "0x07550309", "0x9a13636e", "0xca2717bd", "0x368f1792", "0x1b1fb6b2", "0xa7129379"],
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
        "logoutComponent": 2458,
        "logLevel": "verbose",
        "idleSeconds": 5
    }
}
)json"sv;

    constexpr auto SAMPLE_HEADER =
        "// Sample config, written because none was found.\n"
        "// Set server.url, the account, and the login CRCs and RSA key, then run again.\n"sv;

    constexpr auto SAMPLE_BODY = R"json({
    "server": {
        "url": "",
        "origin": "",
        "tlsCaFile": "SYSTEM"
    },
    "account": {
        "username": "",
        "password": ""
    },
    "login": {
        "crcs": [
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000"
        ],
        "rsaModulus": "0x0",
        "rsaExponent": "0x0",
        "lowMemory": false,
        "revision": 289
    },
    "client": {
        "logoutComponent": 2458,
        "logLevel": "info",
        "idleSeconds": 5
    }
}
)json"sv;

    constexpr auto MINIMAL = R"json({
    "server": {"url": "ws://localhost:80"},
    "account": {"username": "test", "password": "test"},
    "login": {
        "rsaModulus": "0x88c38748a58228f7261cdc340b5691d7d0975dee0ecdb717609e6bf971eb3fe723ef9d130e4686813739768ad9472eb46d8bfcc042c1a5fcb05e931f632eea5d",
        "rsaExponent": "0x81f390b2cf8ca7039ee507975951d5a0b15a87bf8b3f99c966834118c50fd94d"
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
        {"account", "username"},
        {"account", "password"},
        {"login", "rsaModulus"},
        {"login", "rsaExponent"},
    };

    const auto OPTIONAL_KEYS = std::vector<KeyPath_s>{
        {"server", "origin"},
        {"server", "tlsCaFile"},
        {"login", "crcs"},
        {"login", "lowMemory"},
        {"login", "revision"},
        {"client", "logoutComponent"},
        {"client", "logLevel"},
        {"client", "idleSeconds"},
    };

    s32 Crc(u32 value)
    {
        return std::bit_cast<s32>(value);
    }

    std::array<s32, LoginSettings_s::CRC_COUNT> GetExampleCrcs()
    {
        return {0, Crc(0xde5b3345), Crc(0x6026f8fe), Crc(0x07550309), Crc(0x9a13636e), Crc(0xca2717bd), Crc(0x368f1792), Crc(0x1b1fb6b2), Crc(0xa7129379)};
    }

    nlohmann::json ParseJsonWithComments(std::string_view text)
    {
        return nlohmann::json::parse(text, nullptr, true, true);
    }

    nlohmann::json MakeBase()
    {
        auto json = ParseJsonWithComments(EXAMPLE);
        json["account"]["password"] = SECRET_PASSWORD;
        return json;
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

    void CheckExampleMembers(const Config_s& config, std::string_view password)
    {
        CHECK(config.server.url == "ws://localhost:80");
        CHECK(config.server.origin == "https://w1.rs2b2t.com");
        CHECK(config.server.tlsCaFile == "SYSTEM");
        CHECK(config.account.username == "test");
        CHECK(config.account.password == password);
        CHECK(config.login.crcs == GetExampleCrcs());
        CHECK(config.login.rsaModulus == BigUInt::Parse(EXAMPLE_MODULUS));
        CHECK(config.login.rsaExponent == BigUInt::Parse(EXAMPLE_EXPONENT));
        CHECK_FALSE(config.login.lowMemory);
        CHECK(config.login.revision == 289);
        CHECK(config.client.logoutComponent == 2458);
        CHECK(config.client.logLevel == LogLevel_e::Verbose);
        CHECK(config.client.idleSeconds == 5s);
    }

    void CheckOptionalDefaults(const Config_s& config)
    {
        CHECK(config.server.origin.empty());
        CHECK(config.server.tlsCaFile == "SYSTEM");
        CHECK(config.login.crcs == std::array<s32, LoginSettings_s::CRC_COUNT>{});
        CHECK_FALSE(config.login.lowMemory);
        CHECK(config.login.revision == 289);
        CHECK(config.client.logoutComponent == 2458);
        CHECK(config.client.logLevel == LogLevel_e::Info);
        CHECK(config.client.idleSeconds == 5s);
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
    CheckExampleMembers(ParseAccepted(EXAMPLE), "test");
}

TEST_CASE("ConfigFile parses a file with only the keys that must be set", "[ConfigFile]")
{
    const auto config = ParseAccepted(MINIMAL);

    CHECK(config.server.url == "ws://localhost:80");
    CHECK(config.account.username == "test");
    CHECK(config.account.password == "test");
    CHECK(config.login.rsaModulus == BigUInt::Parse(EXAMPLE_MODULUS));
    CHECK(config.login.rsaExponent == BigUInt::Parse(EXAMPLE_EXPONENT));
    CheckOptionalDefaults(config);
}

TEST_CASE("ConfigFile syntax", "[ConfigFile]")
{
    SECTION("comments on their own lines, after values, and across lines")
    {
        const auto text = ReplaceAll(std::string{EXAMPLE}, "\"tlsCaFile\": \"SYSTEM\"", "\"tlsCaFile\": \"SYSTEM\" // trailing comment\n        /* a comment\n           over two lines */");
        CheckExampleMembers(ParseAccepted(text), "test");
    }

    SECTION("a line comment at the end without a newline")
    {
        CheckExampleMembers(ParseAccepted(std::string{EXAMPLE} + "// the end"), "test");
    }

    SECTION("a UTF-8 byte order mark")
    {
        CheckExampleMembers(ParseAccepted(std::string{BOM} + std::string{EXAMPLE}), "test");
    }

    SECTION("CRLF line endings")
    {
        CheckExampleMembers(ParseAccepted(ReplaceAll(std::string{EXAMPLE}, "\n", "\r\n")), "test");
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
            else if (key.key == "crcs")
            {
                CHECK(config.login.crcs == std::array<s32, LoginSettings_s::CRC_COUNT>{});
            }
            else if (key.key == "lowMemory")
            {
                CHECK_FALSE(config.login.lowMemory);
            }
            else if (key.key == "revision")
            {
                CHECK(config.login.revision == 289);
            }
            else if (key.key == "logoutComponent")
            {
                CHECK(config.client.logoutComponent == 2458);
            }
            else if (key.key == "logLevel")
            {
                CHECK(config.client.logLevel == LogLevel_e::Info);
            }
            else if (key.key == "idleSeconds")
            {
                CHECK(config.client.idleSeconds == 5s);
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
        CheckRejected(removeSection("account"), "account.username");
        CheckRejected(removeSection("login"), "login.rsaModulus");

        const auto config = ParseAccepted(removeSection("client"));
        CHECK(config.client.logoutComponent == 2458);
        CHECK(config.client.logLevel == LogLevel_e::Info);
        CHECK(config.client.idleSeconds == 5s);
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
        CheckExampleMembers(config, SECRET_PASSWORD);
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
            json["account"].erase("username");
            json["account"]["usrname"] = "test";
        }), "account.username");
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

    SECTION("account")
    {
        for (const auto& username : {std::string{"a"}, std::string(12, 'a'), std::string{"a b"}})
        {
            CHECK(ParseAccepted(SetKey({"account", "username"}, username)).account.username == username);
        }

        for (const auto& password : {std::string{"a"}, std::string(20, 'a')})
        {
            CHECK(ParseAccepted(SetKey({"account", "password"}, password)).account.password == password);
        }
    }

    SECTION("login.crcs in any spelling")
    {
        const auto crcs = nlohmann::json::array({"0", "0xde5b3345", "0xDE5B3345", "0Xde5b3345", "0xDe5B3345", "4294967295", "1", "2", "3"});
        const auto config = ParseAccepted(SetKey({"login", "crcs"}, crcs));
        CHECK(config.login.crcs == std::array<s32, LoginSettings_s::CRC_COUNT>{0, Crc(0xde5b3345), Crc(0xde5b3345), Crc(0xde5b3345), Crc(0xde5b3345), -1, 1, 2, 3});
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
        CHECK(ParseAccepted(SetKey({"client", "logoutComponent"}, 0)).client.logoutComponent == 0);
        CHECK(ParseAccepted(SetKey({"client", "logoutComponent"}, 65535)).client.logoutComponent == 65535);

        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "verbose")).client.logLevel == LogLevel_e::Verbose);
        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "info")).client.logLevel == LogLevel_e::Info);
        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "warning")).client.logLevel == LogLevel_e::Warning);
        CHECK(ParseAccepted(SetKey({"client", "logLevel"}, "error")).client.logLevel == LogLevel_e::Error);

        CHECK(ParseAccepted(SetKey({"client", "idleSeconds"}, 1)).client.idleSeconds == 1s);
        CHECK(ParseAccepted(SetKey({"client", "idleSeconds"}, 300)).client.idleSeconds == 300s);
    }
}

TEST_CASE("ConfigFile rejects invalid values", "[ConfigFile]")
{
    const auto crcsWithItem = [](nlohmann::json item)
    {
        auto crcs = nlohmann::json::array({"0", "0", "0", "0", "0", "0", "0", "0", "0"});
        crcs[3] = std::move(item);
        return crcs;
    };

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
        {{"account", "username"}, ""},
        {{"account", "username"}, std::string(13, 'a')},
        {{"account", "username"}, "tab\there"},
        {{"account", "username"}, UTF8_E_ACUTE},
        {{"account", "username"}, 5},
        {{"account", "password"}, ""},
        {{"account", "password"}, std::string(21, 'a')},
        {{"account", "password"}, std::string{"nul\0x", 5}},
        {{"account", "password"}, UTF8_E_ACUTE},
        {{"account", "password"}, 5},
        {{"login", "crcs"}, nlohmann::json::array({"0", "0", "0", "0", "0", "0", "0", "0"})},
        {{"login", "crcs"}, nlohmann::json::array({"0", "0", "0", "0", "0", "0", "0", "0", "0", "0"})},
        {{"login", "crcs"}, "0, 0, 0, 0, 0, 0, 0, 0, 0"},
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
        {{"client", "logoutComponent"}, "2458"},
        {{"client", "logoutComponent"}, nullptr},
        {{"client", "logLevel"}, "warn"},
        {{"client", "logLevel"}, "Info"},
        {{"client", "logLevel"}, "debug"},
        {{"client", "logLevel"}, ""},
        {{"client", "logLevel"}, 2},
        {{"client", "idleSeconds"}, 0},
        {{"client", "idleSeconds"}, 301},
        {{"client", "idleSeconds"}, -5},
        {{"client", "idleSeconds"}, "5"},
    };

    for (const auto& rejection : rejections)
    {
        CAPTURE(rejection.key.GetPath(), rejection.value.dump());
        CheckRejected(SetKey(rejection.key, rejection.value), rejection.key.GetPath());
    }

    for (const auto& item : {nlohmann::json("0x100000000"), nlohmann::json("4294967296"), nlohmann::json("-1"), nlohmann::json("+1"), nlohmann::json(" 1"), nlohmann::json("0x"), nlohmann::json(""), nlohmann::json("0x0x1"), nlohmann::json("1.5"), nlohmann::json(5)})
    {
        CAPTURE(item.dump());
        CheckRejected(SetKey({"login", "crcs"}, crcsWithItem(item)), "login.crcs.3");
    }
}

TEST_CASE("ConfigFile messages never contain credentials", "[ConfigFile]")
{
    SECTION("rejected usernames and passwords aren't quoted")
    {
        for (const auto* const key : {"username", "password"})
        {
            for (const auto& value : {std::string(21, 'q'), std::string{"tab\there"}, std::string{UTF8_E_ACUTE}, std::string{"nul\0x", 5}})
            {
                const auto text = SetKey({"account", key}, value);
                auto capture = LogCapture{};
                CHECK_THROWS_WITH(ConfigFile::Parse(text, *capture.GetLogger()), !Catch::Matchers::ContainsSubstring(value));
            }
        }
    }

    SECTION("a syntax error inside the password doesn't quote it")
    {
        for (const auto* const text : {R"json({"account": {"password": "hunter\q2"}})json", R"json({"account": {"password": "hunter2)json"})
        {
            CAPTURE(text);
            auto capture = LogCapture{};
            CHECK_THROWS_AS(ConfigFile::Parse(text, *capture.GetLogger()), ConfigError);
            CHECK_THROWS_WITH(ConfigFile::Parse(text, *capture.GetLogger()), !Catch::Matchers::ContainsSubstring("hunter"));
        }
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
        CheckExampleMembers(reparsed, "test");
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
            {"crc 0", [](Config_s& config) { config.login.crcs[0] = 0; }, "/login/crcs/0", "0x00000000"},
            {"crc -1", [](Config_s& config) { config.login.crcs[0] = -1; }, "/login/crcs/0", "0xffffffff"},
            {"crc 0xde5b3345", [](Config_s& config) { config.login.crcs[0] = Crc(0xde5b3345); }, "/login/crcs/0", "0xde5b3345"},
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
            CHECK(reparsed.login.crcs == config.login.crcs);
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
        auto upper = ReplaceAll(std::string{EXAMPLE}, "0xde5b3345", "0XDE5B3345");
        upper = ReplaceAll(upper, EXAMPLE_MODULUS, ToUpper(EXAMPLE_MODULUS));
        const auto config = ParseAccepted(upper);
        CheckExampleMembers(config, "test");

        const auto serialized = ConfigFile::Serialize(config);
        CHECK_THAT(serialized, Catch::Matchers::ContainsSubstring("\"0xde5b3345\""));
        CHECK_THAT(serialized, Catch::Matchers::ContainsSubstring(std::format("\"{}\"", EXAMPLE_MODULUS)));
    }

    SECTION("the sample works once filled in")
    {
        auto sample = ParseJsonWithComments(std::string{SAMPLE_HEADER} + std::string{SAMPLE_BODY});
        sample["server"]["url"] = "ws://localhost:80";
        sample["account"]["username"] = "test";
        sample["account"]["password"] = "test";
        sample["login"]["rsaModulus"] = "3233";
        sample["login"]["rsaExponent"] = "17";

        const auto config = ParseAccepted(sample.dump());
        CHECK(config.server.url == "ws://localhost:80");
        CHECK(config.account.username == "test");
        CHECK(config.account.password == "test");
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
        CheckExampleMembers(ConfigFile::Load(path, logger), "test");
    }

    SECTION("loads a file with CRLF line endings and a byte order mark")
    {
        WriteFile(path, std::string{BOM} + ReplaceAll(std::string{EXAMPLE}, "\n", "\r\n"));
        CheckExampleMembers(ConfigFile::Load(path, logger), "test");
    }

    SECTION("puts the file's path in front of the message")
    {
        auto json = ParseJsonWithComments(EXAMPLE);
        json["login"]["crcs"].erase(0);
        WriteFile(path, json.dump());

        CHECK_THROWS_AS(ConfigFile::Load(path, logger), ConfigError);
        CHECK_THROWS_WITH(ConfigFile::Load(path, logger), Catch::Matchers::StartsWith(path.string() + ": ") && Catch::Matchers::ContainsSubstring("login.crcs"));
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

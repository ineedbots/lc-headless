#include "pch.hpp"
#include "../Support/TempFolder.hpp"

#include "Config/AccountConfig_s.hpp"
#include "Config/AccountFile.hpp"
#include "Config/Error/ConfigError.hpp"
#include "Config/Transport_e.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_tostring.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <nlohmann/json.hpp>

namespace
{
    constexpr auto ACCOUNT_EXAMPLE = R"json({
    // The account and what it runs.
    "username": "bot1",
    "password": "s3cret-pw",
    "enabled": false,
    "idleSeconds": 60,
    "randomEvents": false,
    "stallMinutes": 30,
    "runAuto": false,
    "runEnergyMin": 50,
    "script": {
        "file": "examples/chicken_killer.py",
        "progressReportMinutes": 20,
        "settings": {"npc_ids": [41], "loot": true, "area": {"x": 3230, "z": 3298}, "name": "chickens"}
    }
})json"sv;
    constexpr auto SECRET_PASSWORD = "s3cret-pw";
    constexpr auto UTF8_E_ACUTE = "\xC3\xA9";

    nlohmann::json ParseJsonWithComments(std::string_view text)
    {
        return nlohmann::json::parse(text, nullptr, true, true);
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
        CHECK_THROWS_AS(AccountFile::Parse(text, "bot1"), ConfigError);
        CHECK_THROWS_WITH(AccountFile::Parse(text, "bot1"), Catch::Matchers::ContainsSubstring(path) && !Catch::Matchers::ContainsSubstring(SECRET_PASSWORD));
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

TEST_CASE("AccountFile parses an account file", "[AccountFile]")
{
    const auto account = AccountFile::Parse(ACCOUNT_EXAMPLE, "bot1");
    CHECK(account.name == "bot1");
    CHECK(account.credentials.username == "bot1");
    CHECK(account.credentials.password == SECRET_PASSWORD);
    CHECK_FALSE(account.enabled);
    CHECK(account.idleSeconds == 60s);
    CHECK_FALSE(account.randomEvents);
    CHECK(account.stallMinutes == std::chrono::minutes{30});
    CHECK_FALSE(account.runAuto);
    CHECK(account.runEnergyMin == 50);
    REQUIRE(account.script.has_value());
    CHECK(account.script->file == "examples/chicken_killer.py");
    CHECK(account.script->progressReportMinutes == std::chrono::minutes{20});
    CHECK(nlohmann::json::parse(account.script->settings) == nlohmann::json::parse(R"json({"npc_ids": [41], "loot": true, "area": {"x": 3230, "z": 3298}, "name": "chickens"})json"));

    SECTION("only the credentials are required")
    {
        const auto minimal = AccountFile::Parse(R"json({"username": "bot2", "password": "pw"})json", "bot2");
        CHECK(minimal.enabled);
        CHECK(minimal.idleSeconds == 0s);
        CHECK(minimal.randomEvents);
        CHECK(minimal.stallMinutes == std::chrono::minutes{10});
        CHECK(minimal.runAuto);
        CHECK(minimal.runEnergyMin == 20);
        CHECK_FALSE(minimal.script.has_value());
    }

    SECTION("idle time and upkeep at their limits")
    {
        CHECK(AccountFile::Parse(SetAccountKey("idleSeconds", 0), "bot1").idleSeconds == 0s);
        CHECK(AccountFile::Parse(SetAccountKey("idleSeconds", 86400), "bot1").idleSeconds == 86400s);
        CHECK(AccountFile::Parse(SetAccountKey("stallMinutes", 0), "bot1").stallMinutes == std::chrono::minutes{0});
        CHECK(AccountFile::Parse(SetAccountKey("stallMinutes", 1440), "bot1").stallMinutes == std::chrono::minutes{1440});
        CHECK(AccountFile::Parse(SetAccountKey("runEnergyMin", 0), "bot1").runEnergyMin == 0);
        CHECK(AccountFile::Parse(SetAccountKey("runEnergyMin", 100), "bot1").runEnergyMin == 100);
    }

    SECTION("a null script means no script")
    {
        CHECK_FALSE(AccountFile::Parse(SetAccountKey("script", nullptr), "bot1").script.has_value());
    }

    SECTION("a script without settings gets an empty object")
    {
        const auto text = EditAccount([](nlohmann::json& json)
        {
            json["script"].erase("settings");
        });
        CHECK(AccountFile::Parse(text, "bot1").script->settings == "{}");
    }

    SECTION("progress reports are off unless asked for, and allowed up to a day apart")
    {
        const auto text = EditAccount([](nlohmann::json& json)
        {
            json["script"].erase("progressReportMinutes");
        });
        CHECK(AccountFile::Parse(text, "bot1").script->progressReportMinutes == std::chrono::minutes{0});
        CHECK(AccountFile::Parse(SetScriptKey("progressReportMinutes", 1), "bot1").script->progressReportMinutes == std::chrono::minutes{1});
        CHECK(AccountFile::Parse(SetScriptKey("progressReportMinutes", 1440), "bot1").script->progressReportMinutes == std::chrono::minutes{1440});
    }

    SECTION("usernames and passwords at their limits")
    {
        for (const auto& username : {std::string{"a"}, std::string(12, 'a'), std::string{"a b"}})
        {
            CHECK(AccountFile::Parse(SetAccountKey("username", username), "bot1").credentials.username == username);
        }

        for (const auto& password : {std::string{"a"}, std::string(20, 'a')})
        {
            CHECK(AccountFile::Parse(SetAccountKey("password", password), "bot1").credentials.password == password);
        }
    }
}

TEST_CASE("AccountFile reads an account's own server", "[AccountFile]")
{
    CHECK_FALSE(AccountFile::Parse(ACCOUNT_EXAMPLE, "bot1").server.has_value());

    const auto account = AccountFile::Parse(SetAccountKey("server", {{"transport", "wss"}, {"host", "w2.example.com"}, {"port", 443}, {"origin", "https://w2.example.com"}}), "bot1");
    REQUIRE(account.server.has_value());
    CHECK(account.server->transport == Transport_e::Wss);
    CHECK(account.server->host == "w2.example.com");
    CHECK(account.server->port == 443);
    CHECK(account.server->origin == "https://w2.example.com");
    CHECK(account.server->tlsCaFile == "SYSTEM");

    CheckAccountRejected(SetAccountKey("server", {{"host", "http://w2.example.com"}, {"port", 80}}), "server.host");
    CheckAccountRejected(SetAccountKey("server", {{"host", "w2.example.com"}}), "server.port");
    CheckAccountRejected(SetAccountKey("server", nlohmann::json::object()), "server.host");
    CheckAccountRejected(SetAccountKey("server", {{"url", "wss://w2.example.com:443"}}), "server.host");
    CheckAccountRejected(SetAccountKey("server", "ws://w2.example.com"), "server");
}

TEST_CASE("AccountFile reads an account's own proxy", "[AccountFile]")
{
    CHECK_FALSE(AccountFile::Parse(ACCOUNT_EXAMPLE, "bot1").proxy.has_value());
    CHECK_FALSE(AccountFile::Parse(SetAccountKey("proxy", nullptr), "bot1").proxy.has_value());

    const auto account = AccountFile::Parse(SetAccountKey("proxy", {{"host", "127.0.0.1"}, {"username", "user"}, {"password", "pass"}}), "bot1");
    REQUIRE(account.proxy.has_value());
    CHECK(account.proxy->host == "127.0.0.1");
    CHECK(account.proxy->port == 1080);
    CHECK(account.proxy->username == "user");
    CHECK(account.proxy->password == "pass");

    const auto direct = AccountFile::Parse(SetAccountKey("proxy", {{"host", ""}}), "bot1");
    REQUIRE(direct.proxy.has_value());
    CHECK(direct.proxy->host.empty());

    CheckAccountRejected(SetAccountKey("proxy", 5), "proxy");
    CheckAccountRejected(SetAccountKey("proxy", {{"host", "127.0.0.1"}, {"port", 0}}), "proxy.port");
    CheckAccountRejected(SetAccountKey("proxy", {{"host", "127.0.0.1"}, {"username", "user"}}), "proxy.password");
}

TEST_CASE("AccountFile rejects invalid account files", "[AccountFile]")
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
        {"idleSeconds", -1},
        {"idleSeconds", 86401},
        {"idleSeconds", "5"},
        {"randomEvents", "yes"},
        {"stallMinutes", -1},
        {"stallMinutes", 1441},
        {"runAuto", 1},
        {"runEnergyMin", -1},
        {"runEnergyMin", 101},
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
    // clang-format off
    CheckAccountRejected(EditAccount([](nlohmann::json& json)
    {
        json["script"].erase("file");
    }), "script.file");
    CheckAccountRejected(EditAccount([](nlohmann::json& json)
    {
        json.erase("password");
    }), "password");
    // clang-format on
    CHECK_THROWS_AS(AccountFile::Parse("[]", "bot1"), ConfigError);
}

TEST_CASE("AccountFile messages never contain credentials", "[AccountFile]")
{
    SECTION("rejected usernames and passwords aren't quoted")
    {
        for (const auto* const key : {"username", "password"})
        {
            for (const auto& value : {std::string(21, 'q'), std::string{"tab\there"}, std::string{UTF8_E_ACUTE}, std::string{"nul\0x", 5}})
            {
                CHECK_THROWS_WITH(AccountFile::Parse(SetAccountKey(key, value), "bot1"), !Catch::Matchers::ContainsSubstring(value));
            }
        }
    }

    SECTION("a syntax error inside the password doesn't quote it")
    {
        for (const auto* const text : {R"json({"username": "bot1", "password": "hunter\q2"})json", R"json({"username": "bot1", "password": "hunter2)json"})
        {
            CAPTURE(text);
            CHECK_THROWS_AS(AccountFile::Parse(text, "bot1"), ConfigError);
            CHECK_THROWS_WITH(AccountFile::Parse(text, "bot1"), !Catch::Matchers::ContainsSubstring("hunter"));
        }
    }
}

TEST_CASE("AccountFile::Load", "[AccountFile]")
{
    const auto folder = TempFolder{"rs2004-config-tests"};
    const auto path = folder.GetPath() / "bot1.jsonc";

    SECTION("names the account after the file")
    {
        WriteFile(path, ACCOUNT_EXAMPLE);

        const auto account = AccountFile::Load(path);
        CHECK(account.name == "bot1");
        CHECK(account.file == path);
        CHECK(account.credentials.username == "bot1");
        CHECK(AccountFile::Parse(ACCOUNT_EXAMPLE, "bot1").file.empty());
    }

    SECTION("puts the file's path in front of the message")
    {
        WriteFile(path, SetAccountKey("username", ""));
        CHECK_THROWS_WITH(AccountFile::Load(path), Catch::Matchers::StartsWith(path.string() + ": ") && Catch::Matchers::ContainsSubstring("username"));
    }

    SECTION("a missing file is an error, and no sample is written")
    {
        CHECK_THROWS_WITH(AccountFile::Load(path), Catch::Matchers::ContainsSubstring(path.string()) && Catch::Matchers::ContainsSubstring("not found"));
        CHECK_FALSE(std::filesystem::exists(path));
    }
}

TEST_CASE("AccountFile::AddScriptSettings", "[AccountFile]")
{
    const auto folder = TempFolder{"rs2004-config-tests"};
    const auto path = folder.GetPath() / "bot1.jsonc";
    const auto defaults = R"json({"npcs": ["Chicken"], "loot_goal": 3})json"sv;

    SECTION("adds a bot's settings under its name, and only the ones missing")
    {
        WriteFile(path, ACCOUNT_EXAMPLE);
        CHECK(AccountFile::AddScriptSettings(path, "Chicken killer", defaults) == std::vector<std::string>{"npcs", "loot_goal"});

        const auto text = ReadFile(path);
        CHECK(text.starts_with("{\n    // The account and what it runs.\n"));
        CHECK(text.find(R"json("settings": {"npc_ids": [41], "loot": true, "area": {"x": 3230, "z": 3298}, "name": "chickens", "Chicken killer": {"npcs": ["Chicken"], "loot_goal": 3}})json") != std::string::npos);
        CHECK(nlohmann::json::parse(AccountFile::Parse(text, "bot1").script->settings)["Chicken killer"] == nlohmann::json::parse(defaults));
        CHECK_FALSE(std::filesystem::exists(folder.GetPath() / "bot1.jsonc.tmp"));

        CHECK(AccountFile::AddScriptSettings(path, "Chicken killer", R"json({"npcs": ["Cow"], "radius": 8})json") == std::vector<std::string>{"radius"});
        CHECK(ReadFile(path).find(R"json("Chicken killer": {"npcs": ["Chicken"], "loot_goal": 3, "radius": 8})json") != std::string::npos);
    }

    SECTION("leaves a file that has them all untouched")
    {
        WriteFile(path, ACCOUNT_EXAMPLE);

        const auto before = std::filesystem::last_write_time(path);
        CHECK(AccountFile::AddScriptSettings(path, "Chicken killer", "{}").empty());
        CHECK(ReadFile(path) == ACCOUNT_EXAMPLE);
        CHECK(std::filesystem::last_write_time(path) == before);
    }

    SECTION("puts the file's path in front of the message")
    {
        WriteFile(path, "{\"script\": {\"settings\": {\"Chicken killer\": []}}}");
        CHECK_THROWS_WITH(AccountFile::AddScriptSettings(path, "Chicken killer", defaults), path.string() + ": script.settings.Chicken killer: must be an object");

        WriteFile(path, "{\"script\": ");
        CHECK_THROWS_WITH(AccountFile::AddScriptSettings(path, "Chicken killer", defaults), Catch::Matchers::StartsWith(path.string() + ": invalid JSON at line 1"));
    }
}

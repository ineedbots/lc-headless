#include "pch.hpp"

#include "Config/Error/ConfigError.hpp"
#include "Config/JsoncEditor.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_exception.hpp>
#include <nlohmann/json.hpp>

namespace
{
    const auto MINER_PATH = std::vector<std::string>{"script", "settings", "Miner"};

    JsoncEdit_s AddToMiner(std::string_view text, std::string_view members)
    {
        return JsoncEditor::AddMissing(text, MINER_PATH, members);
    }
}

TEST_CASE("JsoncEditor adds the members an object lacks, keeping its comments", "[JsoncEditor]")
{
    // clang-format off
    const auto edit = AddToMiner(R"json({
    // The account.
    "username": "bot1",
    "script": {
        "file": "main.py",
        "settings": {
            "Miner": {
                "rock": "Tin rocks" // the user's choice
            }
        }
    }
}
)json",
        R"json({"rock": "Copper rocks", "trips": 10, "keep": ["Pickaxe", "Hammer"]})json");
    // clang-format on

    CHECK(edit.text == R"json({
    // The account.
    "username": "bot1",
    "script": {
        "file": "main.py",
        "settings": {
            "Miner": {
                "rock": "Tin rocks", // the user's choice
                "trips": 10,
                "keep": ["Pickaxe", "Hammer"]
            }
        }
    }
}
)json");
    CHECK(edit.added == std::vector<std::string>{"trips", "keep"});
}

TEST_CASE("JsoncEditor creates the objects on the path that are missing", "[JsoncEditor]")
{
    // clang-format off
    const auto edit = AddToMiner(R"json({
    "script": {
        "file": "main.py" /* no settings yet */
    }
}
)json",
        R"json({"rock": "Copper rocks", "home": [1, 2, 0]})json");
    // clang-format on

    CHECK(edit.text == R"json({
    "script": {
        "file": "main.py", /* no settings yet */
        "settings": {
            "Miner": {
                "rock": "Copper rocks",
                "home": [1, 2, 0]
            }
        }
    }
}
)json");
    CHECK(edit.added == std::vector<std::string>{"rock", "home"});
}

TEST_CASE("JsoncEditor fills an empty object", "[JsoncEditor]")
{
    const auto members = R"json({"rock": "Copper rocks"})json"sv;

    SECTION("written as {}")
    {
        // clang-format off
        const auto edit = AddToMiner(R"json({
    "script": {
        "file": "main.py",
        "settings": {}
    }
}
)json",
            members);
        // clang-format on

        CHECK(edit.text == R"json({
    "script": {
        "file": "main.py",
        "settings": {
            "Miner": {
                "rock": "Copper rocks"
            }
        }
    }
}
)json");
    }

    SECTION("holding a comment, with its closing brace on a line of its own")
    {
        // clang-format off
        const auto edit = AddToMiner(R"json({
    "script": {
        "settings": {
            // set these for the miner
        }
    }
}
)json",
            members);
        // clang-format on

        CHECK(edit.text == R"json({
    "script": {
        "settings": {
            // set these for the miner
            "Miner": {
                "rock": "Copper rocks"
            }
        }
    }
}
)json");
    }
}

TEST_CASE("JsoncEditor follows the layout around it", "[JsoncEditor]")
{
    SECTION("an object on one line stays on one line")
    {
        const auto edit = AddToMiner(R"json({"script": {"settings": {"Miner": {"rock": "Tin rocks"}}}})json", R"json({"trips": 10, "keep": ["Pickaxe"]})json");
        CHECK(edit.text == R"json({"script": {"settings": {"Miner": {"rock": "Tin rocks", "trips": 10, "keep": ["Pickaxe"]}}}})json");
    }

    SECTION("a closing brace on the last member's line moves below the new members")
    {
        // clang-format off
        const auto edit = AddToMiner(R"json({
    "script": {
        "settings": {
            "Miner": {
                "rock": "Tin rocks" }
        }
    }
}
)json",
            R"json({"trips": 10})json");
        // clang-format on

        CHECK(edit.text == R"json({
    "script": {
        "settings": {
            "Miner": {
                "rock": "Tin rocks",
                "trips": 10
            }
        }
    }
}
)json");
    }

    SECTION("tabs and CRLF line endings")
    {
        const auto edit = AddToMiner("{\r\n\t\"script\": {\r\n\t\t\"settings\": {}\r\n\t}\r\n}\r\n", R"json({"rock": "Copper rocks", "area": {"x": 1, "z": 2}})json");
        CHECK(edit.text == "{\r\n\t\"script\": {\r\n\t\t\"settings\": {\r\n\t\t\t\"Miner\": {\r\n\t\t\t\t\"rock\": \"Copper rocks\",\r\n\t\t\t\t\"area\": {\r\n\t\t\t\t\t\"x\": 1,\r\n\t\t\t\t\t\"z\": 2\r\n\t\t\t\t}\r\n\t\t\t}\r\n\t\t}\r\n\t}\r\n}\r\n");
    }

    SECTION("a byte order mark stays, and escaped keys are matched by what they spell")
    {
        const auto edit = AddToMiner("\xEF\xBB\xBF{\"script\": {\"settings\": {\"Mi\\u006eer\": {}}}}", R"json({"rock": "Copper rocks"})json");
        CHECK(edit.text == "\xEF\xBB\xBF{\"script\": {\"settings\": {\"Mi\\u006eer\": {\n    \"rock\": \"Copper rocks\"\n}}}}");
    }
}

TEST_CASE("JsoncEditor leaves text that has every member as it is", "[JsoncEditor]")
{
    const auto text = R"json({
    "script": {"settings": {"Miner": {"rock": "Tin rocks", "trips": 3}}}
}
)json"sv;

    for (const auto members : {R"json({"rock": "Copper rocks", "trips": 10})json"sv, R"json({})json"sv})
    {
        const auto edit = AddToMiner(text, members);
        CHECK(edit.text == text);
        CHECK(edit.added.empty());
    }

    CHECK(JsoncEditor::AddMissing("{}", MINER_PATH, "{}").text == "{}");
}

TEST_CASE("JsoncEditor rejects what it can't add to", "[JsoncEditor]")
{
    const auto members = R"json({"rock": "Copper rocks"})json"sv;
    CHECK_THROWS_MATCHES(AddToMiner(R"json({"script": {"settings": []}})json", members), ConfigError, Catch::Matchers::Message("script.settings: must be an object"));
    CHECK_THROWS_MATCHES(AddToMiner(R"json({"script": {"settings": {"Miner": 5}}})json", members), ConfigError, Catch::Matchers::Message("script.settings.Miner: must be an object"));
    CHECK_THROWS_AS(AddToMiner("[]", members), ConfigError);
    CHECK_THROWS_AS(AddToMiner(R"json({"script": {"settings": {})json", members), ConfigError);
    CHECK_THROWS_AS(AddToMiner(R"json({"script": /* open)json", members), ConfigError);
}

TEST_CASE("JsoncEditor sets members in place, keeping the comments around them", "[JsoncEditor]")
{
    // clang-format off
    const auto edit = JsoncEditor::Set(R"json({
    "script": {
        "settings": {
            "Miner": {
                // Which rock.
                "rock": "Tin rocks", // the user's choice
                "keep": ["Pickaxe"],
                "home": {"x": 1, "z": 2}
            }
        }
    }
}
)json",
        MINER_PATH, R"json({"rock": "Iron rocks", "home": {"x": 3, "z": 4, "level": 0}, "trips": 10})json");
    // clang-format on

    CHECK(edit.text == R"json({
    "script": {
        "settings": {
            "Miner": {
                // Which rock.
                "rock": "Iron rocks", // the user's choice
                "keep": ["Pickaxe"],
                "home": {
                    "x": 3,
                    "z": 4,
                    "level": 0
                },
                "trips": 10
            }
        }
    }
}
)json");
    CHECK(edit.added == std::vector<std::string>{"trips"});
}

TEST_CASE("JsoncEditor sets members of objects the path lacks by adding them", "[JsoncEditor]")
{
    const auto edit = JsoncEditor::Set(R"json({"script": {"file": "main.py"}})json", MINER_PATH, R"json({"rock": "Iron rocks"})json");
    CHECK(edit.text == R"json({"script": {"file": "main.py", "settings": {"Miner": {"rock": "Iron rocks"}}}})json");
    CHECK(edit.added == std::vector<std::string>{"rock"});

    const auto notObject = R"json({"script": {"settings": {"Miner": 5}}})json";
    CHECK_THROWS_MATCHES(JsoncEditor::Set(notObject, MINER_PATH, R"json({"rock": "Iron rocks"})json"), ConfigError, Catch::Matchers::Message("script.settings.Miner: must be an object"));
}

TEST_CASE("JsoncEditor Set rejects non-object roots before attempting an edit", "[JsoncEditor][JsoncBoundaryCoverage]")
{
    const auto root = GENERATE("[]", "null", "42", "\"text\"");
    CHECK_THROWS_MATCHES(JsoncEditor::Set(root, MINER_PATH, R"({"rock": "Iron rocks"})"), ConfigError,
                        Catch::Matchers::Message("the top level must be an object"));
}

TEST_CASE("JsoncEditor adds members to an object containing only an inline block comment", "[JsoncEditor][JsoncBoundaryCoverage]")
{
    const auto path = std::vector<std::string>{};
    const auto edit = JsoncEditor::AddMissing("{/* keep */}", path, R"({"value": 7})");
    CHECK(edit.text == "{/* keep */\n    \"value\": 7\n}");
    CHECK(edit.added == std::vector<std::string>{"value"});
    CHECK(nlohmann::json::parse(edit.text, nullptr, true, true).at("value") == 7);
    CHECK(JsoncEditor::AddMissing(edit.text, path, R"({"value": 9})").text == edit.text);
}

TEST_CASE("JsoncEditor preserves a trailing block comment spanning multiple lines", "[JsoncEditor][JsoncBoundaryCoverage]")
{
    const auto path = std::vector<std::string>{};
    const auto text = "{\n  \"old\": 1 /* keep\n     this block */\n}\n";
    const auto comment = std::string{"/* keep\n     this block */"};
    const auto edit = JsoncEditor::AddMissing(text, path, R"({"new": [2, 3]})");
    const auto value = nlohmann::json::parse(edit.text, nullptr, true, true);
    CHECK(value.at("old") == 1);
    CHECK(value.at("new") == nlohmann::json::array({2, 3}));
    REQUIRE(edit.text.find(comment) != std::string::npos);
    CHECK(edit.text.find(comment, edit.text.find(comment) + comment.size()) == std::string::npos);
    CHECK(edit.added == std::vector<std::string>{"new"});
    CHECK(JsoncEditor::AddMissing(edit.text, path, R"({"new": []})").text == edit.text);
}

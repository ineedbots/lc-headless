#include "pch.hpp"

#include "Core/ConfigError.hpp"
#include "Core/JsoncEditor.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_exception.hpp>

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
    const auto edit = AddToMiner(R"json({
    "script": {
        "file": "main.py" /* no settings yet */
    }
}
)json",
        R"json({"rock": "Copper rocks", "home": [1, 2, 0]})json");

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
        const auto edit = AddToMiner(R"json({
    "script": {
        "file": "main.py",
        "settings": {}
    }
}
)json",
            members);

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
        const auto edit = AddToMiner(R"json({
    "script": {
        "settings": {
            // set these for the miner
        }
    }
}
)json",
            members);

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

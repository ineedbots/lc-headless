#include "pch.hpp"

#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

// rs2b0t's shieldofarrav-doors.test.ts, on the exported graph this client actually uses.
TEST_CASE("Shield of Arrav drives its locked doors while the street door stays routable", "[Navigation]")
{
    const auto text = FileUtils::ReadText(std::filesystem::path{RS2004_SOURCE_DIR} / "data" / "nav" / "edges.json");
    REQUIRE(text.has_value());
    const auto edges = nlohmann::json::parse(*text);
    auto streetDoors = 0;

    for (const auto& edge : edges)
    {
        if (edge.value("kind", "") != "door")
        {
            continue;
        }

        const auto id = edge.value("locId", -1);
        CHECK(id != 2397);
        CHECK(id != 2398);
        CHECK(id != 2399);

        if (id == 1530)
        {
            ++streetDoors;
        }
    }

    CHECK(streetDoors > 0);
}

// rs2b0t's arenaDoorsRefused.test.ts: arena_prisondoor and arena_jeremydoor never open, and fightarena_door1
// teleports the player into the arena, so Fight Arena drives all three itself.
TEST_CASE("Fight Arena drives its scripted doors while Port Khazard's doors stay routable", "[Navigation]")
{
    constexpr auto REFUSED_IDS = std::array{79, 80, 81};
    const auto text = FileUtils::ReadText(std::filesystem::path{RS2004_SOURCE_DIR} / "data" / "nav" / "edges.json");
    REQUIRE(text.has_value());
    const auto edges = nlohmann::json::parse(*text);
    auto portKhazardDoors = 0;

    for (const auto& edge : edges)
    {
        const auto id = edge.value("locId", -1);
        CAPTURE(id);
        CHECK(std::ranges::find(REFUSED_IDS, id) == REFUSED_IDS.end());

        if (edge.value("kind", "") != "door")
        {
            continue;
        }

        const auto x = edge["from"].value("x", 0);
        const auto z = edge["from"].value("z", 0);
        if (x >= 2560 && x <= 2624 && z >= 3136 && z <= 3200)
        {
            ++portKhazardDoors;
        }
    }

    CHECK(portKhazardDoors > 0);
}

// rs2b0t's waterfallTransports.test.ts: the raised room's door, the dungeon's exit and the ledge's barrel teleport,
// so the finished quest's way out is three curated edges.
TEST_CASE("Waterfall Quest's instance exits are curated transports", "[Navigation]")
{
    struct Exit_s
    {
        std::array<s32, 2> from;
        std::array<s32, 2> to;
        std::string_view locName;
        std::string_view action;
        s32 locId;
        std::array<s32, 2> loc;
    };

    constexpr auto EXITS = std::array{
        Exit_s{{2604, 9901}, {2566, 9901}, "Door", "Open", 2002, {2604, 9900}},
        Exit_s{{2575, 9861}, {2511, 3463}, "Door", "Open", 2000, {2575, 9861}},
        Exit_s{{2511, 3463}, {2527, 3413}, "Barrel", "Get in", 2022, {2512, 3463}},
    };
    const auto text = FileUtils::ReadText(std::filesystem::path{RS2004_SOURCE_DIR} / "data" / "nav" / "edges.json");
    REQUIRE(text.has_value());
    const auto edges = nlohmann::json::parse(*text);

    for (const auto& exit : EXITS)
    {
        CAPTURE(exit.locId, exit.from[0], exit.from[1]);
        const auto found = std::ranges::find_if(edges, [&exit](const nlohmann::json& edge)
        {
            const auto& from = edge["from"];
            const auto& to = edge["to"];
            const auto starts = from.value("x", 0) == exit.from[0] && from.value("z", 0) == exit.from[1] && from.value("level", -1) == 0;
            const auto lands = to.value("x", 0) == exit.to[0] && to.value("z", 0) == exit.to[1] && to.value("level", -1) == 0;
            return edge.value("kind", "") == "dungeon" && starts && lands;
        });
        REQUIRE(found != edges.end());
        CHECK((*found).value("locName", "") == exit.locName);
        CHECK((*found).value("action", "") == exit.action);
        CHECK((*found).value("locId", -1) == exit.locId);
        CHECK((*found).value("locX", 0) == exit.loc[0]);
        CHECK((*found).value("locZ", 0) == exit.loc[1]);
    }
}

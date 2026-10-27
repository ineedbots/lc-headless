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

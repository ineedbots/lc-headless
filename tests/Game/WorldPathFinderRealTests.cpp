#include "pch.hpp"
#include "../Support/Cache/RealCache.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/Revision_e.hpp"
#include "Game/Nav/NavPoint_s.hpp"
#include "Game/Nav/NavState_s.hpp"
#include "Game/Nav/Navigation.hpp"
#include "Game/Nav/WorldPathFinder.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    const Navigation& GetNavigation()
    {
        static const auto navigation = []
        {
            const auto started = std::chrono::steady_clock::now();
            auto loaded = std::make_unique<Navigation>(RealCache::Require(Revision_e::Rev289), std::filesystem::path{RS2004_SOURCE_DIR} / "data" / "nav");
            const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started);
            UNSCOPED_INFO(std::format("Navigation built in {} ms: {} edges ({} doors), {} teleports", elapsed.count(), loaded->GetGraph().GetEdgeCount(), loaded->GetGraph().GetDoorCount(), loaded->GetGraph().GetTeleports().size()));
            return loaded;
        }();

        return *navigation;
    }

    NavState_s MakeState(s32 coins)
    {
        auto state = NavState_s{.members = true, .freeSlots = 20};
        for (const auto* const skill : {"attack", "strength", "defence", "hitpoints", "agility", "magic", "mining"})
        {
            state.skills[skill] = 10;
        }

        state.items["coins"] = coins;
        state.quests["prince ali rescue"] = "not_started";
        return state;
    }

    NavPath_s Find(NavPoint_s from, NavPoint_s to, std::optional<NavState_s> state = std::nullopt)
    {
        auto options = NavFindOptions_s{.state = std::move(state)};
        options.policy.useTeleports = false;

        const auto started = std::chrono::steady_clock::now();
        auto path = WorldPathFinder::FindPath(GetNavigation(), from, to, options);
        const auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - started);
        UNSCOPED_INFO(std::format("({},{},{}) to ({},{},{}): {} in {} us, cost {}, {} expanded, {} waypoints", from.x, from.z, from.level, to.x, to.z, to.level, path.ok ? "found" : path.reason, elapsed.count(), path.cost, path.expanded, path.waypoints.size()));
        return path;
    }

    std::vector<std::string> GetHops(const NavPath_s& path)
    {
        auto hops = std::vector<std::string>{};
        for (const auto& waypoint : path.waypoints)
        {
            if (waypoint.edge != nullptr)
            {
                hops.push_back(std::format("{} {}", waypoint.edge->action, waypoint.edge->locName));
            }
        }

        return hops;
    }

    bool Has(const std::vector<std::string>& hops, std::string_view hop)
    {
        return std::ranges::find(hops, hop) != hops.end();
    }
}

TEST_CASE("WorldPathFinder plans routes across the real map", "[RealCache]")
{
    constexpr auto LUMBRIDGE = NavPoint_s{.x = 3222, .z = 3218, .level = 0};

    SECTION("Lumbridge to Varrock east bank, on foot")
    {
        const auto path = Find(LUMBRIDGE, {.x = 3253, .z = 3420, .level = 0});
        REQUIRE(path.ok);
        CHECK(path.cost > 200);
        CHECK(path.waypoints.back().point == NavPoint_s{.x = 3253, .z = 3420, .level = 0});
    }

    SECTION("up Lumbridge castle's stairs to its bank")
    {
        const auto path = Find(LUMBRIDGE, {.x = 3208, .z = 3220, .level = 2}, MakeState(0));
        REQUIRE(path.ok);

        const auto hops = GetHops(path);
        CHECK(std::ranges::count_if(hops, [](const std::string& hop)
        {
            return hop.starts_with("Climb-up");
        }) == 2);
        CHECK(path.waypoints.back().point.level == 2);
    }

    SECTION("into Al Kharid through the toll gate, which needs 10 coins")
    {
        constexpr auto AL_KHARID_BANK = NavPoint_s{.x = 3269, .z = 3167, .level = 0};
        const auto paying = Find(LUMBRIDGE, AL_KHARID_BANK, MakeState(10));
        REQUIRE(paying.ok);
        CHECK(Has(GetHops(paying), "Open Gate"));

        const auto broke = Find(LUMBRIDGE, AL_KHARID_BANK, MakeState(0));
        CHECK_FALSE((broke.ok && Has(GetHops(broke), "Open Gate") && broke.cost <= paying.cost));
    }

    SECTION("to Karamja by ship, paying the fare")
    {
        const auto path = Find({.x = 3029, .z = 3217, .level = 0}, {.x = 2918, .z = 3176, .level = 0}, MakeState(30));
        REQUIRE(path.ok);

        const auto hops = GetHops(path);
        CHECK(Has(hops, "Pay-fare Seaman Thresnor"));
        CHECK(Has(hops, "Cross Gangplank"));

        const auto broke = Find({.x = 3029, .z = 3217, .level = 0}, {.x = 2918, .z = 3176, .level = 0}, MakeState(0));
        CHECK_FALSE((broke.ok && Has(GetHops(broke), "Pay-fare Seaman Thresnor")));
    }

    SECTION("a booth is reached from beside it")
    {
        const auto path = Find(LUMBRIDGE, {.x = 3252, .z = 3419, .level = 0});
        REQUIRE(path.ok);

        const auto end = path.waypoints.back().point;
        CHECK(std::max(std::abs(end.x - 3252), std::abs(end.z - 3419)) <= 1);
    }
}

TEST_CASE("WorldPathFinder leaves the essence mine by the portal back to the wizard who sent you in", "[RealCache]")
{
    constexpr auto MINE = NavPoint_s{.x = 2910, .z = 4832, .level = 0};
    constexpr auto AUBURY = NavPoint_s{.x = 3253, .z = 3401, .level = 0};
    constexpr auto SEDRIDOR = NavPoint_s{.x = 3106, .z = 9572, .level = 0};

    const auto landing = [&](const std::string& returnId)
    {
        auto state = MakeState(0);
        state.essenceExitReturn = returnId;
        const auto path = Find(MINE, {.x = 3253, .z = 3420, .level = 0}, state);
        REQUIRE(path.ok);
        const auto portal = std::ranges::find_if(path.waypoints, [](const NavWaypoint_s& waypoint)
        {
            return waypoint.edge != nullptr && waypoint.edge->locName == "Portal";
        });
        REQUIRE(portal != path.waypoints.end());
        return portal->point;
    };

    const auto aubury = landing("aubury");
    CHECK(std::max(std::abs(aubury.x - AUBURY.x), std::abs(aubury.z - AUBURY.z)) <= 2);

    const auto sedridor = landing("sedridor");
    CHECK(sedridor.level == SEDRIDOR.level);
    CHECK(std::max(std::abs(sedridor.x - SEDRIDOR.x), std::abs(sedridor.z - SEDRIDOR.z)) <= 2);
}

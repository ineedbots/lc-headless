#pragma once

#include "Type/NavEdge_s.hpp"
#include "Type/NavPoint_s.hpp"
#include "Type/NavRect_s.hpp"
#include "Type/NavState_s.hpp"
#include "Type/NavTeleport_s.hpp"
#include "Navigation.hpp"

#include <nlohmann/json.hpp>

// rs2b0t's PathPolicy: which kinds of hop a route may use.
struct NavPolicy_s
{
    // Teleports and the rest default to allowed when unset, as rs2b0t's do; the walker sets them.
    std::optional<bool> useTeleports;
    std::optional<bool> useShips;
    std::optional<bool> useShortcuts;
    // Below this Chebyshev distance from start to goal, no teleport is planned.
    s32 distanceBeforeTeleport = 0;
    std::vector<std::string> allowTeleportIds;
    std::vector<std::string> denyTeleportIds;
};

struct NavFindOptions_s
{
    static constexpr s32 MAX_EXPANSIONS = 1'200'000;

    // Door placements (x, z) to route round, after they refused.
    std::vector<std::pair<s32, s32>> avoidDoors;
    s32 maxExpansions = MAX_EXPANSIONS;
    // What the account has; without it, gated edges are planned regardless, as rs2b0t plans offline.
    std::optional<NavState_s> state;
    NavPolicy_s policy;
    // Whether to plan teleports from the start; it defaults to the policy's useTeleports.
    std::optional<bool> useTeleportCatalog;
    // Never entered, by a step or a landing, though a route may leave one it starts in.
    std::vector<NavRect_s> avoidZones;
};

struct NavWaypoint_s
{
    NavPoint_s point;
    // The hop that arrives here, if it's not a step.
    const NavEdge_s* edge = nullptr;
    // For a teleport, which leaves from wherever you are.
    const NavTeleport_s* teleport = nullptr;
};

struct NavPath_s
{
    bool ok = false;
    // Why the search failed: "unreachable", "start ... not walkable", "expansion budget exceeded (n)" and so on.
    std::string reason;
    std::vector<NavWaypoint_s> waypoints;
    s32 cost = 0;
    s32 expanded = 0;
};

inline void to_json(nlohmann::json& value, const NavWaypoint_s& waypoint)
{
    auto entry = nlohmann::json(waypoint.point);

    if (const auto* const edge = waypoint.edge)
    {
        auto transport = nlohmann::json{
            {"kind", edge->kind},
            {"loc_name", edge->locName},
            {"action", edge->action},
            {"loc_x", edge->locX},
            {"loc_z", edge->locZ},
            {"accept_any_landing", edge->acceptAnyLanding},
            {"edge_cost", edge->cost},
        };

        if (edge->locId)
        {
            transport["loc_id"] = *edge->locId;
        }

        if (edge->openLocId)
        {
            transport["open_loc_id"] = *edge->openLocId;
        }

        if (edge->toLevel)
        {
            transport["to_level"] = *edge->toLevel;
        }

        if (edge->toTile)
        {
            transport["to_tile"] = {edge->toTile->first, edge->toTile->second};
        }

        entry["transport"] = std::move(transport);
    }
    else if (const auto* const teleport = waypoint.teleport)
    {
        entry["transport"] = nlohmann::json{
            {"kind", "teleport"},
            {"loc_name", teleport->label},
            {"action", teleport->family == "spell" ? "Cast" : "Rub"},
            {"teleport_id", teleport->id},
            {"family", teleport->family},
            {"to_tile", {teleport->to.x, teleport->to.z}},
            {"accept_any_landing", true},
            {"edge_cost", teleport->cost},
        };
    }

    value = std::move(entry);
}

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(NavPath_s, ok, reason, cost, expanded, waypoints)

// A* by Chebyshev distance with the graph's hops as extra moves, falling back to Dijkstra when long hops would
// make the heuristic overestimate. A route's waypoints are its turns, the tiles either side of each hop, and its end.
class WorldPathFinder
{
public:
    WorldPathFinder() = delete;

    [[nodiscard]] static NavPath_s FindPath(const Navigation& navigation, NavPoint_s from, NavPoint_s to, const NavFindOptions_s& options);
    // The wilderness level at a tile, 0 outside it.
    [[nodiscard]] static s32 GetWildernessLevel(NavPoint_s tile);
};

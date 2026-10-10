#pragma once

#include "NavGraph.hpp"

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

// rs2b0t's PathFinder over WalkMap and NavGraph: A* by Chebyshev distance with the graph's hops as extra
// moves, falling back to Dijkstra when long hops would make the heuristic overestimate. It snaps the start
// and the goal to walkable tiles as rs2b0t's snapWalkable and goalCandidates do, so a booth or a furnace
// can be the goal. A route's waypoints are its turns, the tiles either side of each hop, and its end.
class WorldPathFinder
{
public:
    WorldPathFinder() = delete;

    [[nodiscard]] static NavPath_s FindPath(const Navigation_s& navigation, NavPoint_s from, NavPoint_s to, const NavFindOptions_s& options);
    // The wilderness level at a tile, 0 outside it.
    [[nodiscard]] static s32 GetWildernessLevel(NavPoint_s tile);
};

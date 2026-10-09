#pragma once

#include "../Tile_s.hpp"
#include "WorldMap.hpp"

enum class RouteKind_e : u8
{
    // Stop on the tile.
    Tile,
    // Stop where the wall or wall decor on the tile can be used.
    Wall,
    // Stop on or beside the width x length area whose south-west tile is the target.
    Area,
};

struct RouteTarget_s
{
    RouteKind_e kind = RouteKind_e::Tile;
    Tile_s tile;
    // Tile: when the tile can't be reached, stop on the reachable tile around it that's fewest steps away.
    bool tryNearest = false;
    // Wall: the loc's shape and angle.
    u8 shape = 0;
    u8 angle = 0;
    // Area: already turned for the loc's angle.
    u8 width = 1;
    u8 length = 1;
    u8 forceApproach = 0;
};

// The webclient's tryMove: a breadth-first search over the build area, so the server sees the waypoints
// a real client would send.
class PathFinder
{
public:
    static constexpr std::size_t MAX_WAYPOINTS = 25;

    PathFinder() = delete;

    // The waypoints the webclient would send: the turning points of a shortest route, from the first turn
    // after the start to the stop tile, as absolute tiles on the start's level, cut to MAX_WAYPOINTS. When
    // the start already reaches the target, the start is the one waypoint. nullopt when nothing reaches
    // the target, or when the start or the target is outside the build area.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindPath(const WorldMap& map, const Tile_s& start, const RouteTarget_s& target);
};

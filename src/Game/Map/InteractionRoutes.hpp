#pragma once

#include "../Tile_s.hpp"
#include "PathFinder.hpp"
#include "WorldMap.hpp"

// The routes the webclient walks for each kind of target, as waypoints to send. Nullopt when there's none.
class InteractionRoutes
{
public:
    InteractionRoutes() = delete;

    // To the tile, or else as near to it as can be reached.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindWalkRoute(const WorldMap& map, const Tile_s& start, const Tile_s& destination);
    // An NPC of any size, or a player, is reached as the 1x1 area on its tile.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindEntityRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile);
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindGroundItemRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile);
    // Also nullopt when the map has no loc with that id on the tile.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindLocRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile, u16 loc);
    // How the loc with that id on the tile is reached, or nullopt when the map has none there.
    [[nodiscard]] static std::optional<RouteTarget_s> FindLocTarget(const WorldMap& map, const Tile_s& tile, u16 loc);
    // The route to the first of the targets that has one.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindRoute(const WorldMap& map, const Tile_s& start, std::initializer_list<RouteTarget_s> targets);
};

#include "pch.hpp"
#include "InteractionRoutes.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/LocType_s.hpp"
#include "../Tile_s.hpp"
#include "LocShape.hpp"
#include "PathFinder.hpp"
#include "WorldMap.hpp"

namespace
{
    constexpr auto ANGLE_NORTH = u8{1};
    constexpr auto ANGLE_SOUTH = u8{3};
    constexpr auto SIDE_COUNT = 4;
    constexpr auto SIDE_MASK = 0xF;

    RouteTarget_s MakeAreaTarget(const Tile_s& tile, u8 width = 1, u8 length = 1, u8 forceApproach = 0)
    {
        return {.kind = RouteKind_e::Area, .tile = tile, .width = width, .length = length, .forceApproach = forceApproach};
    }

    // interactWithLoc turns the sides a loc forbids with the loc.
    u8 TurnForceApproach(u8 forceApproach, u8 angle)
    {
        if (angle == 0)
        {
            return forceApproach;
        }

        return static_cast<u8>(((forceApproach << angle) & SIDE_MASK) + (forceApproach >> (SIDE_COUNT - angle)));
    }

    // Centrepieces and ground decor are reached as an area of the type's size, and everything else as a wall.
    RouteTarget_s MakeLocTarget(const SceneLoc_s& loc, const LocType_s* type)
    {
        const auto isArea = loc.shape == LocShape::CENTREPIECE_STRAIGHT || loc.shape == LocShape::CENTREPIECE_DIAGONAL || loc.shape == LocShape::GROUND_DECOR;
        if (!isArea)
        {
            return {.kind = RouteKind_e::Wall, .tile = loc.tile, .shape = loc.shape, .angle = loc.angle};
        }

        if (type == nullptr)
        {
            return MakeAreaTarget(loc.tile);
        }

        const auto turned = loc.angle == ANGLE_NORTH || loc.angle == ANGLE_SOUTH;
        const auto width = turned ? type->length : type->width;
        const auto length = turned ? type->width : type->length;
        return MakeAreaTarget(loc.tile, width, length, TurnForceApproach(type->forceApproach, loc.angle));
    }
}

std::optional<std::vector<Tile_s>> InteractionRoutes::FindWalkRoute(const WorldMap& map, const Tile_s& start, const Tile_s& destination)
{
    return FindRoute(map, start, {{.kind = RouteKind_e::Tile, .tile = destination, .tryNearest = true}});
}

std::optional<std::vector<Tile_s>> InteractionRoutes::FindEntityRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile)
{
    return FindRoute(map, start, {MakeAreaTarget(tile)});
}

std::optional<std::vector<Tile_s>> InteractionRoutes::FindGroundItemRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile)
{
    return FindRoute(map, start, {{.kind = RouteKind_e::Tile, .tile = tile}, MakeAreaTarget(tile)});
}

std::optional<std::vector<Tile_s>> InteractionRoutes::FindLocRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile, u16 loc)
{
    const auto target = FindLocTarget(map, tile, loc);
    if (!target)
    {
        return std::nullopt;
    }

    return FindRoute(map, start, {*target});
}

std::optional<RouteTarget_s> InteractionRoutes::FindLocTarget(const WorldMap& map, const Tile_s& tile, u16 loc)
{
    for (const auto layer : WorldMap::LOC_LAYERS)
    {
        const auto scene = map.GetLoc(tile, layer);
        if (scene && scene->id == loc)
        {
            return MakeLocTarget(*scene, map.GetCache().FindLoc(loc));
        }
    }

    return std::nullopt;
}

std::optional<std::vector<Tile_s>> InteractionRoutes::FindRoute(const WorldMap& map, const Tile_s& start, std::initializer_list<RouteTarget_s> targets)
{
    for (const auto& target : targets)
    {
        if (auto route = PathFinder::FindPath(map, start, target))
        {
            return route;
        }
    }

    return std::nullopt;
}

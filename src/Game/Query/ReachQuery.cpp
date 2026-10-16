#include "pch.hpp"
#include "ReachQuery.hpp"

#include "../Map/InteractionRoutes.hpp"
#include "../Map/PathFinder.hpp"
#include "../Map/WorldMap.hpp"
#include "../State/GameState_s.hpp"
#include "../Tile_s.hpp"

ReachQuery::ReachQuery(const GameState_s& state, const WorldMap& map)
    : m_state{state}
    , m_map{map}
{
}

bool ReachQuery::CanReachEntity(const Tile_s& tile) const
{
    return InteractionRoutes::FindEntityRoute(m_map, GetPosition(), tile).has_value();
}

bool ReachQuery::CanReachGroundItem(const Tile_s& tile) const
{
    return InteractionRoutes::FindGroundItemRoute(m_map, GetPosition(), tile).has_value();
}

bool ReachQuery::CanReachLoc(const Tile_s& tile, u16 loc) const
{
    return InteractionRoutes::FindLocRoute(m_map, GetPosition(), tile, loc).has_value();
}

bool ReachQuery::IsReachable(const Tile_s& tile) const
{
    const auto target = RouteTarget_s{.kind = RouteKind_e::Tile, .tile = tile};
    return PathFinder::FindPath(m_map, GetPosition(), target).has_value();
}

bool ReachQuery::CanStep(const Tile_s& from, const Tile_s& to) const
{
    return PathFinder::CanStep(m_map, from, to);
}

std::optional<std::vector<Tile_s>> ReachQuery::FindPath(const Tile_s& tile) const
{
    return InteractionRoutes::FindWalkRoute(m_map, GetPosition(), tile);
}

const Tile_s& ReachQuery::GetPosition() const
{
    return m_state.localPlayer.tile;
}
